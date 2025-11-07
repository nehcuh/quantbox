"""
AsyncMarketDataService - 异步统一市场数据查询服务

提供统一的异步市场数据查询接口，自动选择合适的数据源（本地优先）
支持并发数据查询，显著提升性能。

性能提升：
- 自动选择最优数据源（本地/远程）
- 支持并发查询多个数据类型
- 异步 I/O 避免阻塞
- 智能回退机制

Python 3.14+ nogil 兼容性：
- 使用 asyncio 异步框架
- 无 GIL 依赖设计
"""

from typing import Optional, Union, List
import datetime
import pandas as pd

from quantbox.adapters.asynchronous.base import AsyncBaseDataAdapter
from quantbox.adapters.asynchronous.local_adapter import AsyncLocalAdapter
from quantbox.adapters.asynchronous.ts_adapter import AsyncTSAdapter
from quantbox.util.date_utils import DateLike


class AsyncMarketDataService:
    """
    异步市场数据服务

    统一的异步数据查询接口，支持：
    - 自动选择数据源（本地优先，远程备用）
    - 交易日历查询
    - 期货合约信息查询
    - 期货日线数据查询
    - 期货持仓数据查询
    - 股票列表查询

    与同步版本相比的优势：
    - 并发查询多个数据源/交易所
    - 非阻塞 I/O 操作
    - 更高的吞吐量

    示例:
        >>> import asyncio
        >>> from quantbox.services import AsyncMarketDataService
        >>>
        >>> async def main():
        >>>     service = AsyncMarketDataService()
        >>>
        >>>     # 查询交易日历
        >>>     calendar = await service.get_trade_calendar(
        >>>         exchanges=["SHFE", "DCE"],
        >>>         start_date="20240101",
        >>>         end_date="20241231"
        >>>     )
        >>>
        >>>     # 查询期货合约
        >>>     contracts = await service.get_future_contracts(
        >>>         exchanges="SHFE"
        >>>     )
        >>>
        >>>     # 查询期货持仓
        >>>     holdings = await service.get_future_holdings(
        >>>         exchanges=["SHFE", "DCE"],
        >>>         start_date="20240101",
        >>>         end_date="20240110"
        >>>     )
        >>>
        >>>     print(f"Calendar: {len(calendar)} records")
        >>>     print(f"Contracts: {len(contracts)} records")
        >>>     print(f"Holdings: {len(holdings)} records")
        >>>
        >>> asyncio.run(main())
    """

    def __init__(
        self,
        local_adapter: Optional[AsyncBaseDataAdapter] = None,
        remote_adapter: Optional[AsyncBaseDataAdapter] = None,
        prefer_local: bool = True
    ):
        """
        初始化异步市场数据服务

        Args:
            local_adapter: 本地异步数据适配器，默认使用 AsyncLocalAdapter
            remote_adapter: 远程异步数据适配器，默认使用 AsyncTSAdapter
            prefer_local: 是否优先使用本地数据源，默认为 True

        示例:
            >>> # 使用默认适配器
            >>> service = AsyncMarketDataService()
            >>>
            >>> # 自定义适配器
            >>> from quantbox.adapters.async import AsyncTSAdapter, AsyncLocalAdapter
            >>> service = AsyncMarketDataService(
            >>>     local_adapter=AsyncLocalAdapter(),
            >>>     remote_adapter=AsyncTSAdapter(max_concurrent=20),
            >>>     prefer_local=True
            >>> )
        """
        self.local_adapter = local_adapter or AsyncLocalAdapter()
        self.remote_adapter = remote_adapter or AsyncTSAdapter()
        self.prefer_local = prefer_local

    async def _get_adapter(self, use_local: Optional[bool] = None) -> AsyncBaseDataAdapter:
        """
        异步获取适配器

        根据配置和可用性自动选择合适的适配器。

        Args:
            use_local: 是否使用本地适配器，None 表示根据 prefer_local 自动选择

        Returns:
            适配器实例
        """
        if use_local is None:
            use_local = self.prefer_local

        if use_local:
            # 检查本地适配器是否可用
            if self.local_adapter and await self.local_adapter.check_availability():
                return self.local_adapter
            # 本地不可用，回退到远程
            return self.remote_adapter
        else:
            return self.remote_adapter

    async def get_trade_calendar(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        use_local: Optional[bool] = None
    ) -> pd.DataFrame:
        """
        异步获取交易日历

        Args:
            exchanges: 交易所代码或列表，None 表示所有交易所
            start_date: 起始日期
            end_date: 结束日期
            use_local: 是否使用本地数据源，None 表示自动选择

        Returns:
            交易日历 DataFrame，包含字段：
            - date: 日期（整数格式 YYYYMMDD）
            - exchange: 交易所代码
            - is_open: 是否开市

        示例:
            >>> service = AsyncMarketDataService()
            >>> calendar = await service.get_trade_calendar(
            >>>     exchanges=["SHFE", "DCE"],
            >>>     start_date="20240101",
            >>>     end_date="20241231"
            >>> )
        """
        adapter = await self._get_adapter(use_local)
        return await adapter.get_trade_calendar(
            exchanges=exchanges,
            start_date=start_date,
            end_date=end_date
        )

    async def get_future_contracts(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        symbols: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        date: Optional[DateLike] = None,
        use_local: Optional[bool] = None
    ) -> pd.DataFrame:
        """
        异步获取期货合约信息

        Args:
            exchanges: 交易所代码或列表
            symbols: 合约代码或列表
            spec_names: 品种名称或列表
            date: 查询日期（合约在该日期有效）
            use_local: 是否使用本地数据源，None 表示自动选择

        Returns:
            期货合约信息 DataFrame，包含字段：
            - symbol: 合约代码
            - exchange: 交易所代码
            - spec_name: 品种名称
            - name: 合约名称
            - list_date: 上市日期
            - delist_date: 退市日期

        示例:
            >>> service = AsyncMarketDataService()
            >>> contracts = await service.get_future_contracts(
            >>>     exchanges="SHFE",
            >>>     date="20240101"
            >>> )
        """
        adapter = await self._get_adapter(use_local)
        return await adapter.get_future_contracts(
            exchanges=exchanges,
            symbols=symbols,
            spec_names=spec_names,
            date=date
        )

    async def get_future_daily(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
        use_local: Optional[bool] = None
    ) -> pd.DataFrame:
        """
        异步获取期货日线数据

        Args:
            symbols: 合约代码或列表
            exchanges: 交易所代码或列表
            start_date: 起始日期（范围查询）
            end_date: 结束日期（范围查询）
            date: 单日查询日期
            use_local: 是否使用本地数据源，None 表示自动选择

        Returns:
            期货日线数据 DataFrame，包含字段：
            - symbol: 合约代码
            - exchange: 交易所代码
            - date: 日期（整数格式 YYYYMMDD）
            - open: 开盘价
            - high: 最高价
            - low: 最低价
            - close: 收盘价
            - volume: 成交量
            - amount: 成交金额
            - oi: 持仓量（可选）

        示例:
            >>> service = AsyncMarketDataService()
            >>> daily = await service.get_future_daily(
            >>>     exchanges="SHFE",
            >>>     start_date="20240101",
            >>>     end_date="20240131"
            >>> )
        """
        adapter = await self._get_adapter(use_local)
        return await adapter.get_future_daily(
            symbols=symbols,
            exchanges=exchanges,
            start_date=start_date,
            end_date=end_date,
            date=date
        )

    async def get_future_holdings(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
        use_local: Optional[bool] = None,
        show_progress: bool = False,
    ) -> pd.DataFrame:
        """
        异步获取期货持仓数据

        核心性能优化方法，支持大规模并发查询。

        Args:
            symbols: 合约代码或列表
            exchanges: 交易所代码或列表
            spec_names: 品种名称或列表
            start_date: 起始日期（范围查询）
            end_date: 结束日期（范围查询）
            date: 单日查询日期
            use_local: 是否使用本地数据源，None 表示自动选择
            show_progress: 是否显示进度条

        Returns:
            期货持仓数据 DataFrame，包含字段：
            - symbol: 合约代码
            - exchange: 交易所代码
            - date: 日期（整数格式 YYYYMMDD）
            - broker: 会员名称
            - vol: 成交量
            - vol_chg: 成交量变化
            - long_hld: 多头持仓
            - long_chg: 多头持仓变化
            - short_hld: 空头持仓
            - short_chg: 空头持仓变化

        示例:
            >>> service = AsyncMarketDataService()
            >>> holdings = await service.get_future_holdings(
            >>>     exchanges=["SHFE", "DCE"],
            >>>     start_date="20240101",
            >>>     end_date="20240110",
            >>>     show_progress=True
            >>> )
        """
        adapter = await self._get_adapter(use_local)
        return await adapter.get_future_holdings(
            symbols=symbols,
            exchanges=exchanges,
            spec_names=spec_names,
            start_date=start_date,
            end_date=end_date,
            date=date,
            show_progress=show_progress,
        )

    async def get_stock_list(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        names: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        markets: Optional[Union[str, List[str]]] = None,
        list_status: Union[str, List[str], None] = "L",
        is_hs: Optional[str] = None,
        use_local: Optional[bool] = None
    ) -> pd.DataFrame:
        """
        异步获取股票列表

        Args:
            symbols: 股票代码或列表（标准格式）
            names: 股票名称或列表
            exchanges: 交易所代码或列表（如 SSE, SZSE, BSE）
            markets: 市场板块或列表（如 主板, 创业板, 科创板, CDR, 北交所）
            list_status: 上市状态（'L' 上市, 'D' 退市, 'P' 暂停上市）
            is_hs: 沪港通状态（'N' 否, 'H' 沪股通, 'S' 深股通）
            use_local: 是否使用本地数据源，None 表示自动选择

        Returns:
            股票列表 DataFrame，包含字段：
            - symbol: 股票代码（标准格式）
            - name: 股票名称
            - exchange: 交易所代码
            - list_date: 上市日期
            - delist_date: 退市日期（可选）
            - industry: 所属行业
            - area: 地区

        示例:
            >>> service = AsyncMarketDataService()
            >>> stocks = await service.get_stock_list(
            >>>     exchanges=["SSE", "SZSE"],
            >>>     list_status="L"
            >>> )
        """
        adapter = await self._get_adapter(use_local)
        return await adapter.get_stock_list(
            symbols=symbols,
            names=names,
            exchanges=exchanges,
            markets=markets,
            list_status=list_status,
            is_hs=is_hs
        )

    def __del__(self):
        """清理资源"""
        # 清理适配器资源
        if hasattr(self, 'local_adapter') and hasattr(self.local_adapter, '__del__'):
            self.local_adapter.__del__()
        if hasattr(self, 'remote_adapter') and hasattr(self.remote_adapter, '__del__'):
            self.remote_adapter.__del__()
