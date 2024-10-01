import tushare as ts
from quantbox.util.basic import FUTURE_EXCHANGES, STOCK_EXCHANGES, TSPRO, EXCHANGES, DATABASE, DEFAULT_START
from quantbox.fetchers.local_fetch import Queryer
import re
import datetime
import pandas as pd
from typing import Union, List, Optional

from quantbox.util.tools import util_make_date_stamp

class TSFetcher:
    def __init__(self):
        """
        基于 tushare 的接口优化的查询类
        """
        self.pro = TSPRO
        self.exchanges = EXCHANGES
        self.stock_exchanges = STOCK_EXCHANGES
        self.future_exchanges = FUTURE_EXCHANGES
        self.client = DATABASE
        self.default_start = DEFAULT_START
        self.local_queryer = Queryer()

    def fetch_get_trade_dates(
        self,
        exchanges: Union[List[str], str, None] = None,
        start_date: Union[str, datetime.date, int, None] = None,
        end_date: Union[str, datetime.date, int, None] = None
    ) -> pd.DataFrame:
        """
        explanation:
            获取指定交易所的日期范围内的交易日

        params:
            * exchanges ->
                含义: 交易所, 默认为上交所 SSE
                类型: str
                参数支持: ['SSE', 'SZSE', 'SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
            * start_date ->
                含义: 起始时间, 默认从 DEFAULT_START 开始
                类型: int, str, datetime
                参数支持: [19910906, '1992-03-02', datetime.date(2024, 9, 16)]
            * end_date ->
                含义: 截止时间
                类型: int, str, datetime, 默认截止为当前日期
                参数支持: [19910906, '1992-03-02', datetime.date(2024, 9, 16)]
        """
        if exchanges is None:
            exchanges = self.exchanges
        if isinstance(exchanges, str):
            exchanges = exchanges.split(",")
        if start_date is None:
            start_date = self.default_start
        if end_date is None:
            end_date = datetime.date(datetime.date.today().year, 12, 31)
        start_date = pd.Timestamp(str(start_date)).strftime("%Y%m%d")
        end_date = pd.Timestamp(str(end_date)).strftime("%Y%m%d")
        results = pd.DataFrame()
        for exchange in exchanges:
            data = self.pro.trade_cal(
                exchange=exchange,
                start_date=start_date,
                end_date=end_date
            )
            # PS: tushare 保留 is_open 这个字段有道理，交易日计划与实际可能会有偏差
            # TODO: 未来考虑优化
            data = data.loc[data["is_open"] == 1]
            data["datestamp"] = data["cal_date"].map(str).apply(
                lambda x: util_make_date_stamp(x)
            )
            results = pd.concat([results, data], axis=0)
        results = results.rename(columns={"cal_date": "trade_date"})
        results.trade_date = pd.to_datetime(results.trade_date).dt.strftime("%Y-%m-%d")
        results.pretrade_date = pd.to_datetime(results.pretrade_date).dt.strftime("%Y-%m-%d")
        return results[["exchange", "trade_date", "pretrade_date", "datestamp"]]

    def fetch_get_future_contracts(
        self,
        exchange: str = "DCE",
        spec_name: Union[str, List[str], None] = None,
        cursor_date: Optional[str] = None,
        fields: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        explanation:
            Tushare 获取交易期货合约接口封装，可以基于品种中文名，日期进行筛选

        params:
            * exchange ->
                含义: 交易所, 默认为大商所 DCE
                类型: str
                参数支持: ['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
            * spec_name ->
                含义：合约中文名称，默认为 None, 取所有品种
                参数：str
                参数支持：["豆粕", "棕榈油", ...]
            * cursor_date ->
                含义: 指定时间, 默认为 None, 即获取所有合约
                类型: int, str, datetime
                参数支持: [19910906, '1992-03-02', datetime.date(2024, 9, 16)]
            * fields ->
                含义：自定义字段，默认为 None, 获取合约所有字段
                类型: List[str]
                参数支持: ['symbol', 'name', 'list_date', 'delist_date']
        returns:
            pd.DataFrame ->
                合约信息
        """
        if fields:
            if "list_date" not in fields:
                fields.append("list_date")
            if "delist_date" not in fields:
                fields.append("delist_date")
            if "name" not in fields:
                fields.append("name")
            if "ts_code" not in fields:
                fields.append("ts_code")
            data = self.pro.fut_basic(exchange=exchange, fut_type="1", fields=fields)
        else:
            data = self.pro.fut_basic(
                exchange=exchange,
                fut_type="1",
            )
        data["list_datestamp"] = (
            data["list_date"].map(str).apply(lambda x: util_make_date_stamp(x))
        )
        data["delist_datestamp"] = (
            data["delist_date"].map(str).apply(lambda x: util_make_date_stamp(x))
        )
        pattern = r"(.*?)\d+\s*"
        data["chinese_name"] = data["name"].apply(lambda x: re.findall(pattern, x)[0])
        if exchange == "CZCE":
            data["symbol"] = data["ts_code"].map(str).apply(lambda x: x.split(".")[0])

        if spec_name:
            if isinstance(spec_name, str):
                spec_name = spec_name.split(",")
            data = data.loc[data["chinese_name"].isin(spec_name)]
            columns = data.columns.tolist()
            data = data[columns]

        columns = data.columns.tolist()

        data.list_date = pd.to_datetime(data.list_date).dt.strftime("%Y-%m-%d")
        data.delist_date = pd.to_datetime(data.delist_date).dt.strftime("%Y-%m-%d")

        if ("ts_code" in columns) and (fields is None):
            columns.remove("ts_code")

        data = data[columns]

        if cursor_date is None:
            return data
        else:
            cursor_date = pd.Timestamp(str(cursor_date)).strftime("%Y-%m-%d")
            return data.loc[
                (data["list_date"] <= cursor_date) & (data["delist_date"] > cursor_date)
            ]

    def fetch_get_holdings(
        self,
        exchanges: Union[str, List[str], None] = None,
        cursor_date: Union[int, str, datetime.date, None] = None,
        start_date: Union[int, str, datetime.date, None] = None,
        end_date: Union[int, str, datetime.date, None] = None,
        symbols: Union[str, List[str], None]=None,
    ) -> pd.DataFrame:
        """
        explanation:
            获取指定交易所指定品种持仓情况

        params:
            * exchanges ->
                含义：交易所, 默认为 DCE
                类型：Union[str, List[str], None]
                参数支持：DEC, INE, SHFE, INE, CFFEX
            * cursor_date ->
                含义：指定日期，默认为 None，取离今天最近的交易日（今天包含在内）
                类型：Union[str, int, datetime.date]
                参数支持：20200913, "20210305", ...
            * start_date ->
                含义：起始时间，默认为 None
                类型：Union[str, int, datetime.date]
                参数支持：20200913, "20210305", ...
            * end_date ->
                含义： 结束时间，默认为 None
                类型：Union[str, int, datetime.date]
                参数支持：20200913, "20210305", ...
            * symbols ->
                含义：指定交易品种，默认为 None, 当前交易所所有合约
        returns:
            pd.DataFrame ->
                实际龙虎榜数据
        """
        if exchanges is None:
            exchanges = self.future_exchanges
        if isinstance(exchanges, str):
            exchanges = exchanges.split(",")
        total_holdings = pd.DataFrame()
        for exchange in exchanges:
            # 如果 start_date 为 None, 默认按照指定日期进行查询
            if start_date is None:
                if cursor_date is None:
                    cursor_date = datetime.date.today()
                latest_trade_date = self.local_queryer.fetch_pre_trade_date(
                    exchange=exchange,
                    cursor_date=cursor_date,
                    include=True
                )['trade_date']
                if symbols is None:
                    symbols = self.local_queryer.fetch_future_contracts(
                        exchanges=exchange,
                        cursor_date=cursor_date
                    ).symbol.tolist()
                else:
                    if isinstance(symbols, str):
                        symbols = symbols.split(",")
                for symbol in symbols:
                    holdings = self.pro.fut_holding(
                        trade_date=latest_trade_date.replace("-", ""),
                        symbol = symbol,
                        exchange=exchange
                    )
                    if not holdings.empty:
                        if total_holdings.empty:
                            total_holdings = holdings
                        else:
                            total_holdings = pd.concat([total_holdings, holdings], axis=0)
            else:
                if end_date is None:
                    end_date = datetime.date.today()
                start_date = pd.Timestamp(str(start_date)).strftime("%Y%m%d")
                end_date = pd.Timestamp(str(end_date)).strftime("%Y%m%d")
                if symbols is None:
                    # 对于这种场景，可以先去根据交易日获取所有的合约列表，然后去查询
                    trade_dates = self.local_queryer.fetch_trade_dates(exchanges=exchange, start_date=start_date, end_date=end_date).trade_date.tolist()
                    symbols = []
                    for trade_date in trade_dates:
                        symbols = symbols + self.local_queryer.fetch_future_contracts(
                            exchanges=exchange,
                            cursor_date=trade_date
                        ).symbol.tolist()
                    symbols = list(set(symbols))
                else:
                    if isinstance(symbols, str):
                        symbols = symbols.split(",")
                for symbol in symbols:
                    holdings = self.pro.fut_holding(
                        symbol=symbol,
                        exchange=exchange,
                        start_date=start_date,
                        end_date=end_date
                    )
                    if not holdings.empty:
                        if total_holdings.empty:
                            total_holdings = holdings
                        else:
                            total_holdings = pd.concat([total_holdings, holdings], axis=0)
            if total_holdings.empty:
                print(f"当前期货交易所 {exchange} 没有持仓数据")
                continue
            total_holdings["datestamp"] = total_holdings['trade_date'].apply(lambda x: util_make_date_stamp(x))
            total_holdings['trade_date'] = pd.to_datetime(total_holdings['trade_date']).dt.strftime("%Y-%m-%d")
            total_holdings["exchange"] = exchange
        return total_holdings


# 添加全局函数
def fetch_get_trade_dates(exchanges=None, start_date=None, end_date=None):
    fetcher = TSFetcher()
    return fetcher.fetch_get_trade_dates(exchanges, start_date, end_date)

def fetch_get_future_contracts(exchange="DCE", spec_name=None, cursor_date=None, fields=None):
    fetcher = TSFetcher()
    return fetcher.fetch_get_future_contracts(exchange, spec_name, cursor_date, fields)

def fetch_get_holdings(exchanges=None, cursor_date=None, start_date=None, end_date=None, symbols=None):
    fetcher = TSFetcher()
    return fetcher.fetch_get_holdings(exchanges, cursor_date, start_date, end_date, symbols)

if __name__ == "__main__":
    fetcher = TSFetcher()
    # print(fetcher.fetch_get_trade_dates(
    #     "SSE",
    #     "2024-08-01",
    #     "2024-09-01"
    # ))
    # print(fetcher.fetch_get_trade_dates(
    #     ["SSE", "DCE"],
    #     "2024-08-01",
    #     "2024-09-01"
    # ))
    print(fetcher.fetch_get_future_contracts(
        exchange="DCE",
        spec_name="豆粕",
    ))

    # print(fetcher.fetch_get_future_contracts(
    #     exchange="DCE",
    #     spec_name="豆粕",
    #     cursor_date="2024-09-30"
    # ))

    # print(fetcher.fetch_get_future_contracts(
    #     exchange="DCE",
    #     spec_name="豆粕",
    #     cursor_date="2024-09-30",
    #     fields=['ts_code', 'symbol', 'exchange', 'name']
    # ))

    # print(fetcher.fetch_trade_dates(exchanges="SSE", start_date="2024-09-01", end_date="2024-09-30"))
