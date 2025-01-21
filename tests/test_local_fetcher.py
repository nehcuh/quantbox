import pytest
from datetime import datetime, timedelta
import pandas as pd
from quantbox.fetchers.local_fetcher import LocalFetcher


@pytest.fixture
def fetcher():
    """创建测试用的本地数据获取器"""
    class MockCursor:
        def __init__(self, items):
            self.items = items

        def sort(self, *args, **kwargs):
            return self

        def __iter__(self):
            return iter(self.items)

    class MockCollection:
        def __init__(self):
            self.find_results = []
            self.count_results = {}

        def find(self, *args, **kwargs):
            result = self.find_results.pop(0) if self.find_results else []
            if isinstance(result, Exception):
                raise result
            return MockCursor(result)

        def count_documents(self, *args, **kwargs):
            return self.count_results.get(args[0].get("exchange"), 0)

    class MockClient:
        def __init__(self):
            self.trade_date = MockCollection()
            self.future_contracts = MockCollection()

    fetcher = LocalFetcher()
    fetcher.client = MockClient()
    return fetcher


def test_fetch_trade_dates(fetcher):
    """测试获取交易日历"""
    # 准备测试数据
    test_dates = [
        {
            "exchange": "SHFE",
            "trade_date": "2024-01-02",
            "pretrade_date": "2023-12-29",
            "datestamp": "20240102"
        },
        {
            "exchange": "SHFE",
            "trade_date": "2024-01-03",
            "pretrade_date": "2024-01-02",
            "datestamp": "20240103"
        }
    ]
    fetcher.client.trade_date.find_results = [test_dates]

    # 测试获取指定交易所的交易日历
    result = fetcher.fetch_trade_dates(exchanges="SHFE")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert result.iloc[0]["trade_date"] == "2024-01-02"
    assert result.iloc[1]["trade_date"] == "2024-01-03"


def test_fetch_future_contracts_by_symbol(fetcher):
    """测试通过合约代码获取期货合约信息"""
    # 准备测试数据
    test_contract = [{
        "symbol": "m2405",
        "exchange": "DCE",
        "name": "豆粕2405",
        "chinese_name": "豆粕",
        "list_date": "2023-03-01",
        "delist_date": "2024-05-15",
        "list_datestamp": "20230301",
        "delist_datestamp": "20240515"
    }]
    fetcher.client.future_contracts.find_results = [test_contract]

    # 测试获取指定合约的信息
    result = fetcher.fetch_future_contracts(symbol="m2405")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result.iloc[0]["symbol"] == "m2405"
    assert result.iloc[0]["exchange"] == "DCE"


def test_fetch_future_contracts_by_exchange_and_spec(fetcher):
    """测试通过交易所和品种获取期货合约信息"""
    # 准备测试数据
    test_contracts = [
        {
            "symbol": "m2405",
            "exchange": "DCE",
            "name": "豆粕2405",
            "chinese_name": "豆粕",
            "list_date": "2023-03-01",
            "delist_date": "2024-05-15",
            "list_datestamp": "20230301",
            "delist_datestamp": "20240515"
        },
        {
            "symbol": "m2407",
            "exchange": "DCE",
            "name": "豆粕2407",
            "chinese_name": "豆粕",
            "list_date": "2023-05-01",
            "delist_date": "2024-07-15",
            "list_datestamp": "20230501",
            "delist_datestamp": "20240715"
        }
    ]
    fetcher.client.future_contracts.find_results = [test_contracts]

    # 测试获取指定交易所和品种的合约信息
    result = fetcher.fetch_future_contracts(
        exchanges="DCE",
        spec_name="豆粕",
        cursor_date="2024-01-21"
    )
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert all(result["exchange"] == "DCE")
    assert all(result["chinese_name"] == "豆粕")


def test_fetch_future_contracts_with_cursor_date(fetcher):
    """测试使用日期过滤获取期货合约信息"""
    # 准备测试数据
    test_contracts = [
        {
            "symbol": "m2405",
            "exchange": "DCE",
            "name": "豆粕2405",
            "chinese_name": "豆粕",
            "list_date": "2023-03-01",
            "delist_date": "2024-05-15",
            "list_datestamp": "20230301",
            "delist_datestamp": "20240515"
        }
    ]
    fetcher.client.future_contracts.find_results = [test_contracts]

    # 测试使用日期过滤
    result = fetcher.fetch_future_contracts(cursor_date="2024-01-21")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result.iloc[0]["symbol"] == "m2405"


def test_fetch_future_contracts_empty_result(fetcher):
    """测试没有数据的情况"""
    fetcher.client.future_contracts.find_results = [[]]  # 空结果

    result = fetcher.fetch_future_contracts(
        exchanges="SHFE",
        spec_name="铜"
    )
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0


def test_fetch_future_contracts_error_handling(fetcher):
    """测试错误处理"""
    # 设置 mock 在查询时抛出异常
    fetcher.client.future_contracts.find_results = [Exception("Database error")]

    with pytest.raises(Exception) as exc_info:
        fetcher.fetch_future_contracts(symbol="m2405")
    assert "Database error" in str(exc_info.value)
