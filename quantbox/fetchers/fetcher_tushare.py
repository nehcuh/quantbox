import datetime
import re
from typing import List, Optional, Union

import pandas as pd

from quantbox.fetchers.base import BaseFetcher
from quantbox.util.basic import (
    DATABASE,
    DEFAULT_START,
    EXCHANGES,
    FUTURE_EXCHANGES,
    STOCK_EXCHANGES,
    TSPRO,
)
from quantbox.util.tools import (
    util_format_future_symbols,
    util_format_stock_symbols,
    util_make_date_stamp,
)


class TSFetcher(BaseFetcher):
    """
    TuShare data fetcher implementation.
    基于 Tushare 的数据获取实现。

    This class provides methods to fetch various financial data from TuShare API, including:
    提供从 Tushare API 获取各种金融数据的方法，包括：

    - Trading dates / 交易日历
    - Future contracts / 期货合约
    - Stock listings / 股票列表
    - Holdings data / 持仓数据
    - Daily market data / 日线行情

    Attributes:
        pro: TuShare API client / Tushare API 客户端
        exchanges: List of supported exchanges / 支持的交易所列表
        stock_exchanges: List of supported stock exchanges / 支持的股票交易所列表
        future_exchanges: List of supported future exchanges / 支持的期货交易所列表
        client: Database client / 数据库客户端
        default_start: Default start date / 默认起始日期
    """

    def __init__(self):
        """
        Initialize TuShare fetcher with API client and configuration.
        初始化 Tushare 数据获取器，设置 API 客户端和配置。
        """
        super().__init__()
        self.pro = TSPRO
        self.exchanges = EXCHANGES
        self.stock_exchanges = STOCK_EXCHANGES
        self.future_exchanges = FUTURE_EXCHANGES
        self.client = DATABASE
        self.default_start = DEFAULT_START

    def initialize(self):
        """
        Initialize the fetcher with necessary credentials and settings.
        使用必要的凭证和设置初始化获取器。
        """
        # TuShare API client is already initialized in __init__
        # Tushare API 客户端已经在 __init__ 中初始化
        pass

    def fetch_get_trade_dates(
        self,
        exchanges: Union[List[str], str, None] = None,
        start_date: Union[str, datetime.date, int, None] = None,
        end_date: Union[str, datetime.date, int, None] = None,
    ) -> pd.DataFrame:
        """
        Fetch trading dates for specified exchanges within a date range.
        获取指定交易所的日期范围内的交易日。

        Args:
            exchanges: Exchange(s) to fetch data from, defaults to all exchanges
                     要获取数据的交易所，默认为所有交易所
                Supported: ['SSE', 'SZSE', 'SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
                支持: ['SSE', 'SZSE', 'SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
            start_date: Start date, defaults to DEFAULT_START
                       起始时间，默认从 DEFAULT_START 开始
                Formats: [19910906, '1992-03-02', datetime.date(2024, 9, 16)]
                支持格式: [19910906, '1992-03-02', datetime.date(2024, 9, 16)]
            end_date: End date, defaults to current year end
                     截止时间，默认截止为当前年底
                Formats: [19910906, '1992-03-02', datetime.date(2024, 9, 16)]
                支持格式: [19910906, '1992-03-02', datetime.date(2024, 9, 16)]

        Returns:
            DataFrame containing trading dates with columns:
            包含以下字段的交易日期DataFrame：
            - exchange: Exchange code / 交易所代码
            - trade_date: Trading date / 交易日期
            - pretrade_date: Previous trading date / 前一交易日
            - datestamp: Date timestamp / 日期时间戳

        Raises:
            ValueError: If invalid exchange or date format is provided
                      当提供的交易所或日期格式无效时
            RuntimeError: If API call fails
                        当API调用失败时
        """
        try:
            # Validate and normalize exchanges
            # 验证并标准化交易所参数
            if exchanges is None:
                exchanges = self.exchanges
            elif isinstance(exchanges, str):
                exchanges = [ex.strip() for ex in exchanges.split(",")]
            
            # Validate exchanges
            # 验证交易所代码
            invalid_exchanges = [ex for ex in exchanges if ex not in self.exchanges]
            if invalid_exchanges:
                raise ValueError(f"Invalid exchanges: {invalid_exchanges}. Supported exchanges: {self.exchanges}")

            # Normalize dates
            # 标准化日期
            try:
                start_date = pd.Timestamp(str(start_date)) if start_date else pd.Timestamp(self.default_start)
                end_date = pd.Timestamp(str(end_date)) if end_date else pd.Timestamp(f"{datetime.date.today().year}-12-31")
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid date format: {str(e)}")

            if start_date > end_date:
                raise ValueError(f"Start date ({start_date}) must be before end date ({end_date})")

            results = []
            for exchange in exchanges:
                try:
                    # Convert exchange code for TuShare API
                    # 转换交易所代码以适配 Tushare API
                    ts_exchange = "SSE" if exchange == "SHSE" else exchange

                    # Fetch trading calendar
                    # 获取交易日历
                    data = self.pro.trade_cal(
                        exchange=ts_exchange,
                        start_date=start_date.strftime("%Y%m%d"),
                        end_date=end_date.strftime("%Y%m%d")
                    )
                    
                    if data.empty:
                        continue

                    # Filter trading days and add required information
                    # 过滤交易日并添加必要信息
                    data = data.loc[data["is_open"] == 1].copy()
                    data["exchange"] = "SHSE" if ts_exchange == "SSE" else ts_exchange
                    data["datestamp"] = data["cal_date"].map(str).apply(util_make_date_stamp)
                    
                    # Format dates
                    # 格式化日期
                    data = data.rename(columns={"cal_date": "trade_date"})
                    data['trade_date'] = pd.to_datetime(data['trade_date']).dt.strftime('%Y-%m-%d')
                    data['pretrade_date'] = data['trade_date'].shift(1)
                    
                    results.append(data)

                except Exception as e:
                    self._handle_error(e, f"Failed to fetch trading dates for exchange {exchange}")

            if not results:
                return pd.DataFrame(columns=["exchange", "trade_date", "pretrade_date", "datestamp"])

            # Combine results and ensure column order
            # 合并结果并确保列顺序
            return pd.concat(results, axis=0)[["exchange", "trade_date", "pretrade_date", "datestamp"]]

        except Exception as e:
            self._handle_error(e, "fetch_get_trade_dates")

    def fetch_get_future_contracts(
        self,
        exchange: str = "DCE",
        spec_name: Union[str, List[str], None] = None,
        cursor_date: Optional[str] = None,
        fields: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        explanation:
            Tushare 获取交易期货合约接口封装，可以基于品种中文名，日期进行筛选

        params:
            * exchange ->
                含义: 交易所, 默认为大商所 DCE
                类型: str
                参数支持: ['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
            * spec_name ->
                含义：合约中文名称，默认为 None, 取所有品种
                参数：str
                参数支持：["豆粕", "棕榈油", ...]
            * cursor_date ->
                含义: 指定时间, 默认为 None, 即获取所有合约
                类型: int, str, datetime
                参数支持: [19910906, '1992-03-02', datetime.date(2024, 9, 16)]
            * fields ->
                含义：自定义字段，默认为 None, 获取合约所有字段
                类型: List[str]
                参数支持: ['symbol', 'name', 'list_date', 'delist_date']
        returns:
            pd.DataFrame ->
                合约信息
        """
        if fields:
            if "list_date" not in fields:
                fields.append("list_date")
            if "delist_date" not in fields:
                fields.append("delist_date")
            if "name" not in fields:
                fields.append("name")
            if "ts_code" not in fields:
                fields.append("ts_code")
            data = self.pro.fut_basic(exchange=exchange, fut_type="1", fields=fields)
        else:
            data = self.pro.fut_basic(
                exchange=exchange,
                fut_type="1",
            )
        data["list_datestamp"] = (
            data["list_date"].map(str).apply(lambda x: util_make_date_stamp(x))
        )
        data["delist_datestamp"] = (
            data["delist_date"].map(str).apply(lambda x: util_make_date_stamp(x))
        )
        pattern = r"(.*?)\d+\s*"
        data["chinese_name"] = data["name"].apply(lambda x: re.findall(pattern, x)[0])
        if exchange == "CZCE":
            data["symbol"] = data["ts_code"].map(str).apply(lambda x: x.split(".")[0])

        if spec_name:
            if isinstance(spec_name, str):
                spec_name = spec_name.split(",")
            data = data.loc[data["chinese_name"].isin(spec_name)]
            columns = data.columns.tolist()
            data = data[columns]

        columns = data.columns.tolist()

        data.list_date = pd.to_datetime(data.list_date).dt.strftime("%Y-%m-%d")
        data.delist_date = pd.to_datetime(data.delist_date).dt.strftime("%Y-%m-%d")

        if ("ts_code" in columns) and (fields is None):
            columns.remove("ts_code")

        data = data[columns]

        if cursor_date is None:
            return data
        else:
            cursor_date = pd.Timestamp(str(cursor_date)).strftime("%Y-%m-%d")
            return data.loc[
                (data["list_date"] <= cursor_date) & (data["delist_date"] > cursor_date)
            ]

    def fetch_get_stock_list(
        self,
        symbols: Union[str, List[str], None] = None,
        names: Union[str, List[str], None] = None,
        exchanges: Union[str, List[str], None] = None,
        markets: Union[str, List[str], None] = None,
        list_status: Union[str, List[str], None] = "L",
        is_hs: Union[str, None] = None,
        fields: Union[str, None] = None,
    ) -> pd.DataFrame:
        """
        explanation:
         对 tushare 股票列表获取接口的封装

        params:
            * symbols ->
                含义：股票代码, 默认为 None, 不做筛选
                类型：Union[str, List[str], None]
                参数支持: "SZSE.000001", "SHSE.600000"
            * names ->
                含义：股票名称，默认为 None，不做筛选
                类型: Union[str, List[str], None]
                参数支持: "平安银行", "浦发银行"
            * markets ->
                含义：市场类别，默认为 None, 不做筛选
                类型: Union[str, List[str], None]
                参数支持：主板, 创业板, 科创板, CDR, 北交所
            * list_status ->
                含义: 上市状态，默认为 None, 不做筛选
                类型：Union[str, List[str], None]
                参数支持： L上市 D退市 P暂停上市，默认是L
            * exchanges ->
                含义：交易所，默认为 None, 不做筛选
                类型：Union[str, List[str], None]
                参数支持：SSE上交所 SZSE深交所 BSE北交所
            * is_hs ->
                含义：是否沪港通标的
                类型：Union[str, None] = None,
                参数支持：N否 H沪股通 S深股通
            * fields ->
                含义：指定输出的字段
                类型：Union[str, List[str], None] = None
                参数支持：'ts_code,symbol,name,area,industry,list_date'

        returns:
            pd.DataFrame ->
                符合条件的股票列表
        """
        if fields:
            if isinstance(fields, list):
                fields = ",".join(fields)
        # 指定 symbols 则直接根据 symbols 查询，不考虑其他条件
        if symbols:
            symbols = util_format_stock_symbols(symbols, "ts")
            if fields:
                self.pro.stock_basic(symbols=",".join(symbols))[fields]
            else:
                self.pro.stock_basic(symbols=",".join(symbols))

        # 指定 names 则直接根据 names 查询，不考虑其他条件
        if names:
            if isinstance(names, str):
                names = names.split(",")
            results = pd.DataFrame()
            for name in names:
                df = self.pro.stock_basic(name=name)
                results = pd.concat([results, df], axis=0)
            if fields:
                return results[fields]
            else:
                return results

        # 指定 markets 则直接根据 markets 查询，不考虑 exchanges
        if markets:
            if isinstance(markets, str):
                markets = markets.split(",")
            results = pd.DataFrame()
            for market in markets:
                if list_status:
                    if is_hs:
                        df = self.pro.stock_basic(
                            market=market, list_status=list_status, is_hs=is_hs
                        )
                    else:
                        df = self.pro.stock_basic(
                            market=market, list_status=list_status
                        )
                        results = pd.concat([results, df], axis=0)
                else:
                    if is_hs:
                        df_1 = self.pro.stock_basic(
                            market=market, list_status="L", is_hs=is_hs
                        )
                        df_2 = self.pro.stock_basic(
                            market=market, list_status="D", is_hs=is_hs
                        )
                        df_3 = self.pro.stock_basic(
                            market=market, list_status="P", is_hs=is_hs
                        )
                        results = pd.concat([results, df_1, df_2, df_3], axis=0)
                    else:
                        df_1 = self.pro.stock_basic(market=market, list_status="L")
                        df_2 = self.pro.stock_basic(market=market, list_status="D")
                        df_3 = self.pro.stock_basic(market=market, list_status="P")
                        results = pd.concat([results, df_1, df_2, df_3], axis=0)
            if fields:
                return results[fields]
            else:
                return results

        if exchanges:
            if isinstance(exchanges, str):
                exchanges = exchanges.split(",")
            results = pd.DataFrame()
            for exchange in exchanges:
                if list_status:
                    if is_hs:
                        df = self.pro.stock_basic(
                            exchange=exchange, list_status=list_status, is_hs=is_hs
                        )
                    else:
                        df = self.pro.stock_basic(
                            exchange=exchange, list_status=list_status
                        )
                        results = pd.concat([results, df], axis=0)
                else:
                    if is_hs:
                        df_1 = self.pro.stock_basic(
                            exchange=exchange, list_status="L", is_hs=is_hs
                        )
                        df_2 = self.pro.stock_basic(
                            exchange=exchange, list_status="D", is_hs=is_hs
                        )
                        df_3 = self.pro.stock_basic(
                            exchange=exchange, list_status="P", is_hs=is_hs
                        )
                        results = pd.concat([results, df_1, df_2, df_3], axis=0)
                    else:
                        df_1 = self.pro.stock_basic(exchange=exchange, list_status="L")
                        df_2 = self.pro.stock_basic(exchange=exchange, list_status="D")
                        df_3 = self.pro.stock_basic(exchange=exchange, list_status="P")
                        results = pd.concat([results, df_1, df_2, df_3], axis=0)
            if fields:
                return results[fields]
            else:
                return results

        # 如果交易所，市场都不指定，则认为获取全部
        if list_status:
            results = self.pro.stock_basic(list_status=list_status)
        else:
            df_1 = self.pro.stock_basic(list_status="L")
            df_2 = self.pro.stock_basic(list_status="D")
            df_3 = self.pro.stock_basic(list_status="P")
            results = pd.concat([df_1, df_2, df_3], axis=0)
        if fields:
            return results[fields]
        else:
            return results

    def fetch_get_holdings(
        self,
        exchanges: Union[List[str], str, None] = None,
        cursor_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        symbols: Union[List[str], str, None] = None,
    ) -> pd.DataFrame:
        """
        Fetch holdings data for specified exchanges and symbols.
        获取指定交易所和合约的持仓数据。

        Args:
            exchanges: Exchange(s) to fetch data from, defaults to all future exchanges
                     要获取数据的交易所，默认为所有期货交易所
                Supported: ['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
                支持: ['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
            cursor_date: Reference date for fetching data, defaults to latest trading day
                       获取数据的参考日期，默认为最近交易日
                Formats: [20200913, '2021-03-05']
                支持格式: [20200913, '2021-03-05']
            start_date: Start date for date range query
                       日期范围查询的起始日期
                Formats: [20200913, '2021-03-05']
                支持格式: [20200913, '2021-03-05']
            end_date: End date for date range query
                     日期范围查询的结束日期
                Formats: [20200913, '2021-03-05']
                支持格式: [20200913, '2021-03-05']
            symbols: List of symbols to fetch data for
                    要获取数据的合约代码列表
                Formats: ['IF2403', 'IF2406'] or 'IF2403,IF2406'
                支持格式: ['IF2403', 'IF2406'] 或 'IF2403,IF2406'

        Returns:
            DataFrame containing holdings data with columns:
            包含以下字段的持仓数据DataFrame：
            - trade_date: Trading date / 交易日期
            - symbol: Contract symbol / 合约代码
            - exchange: Exchange code / 交易所代码
            - vol: Volume / 成交量
            - amount: Trading amount / 成交金额
            - datestamp: Date timestamp / 日期时间戳

        Raises:
            ValueError: If invalid exchange, symbol or date format is provided
                      当提供的交易所、合约代码或日期格式无效时
            RuntimeError: If API call fails
                        当API调用失败时
        """
        try:
            # Validate and normalize exchanges
            # 验证并标准化交易所参数
            if exchanges is None:
                exchanges = self.future_exchanges
            elif isinstance(exchanges, str):
                exchanges = [ex.strip() for ex in exchanges.split(",")]

            # Validate exchanges
            # 验证交易所代码
            invalid_exchanges = [ex for ex in exchanges if ex not in self.future_exchanges]
            if invalid_exchanges:
                raise ValueError(
                    f"Invalid exchanges: {invalid_exchanges}. Supported exchanges: {self.future_exchanges}"
                )

            # Normalize symbols
            # 标准化合约代码
            if isinstance(symbols, str):
                symbols = [sym.strip() for sym in symbols.split(",")]

            # Normalize dates
            # 标准化日期
            try:
                if cursor_date:
                    cursor_date = pd.Timestamp(str(cursor_date))
                if start_date:
                    start_date = pd.Timestamp(str(start_date))
                if end_date:
                    end_date = pd.Timestamp(str(end_date))
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid date format: {str(e)}")

            # Validate date range
            # 验证日期范围
            if start_date and end_date and start_date > end_date:
                raise ValueError(f"Start date ({start_date}) must be before end date ({end_date})")

            results = []
            for exchange in exchanges:
                try:
                    if start_date is None:
                        # Single date query
                        # 单日查询
                        query_date = cursor_date or pd.Timestamp.today()
                        trade_date = self._get_latest_trade_date(exchange, query_date)
                        
                        # Get symbols if not provided
                        # 如果未提供合约代码，则获取当前可交易的合约
                        if symbols is None:
                            symbols = self._get_active_symbols(exchange, trade_date)
                        
                        for symbol in symbols:
                            try:
                                # Fetch holdings data
                                # 获取持仓数据
                                data = self.pro.fut_holding(
                                    trade_date=trade_date.strftime("%Y%m%d"),
                                    symbol=symbol,
                                    exchange=exchange,
                                )
                                
                                if not data.empty:
                                    # Add exchange and datestamp
                                    # 添加交易所和日期戳
                                    data["exchange"] = exchange
                                    data["datestamp"] = data["trade_date"].apply(
                                        lambda x: util_make_date_stamp(str(x))
                                    )
                                    results.append(data)
                            
                            except Exception as e:
                                self._handle_error(
                                    e, f"Failed to fetch holdings for symbol {symbol} on {trade_date}"
                                )
                    else:
                        # Date range query
                        # 日期范围查询
                        end_date = end_date or pd.Timestamp.today()
                        current_date = start_date
                        
                        while current_date <= end_date:
                            try:
                                trade_date = self._get_latest_trade_date(exchange, current_date)
                                
                                # Get symbols if not provided
                                # 如果未提供合约代码，则获取当前可交易的合约
                                if symbols is None:
                                    current_symbols = self._get_active_symbols(exchange, trade_date)
                                else:
                                    current_symbols = symbols
                                
                                for symbol in current_symbols:
                                    try:
                                        # Fetch holdings data
                                        # 获取持仓数据
                                        data = self.pro.fut_holding(
                                            trade_date=trade_date.strftime("%Y%m%d"),
                                            symbol=symbol,
                                            exchange=exchange,
                                        )
                                        
                                        if not data.empty:
                                            # Add exchange and datestamp
                                            # 添加交易所和日期戳
                                            data["exchange"] = exchange
                                            data["datestamp"] = data["trade_date"].apply(
                                                lambda x: util_make_date_stamp(str(x))
                                            )
                                            results.append(data)
                                    
                                    except Exception as e:
                                        self._handle_error(
                                            e,
                                            f"Failed to fetch holdings for symbol {symbol} on {trade_date}"
                                        )
                            
                            except Exception as e:
                                self._handle_error(
                                    e, f"Failed to process date {current_date} for exchange {exchange}"
                                )
                            
                            current_date += pd.Timedelta(days=1)

                except Exception as e:
                    self._handle_error(e, f"Failed to fetch holdings for exchange {exchange}")

            if not results:
                return pd.DataFrame(
                    columns=["trade_date", "symbol", "exchange", "vol", "amount", "datestamp"]
                )

            # Combine results and format dates
            # 合并结果并格式化日期
            result_df = pd.concat(results, axis=0)
            result_df["trade_date"] = pd.to_datetime(result_df["trade_date"]).dt.strftime("%Y-%m-%d")
            
            # Ensure column order
            # 确保列顺序
            return result_df[["trade_date", "symbol", "exchange", "vol", "amount", "datestamp"]]

        except Exception as e:
            self._handle_error(e, "fetch_get_holdings")

    def _get_latest_trade_date(self, exchange: str, reference_date: pd.Timestamp) -> pd.Timestamp:
        """
        Get the latest trading date for an exchange, including the reference date.
        获取交易所的最近交易日期（包含参考日期）。

        Args:
            exchange: Exchange code
            reference_date: Reference date

        Returns:
            Latest trading date
        """
        try:
            calendar = self.pro.trade_cal(
                exchange=exchange,
                start_date=reference_date.strftime("%Y%m%d"),
                end_date=reference_date.strftime("%Y%m%d"),
            )
            
            if calendar.empty or calendar.iloc[0]["is_open"] == 0:
                # If reference date is not a trading day, get the previous trading day
                # 如果参考日期不是交易日，获取前一个交易日
                calendar = self.pro.trade_cal(
                    exchange=exchange,
                    end_date=reference_date.strftime("%Y%m%d"),
                    is_open=1,
                )
                if calendar.empty:
                    raise ValueError(f"No trading days found for exchange {exchange}")
                return pd.Timestamp(str(calendar.iloc[-1]["cal_date"]))
            
            return reference_date

        except Exception as e:
            raise RuntimeError(f"Failed to get latest trade date: {str(e)}")

    def _get_active_symbols(self, exchange: str, trade_date: pd.Timestamp) -> List[str]:
        """
        Get active trading symbols for an exchange on a specific date.
        获取指定日期交易所的活跃合约代码。

        Args:
            exchange: Exchange code
            trade_date: Trading date

        Returns:
            List of active symbols
        """
        try:
            contracts = self.fetch_get_future_contracts(
                exchange=exchange,
                cursor_date=trade_date.strftime("%Y-%m-%d"),
            )
            return contracts["symbol"].tolist()

        except Exception as e:
            raise RuntimeError(f"Failed to get active symbols: {str(e)}")

    def fetch_get_future_daily(
        self,
        cursor_date: Union[str, datetime.date, int] = None,
        symbols: Union[str, List[str], None] = None,
        exchanges: Union[str, List[str], None] = None,
        start_date: Union[str, datetime.date, int, None] = None,
        end_date: Union[str, datetime.date, int, None] = None,
        fields: Union[List[str], None] = None,
    ) -> pd.DataFrame:
        """
        explanation:
            获取指定交易所指定合约日线行情, 注意，tushare 的 SHFE 对应查询 symbol 后缀为 SHF, CZCE 查询后缀为 ZCE

        params:
            * cursor_date ->
                含义：指定日期最近交易日（当前日期包括在内）, 默认为 None，如果 start_date 不指定时，将默认 cursor_date 为当前日期
                类型：Union[str, datetime.date, int, None]
                参数支持： 20240930, "20240926"
            * symbols ->
                含义：指定合约代码列表，默认为 None, 当指定 symbols 后，exchanges 参数失效
                类型： Union[str, List[str]]
                参数支持：["M2501, M2505"]
            * exchanges ->
                含义：交易所 列表, 默认为 None
                类型：Union[str, List[str], None]
                参数支持：DEC, INE, SHFE, INE, CFFEX
            * start_date ->
                含义：起始时间，默认为 None，当指定了 start_date 以后，cursor_date 失效
                类型：Union[str, int, datetime.date]
                参数支持：20200913, "20210305", ...
            * end_date ->
                含义： 结束时间，默认为 None, 当指定了 start_date 以后，end_date 如果为 None，则默认为当前日期
                类型：Union[str, int, datetime.date]
                参数支持：20200913, "20210305", ...
            returns:
                pd.DataFrame ->
                    期货日线行情
        """
        results = pd.DataFrame()
        if start_date:
            if end_date is None:
                end_date = datetime.date.today()
            if symbols:
                symbols = util_format_future_symbols(symbols=symbols, format="tushare", tushare_daily_spec=True)
                symbols = ",".join(symbols)
                if fields:
                    results = self.pro.fut_daily(
                        ts_code=symbols,
                        start_date=pd.Timestamp(str(start_date)).strftime("%Y%m%d"),
                        end_date=pd.Timestamp(str(end_date)).strftime("%Y%m%d"),
                        fields=fields,
                    )
                else:
                    results = self.pro.fut_daily(
                        ts_code=symbols,
                        start_date=pd.Timestamp(str(start_date)).strftime("%Y%m%d"),
                        end_date=pd.Timestamp(str(end_date)).strftime("%Y%m%d"),
                    )
            else:
                if exchanges is None:
                    exchanges = self.future_exchanges
                elif isinstance(exchanges, str):
                    exchanges = exchanges.split(",")
                results = pd.DataFrame()
                for exchange in exchanges:
                    if fields:
                        df_local = self.pro.fut_daily(
                            exchange=exchange,
                            start_date=pd.Timestamp(str(start_date)).strftime("%Y%m%d"),
                            end_date=pd.Timestamp(str(end_date)).strftime("%Y%m%d"),
                            fields=fields,
                        )
                    else:
                        df_local = self.pro.fut_daily(
                            start_date=pd.Timestamp(str(start_date)).strftime("%Y%m%d"),
                            end_date=pd.Timestamp(str(end_date)).strftime("%Y%m%d"),
                            exchange=exchange,
                        )
                    results = pd.concat([results, df_local], axis=0)
        else:
            if cursor_date is None:
                cursor_date = datetime.date.today()
            latest_trade_date = self.local_queryer.fetch_pre_trade_date(
                cursor_date=cursor_date, include=True
            )["trade_date"]
            if symbols:
                symbols = util_format_future_symbols(symbols=symbols, format="tushare", tushare_daily_spec=True)
                symbols = ",".join(symbols)
                if fields:
                    results = self.pro.fut_daily(
                        ts_code=symbols,
                        trade_date=latest_trade_date.replace("-", ""),
                        fields=fields,
                    )
                else:
                    results = self.pro.fut_daily(
                        ts_code=symbols,
                        trade_date=latest_trade_date.replace("-", ""),
                    )
            else:
                if exchanges is None:
                    exchanges = self.future_exchanges
                elif isinstance(exchanges, str):
                    exchanges = exchanges.split(",")
                results = pd.DataFrame()
                for exchange in exchanges:
                    if fields:
                        df_local = self.pro.fut_daily(
                            trade_date=latest_trade_date.replace("-", ""),
                            exchange=exchange,
                            fields=fields,
                        )
                    else:
                        df_local = self.pro.fut_daily(
                            trade_date=latest_trade_date.replace("-", ""),
                            exchange=exchange,
                        )
                    results = pd.concat([results, df_local], axis=0)
        if "trade_date" in results.columns:
            results["datestamp"] = results.trade_date.map(str).apply(
                lambda x: util_make_date_stamp(x)
            )
            results.trade_date = pd.to_datetime(results["trade_date"]).dt.strftime(
                "%Y-%m-%d"
            )
        if "ts_code" in results.columns:
            columns = results.columns.tolist()
            results["symbol"] = (
                results.ts_code.map(str).str.split(".").apply(lambda x: x[0])
            )
            results["exchange"] = (
                results.ts_code.map(str).str.split(".").apply(lambda x: x[1])
            )
            replace_dict = {
                r'SHF$': 'SHFE',
                r'ZCE$': 'CZCE'
            }
            results.exchange = results.exchange.replace(replace_dict, regex=True)
            columns = ["symbol", "exchange"] + columns
            if "ts_code" in columns:
                columns.remove("ts_code")
            results = results[columns]
        return results


# 添加全局函数
def fetch_get_trade_dates(exchanges=None, start_date=None, end_date=None):
    fetcher = TSFetcher()
    return fetcher.fetch_get_trade_dates(exchanges, start_date, end_date)


def fetch_get_future_contracts(
    exchange="DCE", spec_name=None, cursor_date=None, fields=None
):
    fetcher = TSFetcher()
    return fetcher.fetch_get_future_contracts(exchange, spec_name, cursor_date, fields)


def fetch_get_holdings(
    exchanges=None, cursor_date=None, start_date=None, end_date=None, symbols=None
):
    fetcher = TSFetcher()
    return fetcher.fetch_get_holdings(
        exchanges, cursor_date, start_date, end_date, symbols
    )


if __name__ == "__main__":
    fetcher = TSFetcher()
    # print(fetcher.fetch_get_trade_dates(
    #     "SSE",
    #     "2024-08-01",
    #     "2024-09-01"
    # ))
    # print(fetcher.fetch_get_trade_dates(
    #     ["SSE", "DCE"],
    #     "2024-08-01",
    #     "2024-09-01"
    # ))

    # print(fetcher.fetch_get_future_contracts(
    #     exchange="DCE",
    #     spec_name="豆粕",
    # ))

    # print(fetcher.fetch_get_future_contracts(
    #     exchange="DCE",
    #     spec_name="豆粕",
    #     cursor_date="2024-09-30"
    # ))

    # print(fetcher.fetch_get_future_contracts(
    #     exchange="DCE",
    #     spec_name="豆粕",
    #     cursor_date="2024-09-30",
    #     fields=['ts_code', 'symbol', 'exchange', 'name']
    # ))

    # print(fetcher.fetch_trade_dates(exchanges="SSE", start_date="2024-09-01", end_date="2024-09-30"))

    print(fetcher.fetch_get_stock_list(symbols="000001, 600000"))
    print(fetcher.fetch_get_stock_list(names=["招商证券", "贵州茅台"]))
    print(fetcher.fetch_get_stock_list(names=["招商证券", "贵州茅台"]))
    print(fetcher.fetch_get_stock_list(markets=["科创板", " 创业板"]))
    print(fetcher.fetch_get_stock_list())
