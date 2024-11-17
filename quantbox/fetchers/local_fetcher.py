"""
Local fetcher module for retrieving data from local database.
"""
import datetime
import pandas as pd
from typing import List, Optional, Union, Dict

from quantbox.fetchers.base import BaseFetcher
from quantbox.util.basic import DATABASE, DEFAULT_START, EXCHANGES, FUTURE_EXCHANGES, STOCK_EXCHANGES
from quantbox.util.tools import util_make_date_stamp, util_format_future_symbols


class LocalFetcher(BaseFetcher):
    """
    Local database fetcher for retrieving market data.
    
    This class provides methods to fetch various types of market data from the local MongoDB database,
    including trading dates, future contracts, holdings, and more.
    """
    def __init__(self):
        super().__init__()
        """
         本地数据库查询器
        """
        self.exchanges = EXCHANGES
        self.stock_exchanges = STOCK_EXCHANGES
        self.future_exchanges = FUTURE_EXCHANGES
        self.client = DATABASE
        self.default_start = DEFAULT_START

    def fetch_trade_dates(
        self,
        exchanges: Union[str, List[str], None] = None,
        start_date: Union[str, int, datetime.datetime, None] = None,
        end_date: Union[str, int, datetime.datetime, None] = None,
    ) -> pd.DataFrame:
        """
        explanation:
            本地获取 时间范围内的交易日历 (闭区间，如果起讫时间为交易日，会包括在内)

        params:
            * exchanges ->
                含义: 交易所, 默认为项目常量 EXCHANGES 定义的所有交易所
                类型: str, list
                参数支持: ['SSE', 'SZSE', 'SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
            * start_date ->
                含义: 起始时间, 默认从 "1990-12-19" 开始
                类型: int, str, datetime
                参数支持: [19910906, '1992-03-02', datetime.datetime(2024, 9, 16)]
            * end_date ->
                含义: 截止时间
                类型: int, str, datetime, 默认截止为当前日期
                参数支持: [19910906, '1992-03-02', datetime.datetime(2024, 9, 16)]
        returns:
            pd.DataFrame ->
                符合条件的交易日
        """
        if exchanges is None:
            exchanges = self.exchanges
        if isinstance(exchanges, str):
            exchanges = exchanges.split(",")
        if start_date is None:
            start_date = self.default_start
        if end_date is None:
            end_date = datetime.datetime.today()
        collections = self.client.trade_date
        cursor = collections.find(
            {
                "exchange": {"$in": exchanges},
                "datestamp": {
                    "$gte": util_make_date_stamp(start_date),
                    "$lte": util_make_date_stamp(end_date),
                },
            },
            {"_id": 0},
            batch_size=10000,
        )
        "获取交易日期"
        return pd.DataFrame([item for item in cursor])


    def fetch_pre_trade_date(
        self,
        exchange: str="SSE",
        cursor_date: Union[str, int, datetime.datetime, None] = None,
        n: int=1,
        include: bool=False
    ) -> str:
        """
        explanation:
            获取指定日期之前 n 个交易日的交易日

        params:
            * exchange ->
                含义: 交易所, 默认为上交所 SSE
                类型: str
                参数支持: 'SSE', 'SZSE', 'SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE'
            cursor_date ->
                含义: 指定时间, 默认为当前日期
                类型: int, str, datetime
                参数支持: 19910906, '1992-03-02', datetime.datetime(2024, 9, 16), ...
            int ->
                含义：往前回溯日期，默认为 1
                类型：int
                参数支持：1,2,3,...
            include ->
                含义：如果当天为交易日，是否包含当天，默认不包含当天
                类型：bool
                参数支持：True, False
        """
        if cursor_date is None:
            cursor_date = datetime.datetime.today()
        collections = self.client.trade_date
        count = collections.count_documents({
            "exchange": exchange,
            "datestamp": util_make_date_stamp(cursor_date)
        })
        if count == 0:
            cursor = collections.find(
                {
                    "exchange": exchange,
                    "datestamp": {
                        "$lte": util_make_date_stamp(cursor_date),
                    },
                },
                {"_id": 0},
                batch_size=1000,
            ).skip(n-1)
        else:
            if include:
                cursor = collections.find(
                    {
                        "exchange": exchange,
                        "datestamp": {
                            "$lte": util_make_date_stamp(cursor_date),
                        },
                    },
                    {"_id": 0},
                    batch_size=1000,
                ).skip(n-1)
            else:
                cursor = collections.find(
                    {
                        "exchange": exchange,
                        "datestamp": {
                            "$lt": util_make_date_stamp(cursor_date),
                        },
                    },
                    {"_id": 0},
                    batch_size=1000,
                ).skip(n-1)
        # 数据库中交易日默认为逆序排列
        item = cursor.next()
        return item


    def fetch_next_trade_date(
        self,
        exchange: str="SSE",
        cursor_date: Union[str, int, datetime.datetime, None] = None,
        n: int=1,
        include: bool=False
    ) -> Dict:
        """
        explanation:
            获取指定日期之 后 n 个交易日的交易日

        params:
            * exchange ->
                含义: 交易所, 默认为上交所 SSE
                类型: str
                参数支持: 'SSE', 'SZSE', 'SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE'
            * cursor_date ->
                含义: 指定时间, 默认为当前日期
                类型: int, str, datetime
                参数支持: 19910906, '1992-03-02', datetime.datetime(2024, 9, 16), ...
            * int ->
                含义：往后回溯日期，默认为 1
                类型：int
                参数支持：1,2,3,...
            * include ->
                含义：如果当天为交易日，是否包含当天，默认不包含当天
                类型：bool
                参数支持：True, False
        returns:
            Dict ->
                符合条件的交易日信息
        """
        if cursor_date is None:
            cursor_date = datetime.datetime.today()
        collections = self.client.trade_date
        count = collections.count_documents({
            "exchange": exchange,
            "datestamp": util_make_date_stamp(cursor_date)
        })
        if count == 0:
            cursor = collections.find(
                {
                    "exchange": exchange,
                    "datestamp": {
                        "$gte": util_make_date_stamp(cursor_date),
                    },
                },
                {"_id": 0},
                batch_size=1000,
            ).sort("datestamp", pymongo.ASCENDING).skip(n)
        else:
            if include:
                cursor = collections.find(
                    {
                        "exchange": exchange,
                        "datestamp": {
                            "$gte": util_make_date_stamp(cursor_date),
                        },
                    },
                    {"_id": 0},
                    batch_size=1000,
                ).sort("datestamp", pymongo.ASCENDING).skip(n)
            else:
                cursor = collections.find(
                    {
                        "exchange": exchange,
                        "datestamp": {
                            "$gt": util_make_date_stamp(cursor_date),
                        },
                    },
                    {"_id": 0},
                    batch_size=1000,
                ).sort("datestamp", pymongo.ASCENDING).skip(n)
        item = cursor.next()
        return item

    def fetch_future_contracts(
        self,
        symbol: Optional[str] = None,
        exchanges: Union[str, List[str], None] = None,
        spec_name: Union[str, List[str], None] = None,
        cursor_date: Union[str, int, datetime.datetime, None] = None,
        fields: Union[List[str], None] = None,
    ) -> pd.DataFrame:
        """
        explanation:
            获取期货合约信息

        params:
            * symbol ->
                含义：合约名称，默认为空
                类型: str,
                参数支持: ["AO2507", "AL0511", ...]
            * exchanges ->
                含义: 交易所, 默认为空，包含所有交易所信息
                类型: Union[str, List[str], None]
                参数支持: ['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
            * spec_name ->
                含义：合约中文名称，默认为 None, 取所有品种
                参数：Union[str, List[str], None]
                参数支持：["豆粕", "棕榈油", ...]
            * cursor_date ->
                含义: 指定时间, 默认为 None, 即获取所有合约
                类型: int, str, datetime
                参数支持: [19910906, '1992-03-02', datetime.datetime(2024, 9, 16)]
            * fields ->
                含义：自定义字段，默认为 None, 获取合约所有字段
                类型: Union[List[str], None]
                参数支持: ['symbol', 'name', 'list_date', 'delist_date']
        returns:
            pd.DataFrame ->
                合约信息
        """
        collections = self.client.future_contracts
        if cursor_date is None:
            if symbol:
                cursor = collections.find(
                    {"symbol": symbol},
                    {"_id": 0},
                    batch_size=1000
                )
            else:
                if exchanges:
                    if isinstance(exchanges, str):
                        exchanges = exchanges.split(",")
                    if spec_name:
                        if isinstance(spec_name, str):
                            spec_name = spec_name.split(",")
                        cursor = collections.find(
                            {
                                "exchange": {"$in": exchanges},
                                "chinese_name": {"$in": spec_name},
                            },
                            {"_id": 0},
                            batch_size=1000,
                        )
                    else:
                        cursor = collections.find(
                            {"exchange": {"$in": exchanges}},
                            {"_id": 0},
                            batch_size=10000
                        )
                else:
                    if spec_name:
                        if isinstance(spec_name, str):
                            spec_name = spec_name.split(",")
                        cursor = collections.find(
                            {"chinese_name": {"$in": spec_name}},
                            {"_id": 0},
                            batch_size=10000
                        )
                    else:
                        cursor = collections.find(
                            {},
                            {"_id":0},
                            batch_size=10000
                        )
        else:
            if symbol:
                cursor = collections.find(
                    {
                        "symbol": symbol,
                        "list_datestamp": {"$lte": util_make_date_stamp(cursor_date)},
                        "delist_datestamp": {"$gte": util_make_date_stamp(cursor_date)}
                    },
                    {"_id": 0},
                    batch_size=1000
                )
            else:
                if exchanges:
                    if isinstance(exchanges, str):
                        exchanges = exchanges.split(",")
                    if spec_name:
                        if isinstance(spec_name, str):
                            spec_name = spec_name.split(",")
                        cursor = collections.find(
                            {
                                "exchange": {"$in": exchanges},
                                "chinese_name": {"$in": spec_name},
                                "list_datestamp": {"$lte": util_make_date_stamp(cursor_date)},
                                "delist_datestamp": {"$gte": util_make_date_stamp(cursor_date)}
                            },
                            {"_id": 0},
                            batch_size=1000,
                        )
                    else:
                        cursor = collections.find(
                            {
                                "exchange": {"$in": exchanges},
                                "list_datestamp": {"$lte": util_make_date_stamp(cursor_date)},
                                "delist_datestamp": {"$gte": util_make_date_stamp(cursor_date)}
                            },
                            {"_id": 0},
                            batch_size=10000
                        )
                else:
                    if spec_name:
                        if isinstance(spec_name, str):
                            spec_name = spec_name.split(",")
                        cursor = collections.find(
                            {
                                "chinese_name": {"$in": spec_name},
                                "list_datestamp": {"$lte": util_make_date_stamp(cursor_date)},
                                "delist_datestamp": {"$gte": util_make_date_stamp(cursor_date)}
                            },
                            {"_id": 0},
                            batch_size=10000
                        )
                    else:
                        cursor = collections.find(
                            {
                                "list_datestamp": {"$lte": util_make_date_stamp(cursor_date)},
                                "delist_datestamp": {"$gte": util_make_date_stamp(cursor_date)}
                            },
                            {"_id": 0},
                            batch_size=10000
                        )
        return pd.DataFrame([item for item in cursor])

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
        explanation:
            获取指定交易所指定品种持仓情况

        params:
            * symbol ->
                含义：合约，默认为 None，会查询所有合约
                类型：str
                参数支持: M2501
            * exchanges ->
                含义：交易所, 默认为 DCE
                类型：Union[str, List[str], None]
                参数支持：DEC, INE, SHFE, INE, CFFEX
            * spec_names ->
                含义：品种，默认为 None, 不限制品种
                类型: Union[str, List[str], None]
                参数支持：豆粕、热卷、...
            * cursor_date ->
                含义：指定日期，默认为 None，取离今天最近的交易日（今天包含在内）
                类型：Union[str, int, datetime.datetime]
                参数支持：20200913, "20210305", ...
            * start_date ->
                含义：起始时间，默认为 None，如果为 None，则默认使用 cursor_date
                类型：Union[str, int, datetime.datetime]
                参数支持：20200913, "20210305", ...
            * end_date ->
                含义： 结束时间，默认为 None, 当 start_date 为 None 时，参数不生效
                类型：Union[str, int, datetime.datetime]
                参数支持：20200913, "20210305", ...
            * symbols ->
                含义：指定交易品种，默认为 None, 当前交易所所有合约
        returns:
            pd.DataFrame ->
                实际龙虎榜数据
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
        explanation:
            获取指定交易所指定品种日线行情

        params:
            * cursor_date ->
                含义：指定日期最近交易日（当前日期包括在内）, 默认为 None，如果 start_date 不指定时，将默认 cursor_date 为当前日期
                类型：Union[str, datetime.datetime, int, None]
                参数支持： 20240930, "20240926"
            * symbols ->
                含义：指定合约代码列表，默认为 None, 当指定 symbols 后，exchanges 参数失效
                类型： Union[str, List[str]]
                参数支持：["M2501, M2505"]
            * exchanges ->
                含义：交易所 列表, 默认为 None
                类型：Union[str, List[str], None]
                参数支持：DEC, INE, SHFE, INE, CFFEX
            * start_date ->
                含义：起始时间，默认为 None，当指定了 start_date 以后，cursor_date 失效
                类型：Union[str, int, datetime.datetime]
                参数支持：20200913, "20210305", ...
            * end_date ->
                含义： 结束时间，默认为 None, 当指定了 start_date 以后，end_date 如果为 None，则默认为当前日期
                类型：Union[str, int, datetime.datetime]
                参数支持：20200913, "20210305", ...
            returns:
                pd.DataFrame ->
                    期货日线行情
        """
        collections = self.client.future_daily
        if start_date:
            if end_date is None:
                end_date = datetime.datetime.today()
            if symbols:
                symbols = util_format_future_symbols(symbols=symbols)
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


# 添加全局函数
def fetch_trade_dates(exchanges=None, start_date=None, end_date=None):
    queryer = LocalFetcher()
    return queryer.fetch_trade_dates(exchanges, start_date, end_date)

def fetch_pre_trade_date(exchange="SSE", cursor_date=None, n=1, include=False):
    queryer = LocalFetcher()
    return queryer.fetch_pre_trade_date(exchange, cursor_date, n, include)

def fetch_next_trade_date(exchange="SSE", cursor_date=None, n=1, include=False):
    queryer = LocalFetcher()
    return queryer.fetch_next_trade_date(exchange, cursor_date, n, include)

def fetch_future_contracts(symbol=None, exchanges=None, spec_name=None, cursor_date=None, fields=None):
    queryer = LocalFetcher()
    return queryer.fetch_future_contracts(symbol, exchanges, spec_name, cursor_date, fields)

def fetch_future_holdings(symbol=None, exchanges=None, spec_names=None, cursor_date=None, start_date=None, end_date=None, fields=None):
    queryer = LocalFetcher()
    return queryer.fetch_future_holdings(symbol, exchanges, spec_names, cursor_date, start_date, end_date, fields)


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
