"""Mock data fetcher for testing"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional

import pandas as pd

from quantbox.data.fetcher.base import DataFetcher
from tests.utils.mock_data import MockData


class MockDataFetcher(DataFetcher):
    """Mock data fetcher for testing"""
    
    def __init__(self):
        """Initialize mock data fetcher"""
        self._mock_data = MockData()
        
    def fetch_calendar(self, exchange: str, start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
        """Fetch calendar data"""
        return self._mock_data.generate_calendar_data(exchange)
        
    def fetch_stock_calendar(self, start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> pd.DataFrame:
        """Fetch stock calendar data"""
        return self.fetch_calendar("SSE", start_date, end_date)
        
    def fetch_futures_calendar(self, start_date: Optional[str] = None,
                             end_date: Optional[str] = None) -> pd.DataFrame:
        """Fetch futures calendar data"""
        return self.fetch_calendar("CFFEX", start_date, end_date)
        
    def fetch_stock_basic(self, fields: Optional[List[str]] = None) -> pd.DataFrame:
        """Fetch stock basic data"""
        return pd.DataFrame({
            "ts_code": ["000001.SZ", "600000.SH"],
            "symbol": ["000001", "600000"],
            "name": ["平安银行", "浦发银行"],
            "area": ["深圳", "上海"],
            "industry": ["银行", "银行"],
            "market": ["主板", "主板"],
            "exchange": ["SZSE", "SSE"],
            "list_status": ["L", "L"],
            "list_date": ["19910403", "19991110"],
            "delist_date": ["", ""],
            "is_hs": ["S", "S"]
        })
        
    def fetch_stock_daily(self, ts_code: str, start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> pd.DataFrame:
        """Fetch stock daily data"""
        return pd.DataFrame({
            "ts_code": [ts_code],
            "trade_date": ["20240102"],
            "open": [10.0],
            "high": [10.5],
            "low": [9.8],
            "close": [10.2],
            "pre_close": [10.0],
            "change": [0.2],
            "pct_chg": [2.0],
            "vol": [100000],
            "amount": [1020000.0]
        })
        
    def is_trade_date(self, date: str) -> bool:
        """Check if a date is a trade date"""
        # 转换日期格式为 YYYY-MM-DD
        if isinstance(date, str) and len(date) == 8:
            date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        return date in self._mock_data._trade_dates["SSE"]
        
    def batch_is_trade_date(self, dates: List[str]) -> Dict[str, bool]:
        """Check if multiple dates are trade dates"""
        return {date: self.is_trade_date(date) for date in dates}
        
    def get_next_trade_date_n(self, date: str, n: int) -> str:
        """Get next n trade date"""
        # 转换日期格式为 YYYY-MM-DD
        if isinstance(date, str) and len(date) == 8:
            date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
            
        # 获取交易日列表
        trade_dates = sorted(self._mock_data._trade_dates["SSE"])
        
        # 找到当前日期之后的第 n 个交易日
        current_idx = -1
        for i, trade_date in enumerate(trade_dates):
            if trade_date >= date:
                current_idx = i
                break
                
        if current_idx == -1:
            return ""
            
        target_idx = current_idx + n - 1
        if target_idx >= len(trade_dates):
            return ""
            
        return trade_dates[target_idx]
        
    def get_previous_trade_date_n(self, date: str, n: int) -> str:
        """Get previous n trade date"""
        # 转换日期格式为 YYYY-MM-DD
        if isinstance(date, str) and len(date) == 8:
            date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
            
        # 获取交易日列表
        trade_dates = sorted(self._mock_data._trade_dates["SSE"])
        
        # 找到当前日期之前的第 n 个交易日
        current_idx = -1
        for i, trade_date in enumerate(trade_dates):
            if trade_date >= date:
                current_idx = i
                break
                
        if current_idx == -1:
            return ""
            
        target_idx = current_idx - n
        if target_idx < 0:
            return ""
            
        return trade_dates[target_idx]
