"""Mock database manager for testing"""

from typing import Dict, Any, Optional, List
import pandas as pd
from datetime import datetime

from quantbox.data.database.base import DatabaseManager


class MockCollection:
    """Mock collection for testing"""
    
    def __init__(self):
        """Initialize mock collection"""
        self._data = []
        self._indexes = {}
        
    def insert_many(self, documents: List[Dict[str, Any]]) -> None:
        """Insert many documents"""
        self._data.extend(documents)
        
    def delete_many(self, filter: Dict[str, Any]) -> None:
        """Delete many documents"""
        self._data = []
        
    def drop(self) -> None:
        """Drop collection"""
        self._data = []
        self._indexes = {}
        
    def create_index(self, keys: List[tuple], unique: bool = False) -> None:
        """Create index"""
        index_name = "_".join(f"{key}_{direction}" for key, direction in keys)
        self._indexes[index_name] = {
            "v": 2,
            "key": keys,
            "unique": unique
        }
        
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
        
    def find(self, filter: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Find documents"""
        if filter is None:
            return self._data
            
        result = []
        for doc in self._data:
            match = True
            for key, value in filter.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                result.append(doc)
        return result


class MockDatabaseManager(DatabaseManager):
    """Mock database manager for testing"""
    
    def __init__(self):
        """Initialize mock database manager"""
        self._collections = {}
        
    def get_collection(self, name: str) -> MockCollection:
        """Get collection by name"""
        if name not in self._collections:
            self._collections[name] = MockCollection()
        return self._collections[name]
        
    def save_calendar(self, data: pd.DataFrame) -> None:
        """Save calendar data"""
        collection = self.get_collection("calendar")
        
        # 转换数据
        documents = []
        for _, row in data.iterrows():
            doc = row.to_dict()
            if isinstance(doc.get("trade_date"), str):
                doc["datestamp"] = int(datetime.strptime(doc["trade_date"], "%Y%m%d").timestamp() * 1_000_000_000)
            documents.append(doc)
            
        # 保存数据
        collection.delete_many({})  # 清空集合
        collection.insert_many(documents)
        
    def get_calendar(self, exchange: Optional[str] = None,
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> pd.DataFrame:
        """Get calendar data"""
        collection = self.get_collection("calendar")
        
        # 构建查询条件
        filter = {}
        if exchange:
            filter["exchange"] = exchange
            
        # 查询数据
        documents = collection.find(filter)
        if not documents:
            return pd.DataFrame()
            
        # 转换为 DataFrame
        df = pd.DataFrame(documents)
        
        # 过滤日期范围
        if start_date:
            df = df[df["trade_date"] >= start_date]
        if end_date:
            df = df[df["trade_date"] <= end_date]
            
        return df
        
    def ensure_calendar_index(self) -> None:
        """Ensure calendar index exists"""
        collection = self.get_collection("calendar")
        
        # 创建索引
        collection.create_index([("exchange", 1), ("trade_date", 1)], unique=True)
        collection.create_index([("exchange", 1), ("datestamp", 1)], unique=True)
        collection.create_index([("exchange", 1), ("pretrade_date", 1)], unique=True)
        
    def save_stock_basic(self, data: pd.DataFrame) -> None:
        """Save stock basic data"""
        collection = self.get_collection("stock_basic")
        
        # 转换数据
        documents = data.to_dict('records')
            
        # 保存数据
        collection.delete_many({})  # 清空集合
        collection.insert_many(documents)
        
    def save_stock_daily(self, data: pd.DataFrame) -> None:
        """Save stock daily data"""
        collection = self.get_collection("stock_daily")
        
        # 转换数据
        documents = data.to_dict('records')
            
        # 保存数据
        collection.delete_many({})  # 清空集合
        collection.insert_many(documents)
        
    def close(self) -> None:
        """Close database connection"""
        pass
