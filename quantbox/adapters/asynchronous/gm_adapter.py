"""
AsyncGMAdapter - 掘金量化异步数据适配器

从掘金量化 API 异步获取市场数据，支持并发查询。

注意：掘金量化 API 不支持 macOS 系统

性能提升：
- 多合约并发查询：5-10倍
- 多日期并发查询：10-20倍

Python 3.14+ nogil 兼容性：
- 使用 asyncio + ThreadPoolExecutor
- 在 nogil 模式下可获得额外性能提升
"""

import warnings
import platform
import asyncio
from typing import Optional, Union, List
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

from quantbox.adapters.asynchronous.base import AsyncBaseDataAdapter
from quantbox.adapters.asynchronous.utils import RateLimiter, AsyncRetry
from quantbox.util.date_utils import DateLike, date_to_int, date_to_str
from quantbox.util.exchange_utils import (
    denormalize_exchange,
    validate_exchanges,
    normalize_exchange,
)
from quantbox.util.contract_utils import (
    normalize_contracts,
    format_contracts,
    ContractFormat,
)
from quantbox.config.config_loader import get_config_loader

# 根据平台导入掘金 API
if platform.system() != "Darwin":  # Not macOS
    try:
        from gm.api import (
            set_token,
            get_trading_dates_by_year,
            fut_get_transaction_rankings,
            history,
            get_symbol_infos,
        )

        GM_API_AVAILABLE = True
    except ImportError:
        GM_API_AVAILABLE = False
        warnings.warn(
            "掘金量化 SDK 未安装。请使用 'pip install gm' 安装。", ImportWarning
        )
else:
    GM_API_AVAILABLE = False
    warnings.warn("掘金量化 API 不支持 macOS 系统", UserWarning)


