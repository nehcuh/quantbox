"""
测试不同数据源的交易日期数据一致性

此脚本用于测试 Tushare 和掘金量化两个数据源获取的交易日期数据是否一致。
主要比较：
1. 日期范围是否一致
2. 每个交易所的交易日是否一致
"""

import pandas as pd
from datetime import datetime, timedelta

from quantbox.fetchers.fetcher_tushare import TSFetcher
from quantbox.fetchers.fetcher_goldminer import GMFetcher
from quantbox.util.basic import EXCHANGES


def get_trade_dates(fetcher, exchange, start_date, end_date=None):
    """获取指定数据源的交易日期数据"""
    df = fetcher.fetch_get_trade_dates(
        exchanges=exchange,
        start_date=start_date,
        end_date=end_date
    )
    if df is not None and not df.empty:
        return set(df['trade_date'].tolist())
    return set()


def compare_trade_dates(exchange, start_date, end_date=None):
    """比较两个数据源的交易日期数据"""
    ts_fetcher = TSFetcher()
    gm_fetcher = GMFetcher()
    
    # 获取两个数据源的数据
    ts_dates = get_trade_dates(ts_fetcher, exchange, start_date, end_date)
    gm_dates = get_trade_dates(gm_fetcher, exchange, start_date, end_date)
    
    # 计算差异
    only_in_ts = ts_dates - gm_dates
    only_in_gm = gm_dates - ts_dates
    common_dates = ts_dates & gm_dates
    
    return {
        'exchange': exchange,
        'period': f"{start_date} to {end_date or 'now'}",
        'ts_count': len(ts_dates),
        'gm_count': len(gm_dates),
        'common_count': len(common_dates),
        'only_in_ts': sorted(list(only_in_ts)) if only_in_ts else [],
        'only_in_gm': sorted(list(only_in_gm)) if only_in_gm else [],
        'match_rate': len(common_dates) / max(len(ts_dates), len(gm_dates)) * 100 if ts_dates or gm_dates else 100
    }


def main():
    # 测试不同时间范围
    test_periods = [
        # 最近一个月
        (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        # 最近一年
        (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
        # 固定的历史时期（例如2020年）
        '2020-01-01'
    ]
    
    for start_date in test_periods:
        print(f"\n测试期间: {start_date} 至今")
        print("-" * 50)
        
        for exchange in EXCHANGES:
            result = compare_trade_dates(exchange, start_date)
            
            print(f"\n交易所: {result['exchange']}")
            print(f"时间范围: {result['period']}")
            print(f"Tushare数据量: {result['ts_count']}")
            print(f"掘金数据量: {result['gm_count']}")
            print(f"共同数据量: {result['common_count']}")
            print(f"匹配率: {result['match_rate']:.2f}%")
            
            if result['only_in_ts']:
                print(f"仅在Tushare中存在的日期: {result['only_in_ts']}")
            if result['only_in_gm']:
                print(f"仅在掘金中存在的日期: {result['only_in_gm']}")
            
            print("-" * 30)


if __name__ == "__main__":
    main()
