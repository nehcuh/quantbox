import datetime
import re
from typing import List, Optional, Union

import pandas as pd

from quantbox.fetchers.local_fetch import Queryer
from quantbox.util.basic import (
    DATABASE,
    DEFAULT_START,
    EXCHANGES,
    FUTURE_EXCHANGES,
    STOCK_EXCHANGES,
    TSPRO,
)
from quantbox.util.tools import (
    util_format_future_symbols,
    util_format_stock_symbols,
    util_make_date_stamp,
)


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
        end_date: Union[str, datetime.date, int, None] = None,
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
                exchange=exchange, start_date=start_date, end_date=end_date
            )
            # PS: tushare 保留 is_open 这个字段有道理，交易日计划与实际可能会有偏差
            # TODO: 未来考虑优化
            data = data.loc[data["is_open"] == 1]
            data["datestamp"] = (
                data["cal_date"].map(str).apply(lambda x: util_make_date_stamp(x))
            )
            results = pd.concat([results, data], axis=0)
        results = results.rename(columns={"cal_date": "trade_date"})
        results.trade_date = pd.to_datetime(results.trade_date).dt.strftime("%Y-%m-%d")
        results.pretrade_date = pd.to_datetime(results.pretrade_date).dt.strftime(
            "%Y-%m-%d"
        )
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

    def fetch_get_stock_list(
        self,
        symbols: Union[str, List[str], None] = None,
        names: Union[str, List[str], None] = None,
        exchanges: Union[str, List[str], None] = None,
        markets: Union[str, List[str], None] = None,
        list_status: Union[str, List[str], None] = "L",
        is_hs: Union[str, None] = None,
        fields: Union[str, None] = None,
    ) -> pd.DataFrame:
        """
        explanation:
         对 tushare 股票列表获取接口的封装

        params:
            * symbols ->
                含义：股票代码, 默认为 None, 不做筛选
                类型：Union[str, List[str], None]
                参数支持: "SZSE.000001", "SHSE.600000"
            * names ->
                含义：股票名称，默认为 None，不做筛选
                类型: Union[str, List[str], None]
                参数支持: "平安银行", "浦发银行"
            * markets ->
                含义：市场类别，默认为 None, 不做筛选
                类型: Union[str, List[str], None]
                参数支持：主板, 创业板, 科创板, CDR, 北交所
            * list_status ->
                含义: 上市状态，默认为 None, 不做筛选
                类型：Union[str, List[str], None]
                参数支持： L上市 D退市 P暂停上市，默认是L
            * exchanges ->
                含义：交易所，默认为 None, 不做筛选
                类型：Union[str, List[str], None]
                参数支持：SSE上交所 SZSE深交所 BSE北交所
            * is_hs ->
                含义：是否沪港通标的
                类型：Union[str, None] = None,
                参数支持：N否 H沪股通 S深股通
            * fields ->
                含义：指定输出的字段
                类型：Union[str, List[str], None] = None
                参数支持：'ts_code,symbol,name,area,industry,list_date'

        returns:
            pd.DataFrame ->
                符合条件的股票列表
        """
        if fields:
            if isinstance(fields, list):
                fields = ",".join(fields)
        # 指定 symbols 则直接根据 symbols 查询，不考虑其他条件
        if symbols:
            symbols = util_format_stock_symbols(symbols, "ts")
            if fields:
                self.pro.stock_basic(symbols=",".join(symbols))[fields]
            else:
                self.pro.stock_basic(symbols=",".join(symbols))

        # 指定 names 则直接根据 names 查询，不考虑其他条件
        if names:
            if isinstance(names, str):
                names = names.split(",")
            results = pd.DataFrame()
            for name in names:
                df = self.pro.stock_basic(name=name)
                results = pd.concat([results, df], axis=0)
            if fields:
                return results[fields]
            else:
                return results

        # 指定 markets 则直接根据 markets 查询，不考虑 exchanges
        if markets:
            if isinstance(markets, str):
                markets = markets.split(",")
            results = pd.DataFrame()
            for market in markets:
                if list_status:
                    if is_hs:
                        df = self.pro.stock_basic(
                            market=market, list_status=list_status, is_hs=is_hs
                        )
                    else:
                        df = self.pro.stock_basic(
                            market=market, list_status=list_status
                        )
                        results = pd.concat([results, df], axis=0)
                else:
                    if is_hs:
                        df_1 = self.pro.stock_basic(
                            market=market, list_status="L", is_hs=is_hs
                        )
                        df_2 = self.pro.stock_basic(
                            market=market, list_status="D", is_hs=is_hs
                        )
                        df_3 = self.pro.stock_basic(
                            market=market, list_status="P", is_hs=is_hs
                        )
                        results = pd.concat([results, df_1, df_2, df_3], axis=0)
                    else:
                        df_1 = self.pro.stock_basic(market=market, list_status="L")
                        df_2 = self.pro.stock_basic(market=market, list_status="D")
                        df_3 = self.pro.stock_basic(market=market, list_status="P")
                        results = pd.concat([results, df_1, df_2, df_3], axis=0)
            if fields:
                return results[fields]
            else:
                return results

        if exchanges:
            if isinstance(exchanges, str):
                exchanges = exchanges.split(",")
            results = pd.DataFrame()
            for exchange in exchanges:
                if list_status:
                    if is_hs:
                        df = self.pro.stock_basic(
                            exchange=exchange, list_status=list_status, is_hs=is_hs
                        )
                    else:
                        df = self.pro.stock_basic(
                            exchange=exchange, list_status=list_status
                        )
                        results = pd.concat([results, df], axis=0)
                else:
                    if is_hs:
                        df_1 = self.pro.stock_basic(
                            exchange=exchange, list_status="L", is_hs=is_hs
                        )
                        df_2 = self.pro.stock_basic(
                            exchange=exchange, list_status="D", is_hs=is_hs
                        )
                        df_3 = self.pro.stock_basic(
                            exchange=exchange, list_status="P", is_hs=is_hs
                        )
                        results = pd.concat([results, df_1, df_2, df_3], axis=0)
                    else:
                        df_1 = self.pro.stock_basic(exchange=exchange, list_status="L")
                        df_2 = self.pro.stock_basic(exchange=exchange, list_status="D")
                        df_3 = self.pro.stock_basic(exchange=exchange, list_status="P")
                        results = pd.concat([results, df_1, df_2, df_3], axis=0)
            if fields:
                return results[fields]
            else:
                return results

        # 如果交易所，市场都不指定，则认为获取全部
        if list_status:
            results = self.pro.stock_basic(list_status=list_status)
        else:
            df_1 = self.pro.stock_basic(list_status="L")
            df_2 = self.pro.stock_basic(list_status="D")
            df_3 = self.pro.stock_basic(list_status="P")
            results = pd.concat([df_1, df_2, df_3], axis=0)
        if fields:
            return results[fields]
        else:
            return results

    def fetch_get_holdings(
        self,
        exchanges: Union[str, List[str], None] = None,
        cursor_date: Union[int, str, datetime.date, None] = None,
        start_date: Union[int, str, datetime.date, None] = None,
        end_date: Union[int, str, datetime.date, None] = None,
        symbols: Union[str, List[str], None] = None,
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
                    exchange=exchange, cursor_date=cursor_date, include=True
                )["trade_date"]
                if symbols is None:
                    symbols = self.local_queryer.fetch_future_contracts(
                        exchanges=exchange, cursor_date=cursor_date
                    ).symbol.tolist()
                else:
                    if isinstance(symbols, str):
                        symbols = symbols.split(",")
                for symbol in symbols:
                    holdings = self.pro.fut_holding(
                        trade_date=latest_trade_date.replace("-", ""),
                        symbol=symbol,
                        exchange=exchange,
                    )
                    if not holdings.empty:
                        if total_holdings.empty:
                            total_holdings = holdings
                        else:
                            total_holdings = pd.concat(
                                [total_holdings, holdings], axis=0
                            )
            else:
                if end_date is None:
                    end_date = datetime.date.today()
                start_date = pd.Timestamp(str(start_date)).strftime("%Y%m%d")
                end_date = pd.Timestamp(str(end_date)).strftime("%Y%m%d")
                if symbols is None:
                    # 对于这种场景，可以先去根据交易日获取所有的合约列表，然后去查询
                    trade_dates = self.local_queryer.fetch_trade_dates(
                        exchanges=exchange, start_date=start_date, end_date=end_date
                    ).trade_date.tolist()
                    symbols = []
                    for trade_date in trade_dates:
                        symbols = (
                            symbols
                            + self.local_queryer.fetch_future_contracts(
                                exchanges=exchange, cursor_date=trade_date
                            ).symbol.tolist()
                        )
                    symbols = list(set(symbols))
                else:
                    if isinstance(symbols, str):
                        symbols = symbols.split(",")
                for symbol in symbols:
                    holdings = self.pro.fut_holding(
                        symbol=symbol,
                        exchange=exchange,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    if not holdings.empty:
                        if total_holdings.empty:
                            total_holdings = holdings
                        else:
                            total_holdings = pd.concat(
                                [total_holdings, holdings], axis=0
                            )
            if total_holdings.empty:
                print(f"当前期货交易所 {exchange} 没有持仓数据")
                continue
            total_holdings["datestamp"] = total_holdings["trade_date"].apply(
                lambda x: util_make_date_stamp(x)
            )
            total_holdings["trade_date"] = pd.to_datetime(
                total_holdings["trade_date"]
            ).dt.strftime("%Y-%m-%d")
            total_holdings["exchange"] = exchange
        return total_holdings

    def fetch_get_future_daily(
        self,
        cursor_date: Union[str, datetime.date, int] = None,
        symbols: Union[str, List[str], None] = None,
        exchanges: Union[str, List[str], None] = None,
        start_date: Union[str, datetime.date, int, None] = None,
        end_date: Union[str, datetime.date, int, None] = None,
        fields: Union[List[str], None] = None,
    ) -> pd.DataFrame:
        """
        explanation:
            获取指定交易所指定品种持仓情况, 注意，tushare 的 SHFE 对应查询 symbol 后缀为 SHF, CZCE 查询后缀为 ZCE

        params:
            * cursor_date ->
                含义：指定日期最近交易日（当前日期包括在内）, 默认为 None，如果 start_date 不指定时，将默认 cursor_date 为当前日期
                类型：Union[str, datetime.date, int, None]
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
                类型：Union[str, int, datetime.date]
                参数支持：20200913, "20210305", ...
            * end_date ->
                含义： 结束时间，默认为 None, 当指定了 start_date 以后，end_date 如果为 None，则默认为当前日期
                类型：Union[str, int, datetime.date]
                参数支持：20200913, "20210305", ...
            returns:
                pd.DataFrame ->
                    期货日线行情
        """
        results = pd.DataFrame()
        if start_date:
            if end_date is None:
                end_date = datetime.date.today()
            if symbols:
                symbols = util_format_future_symbols(symbols=symbols, format="tushare", tushare_daily_spec=True)
                symbols = ",".join(symbols)
                if fields:
                    results = self.pro.fut_daily(
                        ts_code=symbols,
                        start_date=pd.Timestamp(str(start_date)).strftime("%Y%m%d"),
                        end_date=pd.Timestamp(str(end_date)).strftime("%Y%m%d"),
                        fields=fields,
                    )
                else:
                    results = self.pro.fut_daily(
                        ts_code=symbols,
                        start_date=pd.Timestamp(str(start_date)).strftime("%Y%m%d"),
                        end_date=pd.Timestamp(str(end_date)).strftime("%Y%m%d"),
                    )
            else:
                if exchanges is None:
                    exchanges = self.future_exchanges
                elif isinstance(exchanges, str):
                    exchanges = exchanges.split(",")
                results = pd.DataFrame()
                for exchange in exchanges:
                    if fields:
                        df_local = self.pro.fut_daily(
                            exchange=exchange,
                            start_date=pd.Timestamp(str(start_date)).strftime("%Y%m%d"),
                            end_date=pd.Timestamp(str(end_date)).strftime("%Y%m%d"),
                            fields=fields,
                        )
                    else:
                        df_local = self.pro.fut_daily(
                            start_date=pd.Timestamp(str(start_date)).strftime("%Y%m%d"),
                            end_date=pd.Timestamp(str(end_date)).strftime("%Y%m%d"),
                            exchange=exchange,
                        )
                    results = pd.concat([results, df_local], axis=0)
        else:
            if cursor_date is None:
                cursor_date = datetime.date.today()
            latest_trade_date = self.local_queryer.fetch_pre_trade_date(
                cursor_date=cursor_date, include=True
            )["trade_date"]
            if symbols:
                symbols = util_format_future_symbols(symbols=symbols, format="tushare", tushare_daily_spec=True)
                symbols = ",".join(symbols)
                if fields:
                    results = self.pro.fut_daily(
                        ts_code=symbols,
                        trade_date=latest_trade_date.replace("-", ""),
                        fields=fields,
                    )
                else:
                    results = self.pro.fut_daily(
                        ts_code=symbols,
                        trade_date=latest_trade_date.replace("-", ""),
                    )
            else:
                if exchanges is None:
                    exchanges = self.future_exchanges
                elif isinstance(exchanges, str):
                    exchanges = exchanges.split(",")
                results = pd.DataFrame()
                for exchange in exchanges:
                    if fields:
                        df_local = self.pro.fut_daily(
                            trade_date=latest_trade_date.replace("-", ""),
                            exchange=exchange,
                            fields=fields,
                        )
                    else:
                        df_local = self.pro.fut_daily(
                            trade_date=latest_trade_date.replace("-", ""),
                            exchange=exchange,
                        )
                    results = pd.concat([results, df_local], axis=0)
        if "trade_date" in results.columns:
            results["datestamp"] = results.trade_date.map(str).apply(
                lambda x: util_make_date_stamp(x)
            )
            results.trade_date = pd.to_datetime(results["trade_date"]).dt.strftime(
                "%Y-%m-%d"
            )
        if "ts_code" in results.columns:
            columns = results.columns.tolist()
            results["symbol"] = (
                results.ts_code.map(str).str.split(".").apply(lambda x: x[0])
            )
            results["exchange"] = (
                results.ts_code.map(str).str.split(".").apply(lambda x: x[1])
            )
            replace_dict = {
                r'\SHF$': 'SHFE',
                r'\ZCE$': 'CZCE'
            }
            results.exchange = results.exchange.replace(replace_dict, regex=True)
            columns = ["symbol", "exchange"] + columns
            results = results[columns]
        return results


# 添加全局函数
def fetch_get_trade_dates(exchanges=None, start_date=None, end_date=None):
    fetcher = TSFetcher()
    return fetcher.fetch_get_trade_dates(exchanges, start_date, end_date)


def fetch_get_future_contracts(
    exchange="DCE", spec_name=None, cursor_date=None, fields=None
):
    fetcher = TSFetcher()
    return fetcher.fetch_get_future_contracts(exchange, spec_name, cursor_date, fields)


def fetch_get_holdings(
    exchanges=None, cursor_date=None, start_date=None, end_date=None, symbols=None
):
    fetcher = TSFetcher()
    return fetcher.fetch_get_holdings(
        exchanges, cursor_date, start_date, end_date, symbols
    )


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

    # print(fetcher.fetch_get_future_contracts(
    #     exchange="DCE",
    #     spec_name="豆粕",
    # ))

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

    print(fetcher.fetch_get_stock_list(symbols="000001, 600000"))
    print(fetcher.fetch_get_stock_list(names=["招商证券", "贵州茅台"]))
    print(fetcher.fetch_get_stock_list(names=["招商证券", "贵州茅台"]))
    print(fetcher.fetch_get_stock_list(markets=["科创板", " 创业板"]))
    print(fetcher.fetch_get_stock_list())
