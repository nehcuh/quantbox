from datetime import datetime, date
from typing import Union, List, Optional
import pandas as pd
from pydantic import BaseModel
from enum import Enum

class Market(str, Enum):
    """交易市场枚举"""
    ASHARE = "ashare"  # A股市场
    HKEX = "hkex"    # 港股市场
    US = "us"        # 美股市场
    CRYPTO = "crypto"  # 加密货币市场

class TradingCalendar:
    """交易日历类，处理不同市场的交易日期"""
    
    def __init__(self, market: Market = Market.ASHARE):
        self.market = market
        self._trading_dates: Optional[pd.DatetimeIndex] = None
        self._holidays: Optional[List[date]] = None
        
    def is_trading_day(self, check_date: Union[str, date, datetime]) -> bool:
        """判断是否为交易日"""
        if isinstance(check_date, str):
            check_date = pd.to_datetime(check_date).date()
        elif isinstance(check_date, datetime):
            check_date = check_date.date()
            
        # 确保交易日历已加载
        self._ensure_calendar_loaded()
        return check_date in self._trading_dates

    def next_trading_day(self, from_date: Union[str, date, datetime]) -> date:
        """获取下一个交易日"""
        if isinstance(from_date, str):
            from_date = pd.to_datetime(from_date).date()
        elif isinstance(from_date, datetime):
            from_date = from_date.date()
            
        self._ensure_calendar_loaded()
        next_dates = self._trading_dates[self._trading_dates > pd.Timestamp(from_date)]
        if len(next_dates) == 0:
            raise ValueError(f"No trading day found after {from_date}")
        return next_dates[0].date()

    def prev_trading_day(self, from_date: Union[str, date, datetime]) -> date:
        """获取上一个交易日"""
        if isinstance(from_date, str):
            from_date = pd.to_datetime(from_date).date()
        elif isinstance(from_date, datetime):
            from_date = from_date.date()
            
        self._ensure_calendar_loaded()
        prev_dates = self._trading_dates[self._trading_dates < pd.Timestamp(from_date)]
        if len(prev_dates) == 0:
            raise ValueError(f"No trading day found before {from_date}")
        return prev_dates[-1].date()

    def trading_days_between(self, start_date: Union[str, date, datetime],
                           end_date: Union[str, date, datetime]) -> List[date]:
        """获取两个日期之间的所有交易日"""
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date).date()
        elif isinstance(start_date, datetime):
            start_date = start_date.date()
            
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date).date()
        elif isinstance(end_date, datetime):
            end_date = end_date.date()
            
        self._ensure_calendar_loaded()
        mask = (self._trading_dates >= pd.Timestamp(start_date)) & \
               (self._trading_dates <= pd.Timestamp(end_date))
        return [d.date() for d in self._trading_dates[mask]]

    def _ensure_calendar_loaded(self):
        """确保交易日历数据已加载"""
        if self._trading_dates is None:
            self._load_calendar()

    def _load_calendar(self):
        """加载交易日历数据
        
        这里先使用简单的实现，后续可以从数据源加载实际的交易日历
        """
        # 生成2000年到2030年的所有日期
        all_dates = pd.date_range(start='2000-01-01', end='2030-12-31', freq='D')
        
        # 排除周末
        self._trading_dates = all_dates[all_dates.weekday < 5]
        
        # TODO: 从数据源加载实际的交易日历和节假日数据
        # self._holidays = []  # 节假日列表
        # self._trading_dates = self._trading_dates[~self._trading_dates.isin(self._holidays)]

class MarketTime(BaseModel):
    """市场交易时间"""
    market: Market
    morning_open: str = "09:30"
    morning_close: str = "11:30"
    afternoon_open: str = "13:00"
    afternoon_close: str = "15:00"
    
    def is_trading_time(self, check_time: Union[str, datetime]) -> bool:
        """判断是否为交易时间"""
        if isinstance(check_time, str):
            check_time = datetime.strptime(check_time, "%H:%M").time()
        elif isinstance(check_time, datetime):
            check_time = check_time.time()
            
        morning_open = datetime.strptime(self.morning_open, "%H:%M").time()
        morning_close = datetime.strptime(self.morning_close, "%H:%M").time()
        afternoon_open = datetime.strptime(self.afternoon_open, "%H:%M").time()
        afternoon_close = datetime.strptime(self.afternoon_close, "%H:%M").time()
        
        return (morning_open <= check_time <= morning_close) or \
               (afternoon_open <= check_time <= afternoon_close)
