import datetime
import re
from typing import List, Optional, Union
import math
import pandas as pd
from gm.api import *

from quantbox.fetchers.local_fetcher import LocalFetcher
from quantbox.util.basic import (
    DATABASE,
    DEFAULT_START,
    EXCHANGES,
    FUTURE_EXCHANGES,
    STOCK_EXCHANGES,
    QUANTCONFIG,
)
from quantbox.util.tools import (
    util_format_future_symbols,
    util_format_stock_symbols,
    util_make_date_stamp,
)


class GMFetcher:
    def __init__(self):
        """
        基于掘金量化接口封装
        """
        self.exchanges = EXCHANGES
        self.stock_exchanges = STOCK_EXCHANGES
        self.future_exchanges = FUTURE_EXCHANGES
        self.client = DATABASE
        self.default_start = DEFAULT_START
        self.local_queryer = LocalFetcher()
        
        # Initialize GM token
        token = QUANTCONFIG.gm_token
        if not token:
            raise ValueError("GM token not found in configuration")
        set_token(token)

    def fetch_get_holdings(
        self,
        exchanges: Union[List[str], str, None] = None,
        cursor_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        symbols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        fut_get_transaction_rankings(symbols, trade_date="", indicators="volume")

        explanation: 获取期货持仓数据

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
                    )
                    symbols = (symbols['exchange'] + "." + symbols['symbol']).tolist()
                else:
                    if isinstance(symbols, str):
                        symbols = symbols.split(",")
                n_slice = math.ceil(len(symbols) / 100)
                symbols_list = [symbols[i:i + 100] for i in range(0, len(symbols), 100)]
                holdings_data = pd.DataFrame()
                for symbol_chunk in symbols_list:
                    chunk_holdings = fut_get_transaction_rankings(
                        symbols=symbol_chunk,
                        trade_date=latest_trade_date,
                        indicators="volume,long,short"
                    )
                    if not chunk_holdings.empty:
                        transformed_data = []
                        # Group by symbol and trade_date to combine volume, long, and short data
                        for (symbol, date), group in chunk_holdings.groupby(['symbol', 'trade_date']):
                            # Extract symbol without exchange prefix
                            pure_symbol = symbol.split('.')[-1].upper()
                            exchange = symbol.split('.')[0]
                            
                            # Process each broker's data
                            for broker in group['member_name'].unique():
                                broker_data = {
                                    'trade_date': date,
                                    'symbol': pure_symbol,
                                    'broker': broker.replace('（代客）', ''),
                                    'vol': None,
                                    'vol_chg': None,
                                    'long_hld': None,
                                    'long_chg': None,
                                    'short_hld': None,
                                    'short_chg': None,
                                    'datestamp': pd.Timestamp(date).timestamp() * 1000000,
                                    'exchange': exchange
                                }
                                
                                # Fill in volume data
                                vol_row = group[(group['member_name'] == broker) & (group['indicator'] == 'volume')]
                                if not vol_row.empty:
                                    broker_data['vol'] = vol_row['indicator_number'].iloc[0]
                                    broker_data['vol_chg'] = vol_row['indicator_change'].iloc[0]
                                
                                # Fill in long position data
                                long_row = group[(group['member_name'] == broker) & (group['indicator'] == 'long')]
                                if not long_row.empty:
                                    broker_data['long_hld'] = long_row['indicator_number'].iloc[0]
                                    broker_data['long_chg'] = long_row['indicator_change'].iloc[0]
                                
                                # Fill in short position data
                                short_row = group[(group['member_name'] == broker) & (group['indicator'] == 'short')]
                                if not short_row.empty:
                                    broker_data['short_hld'] = short_row['indicator_number'].iloc[0]
                                    broker_data['short_chg'] = short_row['indicator_change'].iloc[0]
                                
                                transformed_data.append(broker_data)
                        
                        holdings_data = pd.concat([holdings_data, pd.DataFrame(transformed_data)], axis=0)
                total_holdings = pd.concat([total_holdings, holdings_data])
        return total_holdings

    def fetch_get_trade_dates(
        self,
        exchanges: Union[List[str], str, None] = None,
        start_date: Union[str, datetime.date, int, None] = None,
        end_date: Union[str, datetime.date, int, None] = None,
    ) -> pd.DataFrame:
        """
        获取指定交易所的日期范围内的交易日

        Args:
            exchanges: 交易所, 默认为所有交易所
                支持: ['SHSE', 'SZSE', 'SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
            start_date: 起始时间, 默认从 DEFAULT_START 开始
                支持格式: [19910906, '1992-03-02', datetime.date(2024, 9, 16)]
            end_date: 截止时间, 默认截止为当前日期
                支持格式: [19910906, '1992-03-02', datetime.date(2024, 9, 16)]

        Returns:
            DataFrame with columns: ['exchange', 'trade_date', 'pretrade_date', 'datestamp']
        """
        if exchanges is None:
            exchanges = self.exchanges
        if isinstance(exchanges, str):
            exchanges = exchanges.split(",")
        if start_date is None:
            start_date = self.default_start
        if end_date is None:
            end_date = datetime.date(datetime.date.today().year, 12, 31)

        # 转换日期格式
        start_date = pd.Timestamp(str(start_date))
        end_date = pd.Timestamp(str(end_date))

        results = pd.DataFrame()
        for exchange in exchanges:
            # 掘金量化的交易所代码与 Tushare 略有不同，需要转换
            gm_exchange = exchange
            if exchange == "SSE":
                gm_exchange = "SHSE"

            # 按年度获取交易日历
            start_year = start_date.year
            end_year = end_date.year
            exchange_dates = pd.DataFrame()

            for year in range(start_year, end_year + 1):
                dates = get_trading_dates(exchange=gm_exchange, start_date=f"{year}-01-01", end_date=f"{year}-12-31")
                df = pd.DataFrame({
                    'trade_date': dates,
                    'exchange': gm_exchange
                })
                exchange_dates = pd.concat([exchange_dates, df], axis=0)

            # 过滤日期范围
            exchange_dates['trade_date'] = pd.to_datetime(exchange_dates['trade_date'])
            mask = (exchange_dates['trade_date'] >= start_date) & (exchange_dates['trade_date'] <= end_date)
            exchange_dates = exchange_dates.loc[mask]

            # 计算前一交易日
            exchange_dates = exchange_dates.sort_values('trade_date')
            exchange_dates['pretrade_date'] = exchange_dates['trade_date'].shift(1)
            
            # 添加日期戳
            exchange_dates["datestamp"] = (
                exchange_dates['trade_date'].apply(lambda x: util_make_date_stamp(x))
            )
            
            # 格式化日期
            exchange_dates['trade_date'] = exchange_dates['trade_date'].dt.strftime('%Y-%m-%d')
            exchange_dates['pretrade_date'] = exchange_dates['pretrade_date'].dt.strftime('%Y-%m-%d')

            results = pd.concat([results, exchange_dates], axis=0)

        return results[["exchange", "trade_date", "pretrade_date", "datestamp"]]
