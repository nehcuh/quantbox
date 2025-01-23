from abc import ABC, abstractmethod
from typing import List, Dict, Union, Optional
from datetime import datetime, date

import pandas as pd


class BaseFetcher(ABC):
    """数据获取基类"""
    
    @abstractmethod
    def fetch_get_calendar(
        self,
        exchange: str,
        start_date: Optional[Union[str, int, date, datetime]] = None,
        end_date: Optional[Union[str, int, date, datetime]] = None
    ) -> pd.DataFrame:
        """从远程数据源获取交易日历
        
        Args:
            exchange: 交易所代码，如 SSE, SZSE
            start_date: 开始日期，如果为None则获取从1990年至今的数据
            end_date: 结束日期，如果为None则获取从start_date至今的数据
            
        Returns:
            pd.DataFrame: 包含以下列的DataFrame：
                - exchange: str, 交易所代码
                - trade_date: int, 交易日期，格式为YYYYMMDD
                - pretrade_date: int, 前一交易日，格式为YYYYMMDD
                - datestamp: int, 纳秒级时间戳
        """
        pass
    
    @abstractmethod
    def fetch_calendar(
        self,
        exchange: str,
        start_date: Optional[Union[str, int, date, datetime]] = None,
        end_date: Optional[Union[str, int, date, datetime]] = None
    ) -> pd.DataFrame:
        """从本地数据库获取交易日历
        
        Args:
            exchange: 交易所代码，如 SSE, SZSE
            start_date: 开始日期，如果为None则获取从1990年至今的数据
            end_date: 结束日期，如果为None则获取从start_date至今的数据
            
        Returns:
            pd.DataFrame: 包含以下列的DataFrame：
                - exchange: str, 交易所代码
                - trade_date: int, 交易日期，格式为YYYYMMDD
                - pretrade_date: int, 前一交易日，格式为YYYYMMDD
                - datestamp: int, 纳秒级时间戳
        """
        pass
    
    @abstractmethod
    def is_trade_date(
        self,
        date: Union[str, int, datetime],
        exchange: str = "SSE"
    ) -> bool:
        """检查日期是否为交易日
        
        Args:
            date: 需要检查的日期
            exchange: 交易所代码，默认为SSE
            
        Returns:
            bool: 是否为交易日
        """
        pass
    
    @abstractmethod
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
            Dict[str, bool]: 日期到是否为交易日的映射，日期格式为YYYY-MM-DD
        """
        pass
    
    @abstractmethod
    def get_previous_trade_date(
        self,
        date: Union[str, int, datetime],
        exchange: str = "SSE"
    ) -> str:
        """获取前一交易日
        
        Args:
            date: 当前日期
            exchange: 交易所代码，默认为SSE
            
        Returns:
            str: 前一交易日，格式为YYYY-MM-DD
        """
        pass
    
    @abstractmethod
    def get_next_trade_date(
        self,
        date: Union[str, int, datetime],
        exchange: str = "SSE"
    ) -> str:
        """获取下一交易日
        
        Args:
            date: 当前日期
            exchange: 交易所代码，默认为SSE
            
        Returns:
            str: 下一交易日，格式为YYYY-MM-DD
        """
        pass
