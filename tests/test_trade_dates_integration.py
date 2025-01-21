"""Integration tests for trade dates fetching functionality."""

import pytest
import pandas as pd
import datetime
from quantbox.fetchers.fetcher_tushare import TSFetcher


@pytest.fixture
def ts_fetcher():
    """Create a TSFetcher instance for testing."""
    return TSFetcher()


def assert_trade_dates_structure(df: pd.DataFrame):
    """Helper function to verify trade dates DataFrame structure."""
    assert isinstance(df, pd.DataFrame)
    required_columns = ["exchange", "trade_date", "pre_trade_date", "datestamp"]
    assert all(col in df.columns for col in required_columns)
    if not df.empty:
        # Verify date formats
        assert all(pd.to_datetime(df["trade_date"], format="%Y-%m-%d"))
        assert all(pd.to_datetime(df["pre_trade_date"], format="%Y-%m-%d"))
        # Verify datestamp is numeric
        assert df["datestamp"].dtype in ["int32", "int64"]


def test_fetch_all_exchanges(ts_fetcher):
    """Test fetching trading dates for all exchanges."""
    df = ts_fetcher.fetch_get_trade_dates()
    assert_trade_dates_structure(df)
    assert len(df) > 0
    assert set(df["exchange"].unique()).issubset(set(ts_fetcher.exchanges))


def test_fetch_single_exchange(ts_fetcher):
    """Test fetching trading dates for a single exchange."""
    df = ts_fetcher.fetch_get_trade_dates(exchanges="SHFE")
    assert_trade_dates_structure(df)
    assert len(df) > 0
    assert all(df["exchange"] == "SHFE")


def test_fetch_multiple_exchanges(ts_fetcher):
    """Test fetching trading dates for multiple exchanges."""
    exchanges = ["SHFE", "DCE"]
    df = ts_fetcher.fetch_get_trade_dates(exchanges=exchanges)
    assert_trade_dates_structure(df)
    assert len(df) > 0
    assert set(df["exchange"].unique()) == set(exchanges)


def test_fetch_with_date_range(ts_fetcher):
    """Test fetching trading dates within a specific date range."""
    start_date = "2024-01-01"
    end_date = "2024-12-31"
    df = ts_fetcher.fetch_get_trade_dates(
        exchanges="SHFE",
        start_date=start_date,
        end_date=end_date
    )
    assert_trade_dates_structure(df)
    assert len(df) > 0
    # Verify dates are within range
    df_dates = pd.to_datetime(df["trade_date"])
    assert all(df_dates >= pd.to_datetime(start_date))
    assert all(df_dates <= pd.to_datetime(end_date))


def test_fetch_with_datetime_dates(ts_fetcher):
    """Test fetching trading dates using datetime objects."""
    start_date = datetime.date(2024, 1, 1)
    end_date = datetime.date(2024, 12, 31)
    df = ts_fetcher.fetch_get_trade_dates(
        exchanges="SHFE",
        start_date=start_date,
        end_date=end_date
    )
    assert_trade_dates_structure(df)
    assert len(df) > 0


def test_fetch_with_integer_dates(ts_fetcher):
    """Test fetching trading dates using integer dates."""
    df = ts_fetcher.fetch_get_trade_dates(
        exchanges="SHFE",
        start_date=20240101,
        end_date=20241231
    )
    assert_trade_dates_structure(df)
    assert len(df) > 0


@pytest.mark.parametrize("exchange", ["INVALID", "TEST"])
def test_invalid_exchange(ts_fetcher, exchange):
    """Test handling of invalid exchange codes."""
    with pytest.raises(ValueError, match="Invalid exchanges"):
        ts_fetcher.fetch_get_trade_dates(exchanges=exchange)


@pytest.mark.parametrize("start,end", [
    ("2024-13-01", "2024-12-31"),  # Invalid month
    ("2024-01-32", "2024-12-31"),  # Invalid day
    ("invalid", "2024-12-31"),     # Invalid format
])
def test_invalid_dates(ts_fetcher, start, end):
    """Test handling of invalid date formats."""
    with pytest.raises(ValueError):
        ts_fetcher.fetch_get_trade_dates(
            exchanges="SHFE",
            start_date=start,
            end_date=end
        )


def test_end_date_before_start_date(ts_fetcher):
    """Test handling of end date before start date."""
    with pytest.raises(ValueError, match="Start date .* must be before end date"):
        ts_fetcher.fetch_get_trade_dates(
            exchanges="SHFE",
            start_date="2024-12-31",
            end_date="2024-01-01"
        )


def test_empty_result_handling(ts_fetcher):
    """Test handling of empty results."""
    # Use a date range in the far future where we expect no trading dates
    df = ts_fetcher.fetch_get_trade_dates(
        exchanges="SHFE",
        start_date="2050-01-01",
        end_date="2050-12-31"
    )
    assert_trade_dates_structure(df)
    assert len(df) == 0
