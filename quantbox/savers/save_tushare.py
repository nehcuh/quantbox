from typing import Union, List
import datetime
import pymongo
import pandas as pd
from quantbox.util.basic import DATABASE, EXCHANGES
from quantbox.fetchers.remote_fetch_tushare import TSFetcher
from quantbox.fetchers.remote_fetch_gm import GMFetcher
from quantbox.fetchers.local_fetch import Queryer
from quantbox.util.tools import util_make_date_stamp, util_to_json_from_pandas, util_format_stock_symbols

class TSSaver:
    def __init__(self):
        self.ts_fetcher = TSFetcher()
        self.gm_fetcher = GMFetcher()
        self.queryer = Queryer()
        self.client = DATABASE
        self.exchanges = EXCHANGES
        self.future_exchanges = EXCHANGES
        self.stock_exchanges = EXCHANGES

    def save_trade_dates(self):
        """
         本地化交易日期
        """
        collections = self.client.trade_date
        collections.create_index(
            [
                ("exchange", pymongo.ASCENDING),
                ("datestamp", pymongo.DESCENDING)]
        )
        for exchange in self.exchanges:
            count = collections.count_documents({"exchange": exchange})
            if count > 0:
                # 获取第一个文档
                first_doc = collections.find_one(
                    {"exchange": exchange},
                    sort=[("datestamp", pymongo.DESCENDING)]
                )
                latest_date = first_doc["trade_date"]
            else:
                latest_date = "1990-12-19"

            data = util_to_json_from_pandas(
                self.ts_fetcher.fetch_get_trade_dates(
                    exchanges=exchange,
                    start_date=latest_date
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
        for exchange in self.exchanges:
            if exchange in ["SSE", "SZSE"]:
                # 只考虑期货交易所
                continue
            total_contracts = self.ts_fetcher.fetch_get_future_contracts(exchange=exchange)
            symbols = total_contracts.symbol.tolist()
            count = collections.count_documents(
                {
                    "exchange": exchange,
                    "symbol": {"$in": symbols}
                })
            if count > 0:
                # 查询当前已有的合约信息
                cursor = collections.find(
                    {
                        "exchange": exchange,
                        "symbol": {
                            "$in": symbols
                        }
                    },
                    {"_id": 0},
                    batch_size=10000
                )
                local_contracts = pd.DataFrame([item for item in cursor])
                external_symbols = set(symbols) - set(local_contracts["symbol"].tolist())
                if external_symbols:
                    external_contracts = total_contracts.loc[total_contracts["symbol"].isin(list(external_symbols))]
                    collections.insert_many(util_to_json_from_pandas(
                        external_contracts
                    ))
            else:
                collections.insert_many(util_to_json_from_pandas(total_contracts))

    def save_future_holdings(
        self,
        exchanges: Union[str, List[str], None] = None,
        start_date: Union[str, datetime.date, None] = None,
        end_date: Union[str,datetime.date, None] = None,
        offset: int=365
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
        if "SSE" in exchanges:
            exchanges.remove("SSE")
        if "SZSE" in exchanges:
            exchanges.remove("SZSE")
        # FIXME: 上海能源交易所在 tushare 的接口上获取相应持仓数据为空
        if "INE" in exchanges:
            exchanges.remove("INE")
        if end_date is None:
            end_date = datetime.date.today()
            if start_date is None:
                start_date = end_date - datetime.timedelta(days=offset)
        else:
            if start_date is None:
                start_date = end_date
        for exchange in exchanges:
            trade_dates = self.queryer.fetch_trade_dates(exchanges=exchange, start_date=start_date, end_date=end_date)
            for trade_date in trade_dates.trade_date.tolist():
                print(f"Now saving future holding of {exchange} at trade_date {trade_date}")
                count = collections.count_documents({
                    "datestamp": util_make_date_stamp(trade_date),
                    "exchange": exchange
                })
                if count == 0:
                    results = self.ts_fetcher.fetch_get_holdings(
                        exchanges=exchange,
                        cursor_date=trade_date
                    )
                    collections.insert_many(util_to_json_from_pandas(results))


    def save_stock_list(self):
        """
         本地化股票列表
        """
        collections = self.client.stock_list
        collections.create_index(
            [
                ("symobl", pymongo.ASCENDING),
                ("list_datestamp", pymongo.ASCENDING)]
        )
        # 数据量比较小，每次更新可以覆盖
        data = self.ts_fetcher.fetch_get_stock_list()
        data.symbol = util_format_stock_symbols(data.symbol, "standard")
        columns = data.columns.tolist()
        if "ts_code" in columns:
            columns.remove("ts_code")
        data["list_datestamp"] = data['list_date'].map(str).apply(lambda x: util_make_date_stamp(x))
        collections.insert_many(util_to_json_from_pandas(data))

if __name__ == "__main__":
    saver = TSSaver()
    # saver.save_trade_dates()
    # saver.save_future_contracts()
    # saver.save_future_holdings(exchanges=["DCE"])
    # saver.save_future_holdings()
    saver.save_stock_list()
