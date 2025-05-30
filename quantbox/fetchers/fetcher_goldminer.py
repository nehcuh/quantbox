import datetime
import re
from typing import List, Optional, Union
import math
import pandas as pd
import platform
import warnings

if platform.system() != 'Darwin':  # Not macOS
    from gm.api import get_symbol_infos, set_token, fut_get_transaction_rankings, history_n, get_trading_dates_by_year
else:
    warnings.warn("GoldMiner API is not supported on macOS")
    get_symbol_infos = None
    set_token = None
    fut_get_transaction_rankings = None
    history_n = None
    get_trading_dates = None

from quantbox.fetchers.base import BaseFetcher
from quantbox.fetchers.local_fetcher import LocalFetcher
from quantbox.util.basic import (
    DATABASE,
    EXCHANGES,
    STOCK_EXCHANGES,
    QUANTCONFIG,
)
from quantbox.util.date_utils import util_make_date_stamp
from quantbox.util.tools import (
    util_format_future_symbols,
    util_format_stock_symbols,
    util_to_json_from_pandas,
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
        self.exchanges = EXCHANGES
        self.stock_exchanges = STOCK_EXCHANGES
        self.future_exchanges = FUTURE_EXCHANGES
        self.client = DATABASE
        self.default_start = "2010-01-01"
        set_token(QUANTCONFIG.gm_token)

    def _format_symbol(self, symbol: str) -> str:
        """
        Format symbol to GoldMiner API format.
        将合约代码格式化为掘金量化API格式。

        Supports the following formats:
        支持以下格式：
        1. Regular contracts (普通合约):
           - With exchange (带交易所): SHFE.rb2011
           - Without exchange (不带交易所): rb2011
        2. Virtual contracts (虚拟合约):
           - Main contract (主力): SHFE.RB
           - Sub-main contract (次主力): SHFE.RB22
           - Weighted index (加权指数): SHFE.RB99
           - Current month (当月): SHFE.RB00
           - Next month (下月): SHFE.RB01
           - Next quarter (下季): SHFE.RB02
           - Next next quarter (隔季): SHFE.RB03

        Args:
            symbol: Contract symbol (合约代码)
                Examples: 'rb2011', 'SHFE.rb2011', 'RB', 'SHFE.RB'

        Returns:
            str: Formatted symbol with exchange prefix
                 带有交易所前缀的格式化合约代码
        """
        # If already has exchange prefix, return as is
        if '.' in symbol:
            exchange = symbol.split(".")[0]
            contract = symbol.split(".")[1]
            if exchange == "CZCE":
                if len(contract) > 4 and contract[2:6].isdigit():
                    contract = contract[:2] + contract[3:]
                    return f"{exchange}.{contract}".upper()
                else:
                    return f"{exchange}.{contract}".upper()
            else:
                return exchange + "." + contract.lower()

        # Handle regular contracts (lowercase symbols)
        fut_code = re.match(r'([A-Za-z]+)', symbol).group(1).upper()
        coll = DATABASE.future_contracts
        result = coll.find_one({'fut_code': fut_code})
        if result is None:
            raise ValueError(f"{symbol} 找不到相应交易所")
        exchange = result["exchange"]
        if exchange == "CZCE":
            if len(symbol) > 4 and symbol[2:6].isdigit():
                contract = symbol[:2] + symbol[3:]
                return f"{exchange}.{contract}".upper()
            else:
                return f"{exchange}.{symbol}".upper()
        else:
            return exchange + "." + symbol.lower()

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

            if exchanges is None:
                exchanges = self.future_exchanges
            if isinstance(exchanges, str):
                exchanges = exchanges.split(",")

            # Initialize result container
            total_holdings = pd.DataFrame()

            # 增加参数兼容性
            if isinstance(symbols, str):
                symbols = symbols.split(",")

            if symbols is not None:
                # formatted_symbols = [self._format_symbol(symbol) for symbol in symbols]
                formatted_symbols = util_format_future_symbols(symbols=symbols, format="gm", include_exchange=True)
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
                        holdings['exchange'] = holdings.symbol.apply(lambda x: x.split(".")[0])
                        holdings['datestamp'] = holdings['trade_date'].map(str).apply(lambda x: util_make_date_stamp(x))
                        total_holdings = pd.concat(
                            [total_holdings, holdings],
                            ignore_index=True
                        )
            else:
                # Process each exchange
                for exchange in exchanges:
                    try:
                        # 使用本地数据库获取合约信息
                        local_fetcher = LocalFetcher()
                        contracts = local_fetcher.fetch_future_contracts(
                            exchanges=exchange,
                            cursor_date=cursor_date or end_date
                        )
                        if not contracts.empty:
                            exchange_symbols = (contracts['exchange'] + '.' + contracts['symbol']).tolist()

                        # Format symbols for API - ensure proper case for each exchange
                        formatted_symbols = [self._format_symbol(symbol) for symbol in exchange_symbols]

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
                                holdings['exchange'] = holdings.symbol.apply(lambda x: x.split(".")[0])
                                holdings['datestamp'] = holdings['trade_date'].map(str).apply(lambda x: util_make_date_stamp(x))
                                total_holdings = pd.concat(
                                    [total_holdings, holdings],
                                    ignore_index=True
                                )

                    except Exception as e:
                        self._handle_error(
                            e,
                            f"fetching holdings for exchange {exchange}"
                        )
            return self._convert_gm_holdings_to_tushare_format(total_holdings)

        except Exception as e:
            self._handle_error(e, "fetch_get_holdings")

    def _convert_gm_holdings_to_tushare_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert GoldMiner holdings data format to match Tushare format.
        将掘金量化持仓数据格式转换为与Tushare一致的格式。

        Args:
            df: GoldMiner holdings DataFrame with columns:
                - symbol: Contract symbol with exchange prefix (e.g., 'DCE.m2501')
                - trade_date: Trading date
                - member_name: Broker name
                - indicator_number: Position volume
                - indicator_change: Volume change
                - ranking: Ranking
                - indicator: Type of indicator (volume/long/short)
                - ranking_change: Ranking change
                - exchange: Exchange code
                - datestamp: Date timestamp

        Returns:
            DataFrame with Tushare format:
                - trade_date: Trading date
                - symbol: Contract symbol without exchange prefix
                - broker: Broker name without '（代客）' suffix
                - vol: Trading volume
                - vol_chg: Volume change
                - long_hld: Long position
                - long_chg: Long position change
                - short_hld: Short position
                - short_chg: Short position change
                - exchange: Exchange code
                - datestamp: Date timestamp
        """
        # Remove exchange prefix from symbol and '（代客）' from broker names
        df['symbol'] = df['symbol'].str.split('.').str[1].str.upper()
        df['broker'] = df['member_name'].str.replace('（代客）', '')

        # Create separate dataframes for volume, long and short positions
        vol_df = df[df['indicator'] == 'volume'].copy()
        long_df = df[df['indicator'] == 'long'].copy()
        short_df = df[df['indicator'] == 'short'].copy()

        # Rename columns for volume data
        vol_df = vol_df.rename(columns={
            'indicator_number': 'vol',
            'indicator_change': 'vol_chg'
        })[['trade_date', 'symbol', 'broker', 'vol', 'vol_chg', 'exchange', 'datestamp']]

        # Rename columns for long position data
        long_df = long_df.rename(columns={
            'indicator_number': 'long_hld',
            'indicator_change': 'long_chg'
        })[['trade_date', 'symbol', 'broker', 'long_hld', 'long_chg']]

        # Rename columns for short position data
        short_df = short_df.rename(columns={
            'indicator_number': 'short_hld',
            'indicator_change': 'short_chg'
        })[['trade_date', 'symbol', 'broker', 'short_hld', 'short_chg']]

        # Merge all dataframes
        result = pd.merge(
            vol_df,
            long_df,
            on=['trade_date', 'symbol', 'broker'],
            how='outer'
        )

        result = pd.merge(
            result,
            short_df,
            on=['trade_date', 'symbol', 'broker'],
            how='outer'
        )

        # Ensure all numeric columns are float type
        numeric_columns = ['vol', 'vol_chg', 'long_hld', 'long_chg', 'short_hld', 'short_chg']
        for col in numeric_columns:
            if col in result.columns:
                result[col] = result[col].astype(float)

        # Sort by volume (descending) and fill any missing values with NaN
        result = result.sort_values(['trade_date', 'symbol', 'vol'], ascending=[True, True, False])

        # Reorder columns to match Tushare format
        columns = [
            'trade_date', 'symbol', 'broker', 'vol', 'vol_chg',
            'long_hld', 'long_chg', 'short_hld', 'short_chg',
            'exchange', 'datestamp'
        ]
        result.loc[:, 'exchange'] = result['exchange'].ffill()
        result.loc[:, 'datestamp'] = result['datestamp'].ffill()

        return result[columns]

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
                    dates = get_trading_dates_by_year(
                        exchange=gm_exchange,
                        start_year=start_date.year,
                        end_year=end_date.year
                    )

                    if not dates:
                        continue

                    # Create DataFrame with all required information
                    # 创建包含所有必需信息的DataFrame
                    dates["exchange"] = gm_exchange
                    # Sort and calculate previous trading date
                    df = dates[["exchange", "trade_date", "pre_trade_date"]]
                    # 排序并计算前一交易日
                    df = df.sort_values('trade_date')

                    # Add datestamp
                    # 添加日期戳
                    df["datestamp"] = df['trade_date'].apply(lambda x: util_make_date_stamp(x))

                    # Format dates
                    # 格式化日期
                    df['trade_date'] = df['trade_date'].dt.strftime('%Y-%m-%d')
                    df['pre_trade_date'] = df['pre_trade_date'].dt.strftime('%Y-%m-%d')

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
        exchange: str = "DCE",
        spec_name: Union[str, List[str], None] = None,
        cursor_date: Optional[str] = None,
        fields: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        获取期货合约信息。

        注意：掘金量化API不支持获取历史合约信息，此方法将返回空DataFrame。
        请使用Tushare API获取合约信息。
        """
        return pd.DataFrame()

    def get_gm_data(
        self,
        symbol: str,
        frequency: str = '1d',
        start_time: Union[str, datetime.datetime] = None,
        end_time: Union[str, datetime.datetime] = None,
        fields: Union[List[str], None] = None,
        adjust: int = 0,
        df: bool = True
    ) -> pd.DataFrame:
        """
        Get historical market data from GoldMiner API using the history function.
        使用掘金量化API的history函数获取历史行情数据。

        Args:
            symbol: Trading symbol with exchange prefix (e.g., 'SHFE.cu2403')
                   带有交易所前缀的交易代码（如'SHFE.cu2403'）
            frequency: Data frequency, defaults to '1d' for daily data
                      数据频率，默认为'1d'（日线数据）
                Supported: ['tick', '1d', '60s', etc.]
                支持: ['tick', '1d', '60s' 等]
            start_time: Start time for data query
                       数据查询起始时间
                Format: 'YYYY-MM-DD' or datetime object
                格式：'YYYY-MM-DD' 或 datetime 对象
            end_time: End time for data query
                     数据查询结束时间
                Format: 'YYYY-MM-DD' or datetime object
                格式：'YYYY-MM-DD' 或 datetime 对象
            fields: List of fields to return, defaults to all available fields
                   要返回的字段列表。如果为 None，则返回所有可用字段。
            adjust: Price adjustment mode
                   价格复权模式
                0: No adjustment / 不复权
                1: Pre-adjustment / 前复权
                2: Post-adjustment / 后复权
            df: Whether to return DataFrame format, defaults to True
                是否返回DataFrame格式，默认为True

        Returns:
            pd.DataFrame: Historical market data with specified fields
                         包含指定字段的历史行情数据

        Raises:
            ValueError: If invalid parameters are provided
                      当提供的参数无效时
            RuntimeError: If API call fails
                        当API调用失败时
        """
        try:
            # Convert datetime objects to strings if necessary
            if isinstance(start_time, datetime.datetime):
                start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
            if isinstance(end_time, datetime.datetime):
                end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')

            # Format fields string if provided
            fields_str = ','.join(fields) if fields else None

            # Call GoldMiner API history function
            data = history_n(
                symbol=symbol,
                frequency=frequency,
                start_time=start_time,
                end_time=end_time,
                fields=fields_str,
                adjust=adjust,
                df=df
            )

            return data if df else pd.DataFrame(data)

        except Exception as e:
            self._handle_error(e, f"getting market data for {symbol}")
            return pd.DataFrame() if df else []

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
        This method is not implemented in GoldMiner fetcher.
        Please use TuShare fetcher for future daily data.
        """
        raise NotImplementedError(
            "fetch_get_future_daily is not implemented in GoldMiner fetcher. "
            "Please use TuShare fetcher for future daily data."
        )

if __name__ == "__main__":
    gm_fetcher = GMFetcher()
    # df2 = gm_fetcher.fetch_get_holdings(cursor_date="2024-11-21", symbols="M2501")
    df = gm_fetcher.fetch_get_holdings(cursor_date="2023-10-11", symbols="M2312")
