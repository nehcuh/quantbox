#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
保存交易日历数据到本地数据库

此脚本从 Tushare 获取交易日历数据，并将其保存到本地 MongoDB 数据库中。
支持以下功能：
1. 保存指定交易所的交易日历
2. 保存指定类型（股票/期货）的所有交易所的交易日历
3. 支持指定日期范围
4. 自动处理增量更新
"""

import argparse
from typing import Optional
from datetime import datetime

from quantbox.data.fetcher import TushareFetcher
from quantbox.core.config import ExchangeType


def save_trade_dates(
    exchange: Optional[str] = None,
    exchange_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """保存交易日历数据
    
    Args:
        exchange: 交易所代码，如SSE, SZSE等。如果不指定，则根据exchange_type保存对应类型的所有交易所
        exchange_type: 交易所类型，STOCK或FUTURES。当exchange未指定时使用
        start_date: 开始日期，格式为YYYYMMDD。如果不指定，则使用19890101
        end_date: 结束日期，格式为YYYYMMDD。如果不指定，则使用当年结束
    """
    try:
        # 创建TushareFetcher实例
        fetcher = TushareFetcher()
        
        # 处理exchange_type
        if exchange_type:
            exchange_type = ExchangeType[exchange_type.upper()]
        
        # 获取并保存交易日历
        if exchange:
            # 保存指定交易所的数据
            fetcher.fetch_calendar(
                exchange=exchange,
                start_date=start_date,
                end_date=end_date
            )
            print(f"成功保存交易所 {exchange} 的交易日历")
        else:
            # 根据exchange_type保存数据
            if exchange_type == ExchangeType.STOCK:
                exchanges = ["SSE", "SZSE"]
            elif exchange_type == ExchangeType.FUTURES:
                exchanges = ["SHFE", "DCE", "CZCE", "CFFEX", "INE", "GFEX"]
            else:
                # 默认保存所有股票交易所
                exchanges = ["SSE", "SZSE"]
            
            for ex in exchanges:
                fetcher.fetch_calendar(
                    exchange=ex,
                    start_date=start_date,
                    end_date=end_date
                )
                print(f"成功保存交易所 {ex} 的交易日历")
                
    except Exception as e:
        print(f"保存交易日历时发生错误: {str(e)}")
        raise


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="保存交易日历数据到本地数据库")
    parser.add_argument(
        "-e", "--exchange",
        help="交易所代码（如SSE, SZSE）。如果不指定，将根据exchange-type保存对应类型的所有交易所",
    )
    parser.add_argument(
        "-t", "--exchange-type",
        choices=["STOCK", "FUTURES"],
        help="交易所类型。当未指定exchange时使用",
    )
    parser.add_argument(
        "-s", "--start-date",
        help="开始日期，格式为YYYYMMDD。如果不指定，则使用19890101",
    )
    parser.add_argument(
        "-d", "--end-date",
        help="结束日期，格式为YYYYMMDD。如果不指定，则使用当年结束",
    )
    
    args = parser.parse_args()
    
    save_trade_dates(
        exchange=args.exchange,
        exchange_type=args.exchange_type,
        start_date=args.start_date,
        end_date=args.end_date,
    )


if __name__ == "__main__":
    main()
