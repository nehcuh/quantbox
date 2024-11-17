import datetime
import re
from typing import List, Optional, Union
import math
import pandas as pd
from gm.api import *

from quantbox.fetchers.local_fetch import LocalFetcher
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
