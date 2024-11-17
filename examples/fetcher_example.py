"""
Example usage of the Remote Data Fetcher
远程数据获取器使用示例
"""

from quantbox.fetchers import RemoteFetcher
import pandas as pd
import time

def main():
    # Initialize fetcher with custom configuration
    fetcher = RemoteFetcher(
        engine='ts',  # Use TuShare as data source
        config_file='examples/config.json'  # Load configuration from file
    )

    # Example 1: Fetch trade dates
    print("\nFetching trade dates...")
    trade_dates = fetcher.fetch_get_trade_dates(
        exchanges=['SHFE'],
        start_date='2024-01-01',
        end_date='2024-01-31'
    )
    print(f"Got {len(trade_dates)} trade dates")

    # Example 2: Fetch future contracts
    print("\nFetching future contracts...")
    contracts = fetcher.fetch_get_future_contracts(
        exchanges=['SHFE'],
        cursor_date='2024-01-15'
    )
    print(f"Got {len(contracts)} contracts")

    # Example 3: Fetch holdings data
    print("\nFetching holdings data...")
    holdings = fetcher.fetch_get_holdings(
        exchanges=['SHFE'],
        start_date='2024-01-01',
        end_date='2024-01-15'
    )
    print(f"Got {len(holdings)} holdings records")

    # Example 4: Fetch future daily data
    print("\nFetching future daily data...")
    daily_data = fetcher.fetch_get_future_daily(
        exchanges=['SHFE'],
        start_date='2024-01-01',
        end_date='2024-01-15'
    )
    print(f"Got {len(daily_data)} daily records")

    # Log performance statistics
    print("\nPerformance Statistics:")
    fetcher.log_performance_stats()

    # Get performance statistics as dictionary
    stats = fetcher.get_performance_stats()
    print("\nDetailed Statistics:")
    print(f"Total Requests: {stats['total_requests']}")
    print(f"Success Rate: {stats['success_rate']:.2%}")
    print(f"Cache Hit Rate: {stats['cache_hit_rate']:.2%}")
    print(f"Average Response Time: {stats['avg_response_time']:.3f}s")
    print(f"Slow Queries: {stats['slow_queries']}")

if __name__ == '__main__':
    main()
