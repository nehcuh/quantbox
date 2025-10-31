"""
LocalAdapter - MongoDB 数据适配器

从本地 MongoDB 数据库读取市场数据
"""

from typing import Optional, Union, List
import datetime
import pandas as pd
import pymongo

from quantbox.adapters.base import BaseDataAdapter
from quantbox.util.date_utils import DateLike, date_to_int, util_make_date_stamp
from quantbox.util.exchange_utils_new import normalize_exchange, validate_exchanges
from quantbox.util.contract_utils_new import normalize_contracts, parse_contract
from quantbox.util.basic import DATABASE


class LocalAdapter(BaseDataAdapter):
    """
    本地数据库适配器
    
    从 MongoDB 读取市场数据，包括交易日历、期货合约、日线数据、持仓数据等。
    """
    
    def __init__(self, database=None):
        """
        初始化 LocalAdapter
        
        Args:
            database: MongoDB 数据库连接，默认使用全局 DATABASE
        """
        super().__init__("LocalAdapter")
        self.database = database or DATABASE
    
    def check_availability(self) -> bool:
        """
        检查数据库连接是否可用
        
        Returns:
            bool: 数据库是否可用
        """
        try:
            # 尝试执行一个简单的查询
            self.database.trade_date.find_one()
            return True
        except Exception:
            return False
    
    def get_trade_calendar(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        从 MongoDB 获取交易日历
        
        Args:
            exchanges: 交易所代码（标准格式）或列表
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            DataFrame 包含以下列：
            - date: 日期（int，YYYYMMDD格式）
            - exchange: 交易所代码（标准格式）
            - is_open: 是否交易日（bool）
        """
        try:
            # 构建查询条件
            query = {}
            
            # 处理交易所过滤
            if exchanges is not None:
                if isinstance(exchanges, str):
                    exchanges = [exchanges]
                # 标准化交易所代码
                exchanges = validate_exchanges(exchanges)
                query["exchange"] = {"$in": exchanges}
            
            # 处理日期范围
            if start_date is not None or end_date is not None:
                date_query = {}
                if start_date is not None:
                    start_stamp = util_make_date_stamp(start_date)
                    date_query["$gte"] = start_stamp
                if end_date is not None:
                    end_stamp = util_make_date_stamp(end_date)
                    date_query["$lte"] = end_stamp
                if date_query:
                    query["datestamp"] = date_query
            
            # 执行查询
            cursor = self.database.trade_date.find(
                query,
                {"_id": 0, "trade_date": 1, "exchange": 1, "datestamp": 1},
                sort=[("exchange", pymongo.ASCENDING), ("datestamp", pymongo.ASCENDING)]
            )
            
            df = pd.DataFrame(list(cursor))
            
            if df.empty:
                # 返回空 DataFrame 但包含正确的列
                return pd.DataFrame(columns=["date", "exchange", "is_open"])
            
            # 转换为标准格式
            df["date"] = df["trade_date"].apply(lambda x: int(x.replace("-", "")))
            df["is_open"] = True  # 数据库中只存储交易日，所以都是 True
            
            # 选择需要的列
            result = df[["date", "exchange", "is_open"]].copy()
            
            return result
        
        except Exception as e:
            raise Exception(f"获取交易日历失败: {str(e)}")
    
    def get_future_contracts(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        symbols: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        从 MongoDB 获取期货合约信息
        
        Args:
            exchanges: 交易所代码或列表
            symbols: 合约代码或列表（标准格式）
            spec_names: 品种名称或列表（如 rb, m, SR等）
            date: 查询日期，None 表示所有合约
        
        Returns:
            DataFrame 包含合约信息
        """
        try:
            # 验证至少有一个参数
            self._validate_symbol_params(symbols, exchanges, spec_names)
            
            # 构建查询条件
            query = {}
            
            # 处理合约代码
            if symbols is not None:
                if isinstance(symbols, str):
                    symbols = [symbols]
                # 标准化合约代码
                symbols = normalize_contracts(symbols)
                query["symbol"] = {"$in": symbols}
            
            # 处理交易所
            if exchanges is not None:
                if isinstance(exchanges, str):
                    exchanges = [exchanges]
                exchanges = validate_exchanges(exchanges)
                query["exchange"] = {"$in": exchanges}
            
            # 处理品种名称
            if spec_names is not None:
                if isinstance(spec_names, str):
                    spec_names = [spec_names]
                # 品种名称在数据库中可能存储为 chinese_name 或 fut_code
                query["$or"] = [
                    {"chinese_name": {"$in": spec_names}},
                    {"fut_code": {"$in": [s.upper() for s in spec_names]}}
                ]
            
            # 处理日期过滤（查询在指定日期上市且未退市的合约）
            if date is not None:
                datestamp = util_make_date_stamp(date)
                query["list_datestamp"] = {"$lte": datestamp}
                query["delist_datestamp"] = {"$gte": datestamp}
            
            # 执行查询
            cursor = self.database.future_contracts.find(
                query,
                {"_id": 0},
                sort=[("exchange", pymongo.ASCENDING), ("symbol", pymongo.ASCENDING)]
            )
            
            df = pd.DataFrame(list(cursor))
            
            if df.empty:
                # 返回空 DataFrame 但包含基本列
                return pd.DataFrame(columns=["symbol", "exchange", "name", "spec_name", "list_date", "delist_date"])
            
            # 转换日期格式
            if "list_date" in df.columns:
                df["list_date"] = df["list_date"].apply(lambda x: int(x.replace("-", "")) if isinstance(x, str) else x)
            if "delist_date" in df.columns:
                df["delist_date"] = df["delist_date"].apply(lambda x: int(x.replace("-", "")) if isinstance(x, str) else x)
            
            # 确保包含 spec_name 列
            if "fut_code" in df.columns and "spec_name" not in df.columns:
                df["spec_name"] = df["fut_code"]
            
            return df
        
        except Exception as e:
            raise Exception(f"获取期货合约信息失败: {str(e)}")
    
    def get_future_daily(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        从 MongoDB 获取期货日线数据
        
        Args:
            symbols: 合约代码或列表
            exchanges: 交易所代码或列表
            start_date: 开始日期
            end_date: 结束日期
            date: 单日查询
        
        Returns:
            DataFrame 包含日线数据
        """
        try:
            # 验证参数
            self._validate_date_range(start_date, end_date, date)
            self._validate_symbol_params(symbols, exchanges, None)
            
            # 构建查询条件
            query = {}
            
            # 处理合约代码
            if symbols is not None:
                if isinstance(symbols, str):
                    symbols = [symbols]
                symbols = normalize_contracts(symbols)
                query["symbol"] = {"$in": symbols}
            
            # 处理交易所
            if exchanges is not None:
                if isinstance(exchanges, str):
                    exchanges = [exchanges]
                exchanges = validate_exchanges(exchanges)
                query["exchange"] = {"$in": exchanges}
            
            # 处理日期范围
            if date is not None:
                # 单日查询
                datestamp = util_make_date_stamp(date)
                query["datestamp"] = datestamp
            else:
                # 日期范围查询
                date_query = {}
                if start_date is not None:
                    start_stamp = util_make_date_stamp(start_date)
                    date_query["$gte"] = start_stamp
                if end_date is not None:
                    end_stamp = util_make_date_stamp(end_date)
                    date_query["$lte"] = end_stamp
                if date_query:
                    query["datestamp"] = date_query
            
            # 执行查询
            cursor = self.database.future_daily.find(
                query,
                {"_id": 0},
                sort=[("symbol", pymongo.ASCENDING), ("datestamp", pymongo.ASCENDING)]
            )
            
            df = pd.DataFrame(list(cursor))
            
            if df.empty:
                # 返回空 DataFrame 但包含基本列
                return pd.DataFrame(columns=["date", "symbol", "exchange", "open", "high", "low", "close", "volume", "amount", "oi"])
            
            # 转换日期格式
            if "trade_date" in df.columns:
                df["date"] = df["trade_date"].apply(lambda x: int(x.replace("-", "")) if isinstance(x, str) else x)
            elif "datestamp" in df.columns:
                # 从 datestamp 提取日期
                df["date"] = df["datestamp"].apply(lambda x: int(x.strftime("%Y%m%d")) if isinstance(x, datetime.datetime) else x)
            
            # 确保字段存在（某些数据源可能缺少某些字段）
            required_fields = ["date", "symbol", "exchange", "open", "high", "low", "close", "volume"]
            for field in required_fields:
                if field not in df.columns:
                    df[field] = None
            
            return df
        
        except Exception as e:
            raise Exception(f"获取期货日线数据失败: {str(e)}")
    
    def get_future_holdings(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        从 MongoDB 获取期货持仓数据
        
        Args:
            symbols: 合约代码或列表
            exchanges: 交易所代码或列表
            spec_names: 品种名称或列表
            start_date: 开始日期
            end_date: 结束日期
            date: 单日查询
        
        Returns:
            DataFrame 包含持仓数据
        """
        try:
            # 验证参数
            self._validate_date_range(start_date, end_date, date)
            self._validate_symbol_params(symbols, exchanges, spec_names)
            
            # 构建查询条件
            query = {}
            
            # 处理合约代码
            if symbols is not None:
                if isinstance(symbols, str):
                    symbols = [symbols]
                symbols = normalize_contracts(symbols)
                query["symbol"] = {"$in": symbols}
            
            # 处理交易所
            if exchanges is not None:
                if isinstance(exchanges, str):
                    exchanges = [exchanges]
                exchanges = validate_exchanges(exchanges)
                query["exchange"] = {"$in": exchanges}
            
            # 处理品种名称（需要先查询合约信息）
            if spec_names is not None:
                if isinstance(spec_names, str):
                    spec_names = [spec_names]
                # 从合约表查询对应的合约代码
                contracts_query = {"$or": [
                    {"chinese_name": {"$in": spec_names}},
                    {"fut_code": {"$in": [s.upper() for s in spec_names]}}
                ]}
                contract_symbols = list(self.database.future_contracts.find(
                    contracts_query,
                    {"symbol": 1, "_id": 0}
                ))
                if contract_symbols:
                    query["symbol"] = {"$in": [c["symbol"] for c in contract_symbols]}
            
            # 处理日期范围
            if date is not None:
                datestamp = util_make_date_stamp(date)
                query["datestamp"] = datestamp
            else:
                date_query = {}
                if start_date is not None:
                    start_stamp = util_make_date_stamp(start_date)
                    date_query["$gte"] = start_stamp
                if end_date is not None:
                    end_stamp = util_make_date_stamp(end_date)
                    date_query["$lte"] = end_stamp
                if date_query:
                    query["datestamp"] = date_query
            
            # 执行查询
            cursor = self.database.future_holdings.find(
                query,
                {"_id": 0},
                sort=[("datestamp", pymongo.ASCENDING), ("symbol", pymongo.ASCENDING), ("rank", pymongo.ASCENDING)]
            )
            
            df = pd.DataFrame(list(cursor))
            
            if df.empty:
                return pd.DataFrame(columns=["date", "symbol", "exchange", "broker", "vol", "vol_chg", "rank"])
            
            # 转换日期格式
            if "trade_date" in df.columns:
                df["date"] = df["trade_date"].apply(lambda x: int(x.replace("-", "")) if isinstance(x, str) else x)
            elif "datestamp" in df.columns:
                df["date"] = df["datestamp"].apply(lambda x: int(x.strftime("%Y%m%d")) if isinstance(x, datetime.datetime) else x)
            
            return df
        
        except Exception as e:
            raise Exception(f"获取期货持仓数据失败: {str(e)}")
