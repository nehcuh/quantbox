"""
Local fetcher module for retrieving data from local database.
"""
import datetime
import pandas as pd
from typing import List, Optional, Union, Dict, Any
from abc import ABC
import pymongo
from quantbox.fetchers.base import BaseFetcher
from quantbox.config.config_loader import get_config_loader
from quantbox.util.date_utils import util_make_date_stamp
from quantbox.util.tools import util_format_future_symbols
from quantbox.fetchers.monitoring import PerformanceMonitor, monitor_performance
from quantbox.fetchers.cache import cache_result
from quantbox.fetchers.utils import QueryBuilder, DateRangeValidator, ExchangeValidator


class LocalBaseFetcher(ABC):
    """
    Base class for local data fetchers that do not require external data fetching methods.
    """
    def __init__(self):
        config_loader = get_config_loader()
        self.exchanges = config_loader.list_exchanges()
        self.stock_exchanges = config_loader.list_exchanges(market_type='stock')
        self.future_exchanges = config_loader.list_exchanges(market_type='futures')
        self.client = config_loader.get_mongodb_client().quantbox
        self.default_start = "1990-12-19"  # 可以从配置获取

    def _save_trade_dates(self, df: pd.DataFrame) -> None:
        """保存交易日历数据到数据库

        Args:
            df: 交易日历数据，包含以下字段：
                - exchange: 交易所代码
                - trade_date: 交易日期
                - pretrade_date: 前一交易日
                - datestamp: 日期时间戳
                - date_int: 整数格式的日期 (YYYYMMDD)
        """
        if df.empty:
            return

        # 确保所有必需的字段都存在
        required_fields = ['exchange', 'trade_date', 'pretrade_date', 'datestamp', 'date_int']
        missing_fields = [field for field in required_fields if field not in df.columns]
        if missing_fields:
            # 如果缺少 date_int 字段，添加它
            if 'date_int' in missing_fields and 'trade_date' in df.columns:
                df['date_int'] = df['trade_date'].apply(lambda x: int(x.replace('-', '')))
                missing_fields.remove('date_int')
            if missing_fields:  # 如果还有其他缺失字段
                raise ValueError(f"Missing required fields: {missing_fields}")

        # 将 DataFrame 转换为字典列表
        records = df.to_dict('records')

        # 批量更新数据库
        for record in records:
            self.client.trade_date.update_one(
                {
                    'exchange': record['exchange'],
                    'date_int': record['date_int']
                },
                {'$set': record},
                upsert=True
            )

    def _ensure_indexes(self) -> None:
        """确保数据库中存在所需的索引"""
        collection = self.client.trade_date
        
        # 获取现有索引
        existing_indexes = collection.index_information()
        
        # 创建所需的索引
        required_indexes = [
            [("exchange", 1), ("datestamp", 1)],  # 复合索引：按交易所和时间戳查询
            [("datestamp", 1)],  # 单字段索引：按时间戳查询
            [("exchange", 1)],  # 单字段索引：按交易所查询
            [("exchange", 1), ("date_int", 1)],  # 复合索引：按交易所和整数日期查询
            [("date_int", 1)]  # 单字段索引：按整数日期查询
        ]
        
        for index in required_indexes:
            index_name = "_".join(f"{field}_{direction}" for field, direction in index)
            if index_name not in existing_indexes:
                print(f"创建索引: {index_name}")
                collection.create_index(index)

    def initialize(self):
        """初始化数据库连接和索引"""
        # 确保索引存在
        self._ensure_indexes()
        
        # 检查数据库是否为空
        if self.client.trade_date.count_documents({}) == 0:
            print("数据库为空，从 TuShare 获取数据...")
            # 获取交易日历数据
            fetcher = TSFetcher()
            df = fetcher.fetch_trade_dates()
            if not df.empty:
                self._save_trade_dates(df)
                print("数据获取和保存完成")

        # 更新所有文档，添加 date_int 字段
        if not self.client.trade_date.find_one({"date_int": {"$exists": True}}):
            print("添加 date_int 字段...")
            cursor = self.client.trade_date.find({})
            for doc in cursor:
                date_int = int(doc['trade_date'].replace('-', ''))
                self.client.trade_date.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"date_int": date_int}}
                )
            print("date_int 字段添加完成")


