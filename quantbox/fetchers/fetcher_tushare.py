import datetime
import time
import re
import functools
from typing import List, Optional, Union, Dict, Any, Tuple
import pandas as pd
import numpy as np

from ..config.config_loader import get_config_loader
from ..util.exchange_utils import validate_exchanges
from .local_fetcher import LocalFetcher

class TSFetcher:
    """TuShare数据获取器"""
    
    def __init__(self):
        """初始化"""
        config_loader = get_config_loader()
        self.pro = config_loader.get_tushare_pro()
        self.default_start = "1990-12-19"  # 可以从配置获取
        self.local_fetcher = LocalFetcher()
        
        # 缓存设置
        self._cache_ttl = 3600  # 缓存有效期（秒）
        self._cache: Dict[str, Tuple[float, Any]] = {}  # {key: (timestamp, data)}

    def _get_cache_key(self, *args, **kwargs) -> str:
        """生成缓存键

        将函数参数转换为缓存键。这个实现很简单，
        但对于我们的用例来说足够了。

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            str: 缓存键
        """
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return "|".join(key_parts)

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存中获取数据

        Args:
            key: 缓存键

        Returns:
            Optional[Any]: 缓存的数据，如果没有找到或已过期则返回 None
        """
        if key not in self._cache:
            return None
        
        timestamp, data = self._cache[key]
        if time.time() - timestamp > self._cache_ttl:
            # 缓存已过期
            del self._cache[key]
            return None
        
        return data

    def _set_cache(self, key: str, data: Any):
        """将数据存入缓存

        Args:
            key: 缓存键
            data: 要缓存的数据
        """
        self._cache[key] = (time.time(), data)

    def _format_date_string(self, date_int: int) -> str:
        """将整数日期格式化为字符串

        使用更高效的字符串格式化方法。

        Args:
            date_int: 整数格式的日期 (YYYYMMDD)

        Returns:
            str: 格式化的日期字符串 (YYYY-MM-DD)
        """
        date_str = str(date_int)
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

    def _batch_fetch_trade_dates(
        self,
        start_dates: List[int],
        end_dates: List[int],
        exchanges: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """批量获取交易日历

        将多个查询合并为一个，减少网络请求次数。

        Args:
            start_dates: 起始日期列表（整数格式）
            end_dates: 结束日期列表（整数格式）
            exchanges: 交易所列表

        Returns:
            pd.DataFrame: 合并后的交易日历数据
        """
        # 找出最早的开始日期和最晚的结束日期
        min_start = min(start_dates)
        max_end = max(end_dates)
        
        # 获取完整的日期范围数据
        df = self.pro.trade_cal(
            exchange='',
            start_date=str(min_start),
            end_date=str(max_end),
            is_open='1'
        )
        
        if df.empty:
            return pd.DataFrame()
        
        # 重命名列
        df = df.rename(columns={
            'cal_date': 'date_int',
            'pretrade_date': 'pretrade_date'
        })
        
        # 确保日期是整数类型
        df['date_int'] = df['date_int'].astype(int)
        
        # 添加交易所列
        exchanges = validate_exchanges(exchanges)
        
        # 展开数据，为每个交易所创建一行
        df_list = []
        for exchange in exchanges:
            df_exchange = df.copy()
            df_exchange['exchange'] = exchange
            df_list.append(df_exchange)
        
        df = pd.concat(df_list, ignore_index=True)
        
        # 使用更高效的方法添加日期字符串
        df['trade_date'] = df['date_int'].apply(self._format_date_string)
        df['pretrade_date'] = df['pretrade_date'].apply(
            lambda x: self._format_date_string(int(x)) if pd.notna(x) else None
        )
        
        # 添加时间戳（使用向量化操作）
        df['datestamp'] = pd.to_datetime(df['trade_date']).astype(int) // 10**9
        
        return df[['exchange', 'trade_date', 'pretrade_date', 'datestamp', 'date_int']]

    def fetch_get_trade_dates(
        self,
        exchanges: Union[List[str], str, None] = None,
        start_date: Union[str, int, datetime.datetime, None] = None,
        end_date: Union[str, int, datetime.datetime, None] = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """获取交易日历

        Args:
            exchanges: 交易所列表或字符串，默认为所有交易所
            start_date: 起始日期，支持以下格式：
                - 整数：20240101
                - 字符串：'20240101' 或 '2024-01-01'
                - datetime 对象
                默认为 default_start
            end_date: 结束日期，格式同 start_date，默认为当前日期
            use_cache: 是否使用缓存，默认为 True

        Returns:
            pd.DataFrame: 交易日历数据，包含以下字段：
                - exchange: 交易所代码
                - trade_date: 交易日期 (YYYY-MM-DD)
                - pretrade_date: 前一交易日 (YYYY-MM-DD)
                - datestamp: 日期时间戳
                - date_int: 整数格式的日期 (YYYYMMDD)
        """
        if start_date is None:
            start_date = self.default_start
        if end_date is None:
            end_date = datetime.datetime.today()

        # 标准化日期格式为整数
        start_int = self._normalize_date(start_date)
        end_int = self._normalize_date(end_date)
        
        # 尝试从缓存获取数据
        if use_cache:
            cache_key = self._get_cache_key(
                'trade_dates',
                start_int,
                end_int,
                exchanges
            )
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data

        # 使用批量查询获取数据
        df = self._batch_fetch_trade_dates(
            start_dates=[start_int],
            end_dates=[end_int],
            exchanges=validate_exchanges(exchanges)
        )
        
        # 缓存结果
        if use_cache:
            self._set_cache(cache_key, df)
        
        return df

    def fetch_get_trade_dates_batch(
        self,
        date_ranges: List[Tuple[Union[str, int, datetime.datetime], Union[str, int, datetime.datetime]]],
        exchanges: Union[str, List[str], None] = None,
        use_cache: bool = True
    ) -> Dict[Tuple[int, int], pd.DataFrame]:
        """批量获取多个日期范围的交易日历

        Args:
            date_ranges: 日期范围列表，每个元素是 (start_date, end_date) 元组
            exchanges: 交易所列表或字符串，默认为所有交易所
            use_cache: 是否使用缓存，默认为 True

        Returns:
            Dict[Tuple[int, int], pd.DataFrame]: 每个日期范围对应的交易日历数据
        """
        # 标准化所有日期
        normalized_ranges = [
            (self._normalize_date(start), self._normalize_date(end))
            for start, end in date_ranges
        ]
        
        # 尝试从缓存获取数据
        results = {}
        to_fetch = []
        start_dates = []
        end_dates = []
        
        if use_cache:
            for start_int, end_int in normalized_ranges:
                cache_key = self._get_cache_key(
                    'trade_dates',
                    start_int,
                    end_int,
                    exchanges
                )
                cached_data = self._get_from_cache(cache_key)
                if cached_data is not None:
                    results[(start_int, end_int)] = cached_data
                else:
                    to_fetch.append((start_int, end_int))
                    start_dates.append(start_int)
                    end_dates.append(end_int)
        else:
            to_fetch = normalized_ranges
            start_dates = [start for start, _ in normalized_ranges]
            end_dates = [end for _, end in normalized_ranges]
        
        if to_fetch:
            # 获取所有需要的数据
            df = self._batch_fetch_trade_dates(
                start_dates=start_dates,
                end_dates=end_dates,
                exchanges=validate_exchanges(exchanges)
            )
            
            # 为每个日期范围过滤数据
            for start_int, end_int in to_fetch:
                mask = (df['date_int'] >= start_int) & (df['date_int'] <= end_int)
                range_df = df[mask].copy()
                results[(start_int, end_int)] = range_df
                
                # 缓存结果
                if use_cache:
                    cache_key = self._get_cache_key(
                        'trade_dates',
                        start_int,
                        end_int,
                        exchanges
                    )
                    self._set_cache(cache_key, range_df)
        
        return results

    def _normalize_date(
        self,
        date: Union[str, int, datetime.datetime, None],
        default: Union[str, datetime.datetime, None] = None
    ) -> int:
        """标准化日期格式

        将各种日期格式转换为整数格式（YYYYMMDD）

        Args:
            date: 日期，支持以下格式：
                - 整数：20240101
                - 字符串：'20240101' 或 '2024-01-01'
                - datetime 对象
                - None：使用默认值
            default: 默认日期，如果 date 为 None 则使用此值

        Returns:
            int: 整数格式的日期，如 20240101
        """
        if date is None:
            date = default if default is not None else datetime.datetime.today()
        
        if isinstance(date, int):
            # 如果是整数，直接返回
            return date
        elif isinstance(date, str):
            # 如果是字符串，去掉连字符并转为整数
            return int(date.replace('-', ''))
        else:
            # 如果是 datetime 对象，转换为整数
            return int(pd.Timestamp(date).strftime('%Y%m%d'))

    def fetch_get_future_contracts(
        self,
        exchange: str = "DCE",
        spec_name: Union[str, List[str], None] = None,
        cursor_date: Optional[str] = None,
        fields: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Fetch future contract information from TuShare.
        从 Tushare 获取期货合约信息。

        Args:
            exchange: Exchange to fetch data from, defaults to DCE
                    要获取数据的交易所，默认为大商所
                Supported: ['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
                支持: ['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
            spec_name: Chinese name of contract, defaults to None to fetch all
                     合约中文名称，默认为 None 获取所有品种
                Examples: ["豆粕", "棕榈油", ...]
                示例: ["豆粕", "棕榈油", ...]
            cursor_date: Reference date for filtering contracts, defaults to None to fetch all
                       过滤合约的参考日期，默认为 None 获取所有合约
                Formats: [19910906, '1992-03-02', datetime.date(2024, 9, 16)]
                支持格式: [19910906, '1992-03-02', datetime.date(2024, 9, 16)]
            fields: Custom fields to return, defaults to None to return all fields
                   自定义返回字段，默认为 None 返回所有字段
                Examples: ['symbol', 'name', 'list_date', 'delist_date']
                示例: ['symbol', 'name', 'list_date', 'delist_date']

        Returns:
            DataFrame containing contract information
            包含合约信息的DataFrame

        Raises:
            ValueError: If invalid exchange or date format is provided
                      当提供的交易所或日期格式无效时
            RuntimeError: If API call fails
                        当API调用失败时
        """
        # 确保必要字段存在
        required_fields = ["list_date", "delist_date", "name", "ts_code"]
        if fields:
            fields.extend([f for f in required_fields if f not in fields])
            # 获取合约信息，没有必要导入主力和连续合约，压根没有 list_date 和 delist_date
            data = self.pro.fut_basic(exchange=exchange, fut_type="1", fields=fields)
        else:
            data = self.pro.fut_basic(exchange=exchange, fut_type="1")

        # 处理日期
        for date_col in ["list_date", "delist_date"]:
            data[f"{date_col}stamp"] = pd.to_datetime(data[date_col].astype(str)).astype(np.int64) // 10**9
            data[date_col] = pd.to_datetime(data[date_col]).dt.strftime("%Y-%m-%d")

        # 提取中文名称
        data["chinese_name"] = data["name"].str.extract(r'(.+?)(?=\d{3,})')
        
        # 处理合约代码
        data["qbcode"] = data["ts_code"].str.split(".").str[0]
        if exchange not in ["CZCE", "CFFEX"]:
            # Tushare 中 symbol 都默认使用大写了，与交易所实际不一致，做特殊处理
            data["symbol"] = data["symbol"].str.lower()

        # 按品种名称过滤
        if spec_name:
            if isinstance(spec_name, str):
                spec_name = spec_name.split(",")
            data = data[data["chinese_name"].isin(spec_name)]

        # 整理列顺序
        if "ts_code" in data.columns and fields is None:
            columns = ["qbcode"] + [col for col in data.columns if col not in ["qbcode", "ts_code"]]
        else:
            columns = ["qbcode"] + [col for col in data.columns if col != "qbcode"]
        data = data[columns]

        # 按日期过滤
        if cursor_date is not None:
            cursor_date = pd.Timestamp(str(cursor_date)).strftime("%Y-%m-%d")
            data = data[(data["list_date"] <= cursor_date) & (data["delist_date"] > cursor_date)]

        return data

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
                exchanges = ['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
            elif isinstance(exchanges, str):
                exchanges = [ex.strip() for ex in exchanges.split(",")]

            # Validate exchanges
            # 验证交易所代码
            invalid_exchanges = [ex for ex in exchanges if ex not in ['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']]
            if invalid_exchanges:
                raise ValueError(
                    f"Invalid exchanges: {invalid_exchanges}. Supported exchanges: ['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']"
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
                return pd.DataFrame(columns=["trade_date", "exchange", "symbol", "broker", "vol", "vol_chg", "long_hld", "long_chg", "short_hld", "short_chg", "datestamp"])

            # Combine results and format dates
            # 合并结果并格式化日期
            result_df = pd.concat(results, axis=0)
            result_df["trade_date"] = pd.to_datetime(result_df["trade_date"]).dt.strftime("%Y-%m-%d")

            # Ensure column order
            # 确保列顺序
            return result_df

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
                symbols = util_format_future_symbols(symbols=symbols, format="ts")
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
                    exchanges = ['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
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
            latest_trade_date = self.local_fetcher.fetch_pre_trade_date(
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
                    exchanges = ['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
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
    df = fetcher.fetch_get_future_daily(symbols="M2501", start_date="2024-11-03", end_date="2024-11-20")
    # print(fetcher.fetch_get_stock_list(symbols="000001, 600000"))
    # print(fetcher.fetch_get_stock_list(names=["招商证券", "贵州茅台"]))
    # print(fetcher.fetch_get_stock_list(names=["招商证券", "贵州茅台"]))
    # print(fetcher.fetch_get_stock_list(markets=["科创板", " 创业板"]))
    # print(fetcher.fetch_get_stock_list())
