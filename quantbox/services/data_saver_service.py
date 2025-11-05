"""
DataSaverService - 统一的数据保存服务

提供统一的数据保存接口，从远程数据源获取数据并保存到本地
"""

from typing import Optional, Union, List
import datetime
import pandas as pd
import pymongo

from quantbox.adapters.base import BaseDataAdapter
from quantbox.adapters.local_adapter import LocalAdapter
from quantbox.adapters.ts_adapter import TSAdapter
from quantbox.util.date_utils import DateLike, date_to_int
from quantbox.util.exchange_utils import FUTURES_EXCHANGES, STOCK_EXCHANGES, ALL_EXCHANGES
from quantbox.config.config_loader import get_config_loader


class SaveResult:
    """
    保存操作结果类
    
    用于跟踪数据保存操作的统计信息
    """
    
    def __init__(self):
        self.success = True
        self.inserted_count = 0
        self.modified_count = 0
        self.error_count = 0
        self.errors = []
        self.start_time = datetime.datetime.now()
        self.end_time = None
    
    def add_error(self, error_type: str, error_msg: str, data=None):
        """添加错误信息"""
        self.success = False
        self.error_count += 1
        self.errors.append({
            "type": error_type,
            "message": error_msg,
            "data": data,
            "timestamp": datetime.datetime.now()
        })
    
    def complete(self):
        """完成操作，记录结束时间"""
        self.end_time = datetime.datetime.now()
    
    @property
    def duration(self):
        """获取操作持续时间"""
        if self.end_time:
            return self.end_time - self.start_time
        return datetime.datetime.now() - self.start_time
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "success": self.success,
            "inserted_count": self.inserted_count,
            "modified_count": self.modified_count,
            "error_count": self.error_count,
            "errors": self.errors,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": str(self.duration)
        }


