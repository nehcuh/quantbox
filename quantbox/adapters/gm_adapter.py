"""
GMAdapter - 掘金量化数据适配器

从掘金量化 API 获取市场数据

注意：掘金量化 API 不支持 macOS 系统
"""

import warnings
import platform
import re
import datetime
from typing import Optional, Union, List
import pandas as pd

from quantbox.adapters.base import BaseDataAdapter
from quantbox.util.date_utils import DateLike, date_to_int, date_to_str
from quantbox.util.exchange_utils import denormalize_exchange, validate_exchanges, normalize_exchange
from quantbox.util.contract_utils import normalize_contracts, format_contracts, ContractFormat
from quantbox.config.config_loader import get_config_loader

# 根据平台导入掘金 API
if platform.system() != 'Darwin':  # Not macOS
    try:
        from gm.api import (
            set_token,
            get_trading_dates_by_year,
            fut_get_transaction_rankings,
            history,
            get_symbol_infos
        )
        GM_API_AVAILABLE = True
    except ImportError:
        GM_API_AVAILABLE = False
        warnings.warn(
            "掘金量化 SDK 未安装。请使用 'pip install gm' 安装。",
            ImportWarning
        )
else:
    GM_API_AVAILABLE = False
    warnings.warn("掘金量化 API 不支持 macOS 系统", UserWarning)


