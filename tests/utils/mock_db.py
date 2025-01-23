"""Mock database for testing"""

from typing import Optional, Dict, Any, List
import pandas as pd
from datetime import datetime

from quantbox.data.database.base import DatabaseManager


class MockDatabaseManager(DatabaseManager):
    """Mock database manager for testing"""
    
    def __init__(self):
        """Initialize mock database"""
        self._collections = {}
        for name in ["calendar", "stock_basic", "stock_daily"]:
            self._collections[name] = []
    
    def get_collection(self, name: str) -> 'MockCollection':
        """Get a mock collection"""
        if name not in self._collections:
            self._collections[name] = []
        return MockCollection(self._collections[name])
    
    def ensure_calendar_index(self) -> None:
        """Ensure calendar index exists"""
        pass  # No need to create indexes in mock database
    
    def save_calendar(self, df: pd.DataFrame) -> None:
        """Save calendar data"""
        records = df.to_dict('records')
        self._collections["calendar"] = records  # Replace existing records
    
    def save_stock_basic(self, df: pd.DataFrame) -> None:
        """Save stock basic data"""
        records = df.to_dict('records')
        self._collections["stock_basic"] = records  # Replace existing records
    
    def save_stock_daily(self, df: pd.DataFrame) -> None:
        """Save stock daily data"""
        records = df.to_dict('records')
        self._collections["stock_daily"] = records  # Replace existing records
    
    def get_calendar(self, exchange: str, start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> pd.DataFrame:
        """Get calendar data"""
        data = self._collections["calendar"]
        df = pd.DataFrame(data)
        
        if df.empty:
            return df
            
        mask = df["exchange"] == exchange
        if start_date:
            # Convert date format from "YYYY-MM-DD" to YYYYMMDD
            if isinstance(start_date, str) and "-" in start_date:
                start_date = start_date.replace("-", "")
            mask &= df["trade_date"].astype(str) >= str(start_date)
        if end_date:
            # Convert date format from "YYYY-MM-DD" to YYYYMMDD
            if isinstance(end_date, str) and "-" in end_date:
                end_date = end_date.replace("-", "")
            elif isinstance(end_date, datetime):
                end_date = end_date.strftime("%Y%m%d")
            mask &= df["trade_date"].astype(str) <= str(end_date)
            
        return df[mask]
    
    def close(self) -> None:
        """Close database connection"""
        pass  # No need to close connection in mock database


class MockCollection:
    """Mock collection for testing"""
    
    def __init__(self, data: List[Dict[str, Any]]):
        """Initialize mock collection"""
        self._data = data
    
    def delete_many(self, filter: Dict[str, Any]) -> None:
        """Delete documents matching filter"""
        self._data.clear()
    
    def insert_many(self, documents: list) -> None:
        """Insert many documents"""
        self._data.extend(documents)
    
    def drop(self) -> None:
        """Drop collection"""
        self._data.clear()
    
    def index_information(self) -> Dict[str, Any]:
        """Get index information"""
        return {
            "_id_": {
                "v": 2,
                "key": [("_id", 1)],
            },
            "calendar_trade_date_index": {
                "v": 2,
                "key": [
                    ("exchange", 1),
                    ("trade_date", 1)
                ],
                "unique": True
            },
            "calendar_datestamp_index": {
                "v": 2,
                "key": [
                    ("exchange", 1),
                    ("datestamp", 1)
                ],
                "unique": True
            },
            "calendar_pretrade_date_index": {
                "v": 2,
                "key": [
                    ("exchange", 1),
                    ("pretrade_date", 1)
                ],
                "unique": True
            }
        }
