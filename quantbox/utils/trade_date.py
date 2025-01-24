from typing import List, Dict, Union, Optional
from datetime import datetime, date
import pandas as pd
from ..data.fetcher.base_fetcher import BaseFetcher
from ..data.fetcher.tushare_fetcher import TushareFetcher


class TradeDateUtils:
    """交易日期工具类"""
    
    def __init__(self, data_fetcher: Optional[BaseFetcher] = None):
        """初始化交易日期工具类
        
        Args:
            data_fetcher: 数据获取器，用于获取交易日历数据。如果不指定，则使用 TushareFetcher
        """
        self._fetcher = data_fetcher if data_fetcher is not None else TushareFetcher()
    
    def get_previous_trade_date(
        self,
        date: Optional[Union[str, int, datetime]] = None,
        n: int = 1,
        include_input_date: bool = False,
        exchange: str = "SSE",
        start_date: Optional[Union[str, int, date, datetime]] = None,
        end_date: Optional[Union[str, int, date, datetime]] = None
    ) -> Union[str, List[str]]:
        """获取前N个交易日
        
        Args:
            date: 当前日期，如果为None则使用当前日期
            n: 获取前N个交易日，默认为1
            include_input_date: 如果输入日期是交易日，是否将其纳入统计，默认为False
            exchange: 交易所代码，默认为SSE
            start_date: 开始日期，可选
            end_date: 结束日期，可选
            
        Returns:
            如果n=1，返回前一个交易日，格式为YYYY-MM-DD
            如果n>1，返回前N个交易日列表，格式为[YYYY-MM-DD, ...]，按时间倒序排列
        """
        # 如果没有指定日期，使用当前日期
        if date is None:
            date = datetime.now()
            
        return self._fetcher.get_previous_trade_date(
            date=date,
            n=n,
            include_input_date=include_input_date,
            exchange=exchange,
            start_date=start_date,
            end_date=end_date
        )
    
    def get_next_trade_date(
        self,
        date: Optional[Union[str, int, datetime]] = None,
        n: int = 1,
        include_input_date: bool = False,
        exchange: str = "SSE",
        start_date: Optional[Union[str, int, date, datetime]] = None,
        end_date: Optional[Union[str, int, date, datetime]] = None
    ) -> Union[str, List[str]]:
        """获取后N个交易日
        
        Args:
            date: 当前日期，如果为None则使用当前日期
            n: 获取后N个交易日，默认为1
            include_input_date: 如果输入日期是交易日，是否将其纳入统计，默认为False
            exchange: 交易所代码，默认为SSE
            start_date: 开始日期，可选
            end_date: 结束日期，可选
            
        Returns:
            如果n=1，返回下一个交易日，格式为YYYY-MM-DD
            如果n>1，返回后N个交易日列表，格式为[YYYY-MM-DD, ...]，按时间顺序排列
        """
        # 如果没有指定日期，使用当前日期
        if date is None:
            date = datetime.now()
            
        return self._fetcher.get_next_trade_date(
            date=date,
            n=n,
            include_input_date=include_input_date,
            exchange=exchange,
            start_date=start_date,
            end_date=end_date
        )
    
    def is_trade_date(
        self,
        date: Optional[Union[str, int, datetime]] = None,
        exchange: str = "SSE"
    ) -> bool:
        """检查日期是否为交易日
        
        Args:
            date: 需要检查的日期，如果为None则使用当前日期
            exchange: 交易所代码，默认为SSE
            
        Returns:
            bool: 是否为交易日
        """
        # 如果没有指定日期，使用当前日期
        if date is None:
            date = datetime.now()
            
        return self._fetcher.is_trade_date(date=date, exchange=exchange)
    
    def batch_is_trade_date(
        self,
        dates: List[Union[str, int, datetime]],
        exchange: str = "SSE"
    ) -> Dict[str, bool]:
        """批量检查日期是否为交易日
        
        Args:
            dates: 需要检查的日期列表
            exchange: 交易所代码，默认为SSE
            
        Returns:
            Dict[str, bool]: 日期到是否为交易日的映射，日期格式为YYYYMMDD
        """
        return self._fetcher.batch_is_trade_date(dates=dates, exchange=exchange)
