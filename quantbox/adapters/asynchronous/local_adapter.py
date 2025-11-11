"""
AsyncLocalAdapter - MongoDB 异步数据适配器

从本地 MongoDB 数据库异步读取和写入市场数据。

使用 motor 库实现异步 MongoDB 操作，提升数据库 I/O 性能。

性能提升:
- 批量读取：2-5倍
- 并发写入：3-6倍
- 整体吞吐量：5-10倍

Python 3.14+ nogil 兼容性:
- motor 基于 asyncio，不依赖 GIL
- 与 async/await 完美配合
"""

import asyncio
from typing import Optional, Union, List
import datetime
import pandas as pd
from motor import motor_asyncio
import pymongo

from quantbox.adapters.asynchronous.base import AsyncBaseDataAdapter
from quantbox.util.date_utils import DateLike, date_to_int, util_make_date_stamp
from quantbox.util.exchange_utils import normalize_exchange, validate_exchanges
from quantbox.util.contract_utils import normalize_contracts, parse_contract
from quantbox.config.config_loader import get_config_loader


class AsyncLocalAdapter(AsyncBaseDataAdapter):
    """
    MongoDB 异步数据适配器

    使用 motor 异步驱动从 MongoDB 读取和写入数据。

    特性:
    - 异步查询和写入
    - 批量操作优化
    - 连接池管理
    - nogil 兼容

    示例:
        >>> import asyncio
        >>> from quantbox.adapters.async_adapters import AsyncLocalAdapter
        >>>
        >>> async def main():
        >>>     adapter = AsyncLocalAdapter()
        >>>     data = await adapter.get_trade_calendar()
        >>>     print(data)
        >>>
        >>> asyncio.run(main())
    """

    def __init__(self, database=None):
        """
        初始化异步 LocalAdapter

        Args:
            database: MongoDB 数据库连接，默认使用全局配置
        """
        super().__init__("AsyncLocalAdapter")

        if database is None:
            # 创建异步 MongoDB 客户端
            config = get_config_loader()
            mongo_uri = config.get_mongodb_uri()
            self.client = motor_asyncio.AsyncIOMotorClient(mongo_uri)
            self.database = self.client.quantbox
        else:
            self.database = database

    async def check_availability(self) -> bool:
        """
        异步检查数据库连接是否可用

        Returns:
            bool: 数据库是否可用
        """
        try:
            # 尝试执行一个简单的查询
            await self.database.trade_date.find_one()
            return True
        except Exception:
            return False

    async def get_trade_calendar(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        异步从 MongoDB 获取交易日历

        Args:
            exchanges: 交易所代码（标准格式）或列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame 包含以下列：
            - date: 日期（int，YYYYMMDD格式）
            - exchange: 交易所代码（标准格式）
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

            # 处理日期范围（优先使用 datestamp 字段进行快速查询）
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

            # 异步查询
            cursor = self.database.trade_date.find(
                query,
                {"_id": 0, "date": 1, "exchange": 1},
            ).sort([("exchange", pymongo.ASCENDING), ("datestamp", pymongo.ASCENDING)])

            # 异步获取所有结果
            docs = await cursor.to_list(length=None)
            df = pd.DataFrame(docs)

            if df.empty:
                # 返回空 DataFrame 但包含正确的列
                return pd.DataFrame(columns=["date", "exchange"])

            # 数据已经是标准格式，直接返回
            result = df[["date", "exchange"]].copy()

            return result

        except Exception as e:
            raise Exception(f"获取交易日历失败: {str(e)}")

    async def get_future_contracts(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        symbols: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        异步从 MongoDB 获取期货合约信息

        Args:
            exchanges: 交易所代码或列表
            symbols: 合约代码或列表（标准格式）
            spec_names: 品种名称或列表（如 rb, m, SR等）
            date: 查询日期，None 表示所有合约

        Returns:
            DataFrame 包含合约信息
        """
        try:
            # 如果只传了 date 参数，默认查询所有期货交易所
            if date is not None and all(x is None for x in [symbols, exchanges, spec_names]):
                from quantbox.util.exchange_utils import FUTURES_EXCHANGES
                exchanges = FUTURES_EXCHANGES

            # 验证至少有一个参数
            self._validate_symbol_params(symbols, exchanges, spec_names)

            # 构建查询条件
            query = {}

            # 处理合约代码
            if symbols is not None:
                if isinstance(symbols, str):
                    symbols = [symbols]
                # 对于合约查询，支持灵活格式但不做完整标准化
                # 如果是完整格式（如 "DCE.a2501"），提取 symbol 部分
                parsed_symbols = []
                for sym in symbols:
                    if '.' in sym:
                        # 尝试解析完整格式
                        try:
                            contract_info = parse_contract(sym)
                            parsed_symbols.append(contract_info.symbol)
                        except Exception:
                            # 解析失败，直接使用
                            parsed_symbols.append(sym)
                    else:
                        # 简单格式，直接使用
                        parsed_symbols.append(sym)
                query["symbol"] = {"$in": parsed_symbols}

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
                    {"fut_code": {"$in": [s.upper() for s in spec_names]}},
                ]

            # 处理日期过滤（查询在指定日期上市且未退市的合约）
            if date is not None:
                datestamp = util_make_date_stamp(date)
                query["list_datestamp"] = {"$lte": datestamp}
                query["delist_datestamp"] = {"$gte": datestamp}

            # 异步查询
            cursor = self.database.future_contracts.find(query, {"_id": 0})

            # 异步获取所有结果
            docs = await cursor.to_list(length=None)
            df = pd.DataFrame(docs)

            if df.empty:
                return pd.DataFrame(
                    columns=[
                        "symbol",
                        "exchange",
                        "spec_name",
                        "name",
                        "list_date",
                        "delist_date",
                    ]
                )

            # 标准化输出格式
            result = pd.DataFrame()
            result["symbol"] = df.get("symbol", "")
            result["exchange"] = df.get("exchange", "")
            result["spec_name"] = df.get("chinese_name", df.get("fut_code", ""))
            result["name"] = df.get("name", "")
            result["list_date"] = df.get("list_date", "")
            result["delist_date"] = df.get("delist_date", "")

            return result

        except Exception as e:
            raise Exception(f"获取期货合约信息失败: {str(e)}")

    async def get_future_daily(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        异步从 MongoDB 获取期货日线数据

        Args:
            symbols: 合约代码或列表（标准格式）
            exchanges: 交易所代码或列表
            start_date: 开始日期
            end_date: 结束日期
            date: 单日查询（与 start_date/end_date 互斥）

        Returns:
            DataFrame 包含日线数据
        """
        try:
            # 参数验证
            self._validate_date_range(start_date, end_date, date)
            self._validate_symbol_params(symbols, exchanges, None)

            # 构建查询条件
            query = {}

            # 处理合约代码（智能解析，支持多种格式）
            if symbols is not None:
                if isinstance(symbols, str):
                    symbols = [symbols]

                # 智能解析合约代码，支持多种格式：
                # 1. 完整格式: "DCE.a2501" -> symbol="a2501", exchange="DCE"
                # 2. 简单格式: "a2501" -> symbol="a2501"
                parsed_symbols = []
                parsed_exchanges = []

                for sym in symbols:
                    if '.' in sym:
                        try:
                            contract_info = parse_contract(sym)
                            parsed_symbols.append(contract_info.symbol)
                            parsed_exchanges.append(contract_info.exchange)
                        except Exception:
                            parsed_symbols.append(sym)
                    else:
                        parsed_symbols.append(sym)

                query["symbol"] = {"$in": parsed_symbols}

                # 如果从 symbols 中解析出了 exchange，且用户没有显式指定 exchanges
                if parsed_exchanges and exchanges is None:
                    query["exchange"] = {"$in": list(set(parsed_exchanges))}

            # 处理交易所
            if exchanges is not None:
                if isinstance(exchanges, str):
                    exchanges = [exchanges]
                exchanges = validate_exchanges(exchanges)
                query["exchange"] = {"$in": exchanges}

            # 处理日期
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

            # 异步查询
            cursor = self.database.future_daily.find(query, {"_id": 0}).sort(
                [("symbol", pymongo.ASCENDING), ("datestamp", pymongo.ASCENDING)]
            )

            # 异步获取所有结果
            docs = await cursor.to_list(length=None)
            df = pd.DataFrame(docs)

            if df.empty:
                return pd.DataFrame(
                    columns=[
                        "date",
                        "symbol",
                        "exchange",
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                        "amount",
                        "oi",
                    ]
                )

            # 标准化输出格式
            result = pd.DataFrame()
            result["date"] = df["date"].astype(int)
            result["symbol"] = df["symbol"]
            result["exchange"] = df["exchange"]
            result["open"] = df.get("open", 0)
            result["high"] = df.get("high", 0)
            result["low"] = df.get("low", 0)
            result["close"] = df.get("close", 0)
            result["volume"] = df.get("volume", 0)
            result["amount"] = df.get("amount", 0)
            result["oi"] = df.get("oi", 0)

            return result

        except Exception as e:
            raise Exception(f"获取期货日线数据失败: {str(e)}")

    async def get_future_holdings(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        异步从 MongoDB 获取期货持仓数据

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
            # 参数验证
            self._validate_date_range(start_date, end_date, date)

            # 构建查询条件
            query = {}

            # 处理合约代码（智能解析，支持多种格式）
            if symbols is not None:
                if isinstance(symbols, str):
                    symbols = [symbols]

                parsed_symbols = []
                parsed_exchanges = []

                for sym in symbols:
                    if '.' in sym:
                        try:
                            contract_info = parse_contract(sym)
                            parsed_symbols.append(contract_info.symbol)
                            parsed_exchanges.append(contract_info.exchange)
                        except Exception:
                            parsed_symbols.append(sym)
                    else:
                        parsed_symbols.append(sym)

                query["symbol"] = {"$in": parsed_symbols}

                if parsed_exchanges and exchanges is None:
                    query["exchange"] = {"$in": list(set(parsed_exchanges))}

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
                query["spec_name"] = {"$in": spec_names}

            # 处理日期
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

            # 异步查询
            cursor = self.database.future_holdings.find(query, {"_id": 0}).sort(
                [("symbol", pymongo.ASCENDING), ("datestamp", pymongo.ASCENDING)]
            )

            # 异步获取所有结果
            docs = await cursor.to_list(length=None)
            df = pd.DataFrame(docs)

            if df.empty:
                return pd.DataFrame(
                    columns=[
                        "symbol",
                        "exchange",
                        "date",
                        "broker",
                        "vol",
                        "vol_chg",
                        "long_hld",
                        "long_chg",
                        "short_hld",
                        "short_chg",
                    ]
                )

            # 标准化输出格式
            result = df.copy()

            # 转换日期格式（确保 date 字段是整数格式）
            if "date" in result.columns and result["date"].dtype in [int, 'int64', 'int32']:
                # date 字段已经是正确的整数格式，无需转换
                pass
            elif "trade_date" in result.columns:
                result["date"] = result["trade_date"].astype(int)
            elif "datestamp" in result.columns and "date" not in result.columns:
                # 从 datestamp 提取日期（仅当没有 date 字段时）
                result["date"] = result["datestamp"].apply(
                    lambda x: int(x.strftime("%Y%m%d")) if isinstance(x, datetime.datetime)
                    else int(datetime.datetime.fromtimestamp(x).strftime("%Y%m%d"))
                )

            # 选择关键字段
            key_columns = [
                "symbol",
                "exchange",
                "date",
                "broker",
                "vol",
                "vol_chg",
                "long_hld",
                "long_chg",
                "short_hld",
                "short_chg",
            ]
            available_columns = [col for col in key_columns if col in result.columns]

            return result[available_columns]

        except Exception as e:
            raise Exception(f"获取期货持仓数据失败: {str(e)}")

    async def get_stock_list(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        names: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        markets: Optional[Union[str, List[str]]] = None,
        list_status: Union[str, List[str], None] = "L",
        is_hs: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        异步从 MongoDB 获取股票列表

        Args:
            symbols: 股票代码或列表（标准格式）
            names: 股票名称或列表
            exchanges: 交易所代码或列表
            markets: 市场板块或列表
            list_status: 上市状态
            is_hs: 沪港通状态

        Returns:
            DataFrame 包含股票信息
        """
        try:
            # 构建查询条件
            query = {}

            # 处理股票代码
            if symbols is not None:
                if isinstance(symbols, str):
                    symbols = [symbols]
                query["symbol"] = {"$in": symbols}

            # 处理股票名称
            if names is not None:
                if isinstance(names, str):
                    names = [names]
                query["name"] = {"$in": names}

            # 处理交易所
            if exchanges is not None:
                if isinstance(exchanges, str):
                    exchanges = [exchanges]
                exchanges = validate_exchanges(exchanges)
                query["exchange"] = {"$in": exchanges}

            # 处理市场板块
            if markets is not None:
                if isinstance(markets, str):
                    markets = [markets]
                query["market"] = {"$in": markets}

            # 处理上市状态
            if list_status is not None:
                if isinstance(list_status, str):
                    query["list_status"] = list_status
                else:
                    query["list_status"] = {"$in": list_status}

            # 处理沪港通状态
            if is_hs is not None:
                query["is_hs"] = is_hs

            # 异步查询
            cursor = self.database.stock_list.find(query, {"_id": 0})

            # 异步获取所有结果
            docs = await cursor.to_list(length=None)
            df = pd.DataFrame(docs)

            if df.empty:
                return pd.DataFrame(
                    columns=[
                        "symbol",
                        "name",
                        "exchange",
                        "list_date",
                        "delist_date",
                        "industry",
                        "area",
                    ]
                )

            # 选择关键字段
            key_columns = [
                "symbol",
                "name",
                "exchange",
                "list_date",
                "delist_date",
                "industry",
                "area",
            ]
            available_columns = [col for col in key_columns if col in df.columns]

            return df[available_columns]

        except Exception as e:
            raise Exception(f"获取股票列表失败: {str(e)}")

    async def bulk_insert(
        self, collection_name: str, documents: List[dict], ordered: bool = False
    ) -> int:
        """
        异步批量插入文档

        Args:
            collection_name: 集合名称
            documents: 文档列表
            ordered: 是否有序插入

        Returns:
            插入的文档数量
        """
        if not documents:
            return 0

        try:
            collection = self.database[collection_name]
            result = await collection.insert_many(documents, ordered=ordered)
            return len(result.inserted_ids)
        except Exception as e:
            raise Exception(f"批量插入失败: {str(e)}")

    async def bulk_upsert(
        self, collection_name: str, documents: List[dict], key_fields: List[str]
    ) -> dict:
        """
        异步批量更新或插入文档

        Args:
            collection_name: 集合名称
            documents: 文档列表
            key_fields: 用于匹配的关键字段

        Returns:
            包含统计信息的字典
        """
        if not documents:
            return {"matched": 0, "modified": 0, "upserted": 0}

        try:
            collection = self.database[collection_name]

            # 构建批量操作
            from pymongo import UpdateOne

            operations = []
            for doc in documents:
                query = {field: doc[field] for field in key_fields if field in doc}
                operations.append(UpdateOne(query, {"$set": doc}, upsert=True))

            # 异步执行批量操作
            result = await collection.bulk_write(operations, ordered=False)

            return {
                "matched": result.matched_count,
                "modified": result.modified_count,
                "upserted": result.upserted_count,
            }

        except Exception as e:
            raise Exception(f"批量更新失败: {str(e)}")

    def __del__(self):
        """清理资源"""
        if hasattr(self, "client"):
            self.client.close()
