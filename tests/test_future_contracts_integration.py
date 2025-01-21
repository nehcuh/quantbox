"""Integration tests for future contracts fetching functionality."""

import pytest
import pandas as pd
from quantbox.fetchers.fetcher_tushare import TSFetcher


@pytest.fixture
def ts_fetcher():
    """Create a TSFetcher instance for testing."""
    return TSFetcher()


def assert_dataframe_structure(df: pd.DataFrame):
    """Helper function to verify DataFrame structure."""
    assert isinstance(df, pd.DataFrame)
    assert 'qbcode' in df.columns
    assert 'chinese_name' in df.columns
    assert 'symbol' in df.columns
    assert 'list_date' in df.columns
    assert 'delist_date' in df.columns


def test_fetch_dce_all_contracts(ts_fetcher):
    """Test fetching all contracts from DCE."""
    df = ts_fetcher.fetch_get_future_contracts(exchange="DCE")
    assert_dataframe_structure(df)
    assert len(df) > 0
    assert all(df['exchange'] == 'DCE')


def test_fetch_dce_soybean_meal(ts_fetcher):
    """Test fetching soybean meal contracts from DCE."""
    df = ts_fetcher.fetch_get_future_contracts(exchange="DCE", spec_name="豆粕")
    assert_dataframe_structure(df)
    assert len(df) > 0
    assert all(df['chinese_name'] == '豆粕')
    assert all(df['exchange'] == 'DCE')


def test_fetch_dce_with_date_filter(ts_fetcher):
    """Test fetching contracts with date filter."""
    current_date = "2024-01-21"
    df = ts_fetcher.fetch_get_future_contracts(
        exchange="DCE",
        spec_name="豆粕",
        cursor_date=current_date
    )
    assert_dataframe_structure(df)
    assert len(df) > 0
    assert all(df['chinese_name'] == '豆粕')
    assert all(pd.to_datetime(df['list_date']) <= pd.to_datetime(current_date))
    assert all(pd.to_datetime(df['delist_date']) > pd.to_datetime(current_date))


def test_fetch_with_custom_fields(ts_fetcher):
    """Test fetching contracts with custom fields."""
    fields = ["symbol", "name"]
    df = ts_fetcher.fetch_get_future_contracts(
        exchange="DCE",
        spec_name="豆粕",
        fields=fields
    )
    assert_dataframe_structure(df)
    assert len(df) > 0
    required_fields = ['qbcode', 'symbol', 'name', 'list_date', 'delist_date']
    assert all(field in df.columns for field in required_fields)


def test_fetch_shfe_all_contracts(ts_fetcher):
    """Test fetching all contracts from SHFE."""
    df = ts_fetcher.fetch_get_future_contracts(
        exchange="SHFE",
        cursor_date="2024-01-21"
    )
    assert_dataframe_structure(df)
    assert len(df) > 0
    assert all(df['exchange'] == 'SHFE')
    # Verify symbol case for SHFE
    assert all(df['symbol'].str.islower())


def test_fetch_shfe_copper_contracts(ts_fetcher):
    """Test fetching copper contracts from SHFE."""
    df = ts_fetcher.fetch_get_future_contracts(
        exchange="SHFE",
        spec_name="沪铜",
        cursor_date="2024-01-21"
    )
    assert_dataframe_structure(df)
    assert len(df) > 0
    assert all(df['chinese_name'] == '沪铜')
    assert all(df['exchange'] == 'SHFE')
    assert all(df['symbol'].str.startswith('cu'))
    assert all(df['symbol'].str.islower())
