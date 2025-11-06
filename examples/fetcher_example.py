"""
Example usage of the Market Data Service
市场数据服务使用示例
"""

from quantbox.services.market_data_service import MarketDataService
import pandas as pd
import time

def main():
    # Initialize market data service
    # By default, it uses local data first, then falls back to remote (Tushare)
    service = MarketDataService()

    # Example 1: Fetch trade dates
    print("\nFetching trade dates...")
    trade_dates = service.get_trade_calendar(
        exchanges=['SHFE'],
        start_date='2024-01-01',
        end_date='2024-01-31'
    )
    print(f"Got {len(trade_dates)} trade dates")

    # Example 2: Fetch future contracts
    print("\nFetching future contracts...")
    contracts = service.get_future_contracts(
        exchanges=['SHFE'],
        date='2024-01-15'
    )
    print(f"Got {len(contracts)} contracts")

    # Example 3: Fetch holdings data
    print("\nFetching holdings data...")
    holdings = service.get_future_holdings(
        exchanges=['SHFE'],
        start_date='2024-01-01',
        end_date='2024-01-15'
    )
    print(f"Got {len(holdings)} holdings records")

    # Example 4: Fetch future daily data
    print("\nFetching future daily data...")
    daily_data = service.get_future_daily(
        exchanges=['SHFE'],
        start_date='2024-01-01',
        end_date='2024-01-15'
    )
    print(f"Got {len(daily_data)} daily records")

    # Example 5: Fetch stock list
    print("\nFetching stock list...")
    stock_list = service.get_stock_list(
        exchanges=['SSE'],
        markets=['主板']
    )
    print(f"Got {len(stock_list)} stocks")

    print("\nExample completed successfully!")

if __name__ == '__main__':
    main()
