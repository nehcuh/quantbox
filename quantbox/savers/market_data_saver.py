import datetime
from typing import List, Union
import time

import pandas as pd
import pymongo

from quantbox.fetchers.local_fetch import Queryer, fetch_next_trade_date
from quantbox.fetchers.remote_fetch_gm import GMFetcher
from quantbox.fetchers.remote_fetch_tushare import TSFetcher
from quantbox.util.basic import DATABASE, EXCHANGES, FUTURE_EXCHANGES, STOCK_EXCHANGES
from quantbox.util.tools import (
    util_format_stock_symbols,
    util_make_date_stamp,
    util_to_json_from_pandas,
    is_trade_date
)


class MarketDataSaver:
    """
    市场数据保存器，支持从多个数据源（Tushare、掘金等）获取并保存市场数据，包括：
    - 交易日期数据
    - 期货合约信息
    - 期货持仓数据
    - 期货日线数据
    - 股票列表数据
    """
    def __init__(self):
        self.ts_fetcher = TSFetcher()
        self.gm_fetcher = GMFetcher()
        self.queryer = Queryer()
        self.client = DATABASE
        self.exchanges = EXCHANGES
        self.future_exchanges = FUTURE_EXCHANGES
        self.stock_exchanges = STOCK_EXCHANGES

    def save_trade_dates(self):
        """
        本地化交易日期
        """
        collections = self.client.trade_date
        collections.create_index(
            [("exchange", pymongo.ASCENDING), ("datestamp", pymongo.DESCENDING)]
        )
        for exchange in self.exchanges:
            count = collections.count_documents({"exchange": exchange})
            if count > 0:
                # 获取第一个文档
                first_doc = collections.find_one(
                    {"exchange": exchange}, sort=[("datestamp", pymongo.DESCENDING)]
                )
                latest_date = first_doc["trade_date"]
            else:
                latest_date = "1990-12-19"

            data = util_to_json_from_pandas(
                self.ts_fetcher.fetch_get_trade_dates(
                    exchanges=exchange, start_date=latest_date
                )
            )
            if len(data) > 0:
                collections.insert_many(data)

    def save_future_contracts(self):
        """
        explanation:
            保存期货合约信息到本地
        """
        collections = self.client.future_contracts
        collections.create_index(
            [
                ("exchange", pymongo.ASCENDING),
                ("symbol", pymongo.ASCENDING),
                ("datestamp", pymongo.DESCENDING),
            ]
        )
        for exchange in self.future_exchanges:
            total_contracts = self.ts_fetcher.fetch_get_future_contracts(
                exchange=exchange
            )
            symbols = total_contracts.symbol.tolist()
            count = collections.count_documents(
                {"exchange": exchange, "symbol": {"$in": symbols}}
            )
            if count > 0:
                # 查询当前已有的合约信息
                cursor = collections.find(
                    {"exchange": exchange, "symbol": {"$in": symbols}},
                    {"_id": 0},
                    batch_size=10000,
                )
                local_contracts = pd.DataFrame([item for item in cursor])
                external_symbols = set(symbols) - set(
                    local_contracts["symbol"].tolist()
                )
                if external_symbols:
                    external_contracts = total_contracts.loc[
                        total_contracts["symbol"].isin(list(external_symbols))
                    ]
                    collections.insert_many(
                        util_to_json_from_pandas(external_contracts)
                    )
            else:
                collections.insert_many(util_to_json_from_pandas(total_contracts))

    def save_future_holdings(
        self,
        exchanges: Union[str, List[str], None] = None,
        start_date: Union[str, datetime.date, None] = None,
        end_date: Union[str, datetime.date, None] = None,
        offset: int = 365,
    ):
        """
        保存期货龙虎榜数据到本地
        """
        collections = self.client.future_holdings
        collections.create_index(
            [
                ("exchange", pymongo.ASCENDING),
                ("symbol", pymongo.ASCENDING),
                ("datestamp", pymongo.DESCENDING),
            ]
        )
        if exchanges is None:
            exchanges = self.future_exchanges
        if isinstance(exchanges, str):
            exchanges = exchanges.split(",")
        # 股票交易所不考虑
        exchanges = [x for x in exchanges if x not in self.stock_exchanges]
        # FIXME: 上海能源交易所在 tushare 的接口上获取相应持仓数据为空
        if "INE" in exchanges:
            exchanges.remove("INE")
        if end_date is None:
            end_date = datetime.date.today()
            if start_date is None:
                start_date = end_date - datetime.timedelta(days=offset)
        else:
            if start_date is None:
                start_date = pd.Timestamp(end_date) - pd.Timedelta(days=offset)
        for exchange in exchanges:
            if is_trade_date(end_date, exchange) and (pd.Timstamp(end_date) == pd.Timestamp(datetime.date.today())) and datetime.datetime.now().hour < 16:
                end_date = pd.Timestamp(end_date) - pd.Timedelta(days=1)
            trade_dates = self.queryer.fetch_trade_dates(
                exchanges=exchange, start_date=start_date, end_date=end_date
            )
            for trade_date in trade_dates.trade_date.tolist():
                print(
                    f"Now saving future holding of {exchange} at trade_date {trade_date}"
                )
                count = collections.count_documents(
                    {
                        "datestamp": util_make_date_stamp(trade_date),
                        "exchange": exchange,
                    }
                )
                if count == 0:
                    retry_offset = 5
                    while True:
                        try:
                            print(f"尝试保存交易所 {exchange} 在交易日 {trade_date} 的持仓排名")
                            results = self.ts_fetcher.fetch_get_holdings(
                                exchanges=exchange, cursor_date=trade_date
                            )
                            if not results.empty:
                                print(f"保存交易所 {exchange} 在交易日 {trade_date} 的持仓排名 成功")
                                break
                            if retry_offset >= 5:
                                break
                        except:
                            retry_offset += 1
                            time.sleep(60.0)
                    collections.insert_many(util_to_json_from_pandas(results))

    def save_stock_list(self):
        """
        本地化股票列表
        """
        collections = self.client.stock_list
        collections.create_index(
            [("symobl", pymongo.ASCENDING), ("list_datestamp", pymongo.ASCENDING)]
        )
        # 数据量比较小，每次更新可以覆盖
        data = self.ts_fetcher.fetch_get_stock_list()
        data.symbol = util_format_stock_symbols(data.symbol, "standard")
        columns = data.columns.tolist()
        if "ts_code" in columns:
            columns.remove("ts_code")
        data["list_datestamp"] = (
            data["list_date"].map(str).apply(lambda x: util_make_date_stamp(x))
        )
        collections.insert_many(util_to_json_from_pandas(data))

    def save_future_daily(
        self,
        exchanges: Union[str, List[str], None] = None,
        start_date: Union[str, datetime.date, None] = None,
        end_date: Union[str, datetime.date, None] = None,
        offset: int = 365,
    ):
        """
        保存期货日线行情
        """
        collections = self.client.future_daily
        collections.create_index(
            [("symbol", pymongo.ASCENDING), ("datestamp", pymongo.DESCENDING)]
        )
        cursor_date = datetime.date.today()
        for exchange in self.future_exchanges:
            contracts = self.queryer.fetch_future_contracts(exchanges=exchange)
            for _, contract_info in contracts.iterrows():
                list_date = contract_info["list_date"]
                delist_date = contract_info["delist_date"]
                symbol = contract_info["symbol"]
                count = collections.count_documents(
                    {"symbol": symbol, "datestamp": util_make_date_stamp(cursor_date)}
                )
                if count > 0:
                    first_doc = collections.find_one(
                        {"symbol": symbol}, sort=[("datestamp", pymongo.DESCENDING)]
                    )
                    latest_date = first_doc["trade_date"]
                    print(f"当前保存合约 {symbol} 从 {latest_date} 到 {delist_date} 日线行情")
                    if (pd.Timestamp(latest_date) < pd.Timestamp(delist_date)) and (self.queryer.fetch_next_trade_date(latest_date)['trade_date'] < datetime.date.today().strftime("%Y-%m-%d")):
                        data = self.ts_fetcher.fetch_get_future_daily(
                            symbols=symbol,
                            start_date=self.queryer.fetch_next_trade_date(latest_date)['trade_date'],
                            end_date=delist_date,
                        )
                        collections.insert_many(util_to_json_from_pandas(data[columns]))
                else:
                    print(f"当前保存合约 {symbol} 从 {list_date} 到 {delist_date} 日线行情")
                    data = self.ts_fetcher.fetch_get_future_daily(
                        symbols=symbol,
                        start_date=list_date,
                        end_date=delist_date,
                    )
                    if data is None or data.empty:
                        print(
                            f"当前合约 {symbol}, 上市时间 {list_date}, 下市时间 {delist_date}, 没有查询到数据"
                        )
                        continue
                    collections.insert_many(util_to_json_from_pandas(data))


if __name__ == "__main__":
    saver = MarketDataSaver()
    # saver.save_trade_dates()
    # saver.save_future_contracts()
    # saver.save_future_holdings(exchanges=["DCE"])
    # saver.save_future_holdings()
    # saver.save_stock_list()
    saver.save_future_daily()