class LocalFetcher(LocalBaseFetcher):
    """
    Local database fetcher for retrieving market data.
    
    This class provides methods to fetch various types of market data from the local MongoDB database,
    including trading dates, future contracts, holdings, and more.
    """
    def __init__(self):
        super().__init__()
        self.exchanges = EXCHANGES.copy()
        self.stock_exchanges = STOCK_EXCHANGES.copy()
        self.future_exchanges = FUTURE_EXCHANGES.copy()
        self.client = DATABASE
        self.default_start = DEFAULT_START
        self.monitor = PerformanceMonitor(slow_query_threshold=2.0)  # 设置 2 秒为慢查询阈值

    @cache_result(ttl=3600)  # 缓存 1 小时，因为交易日历数据变化不频繁
    @monitor_performance
    def fetch_trade_dates(
        self,
        exchanges: Union[str, List[str], None] = None,
        start_date: Union[str, int, datetime.datetime, None] = None,
        end_date: Union[str, int, datetime.datetime, None] = None,
    ) -> pd.DataFrame:
        """
        获取交易日历

        Args:
            exchanges: 交易所列表或字符串，默认为所有交易所
            start_date: 起始日期，默认为 default_start
            end_date: 结束日期，默认为当前日期

        Returns:
            pd.DataFrame: 交易日历数据，包含以下字段：
                - exchange: 交易所代码
                - trade_date: 交易日期
                - pretrade_date: 前一交易日
                - datestamp: 日期时间戳
                - date_int: 整数格式的日期 (YYYYMMDD)
        """
        try:
            # 构建查询条件
            query = {}
            query.update(QueryBuilder.build_exchange_query(exchanges))
            query.update(QueryBuilder.build_date_range_query(start_date, end_date))

            # 执行查询，添加适当的索引和排序
            cursor = self.client.trade_date.find(
                query,
                QueryBuilder.build_projection(),
                sort=[("exchange", 1), ("datestamp", 1)],
                hint=[("exchange", 1), ("datestamp", 1)]  # 使用复合索引
            ).batch_size(5000)  # 根据数据量调整批次大小
            
            df = pd.DataFrame(list(cursor))
            if not df.empty:
                # 添加整数日期字段
                df['date_int'] = df['trade_date'].apply(lambda x: int(x.replace('-', '')))
            return df
        except Exception as e:
            raise Exception(f"获取交易日历失败: {str(e)}")

    @cache_result(ttl=300)  # 缓存 5 分钟，因为需要较新的数据
    @monitor_performance
    def fetch_pre_trade_date(
        self,
        exchange: str="SHSE",
        cursor_date: Union[str, int, datetime.datetime, None] = None,
        n: int=1,
        include: bool=False
    ) -> Dict[str, Any]:
        """
        获取指定日期之前的交易日

        Args:
            exchange: 交易所代码，默认为上交所
            cursor_date: 指定日期，默认为当前日期
            n: 往前回溯的天数，默认为 1
            include: 是否包含当天，默认为 False

        Returns:
            Dict: 交易日信息
        """
        if cursor_date is None:
            cursor_date = datetime.datetime.today()
        ExchangeValidator.validate_stock_exchange(exchange)

        try:
            # 构建查询条件
            query = {"exchange": exchange}
            query.update(QueryBuilder.build_single_date_query(
                cursor_date=cursor_date,
                include=include,
                before=True
            ))

            # 优化查询性能：使用排序和限制替代 skip
            cursor = self.client.trade_date.find(
                query,
                QueryBuilder.build_projection(),
                sort=[("datestamp", -1)],
                limit=n
            ).hint("idx_exchange_datestamp")  # 使用复合索引

            # 获取最后一个结果
            result = None
            for doc in cursor:
                result = doc
            return result
        except Exception as e:
            raise Exception(f"获取前一交易日失败: {str(e)}")

    @cache_result(ttl=300)  # 缓存 5 分钟，因为需要较新的数据
    @monitor_performance
    def fetch_next_trade_date(
        self,
        exchange: str="SHSE",
        cursor_date: Union[str, int, datetime.datetime, None] = None,
        n: int=1,
        include: bool=False
    ) -> Dict[str, Any]:
        """
        获取指定日期之后的交易日

        Args:
            exchange: 交易所代码，默认为上交所
            cursor_date: 指定日期，默认为当前日期
            n: 往后回溯的天数，默认为 1
            include: 是否包含当天，默认为 False

        Returns:
            Dict: 交易日信息
        """
        if cursor_date is None:
            cursor_date = datetime.datetime.today()
        ExchangeValidator.validate_stock_exchange(exchange)

        try:
            # 构建查询条件
            query = {"exchange": exchange}
            query.update(QueryBuilder.build_single_date_query(
                cursor_date=cursor_date,
                include=include,
                before=False
            ))

            # 优化查询性能：使用排序和限制替代 skip
            cursor = self.client.trade_date.find(
                query,
                QueryBuilder.build_projection(),
                sort=[("datestamp", 1)],
                limit=n
            ).hint("idx_exchange_datestamp")  # 使用复合索引

            # 获取最后一个结果
            result = None
            for doc in cursor:
                result = doc
            return result
        except Exception as e:
            raise Exception(f"获取下一交易日失败: {str(e)}")

    @cache_result(ttl=300)  # 缓存 5 分钟
    @monitor_performance
    def fetch_future_contracts(
        self,
        symbol: Optional[str] = None,
        exchanges: Union[str, List[str], None] = None,
        spec_name: Union[str, List[str], None] = None,
        cursor_date: Union[str, int, datetime.datetime, None] = None,
        fields: Union[List[str], None] = None,
    ) -> pd.DataFrame:
        """
        获取期货合约信息

        Args:
            symbol: 合约代码
            exchanges: 交易所列表或字符串
            spec_name: 合约品种名称
            cursor_date: 指定日期
            fields: 需要返回的字段列表

        Returns:
            pd.DataFrame: 合约信息
        """
        try:
            # 构建查询条件
            query = {}
            
            # 处理合约代码
            if symbol:
                query["symbol"] = symbol

            # 处理交易所
            if exchanges:
                exchanges = QueryBuilder.normalize_exchanges(exchanges)
                ExchangeValidator.validate_exchanges(exchanges)
                query.update(QueryBuilder.build_exchange_query(exchanges))

            # 处理品种名称
            if spec_name:
                if isinstance(spec_name, str):
                    spec_name = spec_name.split(",")
                query["chinese_name"] = {"$in": spec_name}

            # 处理日期条件
            if cursor_date:
                datestamp = util_make_date_stamp(cursor_date)
                query.update({
                    "list_datestamp": {"$lte": datestamp},
                    "delist_datestamp": {"$gte": datestamp}
                })

            # 执行查询
            cursor = self.client.future_contracts.find(
                query,
                QueryBuilder.build_projection(fields),
                batch_size=10000
            ).sort([("exchange", pymongo.ASCENDING), ("symbol", pymongo.ASCENDING)])
            
            return pd.DataFrame([item for item in cursor])
        except Exception as e:
            raise Exception(f"查询期货合约数据失败: {str(e)}")

    @monitor_performance
    def fetch_future_holdings(
        self,
        symbol: Optional[str] = None,
        exchanges: Union[str, List[str], None] = None,
        spec_names: Union[str, List[str], None] = None,
        cursor_date: Union[str, int, datetime.datetime, None] = None,
        start_date: Union[str, int, datetime.datetime, None] = None,
        end_date: Union[str, int, datetime.datetime, None] = None,
        fields: Union[List[str], None] = None,
    ) -> pd.DataFrame:
        """
        获取指定交易所指定品种持仓情况

        Args:
            symbol: 合约代码
            exchanges: 交易所列表或字符串
            spec_names: 合约品种名称
            cursor_date: 指定日期
            start_date: 开始日期
            end_date: 结束日期
            fields: 需要返回的字段列表

        Returns:
            pd.DataFrame: 持仓信息
        """
        collections = self.client.future_holdings
        collections_contracts = self.client.future_contracts
        # 确定交易所信息
        if exchanges is None:
            exchanges = self.future_exchanges
        else:
            if isinstance(exchanges, str):
                exchanges = exchanges.split(",")

        results = pd.DataFrame()
        # 1. 分支一：明确按照指定日期查询还是按照日期范围查询
        if start_date is None:
            # 按照指定日期查询，需要首先明确交易所，然后查询 最近一个交易日
            if cursor_date is None:
                cursor_date = datetime.datetime.today()
            # 1.1 按照是否指定合约进行判断
            if symbol:
                info = collections_contracts.find_one(
                    {
                        "symbol": symbol
                    }
                )
                if info is None:
                    raise ValueError(f"合约 {symbol} 本地没有找到交易所信息")
                exchange = info["exchange"]
                latest_trade_date = self.fetch_pre_trade_date(exchange=exchange, cursor_date=cursor_date, include=True)["trade_date"]
                cursor = collections.find(
                    {
                        "symbol": symbol,
                        "datestamp": util_make_date_stamp(latest_trade_date)
                    },
                    {"_id": 0},
                    batch_size=1000
                )
                results = pd.DataFrame([item for item in cursor])
                if fields:
                    return results[fields]
                else:
                    return results
            else:
                # 如果不指定合约，则判断是否需要判断品种
                if spec_names:
                    if isinstance(spec_names, str):
                        spec_names = spec_names.split(",")
                    for spec in spec_names:
                        info = collections_contracts.find_one(
                            {
                                "chinese_name": spec
                            }
                        )
                        if info is None:
                            raise ValueError(f"品种 {spec} 本地没有找到交易所信息")
                        exchange = info["exchange"]
                        # 合约查询
                        cursor = collections_contracts.find(
                            {
                                "chinese_name": spec,
                                "list_datestamp": {"$lte": util_make_date_stamp(cursor_date)},
                                "delist_datestamp": {"$gte": util_make_date_stamp(cursor_date)}
                            },
                            {"_id": 0},
                            batch_size=100
                        )
                        df_contracts = pd.DataFrame([item for item in cursor])
                        # 查找最近交易日，包括当前日期
                        latest_trade_date = self.fetch_pre_trade_date(
                            exchange=exchange,
                            cursor_date=cursor_date,
                            include=True
                        )["trade_date"]
                        cursor = collections.find(
                            {
                                "datestamp": util_make_date_stamp(latest_trade_date),
                                "exchange": exchange,
                                "symbol": {"$in": df_contracts['symbol'].tolist()}
                            },
                            {"_id": 0},
                            batch_size=10000
                        )
                        holdings = pd.DataFrame([item for item in cursor])
                        if results.empty:
                            results = holdings
                        else:
                            results = pd.concat([results, holdings], axis=0)
                    if fields:
                        return results[fields]
                    else:
                        return results
                else:
                    for exchange in exchanges:
                        latest_trade_date = self.fetch_pre_trade_date(exchange=exchange, cursor_date=cursor_date, include=True)["trade_date"]
                        cursor = collections.find(
                            {
                                "datestamp": util_make_date_stamp(latest_trade_date),
                                "exchange": exchange,
                            },
                            {"_id": 0},
                            batch_size=10000
                        )
                        holdings = pd.DataFrame([item for item in cursor])
                        if results.empty:
                            results = holdings
                        else:
                            results = pd.concat([results, holdings], axis=0)
                        if fields:
                            return results[fields]
                        else:
                            return results
        else:
            if end_date is None:
                end_date = datetime.datetime.today()
            if symbol:
                info = collections_contracts.find_one(
                    {
                        "symbol": symbol
                    }
                )
                if info is None:
                    raise ValueError(f"合约 {symbol} 本地没有找到交易所信息")
                exchange = info["exchange"]
                cursor = collections.find(
                    {
                        "symbol": symbol,
                        "exchange": exchange,
                        "datestamp": {
                            "$gte": util_make_date_stamp(start_date),
                            "$lte": util_make_date_stamp(end_date)
                        }
                    },
                    {"_id": 0},
                    batch_size=1000
                )
                results = pd.DataFrame([item for item in cursor])
                if fields:
                    return results[fields]
                else:
                    return results
            else:
                if spec_names:
                    if isinstance(spec_names, str):
                        spec_names = spec_names.split(",")
                    for spec in spec_names:
                        info = collections_contracts.find_one(
                            {
                                "chinese_name": spec
                            }
                        )
                        if info is None:
                            raise ValueError(f"品种 {spec} 本地没有找到交易所信息")
                        exchange = info["exchange"]
                        # 合约查询
                        cursor = collections_contracts.find(
                            {
                                "chinese_name": spec,
                                "$or": [
                                    {"list_datestamp": {"$lte": util_make_date_stamp(start_date)}},
                                    {"delist_datestamp": {"$gte": util_make_date_stamp(end_date)}}
                                ]
                            },
                            {"_id": 0},
                            batch_size=10000
                        )
                        df_contracts = pd.DataFrame([item for item in cursor])
                        cursor = collections.find(
                            {
                                "datestamp": {
                                    "$gte": util_make_date_stamp(start_date),
                                    "$lte": util_make_date_stamp(end_date)
                                },
                                "exchange": exchange,
                                "symbol": {"$in": df_contracts['symbol'].tolist()}
                            },
                            {"_id": 0},
                            batch_size=10000
                        )
                        holdings = pd.DataFrame([item for item in cursor])
                        if results.empty:
                            results = holdings
                        else:
                            results = pd.concat([results, holdings], axis=0)
                    if fields:
                        return results[fields]
                    else:
                        return results
                else:
                    cursor = collections.find(
                        {
                            "datestamp": {
                                "$gte": util_make_date_stamp(start_date),
                                "$lte": util_make_date_stamp(end_date)
                            },
                            "exchange": {"$in": exchanges},
                        },
                        {"_id": 0},
                        batch_size=10000
                    )
                    holdings = pd.DataFrame([item for item in cursor])
                    if results.empty:
                        results = holdings
                    if fields:
                        return results[fields]
                    else:
                        return results

    @monitor_performance
    def fetch_future_daily(
       self,
       cursor_date: Union[str, datetime.datetime, int, None] = None,
       symbols: Union[str, List[str], None] = None,
       exchanges: Union[str, List[str], None] = None,
       start_date: Union[str, datetime.datetime, int, None] = None,
       end_date: Union[str, datetime.datetime, int, None] = None,
       fields: Union[List[str], None] = None,
    ) -> pd.DataFrame:
        """
        获取指定交易所指定品种日线行情

        Args:
            cursor_date: 指定日期最近交易日（当前日期包括在内）, 默认为 None，如果 start_date 不指定时，将默认 cursor_date 为当前日期
            symbols: 指定合约代码列表，默认为 None, 当指定 symbols 后，exchanges 参数失效
            exchanges: 交易所列表或字符串，默认为 None
            start_date: 开始日期，默认为 None，当指定了 start_date 以后，cursor_date 失效
            end_date: 结束日期，默认为 None, 当指定了 start_date 以后，end_date 如果为 None，则默认为当前日期
            fields: 需要返回的字段列表

        Returns:
            pd.DataFrame: 日线行情数据
        """
        collections = self.client.future_daily
        if start_date:
            if end_date is None:
                end_date = datetime.datetime.today()
            if symbols:
                symbols = util_format_future_symbols(symbols=symbols, include_exchange=False)
                cursor = collections.find(
                    {
                        "symbol": {"$in": symbols},
                        "datestamp": {
                            "$gte": util_make_date_stamp(start_date),
                            "$lte": util_make_date_stamp(end_date),
                        },
                    },
                    {"_id": 0},
                    batch_size=10000,
                )
                results = pd.DataFrame([item for item in cursor])
                if fields:
                    return results[fields]
                else:
                    return results
            else:
                if exchanges is None:
                    exchanges = self.future_exchanges
                elif isinstance(exchanges, str):
                    exchanges = exchanges.split(",")
                for exchange in exchanges:
                    cursor = collections.find({
                        "datestamp": {
                            "$gte": util_make_date_stamp(start_date),
                            "$lte": util_make_date_stamp(end_date),
                        },
                        "exchange": {"$in": exchanges}
                        },
                        {"_id": 0},
                        batch_size=10000,
                    )
                    results = pd.DataFrame([item for item in cursor])
                    if fields:
                        return results[fields]
                    else:
                        return results
        else:
            if cursor_date is None:
                cursor_date = datetime.datetime.today()
            latest_trade_date = self.fetch_pre_trade_date(
                cursor_date=cursor_date, include=True
            )["trade_date"]
            if symbols:
                symbols = util_format_future_symbols(symbols=symbols)
                cursor = collections.find({
                    "symbol": {"$in": symbols},
                    "datestamp": util_make_date_stamp(cursor_date)
                },
                {"_id": 0},
                batch_size=1000
                )
                results = pd.DataFrame([item for item in cursor])
                if fields:
                    return results[fields]
                else:
                    return results
            else:
                if exchanges is None:
                    exchanges = self.future_exchanges
                elif isinstance(exchanges, str):
                    exchanges = exchanges.split(",")
                cursor = collections.find({
                    "datestamp": util_make_date_stamp(cursor_date),
                    "exchange": {"$in": exchanges}
                },
                {"_id": 0},
                batch_size=1000
                )
                results = pd.DataFrame([item for item in cursor])
                if fields:
                    return results[fields]
                else:
                    return results


