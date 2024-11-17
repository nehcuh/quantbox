import datetime
import re
from typing import List, Optional, Union
import math
import pandas as pd
import platform
import warnings

if platform.system() != 'Darwin':  # Not macOS
    from gm.api import get_symbol_infos, set_token, fut_get_transaction_rankings
else:
    warnings.warn("GoldMiner API is not supported on macOS")
    get_symbol_infos = None
    set_token = None
    fut_get_transaction_rankings = None

from quantbox.fetchers.base import BaseFetcher
from quantbox.fetchers.local_fetcher import LocalFetcher
from quantbox.util.basic import (
    DATABASE,
    DEFAULT_START,
    EXCHANGES,
    FUTURE_EXCHANGES,
    STOCK_EXCHANGES,
    QUANTCONFIG,
)
from quantbox.util.tools import (
    util_format_future_symbols,
    util_format_stock_symbols,
    util_make_date_stamp,
)


class GMFetcher(BaseFetcher):
    """
    GMFetcher implements data fetching from GoldMiner API.
    
    This class handles all interactions with the GoldMiner API, including:
    - Future contracts data
    - Holdings data
    - Market data
    
    Attributes:
        exchanges: List of supported exchanges
        stock_exchanges: List of supported stock exchanges
        future_exchanges: List of supported future exchanges
    """
    
    def __init__(self):
        if platform.system() == 'Darwin':
            raise NotImplementedError(
                "GoldMiner API is not supported on macOS. "
                "Please use other data sources or run on Linux/Windows."
            )
        super().__init__()
        if platform.system() == 'Darwin':
            raise NotImplementedError(
                "GoldMiner API is not supported on macOS. "
                "Please use TuShare or run on Linux/Windows."
            )
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
        if platform.system() != 'Darwin':  # Not macOS
            set_token(QUANTCONFIG.get('goldminer', {}).get('token', ''))

    def _format_symbol(self, symbol: str) -> str:
        """Format symbol to GM API format"""
        if '.' not in symbol:
            # Determine exchange based on symbol prefix
            if symbol.startswith(('IF', 'IC', 'IH', 'IM', 'T', 'TF', 'TS')):
                exchange = 'CFFEX'
            elif symbol.startswith(('cu', 'al', 'zn', 'pb', 'ni', 'sn', 'au', 'ag')):
                exchange = 'SHFE'
            elif symbol.startswith(('c', 'm', 'y', 'p', 'l', 'v', 'pp', 'j', 'jm')):
                exchange = 'DCE'
            elif symbol.startswith(('SR', 'CF', 'CY', 'TA', 'OI', 'MA', 'FG', 'RM')):
                exchange = 'CZCE'
            else:
                exchange = 'SHFE'  # Default to SHFE
            return f"{exchange}.{symbol}"
        return symbol

    def fetch_get_holdings(
        self,
        exchanges: Union[List[str], str, None] = None,
        cursor_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        symbols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Fetch future holdings data from GoldMiner API.
        
        Args:
            exchanges: List of exchanges to fetch data from
            cursor_date: Single date to fetch data for
            start_date: Start date for date range
            end_date: End date for date range
            symbols: List of symbols to fetch data for
            
        Returns:
            DataFrame containing holdings data with columns:
            - trade_date: Trading date
            - symbol: Contract symbol
            - exchange: Exchange code
            - datestamp: Date stamp
            - volume: Trading volume
            - amount: Trading amount
            
        Raises:
            ValueError: If date parameters are invalid
            RuntimeError: If API call fails
        """
        if platform.system() == 'Darwin':
            raise NotImplementedError(
                "GoldMiner API is not supported on macOS. "
                "Please use other data sources or run on Linux/Windows."
            )
        try:
            # Validate inputs
            start_date, end_date = self.validator.validate_dates(
                start_date, end_date, cursor_date
            )
            symbols = self.validator.validate_symbols(symbols)
            
            if exchanges is None:
                exchanges = self.future_exchanges
            if isinstance(exchanges, str):
                exchanges = exchanges.split(",")
                
            # Initialize result container
            total_holdings = pd.DataFrame()
            
            # Process each exchange
            for exchange in exchanges:
                try:
                    # Get symbols for this exchange if not provided
                    exchange_symbols = symbols
                    if not exchange_symbols:
                        contracts = self.fetch_get_future_contracts([exchange])
                        if not contracts.empty:
                            exchange_symbols = contracts['symbol'].tolist()
                    
                    if not exchange_symbols:
                        continue
                        
                    # Format symbols for API
                    formatted_symbols = [
                        self._format_symbol(symbol) 
                        for symbol in exchange_symbols
                    ]
                    
                    # Fetch data in batches to avoid API limits
                    batch_size = 50  # Adjust based on API limits
                    for i in range(0, len(formatted_symbols), batch_size):
                        batch_symbols = formatted_symbols[i:i + batch_size]
                        
                        holdings = fut_get_transaction_rankings(
                            symbols=batch_symbols,
                            trade_date=cursor_date or end_date,
                            indicators="volume,long,short"
                        )
                        
                        if not holdings.empty:
                            # Add exchange information
                            holdings['exchange'] = exchange
                            holdings['datestamp'] = util_make_date_stamp(
                                holdings['trade_date']
                            )
                            total_holdings = pd.concat(
                                [total_holdings, holdings],
                                ignore_index=True
                            )
                            
                except Exception as e:
                    self._handle_error(
                        e, 
                        f"fetching holdings for exchange {exchange}"
                    )
                    
            # Validate and format final response
            required_columns = [
                'trade_date', 'symbol', 'exchange', 
                'datestamp', 'volume', 'long', 'short'
            ]
            return self._format_response(total_holdings, required_columns)
            
        except Exception as e:
            self._handle_error(e, "fetch_get_holdings")

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
                Supported: ['SHSE', 'SZSE', 'SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
                支持: ['SHSE', 'SZSE', 'SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
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
                # Convert exchange code for GoldMiner API
                # 转换交易所代码以适配掘金API
                gm_exchange = "SHSE" if exchange == "SSE" else exchange

                try:
                    # Fetch trading dates for the entire period at once
                    # 一次性获取整个时期的交易日
                    dates = get_trading_dates(
                        exchange=gm_exchange,
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d")
                    )
                    
                    if not dates:
                        continue

                    # Create DataFrame with all required information
                    # 创建包含所有必需信息的DataFrame
                    df = pd.DataFrame({
                        'trade_date': pd.to_datetime(dates),
                        'exchange': gm_exchange
                    })

                    # Sort and calculate previous trading date
                    # 排序并计算前一交易日
                    df = df.sort_values('trade_date')
                    df['pretrade_date'] = df['trade_date'].shift(1)
                    
                    # Add datestamp
                    # 添加日期戳
                    df["datestamp"] = df['trade_date'].apply(lambda x: util_make_date_stamp(x))
                    
                    # Format dates
                    # 格式化日期
                    df['trade_date'] = df['trade_date'].dt.strftime('%Y-%m-%d')
                    df['pretrade_date'] = df['pretrade_date'].dt.strftime('%Y-%m-%d')
                    
                    results.append(df)

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
        exchanges: Union[List[str], str, None] = None,
        symbols: Optional[List[str]] = None,
        cursor_date: Optional[str] = None,
        fields: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Fetch future contracts information from GoldMiner API.
        从掘金量化API获取期货合约信息。

        Args:
            exchanges: Exchange(s) to fetch data from, defaults to all future exchanges
                     要获取数据的交易所，默认为所有期货交易所
                     Supported: ['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
                     支持: ['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
            symbols: List of symbols to fetch, defaults to all symbols
                    要获取的合约代码列表，默认为所有合约
            cursor_date: Reference date for filtering contracts
                       用于筛选合约的参考日期
            fields: List of fields to return, defaults to all fields
                   要返回的字段列表，默认为所有字段
                   Supported: ['symbol', 'name', 'list_date', 'delist_date', etc.]
                   支持: ['symbol', 'name', 'list_date', 'delist_date' 等]

        Returns:
            DataFrame containing contract information with columns:
            包含以下字段的合约信息DataFrame：
            - symbol: Contract symbol / 合约代码
            - name: Contract name / 合约名称
            - list_date: Listing date / 上市日期
            - delist_date: Delisting date / 退市日期
            - list_datestamp: Listing date timestamp / 上市日期时间戳
            - delist_datestamp: Delisting date timestamp / 退市日期时间戳
            - chinese_name: Product Chinese name / 品种中文名
            - exchange: Exchange code / 交易所代码

        Raises:
            ValueError: If invalid exchange or fields are provided
                      当提供的交易所或字段无效时
            RuntimeError: If API call fails
                        当API调用失败时
        """
        try:
            # Validate inputs / 验证输入
            if exchanges is None:
                exchanges = self.future_exchanges
            if isinstance(exchanges, str):
                exchanges = [exchanges]
                
            # Validate exchanges / 验证交易所
            invalid_exchanges = set(exchanges) - set(['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE'])
            if invalid_exchanges:
                raise ValueError(f"Invalid exchanges: {invalid_exchanges}")
                
            total_data = pd.DataFrame()
            
            # Process each exchange / 处理每个交易所
            for exchange in exchanges:
                try:
                    # Call GoldMiner API / 调用掘金API
                    data = get_symbol_infos(sec_type1=1040, exchanges=exchange, df=True)
                    
                    if data.empty:
                        continue
                        
                    # Format dates / 格式化日期
                    data['list_date'] = pd.to_datetime(data['listed_date']).dt.strftime('%Y%m%d')
                    data['delist_date'] = pd.to_datetime(data['delisted_date']).dt.strftime('%Y%m%d')
                    
                    # Add timestamps / 添加时间戳
                    data['list_datestamp'] = data['list_date'].map(lambda x: util_make_date_stamp(x))
                    data['delist_datestamp'] = data['delist_date'].map(lambda x: util_make_date_stamp(x))
                    
                    # Filter by cursor_date if provided / 如果提供了参考日期则进行过滤
                    if cursor_date:
                        cursor_stamp = util_make_date_stamp(cursor_date)
                        mask = (data['list_datestamp'] <= cursor_stamp) & (
                            (data['delist_datestamp'] >= cursor_stamp) |
                            (data['delist_datestamp'].isna())
                        )
                        data = data[mask]
                    
                    # Filter by symbols if provided / 如果提供了合约代码则进行过滤
                    if symbols:
                        data = data[data['symbol'].isin(symbols)]
                    
                    # Select fields if provided / 如果提供了字段列表则进行选择
                    if fields:
                        missing_fields = set(fields) - set(data.columns)
                        if missing_fields:
                            raise ValueError(f"Invalid fields: {missing_fields}")
                        data = data[fields]
                    
                    total_data = pd.concat([total_data, data], ignore_index=True)
                    
                except Exception as e:
                    self._handle_error(e, f"fetching contracts for exchange {exchange}")
            
            # Ensure required columns exist / 确保必需的列存在
            required_columns = ['symbol', 'name', 'list_date', 'delist_date',
                              'list_datestamp', 'delist_datestamp', 'exchange']
            return self._format_response(total_data, required_columns)
            
        except Exception as e:
            self._handle_error(e, "fetch_get_future_contracts")