class AsyncGMAdapter(AsyncBaseDataAdapter):
    """
    掘金量化异步数据适配器

    从掘金量化 API 异步获取市场数据，支持并发查询。

    限制：
    - 不支持 macOS 系统
    - 不支持获取历史期货合约信息（API 限制）
    - 部分功能依赖本地 MongoDB（期货合约查询）

    性能优势：
    - 多合约并发查询
    - 多日期并发查询
    - 异步 I/O 操作

    示例:
        >>> import asyncio
        >>> from quantbox.adapters.async import AsyncGMAdapter
        >>>
        >>> async def main():
        >>>     adapter = AsyncGMAdapter()
        >>>     data = await adapter.get_future_holdings(
        >>>         exchanges=["SHFE", "DCE"],
        >>>         start_date="20240101",
        >>>         end_date="20241231"
        >>>     )
        >>>     print(f"Downloaded {len(data)} records")
        >>>
        >>> asyncio.run(main())
    """

    def __init__(
        self,
        token=None,
        max_concurrent: int = 10,
        rate_limit: float = 10.0,
        max_workers: int = 4,
    ):
        """
        初始化 AsyncGMAdapter

        Args:
            token: 掘金量化 API token，默认使用配置文件中的 token
            max_concurrent: 最大并发请求数
            rate_limit: 每秒最大请求数
            max_workers: ThreadPoolExecutor 工作线程数

        Raises:
            NotImplementedError: 在 macOS 系统上使用时
            ImportError: 掘金 SDK 未安装时
        """
        super().__init__("AsyncGMAdapter")

        # 检查平台支持
        if platform.system() == "Darwin":
            raise NotImplementedError(
                "掘金量化 API 不支持 macOS 系统。请使用其他数据源或在 Linux/Windows 上运行。"
            )

        if not GM_API_AVAILABLE:
            raise ImportError("掘金量化 SDK 未安装。请使用 'pip install gm' 安装。")

        # 获取并设置 token
        self.gm_token = token or self._get_token_from_config()
        if not self.gm_token:
            warnings.warn(
                "掘金量化 API token 未配置，AsyncGMAdapter 将无法使用。"
                "请在配置文件中设置 GM.token 或在初始化时传入 token 参数。",
                UserWarning,
            )
        else:
            set_token(self.gm_token)

        # 并发控制
        self.max_concurrent = max_concurrent
        self.rate_limiter = RateLimiter(calls_per_second=rate_limit, burst=20)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 创建同步适配器实例用于在线程池中执行
        from quantbox.adapters.gm_adapter import GMAdapter
        self.sync_adapter = GMAdapter(token=self.gm_token)

        # 获取配置
        config_loader = get_config_loader()
        self.exchanges = config_loader.list_exchanges()
        self.future_exchanges = config_loader.list_exchanges(market_type="futures")
        self.stock_exchanges = config_loader.list_exchanges(market_type="stock")

        # MongoDB 客户端（用于查询本地合约信息）
        try:
            from motor import motor_asyncio

            mongodb_uri = config_loader.get("mongodb", {}).get(
                "uri", "mongodb://localhost:27017"
            )
            self.mongodb_client = motor_asyncio.AsyncIOMotorClient(mongodb_uri)
            self.db = self.mongodb_client.quantbox
        except Exception:
            self.db = None
            warnings.warn("无法连接到 MongoDB，某些功能可能不可用", UserWarning)

    def _get_token_from_config(self):
        """从配置文件获取 token"""
        try:
            return get_config_loader().get_gm_token()
        except Exception:
            return None

    async def check_availability(self) -> bool:
        """异步检查掘金 API 是否可用"""
        try:
            loop = asyncio.get_running_loop()
            # 尝试获取交易日
            await loop.run_in_executor(
                self.executor, get_trading_dates_by_year, 2024
            )
            return True
        except Exception:
            return False

    @AsyncRetry(max_attempts=3, backoff_factor=2.0)
    async def _fetch_trading_dates(self, year: int) -> list:
        """
        异步获取交易日

        Args:
            year: 年份

        Returns:
            交易日列表
        """
        async with self.rate_limiter:
            loop = asyncio.get_running_loop()
            dates = await loop.run_in_executor(
                self.executor, get_trading_dates_by_year, year
            )
            return dates

    async def get_trade_calendar(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        异步获取交易日历

        掘金 API 只提供年度交易日，不区分交易所。

        Args:
            exchanges: 交易所代码或列表（掘金 API 不区分交易所）
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            交易日历 DataFrame
        """
        try:
            if exchanges is None:
                exchanges = self.exchanges
            elif isinstance(exchanges, str):
                exchanges = [exchanges]

            # 确定年份范围
            if start_date:
                start_year = int(str(date_to_int(start_date))[:4])
            else:
                start_year = 2020

            if end_date:
                end_year = int(str(date_to_int(end_date))[:4])
            else:
                end_year = datetime.datetime.now().year

            # 并发获取所有年份的交易日
            tasks = [
                self._fetch_trading_dates(year)
                for year in range(start_year, end_year + 1)
            ]
            results = await asyncio.gather(*tasks)

            # 合并所有年份的交易日
            all_dates = []
            for dates in results:
                all_dates.extend(dates)

            # 创建 DataFrame
            records = []
            for exchange in exchanges:
                for date in all_dates:
                    date_int = int(date.strftime("%Y%m%d"))
                    # 过滤日期范围
                    if start_date and date_int < date_to_int(start_date):
                        continue
                    if end_date and date_int > date_to_int(end_date):
                        continue

                    records.append(
                        {"date": date_int, "exchange": exchange, "is_open": True}
                    )

            if not records:
                return pd.DataFrame(columns=["date", "exchange", "is_open"])

            return pd.DataFrame(records)

        except Exception as e:
            raise Exception(f"获取交易日历失败: {str(e)}")

    async def get_future_contracts(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        symbols: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        异步获取期货合约信息

        注意：掘金 API 不提供历史合约查询，这里从本地 MongoDB 查询。

        Args:
            exchanges: 交易所代码或列表
            symbols: 合约代码或列表
            spec_names: 品种名称或列表
            date: 查询日期

        Returns:
            期货合约信息 DataFrame
        """
        if not self.db:
            raise Exception("MongoDB 未连接，无法查询合约信息")

        try:
            # 使用 AsyncLocalAdapter 查询
            from quantbox.adapters.asynchronous.local_adapter import AsyncLocalAdapter

            local_adapter = AsyncLocalAdapter(database=self.db)
            return await local_adapter.get_future_contracts(
                exchanges=exchanges, symbols=symbols, spec_names=spec_names, date=date
            )

        except Exception as e:
            raise Exception(f"获取期货合约信息失败: {str(e)}")

    @AsyncRetry(max_attempts=3, backoff_factor=2.0)
    async def _fetch_transaction_rankings(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        异步获取单个合约的持仓排名

        Args:
            symbol: 合约代码（掘金格式）
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            持仓数据 DataFrame
        """
        async with self.rate_limiter:
            loop = asyncio.get_running_loop()
            df = await loop.run_in_executor(
                self.executor,
                lambda: fut_get_transaction_rankings(symbol, start_date, end_date),
            )
            return df

    async def get_future_holdings(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
        show_progress: bool = False,
    ) -> pd.DataFrame:
        """
        异步获取期货持仓数据

        Args:
            symbols: 合约代码或列表
            exchanges: 交易所代码或列表
            spec_names: 品种名称或列表
            start_date: 开始日期
            end_date: 结束日期
            date: 单日查询
            show_progress: 是否显示进度条

        Returns:
            期货持仓数据 DataFrame
        """
        try:
            # 参数验证
            self._validate_date_range(start_date, end_date, date)

            # 处理日期
            if date:
                start_str = date_to_str(date)
                end_str = date_to_str(date)
            else:
                if start_date is None:
                    raise ValueError("必须指定 date 或 start_date")
                start_str = date_to_str(start_date)
                end_str = (
                    date_to_str(end_date) if end_date else date_to_str(datetime.datetime.today())
                )

            # 获取合约列表
            if symbols:
                if isinstance(symbols, str):
                    symbols = [symbols]
                # 转换为掘金格式
                gm_symbols = format_contracts(symbols, ContractFormat.GM)
            else:
                # 从数据库获取合约列表
                contracts_df = await self.get_future_contracts(
                    exchanges=exchanges, spec_names=spec_names
                )
                if contracts_df.empty:
                    return pd.DataFrame(
                        columns=[
                            "symbol",
                            "exchange",
                            "date",
                            "broker",
                            "vol",
                            "vol_chg",
                            "long_hld",
                            "long_chg",
                            "short_hld",
                            "short_chg",
                        ]
                    )
                gm_symbols = format_contracts(
                    contracts_df["symbol"].tolist(), ContractFormat.GM
                )

            # 并发获取所有合约的持仓数据
            semaphore = asyncio.Semaphore(self.max_concurrent)

            async def fetch_with_limit(symbol):
                async with semaphore:
                    try:
                        return await self._fetch_transaction_rankings(
                            symbol, start_str, end_str
                        )
                    except Exception:
                        return pd.DataFrame()

            if show_progress:
                from tqdm.asyncio import tqdm as async_tqdm

                tasks = [fetch_with_limit(symbol) for symbol in gm_symbols]
                results = []
                for coro in async_tqdm(
                    asyncio.as_completed(tasks),
                    total=len(tasks),
                    desc="异步获取期货持仓",
                ):
                    result = await coro
                    results.append(result)
            else:
                results = await asyncio.gather(
                    *[fetch_with_limit(symbol) for symbol in gm_symbols]
                )

            # 合并结果
            all_data = [df for df in results if not df.empty]
            if not all_data:
                return pd.DataFrame(
                    columns=[
                        "symbol",
                        "exchange",
                        "date",
                        "broker",
                        "vol",
                        "vol_chg",
                        "long_hld",
                        "long_chg",
                        "short_hld",
                        "short_chg",
                    ]
                )

            result = pd.concat(all_data, ignore_index=True)

            # 数据处理
            # 标准化合约代码
            result["symbol"] = result["symbol"].apply(
                lambda x: normalize_contracts(x, format=ContractFormat.DEFAULT)[0]
                if x
                else None
            )

            # 添加交易所信息
            result["exchange"] = result["symbol"].apply(
                lambda x: x.split(".")[0] if "." in str(x) else None
            )

            return result

        except Exception as e:
            raise Exception(f"获取期货持仓数据失败: {str(e)}")

    async def get_future_daily(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
        show_progress: bool = False,
    ) -> pd.DataFrame:
        """
        异步获取期货日线数据

        Args:
            symbols: 合约代码或列表（标准格式）
            exchanges: 交易所代码或列表
            start_date: 开始日期
            end_date: 结束日期
            date: 单日查询
            show_progress: 显示进度条（掘金API不支持，此参数被忽略）

        Returns:
            期货日线数据 DataFrame

        Note:
            掘金API要求必须指定symbols参数，不支持按交易所批量下载
        """
        loop = asyncio.get_event_loop()

        # 使用lambda包装函数调用以传递参数
        def sync_call():
            return self.sync_adapter.get_future_daily(
                symbols=symbols,
                exchanges=exchanges,
                start_date=start_date,
                end_date=end_date,
                date=date,
                show_progress=show_progress,
            )

        return await loop.run_in_executor(self.executor, sync_call)

    async def get_stock_list(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        names: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        markets: Optional[Union[str, List[str]]] = None,
        list_status: Union[str, List[str], None] = "L",
        is_hs: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        异步获取股票列表

        注意：掘金 API 功能有限，建议使用 AsyncTSAdapter。

        Returns:
            股票列表 DataFrame
        """
        raise NotImplementedError("建议使用 AsyncTSAdapter 获取股票列表")

    def __del__(self):
        """清理资源"""
        if hasattr(self, "executor"):
            self.executor.shutdown(wait=False)
        if hasattr(self, "mongodb_client"):
            self.mongodb_client.close()
