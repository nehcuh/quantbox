"""Base class for database managers"""

from typing import Optional
import pandas as pd
from abc import ABC, abstractmethod


class DatabaseManager(ABC):
    """Base class for database managers"""
    
    @abstractmethod
    def save_calendar(self, df: pd.DataFrame) -> None:
        """Save calendar data
        
        Args:
            df (pd.DataFrame): Calendar data to save
        """
        pass
    
    @abstractmethod
    def save_stock_basic(self, df: pd.DataFrame) -> None:
        """Save stock basic data
        
        Args:
            df (pd.DataFrame): Stock basic data to save
        """
        pass
    
    @abstractmethod
    def save_stock_daily(self, df: pd.DataFrame) -> None:
        """Save stock daily data
        
        Args:
            df (pd.DataFrame): Stock daily data to save
        """
        pass
    
    @abstractmethod
    def get_calendar(self, exchange: str, start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> pd.DataFrame:
        """Get calendar data
        
        Args:
            exchange (str): Exchange name
            start_date (str, optional): Start date in format YYYYMMDD
            end_date (str, optional): End date in format YYYYMMDD
            
        Returns:
            pd.DataFrame: Calendar data
        """
        pass
