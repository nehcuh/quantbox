import datetime
import time
import re
import functools
import logging
from typing import List, Optional, Union, Dict, Any, Tuple
import pandas as pd
import numpy as np

from ..config.config_loader import get_config_loader, list_futures_exchanges
from ..util.exchange_utils import (
    validate_exchanges,
    get_exchange_for_data_source,
    convert_exchanges_for_data_source
)
from ..util.date_utils import date_to_int, int_to_date_str, util_make_date_stamp
from ..util.tools import util_format_stock_symbols, util_format_future_symbols
from .local_fetcher import LocalFetcher
from .base import BaseFetcher

# Configure logger for this module
logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple rate limiter for API calls
    """

    def __init__(self, calls_per_second: float = 1.0):
        """
        Initialize rate limiter

        Args:
            calls_per_second: Maximum API calls per second
        """
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0.0

    def wait_if_needed(self):
        """Wait if necessary to respect rate limit"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time

        if time_since_last_call < self.min_interval:
            sleep_time = self.min_interval - time_since_last_call
            time.sleep(sleep_time)

        self.last_call_time = time.time()

class TSFetcher(BaseFetcher):
    """
    优化性能和统一日期处理的 TuShare 数据获取器

    该类提供了从 TuShare API 获取各种金融数据的方法，包括交易日历、股票列表、
    期货合约、持仓数据和日线行情数据。它继承自 BaseFetcher，确保了不同数据源之间
    的一致性接口和错误处理。
    """
    
    def __init__(self, rate_limit: float = 2.0):
        """初始化 TSFetcher，包含 TuShare API 连接、缓存和速率限制

        Args:
            rate_limit: 每秒最大 API 调用次数（默认：2.0）
        """
        try:
            config_loader = get_config_loader()
            self.pro = config_loader.get_tushare_pro()
            self.default_start = "1990-12-19"  # 可以从配置获取
            self.local_fetcher = LocalFetcher()

            # 缓存设置
            self._cache_ttl = 3600  # 缓存有效期（秒）
            self._cache: Dict[str, Tuple[float, Any]] = {}  # {key: (timestamp, data)}

            # 速率限制
            self.rate_limiter = RateLimiter(rate_limit)

            logger.info(f"TSFetcher 初始化成功，速率限制：{rate_limit} 次/秒")
        except Exception as e:
            logger.error(f"TSFetcher 初始化失败：{str(e)}")
            raise RuntimeError(f"TSFetcher 初始化失败：{str(e)}") from e

    def _handle_error(self, error: Exception, context: str, reraise: bool = True) -> None:
        """
        增强的错误处理，包含日志记录

        Args:
            error: 发生的异常
            context: 错误发生的上下文
            reraise: 是否重新抛出异常
        """
        error_msg = f"在 {context} 中发生错误：{str(error)}"
        logger.error(error_msg, exc_info=True)

        if reraise:
            # 带有额外上下文信息重新抛出
            raise type(error)(error_msg) from error

    def _log_api_call(self, method: str, params: Dict[str, Any], success: bool = True, result_count: int = 0) -> None:
        """
        记录 API 调用用于监控和调试

        Args:
            method: API 方法名
            params: API 调用中使用的参数
            success: API 调用是否成功
            result_count: 返回的记录数
        """
        if success:
            logger.info(f"API 调用成功：{method}，参数 {params}，返回 {result_count} 条记录")
        else:
            logger.warning(f"API 调用失败：{method}，参数 {params}")

    def _get_cache_key(self, *args, **kwargs) -> str:
        """
        从函数参数生成缓存键

        将函数参数转换为缓存键。这个实现很简单，但对于我们的用例来说足够了。

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
        """从缓存获取数据，包含错误处理

        Args:
            key: 缓存键

        Returns:
            Optional[Any]: 缓存的数据，如果未找到或已过期则返回 None
        """
        try:
            if key not in self._cache:
                logger.debug(f"缓存未命中：{key}")
                return None

            timestamp, data = self._cache[key]
            if time.time() - timestamp > self._cache_ttl:
                # 缓存已过期
                del self._cache[key]
                logger.debug(f"缓存已过期：{key}")
                return None

            logger.debug(f"缓存命中：{key}")
            return data
        except Exception as e:
            logger.warning(f"访问缓存时出错，键 {key}：{str(e)}")
            return None

    def _set_cache(self, key: str, data: Any):
        """将数据存储到缓存，包含错误处理

        Args:
            key: 缓存键
            data: 要缓存的数据
        """
        try:
            self._cache[key] = (time.time(), data)
            logger.debug(f"数据已缓存：{key}")
        except Exception as e:
            logger.warning(f"缓存数据时出错，键 {key}：{str(e)}")

    def _api_call_with_rate_limit(self, api_method, *args, **kwargs):
        """
        进行 API 调用，包含速率限制和错误处理

        Args:
            api_method: 要调用的 API 方法
            *args: API 方法位置参数
            **kwargs: API 方法关键字参数

        Returns:
            API 响应数据
        """
        try:
            self.rate_limiter.wait_if_needed()
            result = api_method(*args, **kwargs)

            # 获取方法名（处理 functools.partial 对象）
            if hasattr(api_method, '__name__'):
                method_name = api_method.__name__
            elif hasattr(api_method, 'func'):
                # 如果是 functools.partial 对象
                method_name = api_method.func.__name__
            else:
                method_name = str(api_method)

            params = {"args": args, "kwargs": kwargs}
            result_count = len(result) if hasattr(result, '__len__') and result is not None else 0
            self._log_api_call(method_name, params, True, result_count)

            return result
        except Exception as e:
            # 获取方法名（处理 functools.partial 对象）
            if hasattr(api_method, '__name__'):
                method_name = api_method.__name__
            elif hasattr(api_method, 'func'):
                # 如果是 functools.partial 对象
                method_name = api_method.func.__name__
            else:
                method_name = str(api_method)

            params = {"args": args, "kwargs": kwargs}
            self._log_api_call(method_name, params, False, 0)

            logger.error(f"API 调用失败 {method_name}：{str(e)}")
            raise

    def _batch_fetch_trade_dates(
        self,
        start_dates: List[int],
        end_dates: List[int],
        exchanges: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        批量获取交易日历以减少 API 调用次数

        将多个查询合并为单个请求来减少网络开销。

        Args:
            start_dates: 起始日期列表（整数格式）
            end_dates: 结束日期列表（整数格式）
            exchanges: 交易所列表

        Returns:
            pd.DataFrame: 合并后的交易日历数据
        """
        try:
            # 转换为 Tushare 格式（convert_exchanges_for_data_source 内部已包含验证）
            tushare_exchanges = convert_exchanges_for_data_source(exchanges, "tushare")
            # 获取标准化的交易所代码用于日志记录
            standard_exchanges = validate_exchanges(exchanges)

            # 找出最早的开始日期和最晚的结束日期
            min_start = min(start_dates)
            max_end = max(end_dates)

            df_list = []
            # 为每个交易所分别获取数据，确保使用正确的交易所格式
            for i, tushare_exchange in enumerate(tushare_exchanges):
                try:
                    original_exchange = standard_exchanges[i]
                    # 获取特定交易所的交易日历数据
                    df = self._api_call_with_rate_limit(
                        self.pro.trade_cal,
                        exchange=tushare_exchange,
                        start_date=str(min_start),
                        end_date=str(max_end),
                        is_open='1'
                    )

                    if df.empty:
                        continue

                    # 重命名列并添加交易所信息
                    df = df.rename(columns={
                        'cal_date': 'date_int',
                        'pretrade_date': 'pretrade_date'
                    })
                    df['exchange'] = original_exchange  # 使用标准化的交易所代码
                    df['date_int'] = df['date_int'].astype(int)

                    df_list.append(df)

                except Exception as e:
                    logger.warning(f"Failed to fetch trade calendar for exchange {original_exchange}: {str(e)}")
                    continue

            if not df_list:
                return pd.DataFrame()

            # 合并所有交易所的数据
            df = pd.concat(df_list, ignore_index=True)

            # 使用统一的日期格式化函数
            df['trade_date'] = df['date_int'].apply(int_to_date_str)
            df['pretrade_date'] = df['pretrade_date'].apply(
                lambda x: int_to_date_str(int(x)) if pd.notna(x) else None
            )

            # 使用项目的日期工具函数添加时间戳（性能更好）
            df['datestamp'] = df['trade_date'].apply(util_make_date_stamp)

            return df[['exchange', 'trade_date', 'pretrade_date', 'datestamp', 'date_int']]

        except Exception as e:
            self._handle_error(e, "batch_fetch_trade_dates")

    def fetch_get_trade_dates(
        self,
        exchanges: Union[List[str], str, None] = None,
        start_date: Union[str, int, datetime.datetime, None] = None,
        end_date: Union[str, int, datetime.datetime, None] = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        获取交易日历，支持缓存

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
                - date_int: 整数格式日期 (YYYYMMDD)
        """
        try:
            if start_date is None:
                start_date = self.default_start
            if end_date is None:
                end_date = datetime.datetime.today()

            # 使用统一函数将日期标准化为整数格式
            start_int = date_to_int(start_date)
            end_int = date_to_int(end_date)

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

        except Exception as e:
            self._handle_error(e, "fetch_get_trade_dates")

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
        # Normalize all dates using unified function
        normalized_ranges = [
            (date_to_int(start), date_to_int(end))
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

    def _fetch_stocks_by_symbols(
        self,
        symbols: Union[str, List[str]],
        fields: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch stocks by symbols with optimized API calls

        Args:
            symbols: Stock symbols or list of symbols
            fields: Fields to return

        Returns:
            DataFrame of stock information
        """
        try:
            symbols = util_format_stock_symbols(symbols, "tushare")
            result = self._api_call_with_rate_limit(
                self.pro.stock_basic,
                symbols=",".join(symbols)
            )
            return result[fields] if fields else result
        except Exception as e:
            self._handle_error(e, f"fetch_stocks_by_symbols with symbols: {symbols}")

    def _fetch_stocks_by_names(
        self,
        names: Union[str, List[str]],
        fields: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch stocks by names with improved error handling

        Args:
            names: Stock names or list of names
            fields: Fields to return

        Returns:
            DataFrame of stock information
        """
        if isinstance(names, str):
            names = names.split(",")

        results = pd.DataFrame()
        successful_fetches = 0

        for name in names:
            try:
                df = self._api_call_with_rate_limit(self.pro.stock_basic, name=name)
                if not df.empty:
                    results = pd.concat([results, df], axis=0, ignore_index=True)
                    successful_fetches += 1
                    logger.debug(f"Successfully fetched stock data for name: {name}")
                else:
                    logger.warning(f"No data found for stock name: {name}")
            except Exception as e:
                logger.warning(f"Failed to fetch stocks by name '{name}': {str(e)}")
                continue

        logger.info(f"Successfully fetched data for {successful_fetches}/{len(names)} stock names")
        return results[fields] if fields else results

    def _fetch_stocks_by_markets(
        self,
        markets: Union[str, List[str]],
        list_status: Optional[str] = None,
        is_hs: Optional[str] = None,
        fields: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch stocks by markets

        Args:
            markets: Market types or list of market types
            list_status: Listing status
            is_hs: Whether it's a Shanghai-Hong Kong Stock Connect stock
            fields: Fields to return

        Returns:
            DataFrame of stock information
        """
        if isinstance(markets, str):
            markets = markets.split(",")

        results = pd.DataFrame()
        for market in markets:
            try:
                df = self._fetch_single_market_data(market, list_status, is_hs)
                results = pd.concat([results, df], axis=0, ignore_index=True)
            except Exception as e:
                self._handle_error(e, f"Failed to fetch stocks for market: {market}")

        return results[fields] if fields else results

    def _fetch_single_market_data(
        self,
        market: str,
        list_status: Optional[str] = None,
        is_hs: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch data for a single market

        Args:
            market: Market type
            list_status: Listing status
            is_hs: Whether it's a Shanghai-Hong Kong Stock Connect stock

        Returns:
            DataFrame of stock information for the market
        """
        if list_status:
            return self.pro.stock_basic(
                market=market,
                list_status=list_status,
                is_hs=is_hs
            )
        else:
            # Fetch all listing statuses
            statuses = ["L", "D", "P"]
            results = pd.DataFrame()
            for status in statuses:
                try:
                    df = self.pro.stock_basic(
                        market=market,
                        list_status=status,
                        is_hs=is_hs
                    )
                    results = pd.concat([results, df], axis=0, ignore_index=True)
                except Exception:
                    # Skip if no data for this status
                    continue
            return results

    def _fetch_stocks_by_exchanges(
        self,
        exchanges: Union[str, List[str]],
        list_status: Optional[str] = None,
        is_hs: Optional[str] = None,
        fields: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch stocks by exchanges with proper format conversion

        Args:
            exchanges: Exchange codes or list of exchange codes (standard format)
            list_status: Listing status
            is_hs: Whether it's a Shanghai-Hong Kong Stock Connect stock
            fields: Fields to return

        Returns:
            DataFrame of stock information
        """
        try:
            # 转换为 Tushare 格式（convert_exchanges_for_data_source 内部已包含验证）
            tushare_exchanges = convert_exchanges_for_data_source(exchanges, "tushare")
            # 获取标准化的交易所代码用于日志记录
            standard_exchanges = validate_exchanges(exchanges)

            results = pd.DataFrame()
            for i, exchange in enumerate(tushare_exchanges):
                try:
                    original_exchange = standard_exchanges[i]
                    df = self._fetch_single_exchange_data(exchange, list_status, is_hs)
                    logger.debug(f"Successfully fetched stocks for exchange: {original_exchange} -> {exchange}")
                    results = pd.concat([results, df], axis=0, ignore_index=True)
                except Exception as e:
                    self._handle_error(e, f"Failed to fetch stocks for exchange: {original_exchange}", reraise=False)

            # Filter fields if specified
            if fields:
                if isinstance(fields, str):
                    field_list = [f.strip() for f in fields.split(',')]
                else:
                    field_list = fields
                # Only return columns that exist in the DataFrame
                available_fields = [f for f in field_list if f in results.columns]
                return results[available_fields] if available_fields else results
            else:
                return results

        except Exception as e:
            self._handle_error(e, "fetch_stocks_by_exchanges")

    def _fetch_single_exchange_data(
        self,
        exchange: str,
        list_status: Optional[str] = None,
        is_hs: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch data for a single exchange

        Args:
            exchange: Exchange code (already converted to Tushare format)
            list_status: Listing status
            is_hs: Whether it's a Shanghai-Hong Kong Stock Connect stock

        Returns:
            DataFrame of stock information for the exchange
        """
        try:
            if list_status:
                result = self._api_call_with_rate_limit(
                    self.pro.stock_basic,
                    exchange=exchange,
                    list_status=list_status,
                    is_hs=is_hs
                )
            else:
                # Fetch all listing statuses
                statuses = ["L", "D", "P"]
                results = pd.DataFrame()
                for status in statuses:
                    try:
                        df = self._api_call_with_rate_limit(
                            self.pro.stock_basic,
                            exchange=exchange,
                            list_status=status,
                            is_hs=is_hs
                        )
                        results = pd.concat([results, df], axis=0, ignore_index=True)
                    except Exception:
                        # Skip if no data for this status
                        continue
                result = results

            return result if not result.empty else pd.DataFrame()

        except Exception as e:
            logger.error(f"Failed to fetch data for exchange {exchange}: {str(e)}")
            return pd.DataFrame()

    def _fetch_all_stocks(
        self,
        list_status: Optional[str] = None,
        fields: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch all stocks with API rate limiting

        Args:
            list_status: Listing status
            fields: Fields to return

        Returns:
            DataFrame of all stock information
        """
        try:
            if list_status:
                result = self._api_call_with_rate_limit(
                    self.pro.stock_basic,
                    list_status=list_status
                )
            else:
                # Fetch all listing statuses
                statuses = ["L", "D", "P"]
                results = pd.DataFrame()
                for status in statuses:
                    try:
                        df = self._api_call_with_rate_limit(
                            self.pro.stock_basic,
                            list_status=status
                        )
                        results = pd.concat([results, df], axis=0, ignore_index=True)
                    except Exception:
                        # Skip if no data for this status
                        continue
                result = results

            return result[fields] if fields else result

        except Exception as e:
            self._handle_error(e, "fetch_all_stocks")
            return pd.DataFrame()

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
        获取股票列表，支持多种过滤选项

        该方法提供了统一的接口来从 TuShare API 获取股票列表，支持多种过滤选项，
        包括股票代码、名称、交易所、市场板块、上市状态和沪港通状态。

        Args:
            symbols: 股票代码 (Union[str, List[str], None])
                示例： "SZSE.000001", "SHSE.600000" 或 ["SZSE.000001", "SHSE.600000"]
                如果指定，忽略其他过滤器
            names: 股票名称 (Union[str, List[str], None])
                示例： "平安银行" 或 ["平安银行", "贵州茅台"]
                如果指定，忽略除 symbols 外的其他过滤器
            exchanges: 交易所代码 (Union[str, List[str], None])
                支持： ['SSE', 'SZSE', 'BSE']
                示例： "SSE" 或 ["SSE", "SZSE"]
            markets: 市场类型 (Union[str, List[str], None])
                支持： ['主板', '创业板', '科创板', 'CDR', '北交所']
                示例： "科创板" 或 ["科创板", "创业板"]
            list_status: 上市状态 (Union[str, List[str], None])
                支持： 'L' (上市), 'D' (退市), 'P' (暂停上市)
                默认： 'L'
            is_hs: 沪港通状态 (Union[str, None])
                支持： 'N' (否), 'H' (沪股通), 'S' (深股通)
            fields: 返回字段 (Union[str, None])
                示例： 'ts_code,symbol,name,area,industry,list_date'

        Returns:
            pd.DataFrame: 符合指定条件的股票列表

        Raises:
            ValueError: 当提供无效参数时
            RuntimeError: 当 API 调用失败时

        Examples:
            >>> fetcher = TSFetcher()
            >>> # 按代码获取
            >>> df = fetcher.fetch_get_stock_list(symbols="000001,600000")
            >>> # 按名称获取
            >>> df = fetcher.fetch_get_stock_list(names=["平安银行", "贵州茅台"])
            >>> # 按市场板块获取
            >>> df = fetcher.fetch_get_stock_list(markets=["科创板", "创业板"])
        """
        try:
            # 验证并准备字段
            if fields and isinstance(fields, list):
                fields = ",".join(fields)

            # 基于优先级的过滤：symbols > names > markets > exchanges > all
            if symbols:
                return self._fetch_stocks_by_symbols(symbols, fields)

            if names:
                return self._fetch_stocks_by_names(names, fields)

            if markets:
                return self._fetch_stocks_by_markets(markets, list_status, is_hs, fields)

            if exchanges:
                return self._fetch_stocks_by_exchanges(exchanges, list_status, is_hs, fields)

            # 如果没有指定过滤器，获取所有股票
            return self._fetch_all_stocks(list_status, fields)

        except Exception as e:
            self._handle_error(e, "fetch_get_stock_list")

    def fetch_get_future_contracts(
        self,
        exchange: Optional[str] = None,
        spec_name: Optional[Union[str, List[str]]] = None,
        cursor_date: Optional[Union[str, int, datetime.datetime]] = None,
        fields: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Fetch future contract information from TuShare.
        从 Tushare 获取期货合约信息。

        Args:
            exchange: Exchange to fetch data from, defaults to first futures exchange in config
                    要获取数据的交易所，默认为配置中的第一个期货交易所
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
        try:
            # 如果没有指定交易所，使用配置中的第一个期货交易所
            if exchange is None:
                futures_exchanges = list_futures_exchanges()
                exchange = futures_exchanges[0] if futures_exchanges else "DCE"

            # 转换为 Tushare 格式（convert_exchanges_for_data_source 内部已包含验证）
            tushare_exchanges = convert_exchanges_for_data_source(exchange, "tushare")
            tushare_exchange = tushare_exchanges[0] if tushare_exchanges else exchange

            logger.debug(f"Fetching future contracts: {exchange} -> {tushare_exchange}")

            # 确保必要字段存在
            required_fields = ["list_date", "delist_date", "name", "ts_code"]
            if fields:
                fields.extend([f for f in required_fields if f not in fields])
                # 获取合约信息，没有必要导入主力和连续合约，压根没有 list_date 和 delist_date
                data = self._api_call_with_rate_limit(
                    self.pro.fut_basic,
                    exchange=tushare_exchange,
                    fut_type="1",
                    fields=fields
                )
            else:
                data = self._api_call_with_rate_limit(
                    self.pro.fut_basic,
                    exchange=tushare_exchange,
                    fut_type="1"
                )

        except Exception as e:
            logger.error(f"Failed to fetch future contracts for exchange {exchange}: {str(e)}")
            return pd.DataFrame()

        # 使用标准化函数处理期货合约数据
        data = self._standardize_future_contract_data(data, exchange)

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

    def _standardize_future_contract_data(
        self,
        data: pd.DataFrame,
        exchange: str
    ) -> pd.DataFrame:
        """
        标准化期货合约数据格式

        Args:
            data: 原始期货合约数据
            exchange: 标准化的交易所代码

        Returns:
            pd.DataFrame: 标准化后的期货合约数据
        """
        if data.empty:
            return data

        # 处理日期 - 使用项目的日期工具函数替代 pd.to_datetime
        for date_col in ["list_date", "delist_date"]:
            if date_col in data.columns:
                # 使用项目的日期工具函数，性能更好
                data[f"{date_col}stamp"] = data[date_col].apply(lambda x: util_make_date_stamp(x) if pd.notna(x) else None)
                data[date_col] = data[f"{date_col}stamp"].apply(lambda x: int_to_date_str(x) if x is not None else None)

        # 提取中文名称
        data["chinese_name"] = data["name"].str.extract(r'(.+?)(?=\d{3,})')

        # 使用项目工具函数标准化合约代码
        if "ts_code" in data.columns:
            # 使用 util_format_future_symbols 进行标准化处理
            data["qbcode"] = data["ts_code"].apply(
                lambda x: util_format_future_symbols(x, format="standard", include_exchange=False)[0]
                if pd.notna(x) else x
            )

        # 使用配置模块进行交易所代码大小写处理
        # 获取交易所特定的大小写规则
        try:
            from ..config.config_loader import get_exchange_info
            exchange_info = get_exchange_info(exchange)
            # 对于某些交易所，symbol 需要转换为小写（与交易所实际格式一致）
            if exchange_info["code"] not in ["CZCE", "CFFEX"]:
                if "symbol" in data.columns:
                    data["symbol"] = data["symbol"].str.lower()
        except Exception as e:
            logger.warning(f"Failed to get exchange info for {exchange}: {e}")
            # 降级处理：保持原有的硬编码逻辑
            if exchange not in ["CZCE", "CFFEX"]:
                if "symbol" in data.columns:
                    data["symbol"] = data["symbol"].str.lower()

        return data

    def _standardize_future_daily_data(
        self,
        data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        标准化期货日线数据格式

        Args:
            data: 原始期货日线数据

        Returns:
            pd.DataFrame: 标准化后的期货日线数据
        """
        if data.empty:
            return data

        # 处理日期 - 使用项目的日期工具函数
        if "trade_date" in data.columns:
            data["datestamp"] = data["trade_date"].map(str).apply(
                lambda x: util_make_date_stamp(x)
            )
            data["trade_date"] = data["trade_date"].apply(
                lambda x: int_to_date_str(date_to_int(x)) if pd.notna(x) else None
            )

        # 处理 ts_code 分解为 symbol 和 exchange
        if "ts_code" in data.columns:
            columns = data.columns.tolist()

            # 使用项目工具函数提取 symbol
            data["symbol"] = data["ts_code"].apply(
                lambda x: util_format_future_symbols(x, format="standard", include_exchange=False)[0]
                if pd.notna(x) else x
            )

            # 使用项目工具函数获取标准交易所代码
            data["exchange"] = data["ts_code"].apply(
                lambda x: util_format_future_symbols(x, format="standard", include_exchange=True)[0].split('.')[0]
                if pd.notna(x) else x
            )

            # 重新组织列顺序
            columns = ["symbol", "exchange"] + [col for col in columns if col not in ["symbol", "exchange", "ts_code"]]
            data = data[columns]

        return data

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
            # Convert to Tushare format for API calls (convert_exchanges_for_data_source handles validation internally)
            tushare_exchanges = convert_exchanges_for_data_source(exchanges or list_futures_exchanges(), "tushare")

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
            for i, exchange in enumerate(validated_exchanges):
                try:
                    tushare_exchange = tushare_exchanges[i]
                    logger.debug(f"Processing holdings for exchange: {exchange} -> {tushare_exchange}")

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
                                data = self._api_call_with_rate_limit(
                                    self.pro.fut_holding,
                                    trade_date=trade_date.strftime("%Y%m%d"),
                                    symbol=symbol,
                                    exchange=tushare_exchange,
                                )

                                if not data.empty:
                                    # Add exchange and datestamp using unified function
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
                                        data = self._api_call_with_rate_limit(
                                            self.pro.fut_holding,
                                            trade_date=trade_date.strftime("%Y%m%d"),
                                            symbol=symbol,
                                            exchange=tushare_exchange,
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
            # 使用项目的日期工具函数进行格式化（性能更好）
            result_df["trade_date"] = result_df["trade_date"].apply(
                lambda x: int_to_date_str(date_to_int(x)) if pd.notna(x) else None
            )

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
                symbols = util_format_future_symbols(symbols=symbols, format="tushare")
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
                # Convert to Tushare format for API calls (convert_exchanges_for_data_source handles validation internally)
                default_futures_exchanges = list_futures_exchanges()
                tushare_exchanges = convert_exchanges_for_data_source(exchanges or default_futures_exchanges, "tushare")
                # Get standard exchanges for logging
                standard_exchanges = validate_exchanges(exchanges or default_futures_exchanges)

                results = pd.DataFrame()
                for i, exchange in enumerate(tushare_exchanges):
                    original_exchange = standard_exchanges[i]
                    logger.debug(f"Fetching future daily for exchange: {original_exchange} -> {exchange}")

                    if fields:
                        df_local = self._api_call_with_rate_limit(
                            self.pro.fut_daily,
                            exchange=exchange,
                            start_date=pd.Timestamp(str(start_date)).strftime("%Y%m%d"),
                            end_date=pd.Timestamp(str(end_date)).strftime("%Y%m%d"),
                            fields=fields,
                        )
                    else:
                        df_local = self._api_call_with_rate_limit(
                            self.pro.fut_daily,
                            exchange=exchange,
                            start_date=pd.Timestamp(str(start_date)).strftime("%Y%m%d"),
                            end_date=pd.Timestamp(str(end_date)).strftime("%Y%m%d"),
                        )
                    results = pd.concat([results, df_local], axis=0)
        else:
            if cursor_date is None:
                cursor_date = datetime.date.today()
            latest_trade_date = self.local_fetcher.fetch_pre_trade_date(
                cursor_date=cursor_date, include=True
            )["trade_date"]
            if symbols:
                symbols = util_format_future_symbols(symbols=symbols, format="tushare")
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
                    exchanges = list_futures_exchanges()
                elif isinstance(exchanges, str):
                    exchanges = exchanges.split(",")

                # 转换为 Tushare 格式
                tushare_exchanges = convert_exchanges_for_data_source(exchanges, "tushare")

                results = pd.DataFrame()
                for i, exchange in enumerate(tushare_exchanges):
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
        # 使用标准化函数处理期货日线数据
        results = self._standardize_future_daily_data(results)
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
