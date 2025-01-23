"""Mock data fetcher for testing"""

from typing import Optional, List, Dict, Union
import pandas as pd

from quantbox.data.fetcher.base import DataFetcher
from tests.utils.mock_data import MockData


class MockDataFetcher(DataFetcher):
    """Mock data fetcher for testing"""
    
    def __init__(self):
        """Initialize mock data fetcher"""
        self.mock = MockData()
        self._calendar_cache = {}
    
    def fetch_calendar(self, exchange: str, start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
        """Mock fetch calendar data"""
        if exchange not in self._calendar_cache:
            self._calendar_cache[exchange] = self.mock.generate_calendar_data(exchange=exchange)
        return self._calendar_cache[exchange]
    
    def fetch_stock_basic(self) -> pd.DataFrame:
        """Mock fetch stock basic data"""
        return self.mock.generate_stock_basic_data()
    
    def fetch_stock_daily(self, ts_code: str, start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> pd.DataFrame:
        """Mock fetch stock daily data"""
        # TODO: Implement when needed
        return pd.DataFrame()
    
    def is_trade_date(self, date: str) -> bool:
        """Check if a date is a trade date"""
        df = self.fetch_calendar("SSE")  # Use SSE as default exchange
        return date in df["trade_date"].values
    
    def batch_is_trade_date(self, dates: List[str]) -> Dict[str, bool]:
        """Batch check if dates are trade dates"""
        df = self.fetch_calendar("SSE")  # Use SSE as default exchange
        trade_dates = set(df["trade_date"].values)
        return {date: date in trade_dates for date in dates}
    
    def get_next_trade_date_n(self, date: str, n: int = 1) -> Union[str, List[str]]:
        """Get next nth trade date"""
        df = self.fetch_calendar("SSE")  # Use SSE as default exchange
        trade_dates = sorted(df["trade_date"].values)
        try:
            idx = trade_dates.index(date)
            if n == 1:
                if idx + 1 < len(trade_dates):
                    return trade_dates[idx + 1]
                return ""
            else:
                if idx + n < len(trade_dates):
                    return trade_dates[idx + 1:idx + n + 1]
                return trade_dates[idx + 1:]
        except ValueError:
            return "" if n == 1 else []
    
    def get_previous_trade_date_n(self, date: str, n: int = 1) -> Union[str, List[str]]:
        """Get previous nth trade date"""
        df = self.fetch_calendar("SSE")  # Use SSE as default exchange
        trade_dates = sorted(df["trade_date"].values)
        try:
            idx = trade_dates.index(date)
            if n == 1:
                if idx > 0:
                    return trade_dates[idx - 1]
                return ""
            else:
                if idx >= n:
                    return list(reversed(trade_dates[idx - n:idx]))
                return list(reversed(trade_dates[:idx]))
        except ValueError:
            return "" if n == 1 else []
