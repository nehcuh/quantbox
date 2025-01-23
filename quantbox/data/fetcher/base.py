"""Base class for data fetchers"""

from typing import Optional
import pandas as pd
from abc import ABC, abstractmethod


class DataFetcher(ABC):
    """Base class for data fetchers"""
    
    @abstractmethod
    def fetch_calendar(self, exchange: str, start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
        """Fetch calendar data
        
        Args:
            exchange (str): Exchange name
            start_date (str, optional): Start date in format YYYYMMDD
            end_date (str, optional): End date in format YYYYMMDD
            
        Returns:
            pd.DataFrame: Calendar data
        """
        pass
    
    @abstractmethod
    def fetch_stock_basic(self) -> pd.DataFrame:
        """Fetch stock basic data
        
        Returns:
            pd.DataFrame: Stock basic data
        """
        pass
    
    @abstractmethod
    def fetch_stock_daily(self, ts_code: str, start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> pd.DataFrame:
        """Fetch stock daily data
        
        Args:
            ts_code (str): Stock code
            start_date (str, optional): Start date in format YYYYMMDD
            end_date (str, optional): End date in format YYYYMMDD
            
        Returns:
            pd.DataFrame: Stock daily data
        """
        pass