if __name__ == "__main__":
    local_fetcher = LocalFetcher()
    # print(local_fetcher.fetch_pre_trade_date())
    # print(local_fetcher.fetch_pre_trade_date(n=2, include=True))
    # print(local_fetcher.fetch_pre_trade_date(n=2, include=False))
    # print(local_fetcher.fetch_next_trade_date())
    # print(local_fetcher.fetch_next_trade_date(n=2, include=True))
    # print(local_fetcher.fetch_next_trade_date(n=2, include=False))
    # print(local_fetcher.fetch_trade_dates(exchanges="SSE", start_date="2024-09-01", end_date="2024-09-30"))
    # print(local_fetcher.fetch_trade_dates(exchanges=["SSE", "DCE"], start_date="2024-09-01", end_date="2024-09-30"))
    # print(local_fetcher.fetch_future_contracts(exchanges=["DCE"], spec_name="豆粕"))
    # print(local_fetcher.fetch_future_contracts(exchanges=["DCE"], spec_name="豆粕", cursor_date="2024-09-30"))
    # print(local_fetcher.fetch_future_contracts(spec_name="豆粕", cursor_date="2024-09-30"))
    # print(local_fetcher.fetch_future_contracts(cursor_date="2024-09-30"))
    # print(local_fetcher.fetch_future_holdings(symbol="M2501", cursor_date="2024-09-27"))
    # print(local_fetcher.fetch_future_holdings(symbol="M2501", start_date="2024-09-26", end_date="2024-09-27"))
    # print(local_fetcher.fetch_future_holdings(spec_names=["豆粕", "热轧卷板"], start_date="2024-09-01", end_date="2024-09-10"))
    # print(local_fetcher.fetch_future_holdings(spec_names=["豆粕", "热轧卷板"], cursor_date="2024-09-30"))
    print(local_fetcher.fetch_future_daily(
        symbols=["M2501", "RB2501"],
        start_date="20240901",
        end_date="20240930"
    ))

    print(local_fetcher.fetch_future_daily(
        exchanges="SHFE, DCE",
        cursor_date="20240930"
    ))
