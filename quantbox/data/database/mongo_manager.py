"""MongoDB管理器"""

from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime, date
import pandas as pd
from pymongo import MongoClient, ASCENDING, DESCENDING, IndexModel
from pymongo.collection import Collection
from pymongo.database import Database
import pymongo
import logging

logger = logging.getLogger(__name__)

from quantbox.core.config import MongoDBConfig


class MongoDBManager:
    """MongoDB管理器"""
    
    def __init__(self, config: MongoDBConfig):
        """初始化MongoDB管理器
        
        Args:
            config: MongoDB配置
        """
        self.config = config
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
        
    @property
    def client(self) -> MongoClient:
        """获取MongoDB客户端"""
        if self._client is None:
            self._client = MongoClient(self.config.uri)
        return self._client
    
    @property
    def db(self) -> Database:
        """获取MongoDB数据库"""
        if self._db is None:
            self._db = self.client[self.config.database]
        return self._db
    
    def get_collection(self, name: str) -> Collection:
        """获取集合
        
        Args:
            name: 集合名称
            
        Returns:
            Collection: MongoDB集合
        """
        return self.db[f"{self.config.collection_prefix}{name}"]
    
    @property
    def future_contracts(self) -> Collection:
        """获取期货合约集合"""
        return self.get_collection("future_contracts")
    
    def ensure_calendar_index(self):
        """确保交易日历索引存在"""
        collection = self.get_collection("calendar")
        
        # 创建索引
        indexes = [
            IndexModel([("exchange", ASCENDING), ("trade_date", ASCENDING)], unique=True),
            IndexModel([("exchange", ASCENDING), ("datestamp", ASCENDING)]),
            IndexModel([("exchange", ASCENDING), ("pretrade_date", ASCENDING)])
        ]
        collection.create_indexes(indexes)
    
    def save_calendar(self, df: pd.DataFrame):
        """保存交易日历
        
        Args:
            df: 交易日历数据，包含以下列：
                - exchange: str, 交易所代码
                - trade_date: int, 交易日期，格式为YYYYMMDD
                - pretrade_date: int, 前一交易日，格式为YYYYMMDD
                - datestamp: int, 纳秒级时间戳
                - is_open: int, 是否为交易日
        """
        collection = self.get_collection("calendar")
        
        # 转换为字典列表
        records = df.to_dict("records")
        
        # 批量更新，如果存在则更新，不存在则插入
        for record in records:
            collection.update_one(
                {
                    "exchange": record["exchange"],
                    "trade_date": record["trade_date"]
                },
                {"$set": record},
                upsert=True
            )
    
    def get_calendar(
        self,
        exchange: str,
        start_date: Optional[Union[str, int, date, datetime]] = None,
        end_date: Optional[Union[str, int, date, datetime]] = None
    ) -> pd.DataFrame:
        """获取交易日历
        
        Args:
            exchange: 交易所代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            pd.DataFrame: 包含以下列的DataFrame：
                - exchange: str, 交易所代码
                - trade_date: int, 交易日期，格式为YYYYMMDD
                - pretrade_date: int, 前一交易日，格式为YYYYMMDD
                - datestamp: int, 纳秒级时间戳
                - is_open: int, 是否为交易日
        """
        collection = self.get_collection("calendar")
        
        # 构建查询条件
        query = {"exchange": exchange}
        if start_date is not None:
            if isinstance(start_date, (date, datetime)):
                start_date = int(start_date.strftime("%Y%m%d"))
            elif isinstance(start_date, str):
                start_date = int(start_date.replace("-", ""))
            query["trade_date"] = {"$gte": start_date}
        
        if end_date is not None:
            if isinstance(end_date, (date, datetime)):
                end_date = int(end_date.strftime("%Y%m%d"))
            elif isinstance(end_date, str):
                end_date = int(end_date.replace("-", ""))
            if "trade_date" in query:
                query["trade_date"]["$lte"] = end_date
            else:
                query["trade_date"] = {"$lte": end_date}
        
        # 查询数据
        cursor = collection.find(query)
        
        # 转换为DataFrame
        df = pd.DataFrame(list(cursor))
        
        # 如果没有数据，返回空DataFrame
        if len(df) == 0:
            return pd.DataFrame(columns=["exchange", "trade_date", "pretrade_date", "datestamp", "is_open"])
        
        # 删除_id列
        df = df.drop("_id", axis=1)
        
        return df
    
    def save_future_contracts(
        self,
        data: pd.DataFrame,
        exchange: str,
    ) -> Tuple[int, int]:
        """保存期货合约数据到数据库。

        Args:
            data: 包含期货合约数据的 DataFrame
            exchange: 交易所代码

        Returns:
            Tuple[int, int]: (新增数据数量, 更新数据数量)

        Raises:
            ValueError: 当输入数据无效时
            pymongo.errors.PyMongoError: 数据库操作错误
        """
        if data is None or data.empty:
            raise ValueError("输入数据为空")

        collection = self.future_contracts
        inserted_count = 0
        updated_count = 0

        try:
            # 创建索引
            collection.create_index(
                [
                    ("exchange", pymongo.ASCENDING),
                    ("symbol", pymongo.ASCENDING),
                    ("list_date", pymongo.ASCENDING)
                ],
                unique=True,
                background=True
            )
            collection.create_index(
                [("list_datestamp", pymongo.DESCENDING)],
                background=True
            )
            collection.create_index(
                [("delist_datestamp", pymongo.DESCENDING)],
                background=True
            )

            # 保存数据
            for _, row in data.iterrows():
                filter_condition = {
                    "exchange": exchange,
                    "symbol": row["symbol"],
                    "list_date": row["list_date"]
                }

                update_data = row.to_dict()
                result = collection.update_one(
                    filter_condition,
                    {"$set": update_data},
                    upsert=True
                )

                if result.upserted_id:
                    inserted_count += 1
                elif result.modified_count > 0:
                    updated_count += 1

            return inserted_count, updated_count

        except pymongo.errors.PyMongoError as e:
            logger.error(f"保存期货合约数据时发生错误: {str(e)}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