class DataSaverService:
    """
    数据保存服务
    
    统一的数据保存接口，支持：
    - 从远程数据源获取数据
    - 数据验证和清洗
    - 批量保存到本地数据库
    - 增量更新和去重
    """
    
    def __init__(
        self,
        remote_adapter: Optional[BaseDataAdapter] = None,
        local_adapter: Optional[LocalAdapter] = None,
        database=None
    ):
        """
        初始化数据保存服务
        
        Args:
            remote_adapter: 远程数据适配器，默认使用 TSAdapter
            local_adapter: 本地数据适配器，默认使用 LocalAdapter
            database: MongoDB 数据库实例，默认使用全局 DATABASE
        """
        self.remote_adapter = remote_adapter or TSAdapter()
        self.local_adapter = local_adapter or LocalAdapter()
        self.database = database or get_config_loader().get_mongodb_client().quantbox
    
    def _create_index(self, collection, index_keys, unique=False):
        """
        创建索引
        
        Args:
            collection: MongoDB 集合
            index_keys: 索引键列表
            unique: 是否唯一索引
        """
        try:
            collection.create_index(
                index_keys,
                unique=unique,
                background=True
            )
        except pymongo.errors.DuplicateKeyError:
            pass
        except Exception as e:
            print(f"创建索引失败: {str(e)}")
    
    def _bulk_upsert(self, collection, data: List[dict], key_fields: List[str]) -> dict:
        """
        批量更新或插入数据
        
        Args:
            collection: MongoDB 集合
            data: 数据列表
            key_fields: 唯一键字段列表
        
        Returns:
            结果字典，包含 upserted_count 和 modified_count
        """
        if not data:
            return {"upserted_count": 0, "modified_count": 0}
        
        operations = []
        for doc in data:
            # 构建查询条件
            query = {field: doc[field] for field in key_fields if field in doc}
            operations.append(
                pymongo.UpdateOne(
                    query,
                    {"$set": doc},
                    upsert=True
                )
            )
        
        result = collection.bulk_write(operations)
        return {
            "upserted_count": result.upserted_count,
            "modified_count": result.modified_count
        }
    
    def save_trade_calendar(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None
    ) -> SaveResult:
        """
        保存交易日历数据

        Args:
            exchanges: 交易所代码或列表，默认 None（使用所有交易所）
            start_date: 起始日期，默认 None（使用今年年初）
            end_date: 结束日期，默认 None（使用今天）

        智能默认行为：
            - 如果 exchanges 为 None，使用所有交易所
            - 如果 start_date 为 None，使用今年年初
            - 如果 end_date 为 None，使用今天

        Returns:
            SaveResult: 保存结果
        """
        result = SaveResult()

        try:
            # 智能默认
            if exchanges is None:
                exchanges = ALL_EXCHANGES

            if start_date is None:
                # 默认从今年年初开始
                start_date = datetime.datetime(datetime.datetime.today().year, 1, 1).strftime("%Y%m%d")

            if end_date is None:
                # 默认到今天
                end_date = datetime.datetime.today().strftime("%Y%m%d")

            # 从远程获取数据
            df = self.remote_adapter.get_trade_calendar(
                exchanges=exchanges,
                start_date=start_date,
                end_date=end_date
            )
            
            if df.empty:
                result.add_error("NO_DATA", "未获取到交易日历数据")
                result.complete()
                return result
            
            # 转换为字典列表
            data = df.to_dict('records')
            
            # 创建索引
            collection = self.database.trade_date
            self._create_index(
                collection,
                [("exchange", pymongo.ASCENDING), ("date", pymongo.ASCENDING)],
                unique=True
            )
            
            # 批量保存
            save_result = self._bulk_upsert(
                collection,
                data,
                ["exchange", "date"]
            )
            
            result.inserted_count = save_result["upserted_count"]
            result.modified_count = save_result["modified_count"]
            result.complete()
            
        except Exception as e:
            result.add_error("SAVE_ERROR", f"保存交易日历失败: {str(e)}")
            result.complete()
        
        return result
    
    def save_future_contracts(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        symbols: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        date: Optional[DateLike] = None
    ) -> SaveResult:
        """
        保存期货合约信息

        Args:
            exchanges: 交易所代码或列表，默认 None（使用所有期货交易所）
            symbols: 合约代码或列表
            spec_names: 品种名称或列表
            date: 查询日期

        智能默认行为：
            - 如果所有参数都为 None，使用所有期货交易所

        Returns:
            SaveResult: 保存结果
        """
        result = SaveResult()

        try:
            # 智能默认：如果没有指定任何参数，使用所有期货交易所
            if all(x is None for x in [exchanges, symbols, spec_names, date]):
                exchanges = FUTURES_EXCHANGES

            # 从远程获取数据
            df = self.remote_adapter.get_future_contracts(
                exchanges=exchanges,
                symbols=symbols,
                spec_names=spec_names,
                date=date
            )
            
            if df.empty:
                result.add_error("NO_DATA", "未获取到期货合约数据")
                result.complete()
                return result
            
            # 转换为字典列表
            data = df.to_dict('records')
            
            # 创建索引
            collection = self.database.future_contracts
            self._create_index(
                collection,
                [("symbol", pymongo.ASCENDING), ("exchange", pymongo.ASCENDING)],
                unique=True
            )
            
            # 批量保存
            save_result = self._bulk_upsert(
                collection,
                data,
                ["symbol", "exchange"]
            )
            
            result.inserted_count = save_result["upserted_count"]
            result.modified_count = save_result["modified_count"]
            result.complete()
            
        except Exception as e:
            result.add_error("SAVE_ERROR", f"保存期货合约失败: {str(e)}")
            result.complete()
        
        return result
    
    def save_future_daily(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None
    ) -> SaveResult:
        """
        保存期货日线数据

        Args:
            symbols: 合约代码或列表，默认 None（获取所有合约）
            exchanges: 交易所代码或列表，默认 None（使用所有期货交易所）
            start_date: 起始日期，默认 None
            end_date: 结束日期，默认 None
            date: 单日查询日期，默认 None（使用今天）

        智能默认行为：
            - 如果 symbols、exchanges、start_date、end_date、date 都为 None，
              则默认保存今天所有期货交易所的数据

        Returns:
            SaveResult: 保存结果
        """
        result = SaveResult()

        try:
            # 智能默认：如果没有指定任何参数，默认保存今天的数据
            if all(x is None for x in [symbols, exchanges, start_date, end_date, date]):
                date = datetime.datetime.today().strftime("%Y%m%d")
                exchanges = FUTURES_EXCHANGES  # 默认使用所有期货交易所

            # 从远程获取数据
            df = self.remote_adapter.get_future_daily(
                symbols=symbols,
                exchanges=exchanges,
                start_date=start_date,
                end_date=end_date,
                date=date
            )
            
            if df.empty:
                result.add_error("NO_DATA", "未获取到期货日线数据")
                result.complete()
                return result
            
            # 转换为字典列表
            data = df.to_dict('records')
            
            # 创建索引
            collection = self.database.future_daily
            self._create_index(
                collection,
                [("symbol", pymongo.ASCENDING), ("exchange", pymongo.ASCENDING), ("date", pymongo.ASCENDING)],
                unique=True
            )
            self._create_index(
                collection,
                [("date", pymongo.DESCENDING)]
            )
            
            # 批量保存
            save_result = self._bulk_upsert(
                collection,
                data,
                ["symbol", "exchange", "date"]
            )
            
            result.inserted_count = save_result["upserted_count"]
            result.modified_count = save_result["modified_count"]
            result.complete()
            
        except Exception as e:
            result.add_error("SAVE_ERROR", f"保存期货日线失败: {str(e)}")
            result.complete()
        
        return result
    
    def save_future_holdings(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None
    ) -> SaveResult:
        """
        保存期货持仓数据

        Args:
            symbols: 合约代码或列表
            exchanges: 交易所代码或列表，默认 None（使用所有期货交易所）
            spec_names: 品种名称或列表
            start_date: 起始日期
            end_date: 结束日期
            date: 单日查询日期，默认 None（使用今天）

        智能默认行为：
            - 如果所有参数都为 None，默认保存今天所有期货交易所的持仓数据

        Returns:
            SaveResult: 保存结果
        """
        result = SaveResult()

        try:
            # 智能默认：如果没有指定任何参数，默认保存今天的数据
            if all(x is None for x in [symbols, exchanges, spec_names, start_date, end_date, date]):
                date = datetime.datetime.today().strftime("%Y%m%d")
                exchanges = FUTURES_EXCHANGES

            # 从远程获取数据
            df = self.remote_adapter.get_future_holdings(
                symbols=symbols,
                exchanges=exchanges,
                spec_names=spec_names,
                start_date=start_date,
                end_date=end_date,
                date=date
            )
            
            if df.empty:
                result.add_error("NO_DATA", "未获取到期货持仓数据")
                result.complete()
                return result
            
            # 转换为字典列表
            data = df.to_dict('records')
            
            # 创建索引
            collection = self.database.future_holdings
            self._create_index(
                collection,
                [("symbol", pymongo.ASCENDING), ("exchange", pymongo.ASCENDING), 
                 ("date", pymongo.ASCENDING), ("broker", pymongo.ASCENDING)],
                unique=True
            )
            self._create_index(
                collection,
                [("date", pymongo.DESCENDING)]
            )
            
            # 批量保存
            save_result = self._bulk_upsert(
                collection,
                data,
                ["symbol", "exchange", "date", "broker"]
            )
            
            result.inserted_count = save_result["upserted_count"]
            result.modified_count = save_result["modified_count"]
            result.complete()
            
        except Exception as e:
            result.add_error("SAVE_ERROR", f"保存期货持仓失败: {str(e)}")
            result.complete()
        
        return result