class GMAdapter(BaseDataAdapter):
    """
    掘金量化数据适配器

    从掘金量化 API 获取市场数据。

    限制：
    - 不支持 macOS 系统
    - 不支持获取历史期货合约信息（API 限制）
    - 不支持获取期货日线数据（建议使用 TSAdapter）
    """

    def __init__(self, token=None):
        """
        初始化 GMAdapter

        Args:
            token: 掘金量化 API token，默认使用配置文件中的 token

        Raises:
            NotImplementedError: 在 macOS 系统上使用时
        """
        super().__init__("GMAdapter")

        # 检查平台支持
        if platform.system() == 'Darwin':
            raise NotImplementedError(
                "掘金量化 API 不支持 macOS 系统。"
                "请使用其他数据源或在 Linux/Windows 上运行。"
            )

        if not GM_API_AVAILABLE:
            raise ImportError(
                "掘金量化 SDK 未安装。请使用 'pip install gm' 安装。"
            )

        # 获取并设置 token
        self.gm_token = token or self._get_token_from_config()
        if not self.gm_token:
            warnings.warn(
                "掘金量化 API token 未配置，GMAdapter 将无法使用。"
                "请在配置文件中设置 GM.token 或在初始化时传入 token 参数。",
                UserWarning
            )
        else:
            set_token(self.gm_token)

        # 获取配置
        config_loader = get_config_loader()
        self.exchanges = config_loader.list_exchanges()
        self.future_exchanges = config_loader.list_exchanges(market_type='futures')
        self.stock_exchanges = config_loader.list_exchanges(market_type='stock')

        # MongoDB 客户端（用于查询本地合约信息）
        try:
            self.mongodb_client = config_loader.get_mongodb_client()
            self.db = self.mongodb_client.quantbox
        except Exception:
            self.mongodb_client = None
            self.db = None
            warnings.warn("MongoDB 连接失败，部分功能可能受限", UserWarning)

    def _get_token_from_config(self) -> Optional[str]:
        """从配置文件获取掘金量化 token"""
        try:
            config_loader = get_config_loader()
            return config_loader.get_gm_token()
        except Exception:
            return None

    def check_availability(self) -> bool:
        """检查掘金量化 API 是否可用"""
        if not self.gm_token or not GM_API_AVAILABLE:
            return False

        try:
            # 尝试获取一个简单的查询来验证 token
            result = get_trading_dates_by_year(
                exchange='SHSE',
                start_year=2025,
                end_year=2025
            )
            return result is not None and not result.empty
        except Exception:
            return False

    def _format_contract_by_exchange(self, exchange: str, contract: str) -> str:
        """
        根据交易所规则格式化合约代码

        Args:
            exchange: 交易所代码
            contract: 合约代码

        Returns:
            str: 格式化后的合约代码（如 SHFE.rb2501）
        """
        if exchange in ["CFFEX", "CZCE"]:
            # 中金所和郑商所使用大写
            if exchange == "CZCE":
                # 郑商所期货合约使用3位年月格式
                if len(contract) > 4 and contract[2:6].isdigit():
                    # 将4位年月转换为3位年月 (如 2501 -> 501)
                    contract = contract[:2] + contract[3:]
                return f"{exchange}.{contract.upper()}"
            else:
                return f"{exchange}.{contract.upper()}"
        else:
            # 上期所、大商所、上期能源、广期所使用小写
            return f"{exchange}.{contract.lower()}"

    def _format_symbol_to_gm(self, symbol: str) -> str:
        """
        将合约代码格式化为掘金量化 API 格式

        Args:
            symbol: 合约代码（如 "rb2501" 或 "SHFE.rb2501"）

        Returns:
            str: 掘金格式的合约代码（如 "SHFE.rb2501"）
        """
        # 如果已经有交易所前缀，直接格式化返回
        if '.' in symbol:
            exchange, contract = symbol.split(".", 1)
            return self._format_contract_by_exchange(exchange, contract)

        # 提取品种代码
        fut_code = re.match(r'([A-Za-z]+)', symbol).group(1).upper()

        # 从本地数据库查询交易所
        if self.db:
            coll = self.db.future_contracts
            result = coll.find_one({'fut_code': fut_code})
            if result:
                exchange = result["exchange"]
                return self._format_contract_by_exchange(exchange, symbol)

        # 如果查询失败，抛出错误
        raise ValueError(f"无法找到合约 {symbol} 的交易所信息")

    def get_trade_calendar(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """从掘金量化获取交易日历

        Args:
            exchanges: 交易所代码（标准格式）或列表，None 表示所有交易所
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame包含以下列：
            - date: 日期（int，YYYYMMDD格式）
            - exchange: 交易所代码（标准格式）
            - is_open: 是否交易日（bool）
        """
        try:
            # 验证并标准化交易所参数
            if exchanges is None:
                exchanges = self.exchanges
            elif isinstance(exchanges, str):
                exchanges = [exchanges]

            exchanges = validate_exchanges(exchanges, "all")

            # 标准化日期
            if start_date:
                start_dt = pd.Timestamp(date_to_str(start_date))
            else:
                start_dt = pd.Timestamp("2010-01-01")

            if end_date:
                end_dt = pd.Timestamp(date_to_str(end_date))
            else:
                end_dt = pd.Timestamp(f"{datetime.date.today().year}-12-31")

            if start_dt > end_dt:
                raise ValueError(f"起始日期 ({start_dt}) 必须早于结束日期 ({end_dt})")

            # 获取每个交易所的交易日历
            results = []
            for exchange in exchanges:
                # 转换交易所代码为掘金格式
                gm_exchange = denormalize_exchange(exchange, "goldminer")

                try:
                    # 获取交易日期
                    dates_df = get_trading_dates_by_year(
                        exchange=gm_exchange,
                        start_year=start_dt.year,
                        end_year=end_dt.year
                    )

                    if dates_df is None or dates_df.empty:
                        continue

                    # 创建标准格式的 DataFrame
                    # 过滤掉 trade_date 为空的记录
                    dates_df = dates_df[dates_df['trade_date'].notna()].copy()

                    df = pd.DataFrame()
                    df['date'] = pd.to_datetime(dates_df['trade_date']).dt.strftime('%Y%m%d').astype(int)
                    df['exchange'] = normalize_exchange(gm_exchange)
                    df['is_open'] = True

                    # 过滤日期范围
                    start_int = date_to_int(start_date) if start_date else 19900101
                    end_int = date_to_int(end_date) if end_date else 99991231
                    df = df[(df['date'] >= start_int) & (df['date'] <= end_int)]

                    results.append(df)

                except Exception as e:
                    warnings.warn(f"获取交易所 {exchange} 的交易日历失败: {str(e)}")
                    continue

            if not results:
                return pd.DataFrame(columns=['date', 'exchange', 'is_open'])

            # 合并结果
            result_df = pd.concat(results, ignore_index=True)
            return result_df[['date', 'exchange', 'is_open']].sort_values(['exchange', 'date']).reset_index(drop=True)

        except Exception as e:
            raise Exception(f"获取交易日历失败: {str(e)}")

    def get_future_contracts(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        symbols: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """从掘金量化获取期货合约信息

        注意：掘金量化 API 不支持获取历史合约信息，此方法返回空 DataFrame

        Args:
            exchanges: 交易所代码或列表
            symbols: 合约代码或列表（标准格式：EXCHANGE.symbol）
            spec_names: 品种名称或列表（如 rb, m, SR等）
            date: 查询日期，None 表示最新

        Returns:
            空 DataFrame（掘金 API 不支持此功能）
        """
        warnings.warn(
            "掘金量化 API 不支持获取历史期货合约信息。"
            "请使用 TSAdapter 或 LocalAdapter 获取合约信息。",
            UserWarning
        )
        return pd.DataFrame()

    def get_future_daily(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
        show_progress: bool = False,
    ) -> pd.DataFrame:
        """从掘金量化获取期货日线数据

        注意：此方法使用掘金的 history_n API

        Args:
            symbols: 合约代码或列表（标准格式）
            exchanges: 交易所代码或列表
            start_date: 开始日期
            end_date: 结束日期
            date: 单日查询（与 start_date/end_date 互斥）

        Returns:
            DataFrame包含日线数据
        """
        try:
            # 验证日期参数
            if date:
                start_date = end_date = date

            if not start_date:
                start_date = "2010-01-01"
            if not end_date:
                end_date = datetime.date.today().strftime("%Y-%m-%d")

            start_str = date_to_str(start_date)
            end_str = date_to_str(end_date)

            # 处理合约代码
            if not symbols:
                raise ValueError("必须指定 symbols 参数")

            if isinstance(symbols, str):
                symbols = [symbols]

            # 转换为掘金格式
            gm_symbols = []
            for symbol in symbols:
                try:
                    gm_symbol = self._format_symbol_to_gm(symbol)
                    gm_symbols.append(gm_symbol)
                except ValueError as e:
                    warnings.warn(f"跳过无效合约 {symbol}: {str(e)}")
                    continue

            if not gm_symbols:
                return pd.DataFrame()

            # 获取日线数据
            all_data = []
            for gm_symbol in gm_symbols:
                try:
                    data = history(
                        symbol=gm_symbol,
                        frequency='1d',
                        start_time=start_str,
                        end_time=end_str,
                        fields='symbol,eob,open,high,low,close,volume,amount,position',
                        adjust=0,  # 不复权
                        df=True
                    )

                    if data is not None and not data.empty:
                        # 转换为标准格式
                        df = pd.DataFrame()
                        df['date'] = pd.to_datetime(data['eob']).dt.strftime('%Y%m%d').astype(int)

                        # 提取交易所和合约代码
                        exchange, contract = data['symbol'].iloc[0].split('.', 1)
                        df['symbol'] = contract.upper()
                        df['exchange'] = normalize_exchange(exchange)

                        df['open'] = data['open']
                        df['high'] = data['high']
                        df['low'] = data['low']
                        df['close'] = data['close']
                        df['volume'] = data['volume']
                        df['amount'] = data['amount']
                        df['oi'] = data['position']

                        all_data.append(df)

                except Exception as e:
                    warnings.warn(f"获取合约 {gm_symbol} 数据失败: {str(e)}")
                    continue

            if not all_data:
                return pd.DataFrame()

            # 合并所有数据
            result_df = pd.concat(all_data, ignore_index=True)
            return result_df.sort_values(['symbol', 'date']).reset_index(drop=True)

        except Exception as e:
            raise Exception(f"获取期货日线数据失败: {str(e)}")

    def get_future_holdings(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """从掘金量化获取期货持仓数据

        Args:
            symbols: 合约代码或列表（标准格式）
            exchanges: 交易所代码或列表
            spec_names: 品种名称或列表
            start_date: 开始日期
            end_date: 结束日期
            date: 单日查询（与 start_date/end_date 互斥）

        Returns:
            DataFrame包含持仓数据：
            - date: 日期（int，YYYYMMDD格式）
            - symbol: 合约代码
            - exchange: 交易所
            - broker: 席位名称
            - vol: 成交量
            - vol_chg: 成交量变化
            - long_hld: 多头持仓
            - long_chg: 多头持仓变化
            - short_hld: 空头持仓
            - short_chg: 空头持仓变化
        """
        try:
            # 验证日期参数
            if date:
                query_date = date_to_str(date)
            elif end_date:
                query_date = date_to_str(end_date)
            else:
                query_date = datetime.date.today().strftime("%Y-%m-%d")

            # 处理合约代码或交易所
            if symbols:
                # 指定了合约代码
                if isinstance(symbols, str):
                    symbols = [symbols]

                # 转换为掘金格式
                gm_symbols = []
                for symbol in symbols:
                    try:
                        gm_symbol = self._format_symbol_to_gm(symbol)
                        gm_symbols.append(gm_symbol)
                    except ValueError as e:
                        warnings.warn(f"跳过无效合约 {symbol}: {str(e)}")
                        continue

            elif exchanges:
                # 通过交易所查询，需要从本地数据库获取合约列表
                if isinstance(exchanges, str):
                    exchanges = [exchanges]

                exchanges = validate_exchanges(exchanges, "futures")

                if not self.db:
                    raise ValueError("MongoDB 未连接，无法通过交易所查询持仓数据")

                # 从本地数据库获取合约列表
                gm_symbols = []
                for exchange in exchanges:
                    contracts = self.db.future_contracts.find(
                        {
                            'exchange': exchange,
                            'list_date': {'$lte': query_date},
                            'delist_date': {'$gte': query_date}
                        }
                    )
                    for contract in contracts:
                        symbol_str = contract['exchange'] + '.' + contract['symbol']
                        gm_symbol = self._format_symbol_to_gm(symbol_str)
                        gm_symbols.append(gm_symbol)

            else:
                raise ValueError("必须指定 symbols 或 exchanges 参数")

            if not gm_symbols:
                return pd.DataFrame()

            # 分批获取持仓数据（API 限制每次最多 50 个合约）
            all_holdings = []
            batch_size = 50

            for i in range(0, len(gm_symbols), batch_size):
                batch_symbols = gm_symbols[i:i + batch_size]

                try:
                    holdings = fut_get_transaction_rankings(
                        symbols=batch_symbols,
                        trade_date=query_date,
                        indicators="volume,long,short"
                    )

                    if holdings is not None and not holdings.empty:
                        all_holdings.append(holdings)

                except Exception as e:
                    warnings.warn(f"获取持仓数据失败（批次 {i//batch_size + 1}）: {str(e)}")
                    continue

            if not all_holdings:
                return pd.DataFrame()

            # 合并所有批次的数据
            total_holdings = pd.concat(all_holdings, ignore_index=True)

            # 转换为标准格式
            return self._convert_gm_holdings_to_standard_format(total_holdings)

        except Exception as e:
            raise Exception(f"获取期货持仓数据失败: {str(e)}")

    def _convert_gm_holdings_to_standard_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        将掘金持仓数据格式转换为标准格式

        Args:
            df: 掘金持仓数据

        Returns:
            标准格式的持仓数据
        """
        if df.empty:
            return pd.DataFrame()

        # 移除交易所前缀和经纪商名称中的标记
        df['symbol'] = df['symbol'].str.split('.').str[1].str.upper()
        df['exchange'] = df['symbol'].apply(lambda x: x.split(".")[0]) if '.' in df['symbol'].iloc[0] else df['symbol'].apply(lambda x: self._get_exchange_from_symbol(x))
        df['broker'] = df['member_name'].str.replace('（代客）', '')

        # 分离成交量、多头、空头数据
        vol_df = df[df['indicator'] == 'volume'].copy()
        long_df = df[df['indicator'] == 'long'].copy()
        short_df = df[df['indicator'] == 'short'].copy()

        # 重命名列
        vol_df = vol_df.rename(columns={
            'indicator_number': 'vol',
            'indicator_change': 'vol_chg'
        })[['trade_date', 'symbol', 'broker', 'vol', 'vol_chg', 'exchange']]

        long_df = long_df.rename(columns={
            'indicator_number': 'long_hld',
            'indicator_change': 'long_chg'
        })[['trade_date', 'symbol', 'broker', 'long_hld', 'long_chg']]

        short_df = short_df.rename(columns={
            'indicator_number': 'short_hld',
            'indicator_change': 'short_chg'
        })[['trade_date', 'symbol', 'broker', 'short_hld', 'short_chg']]

        # 合并数据
        result = pd.merge(vol_df, long_df, on=['trade_date', 'symbol', 'broker'], how='outer')
        result = pd.merge(result, short_df, on=['trade_date', 'symbol', 'broker'], how='outer')

        # 标准化日期格式
        result['date'] = pd.to_datetime(result['trade_date']).dt.strftime('%Y%m%d').astype(int)

        # 确保数值列为 float 类型
        numeric_columns = ['vol', 'vol_chg', 'long_hld', 'long_chg', 'short_hld', 'short_chg']
        for col in numeric_columns:
            if col in result.columns:
                result[col] = result[col].astype(float)

        # 规范化交易所代码
        result['exchange'] = result['exchange'].apply(lambda x: normalize_exchange(x) if pd.notna(x) else x)

        # 排序并选择最终列
        result = result.sort_values(['date', 'symbol', 'vol'], ascending=[True, True, False])

        columns = ['date', 'symbol', 'broker', 'vol', 'vol_chg', 'long_hld', 'long_chg', 'short_hld', 'short_chg', 'exchange']
        return result[columns].reset_index(drop=True)

    def _get_exchange_from_symbol(self, symbol: str) -> str:
        """从合约代码推断交易所（辅助方法）"""
        if self.db:
            fut_code = re.match(r'([A-Za-z]+)', symbol).group(1).upper()
            result = self.db.future_contracts.find_one({'fut_code': fut_code})
            if result:
                return result['exchange']
        return ""

    def get_stock_list(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        names: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        markets: Optional[Union[str, List[str]]] = None,
        list_status: Union[str, List[str], None] = "L",
        is_hs: Optional[str] = None,
    ) -> pd.DataFrame:
        """从掘金量化获取股票列表

        注意：此功能需要掘金 API 支持，当前返回空 DataFrame

        Args:
            symbols: 股票代码或列表（标准格式）
            names: 股票名称或列表
            exchanges: 交易所代码或列表（如 SSE, SZSE, BSE）
            markets: 市场板块或列表（如 主板, 创业板, 科创板, CDR, 北交所）
            list_status: 上市状态（'L' 上市, 'D' 退市, 'P' 暂停上市）
            is_hs: 沪港通状态（'N' 否, 'H' 沪股通, 'S' 深股通）

        Returns:
            DataFrame包含股票信息
        """
        warnings.warn(
            "掘金量化 API 的股票列表查询功能尚未实现。"
            "请使用 TSAdapter 获取股票列表。",
            UserWarning
        )
        return pd.DataFrame()


# 为了保持向后兼容，提供别名
GoldminerAdapter = GMAdapter
