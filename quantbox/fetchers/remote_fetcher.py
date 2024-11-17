"""
Remote Data Fetcher Module
远程数据获取器模块

This module provides a unified interface for fetching data from different remote sources.
本模块提供了一个统一的接口来从不同的远程数据源获取数据。

Available data sources:
可用数据源：
- TuShare (ts)
- GoldMiner (gm)
"""

from typing import List, Union, Optional, Dict, Any, Callable
import datetime
import functools
import time
import logging
import json
from pathlib import Path
import pandas as pd
import platform

from quantbox.fetchers.base import BaseFetcher
from quantbox.fetchers.fetcher_tushare import TSFetcher
from quantbox.fetchers.fetcher_goldminer import GMFetcher
from quantbox.fetchers.config import FetcherConfig
from quantbox.fetchers.monitoring import PerformanceMonitor, monitor_performance
from quantbox.fetchers.validation import DataValidator
from quantbox.util.basic import EXCHANGES, FUTURE_EXCHANGES, QUANTCONFIG

# Configure logging
# 配置日志
logger = logging.getLogger(__name__)

class RemoteFetcher(BaseFetcher):
    """
    A unified fetcher for remote data sources.
    统一的远程数据获取器。

    This class provides a unified interface to fetch data from different remote sources.
    The actual data source is determined by the engine parameter.
    该类提供了一个统一的接口来从不同的远程数据源获取数据。
    实际的数据源由 engine 参数决定。

    Supported engines:
    支持的引擎：
    - 'ts': TuShare
    - 'gm': GoldMiner
    """

    def __init__(
        self,
        engine: str = 'ts',
        config_file: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the RemoteFetcher.
        初始化远程数据获取器。

        Args:
            engine: Data source engine ('ts' for TuShare, 'gm' for GoldMiner)
                   数据源引擎 ('ts' 代表 TuShare，'gm' 代表掘金)
            config_file: Path to configuration file
                        配置文件路径
            **kwargs: Additional configuration parameters
                     额外的配置参数
        """
        super().__init__()
        self.engine = engine.lower()
        if self.engine == 'gm':
            try:
                import platform
                if platform.system() == 'Darwin':
                    logger.warning("GoldMiner API is not supported on macOS, falling back to TuShare")
                    self.engine = 'ts'
                    self._fetcher = TSFetcher()
                else:
                    self._fetcher = GMFetcher()
            except ImportError:
                logger.warning("GoldMiner API is not available, falling back to TuShare")
                self.engine = 'ts'
                self._fetcher = TSFetcher()
        elif self.engine == 'ts':
            self._fetcher = TSFetcher()
        else:
            raise ValueError(f"Unsupported engine: {self.engine}")

        # Load configuration
        self.config = (
            FetcherConfig.from_file(config_file)
            if config_file
            else FetcherConfig.default()
        )
        
        # Update config with kwargs
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        # Initialize components
        self._init_logging()
        self._init_monitoring()
        self._init_validation()

    def initialize(self):
        """
        Initialize the fetcher with necessary credentials and settings.
        使用必要的凭证和设置初始化获取器。
        """
        if hasattr(self._fetcher, 'initialize'):
            self._fetcher.initialize()

    def _init_logging(self):
        """Initialize logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def _init_monitoring(self):
        """Initialize performance monitoring."""
        self.monitor = PerformanceMonitor(
            slow_query_threshold=self.config.slow_query_threshold
        )

    def _init_validation(self):
        """Initialize data validation."""
        self.validator = DataValidator(
            required_fields=self.config.required_fields,
            validate_types=True
        )

    def _wrap_method(self, method: Callable) -> Callable:
        """
        Wrap a method with retry, cache, monitoring and validation decorators.
        使用重试、缓存、监控和验证装饰器包装方法。

        Args:
            method: Method to wrap
                   要包装的方法

        Returns:
            Wrapped method
            包装后的方法
        """
        @monitor_performance(self.monitor)
        @functools.wraps(method)
        def wrapped(*args, **kwargs):
            try:
                logger.info(f"Fetching data using {self.engine} engine")
                result = method(*args, **kwargs)

                # Validate result if it's a DataFrame
                if isinstance(result, pd.DataFrame):
                    method_name = method.__name__.replace('fetch_', '')
                    validation_result = self.validator.validate_dataframe(
                        result, method_name
                    )
                    if not validation_result.is_valid:
                        logger.warning(
                            "Data validation failed:\n" +
                            "\n".join(validation_result.error_messages)
                        )

                logger.info("Data fetched successfully")
                return result
            except Exception as e:
                logger.error(f"Error fetching data: {str(e)}")
                raise

        return wrapped

    def fetch_get_trade_dates(
        self,
        exchanges: Union[List[str], str, None] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch trading dates for specified exchanges.
        获取指定交易所的交易日期。

        Args:
            exchanges: Exchange(s) to fetch data from
                      要获取数据的交易所
            start_date: Start date of the date range
                       日期范围的开始日期
            end_date: End date of the date range
                     日期范围的结束日期

        Returns:
            DataFrame with trading dates
            包含交易日期的DataFrame
        """
        method = self._wrap_method(self._fetcher.fetch_get_trade_dates)
        return method(
            exchanges=exchanges,
            start_date=start_date,
            end_date=end_date
        )

    def fetch_get_future_contracts(
        self,
        exchanges: Union[List[str], str, None] = None,
        cursor_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch future contracts for specified exchanges.
        获取指定交易所的期货合约。

        Args:
            exchanges: Exchange(s) to fetch data from
                      要获取数据的交易所
            cursor_date: Reference date for fetching data
                        获取数据的参考日期

        Returns:
            DataFrame with future contracts
            包含期货合约的DataFrame
        """
        method = self._wrap_method(self._fetcher.fetch_get_future_contracts)
        return method(
            exchanges=exchanges,
            cursor_date=cursor_date
        )

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
            exchanges: Exchange(s) to fetch data from
                      要获取数据的交易所
            cursor_date: Reference date for fetching data
                        获取数据的参考日期
            start_date: Start date of the date range
                       日期范围的开始日期
            end_date: End date of the date range
                     日期范围的结束日期
            symbols: Symbol(s) to fetch data for
                    要获取数据的合约代码

        Returns:
            DataFrame with holdings data
            包含持仓数据的DataFrame
        """
        method = self._wrap_method(self._fetcher.fetch_get_holdings)
        return method(
            exchanges=exchanges,
            cursor_date=cursor_date,
            start_date=start_date,
            end_date=end_date,
            symbols=symbols
        )

    def fetch_get_future_daily(
        self,
        cursor_date: Union[str, datetime.date, int] = None,
        symbols: Union[str, List[str], None] = None,
        exchanges: Union[str, List[str], None] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch daily data for future contracts.
        获取期货合约的每日数据。

        Args:
            cursor_date: Reference date for fetching data
                        获取数据的参考日期
            symbols: Symbol(s) to fetch data for
                    要获取数据的合约代码
            exchanges: Exchange(s) to fetch data from
                      要获取数据的交易所
            start_date: Start date of the date range
                       日期范围的开始日期
            end_date: End date of the date range
                     日期范围的结束日期

        Returns:
            DataFrame with daily future data
            包含期货每日数据的DataFrame
        """
        method = self._wrap_method(self._fetcher.fetch_get_future_daily)
        return method(
            cursor_date=cursor_date,
            symbols=symbols,
            exchanges=exchanges,
            start_date=start_date,
            end_date=end_date
        )

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        return self.monitor.get_stats()

    def log_performance_stats(self) -> None:
        """Log current performance statistics"""
        if self.config.log_performance_stats:
            self.monitor.log_stats()
