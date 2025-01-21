"""
交易日期和合约查询测试模块
"""
import pytest
from datetime import datetime
import pandas as pd
from quantbox.fetchers.local_fetcher import LocalFetcher


@pytest.fixture
def fetcher():
    """创建测试用的本地数据获取器"""
    class MockCursor:
        def __init__(self, items):
            self.items = items
            self.current = 0

        def sort(self, *args, **kwargs):
            return self

        def skip(self, n):
            self.current = n
            return self

        def next(self):
            if self.current < len(self.items):
                item = self.items[self.current]
                self.current += 1
                return item
            raise StopIteration

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


def test_fetch_trade_dates_basic(fetcher):
    """测试基本的交易日历获取功能"""
    test_dates = [
        {
            "exchange": "SSE",
            "trade_date": "2024-01-02",
            "pretrade_date": "2023-12-29",
            "datestamp": "20240102"
        },
        {
            "exchange": "SSE",
            "trade_date": "2024-01-03",
            "pretrade_date": "2024-01-02",
            "datestamp": "20240103"
        }
    ]
    fetcher.client.trade_date.find_results = [test_dates]

    result = fetcher.fetch_trade_dates(exchanges="SSE")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert result.iloc[0]["trade_date"] == "2024-01-02"
    assert result.iloc[1]["trade_date"] == "2024-01-03"


def test_fetch_trade_dates_multiple_exchanges(fetcher):
    """测试获取多个交易所的交易日历"""
    test_dates = [
        {
            "exchange": "SSE",
            "trade_date": "2024-01-02",
            "datestamp": "20240102"
        },
        {
            "exchange": "SZSE",
            "trade_date": "2024-01-02",
            "datestamp": "20240102"
        }
    ]
    fetcher.client.trade_date.find_results = [test_dates]

    result = fetcher.fetch_trade_dates(exchanges=["SSE", "SZSE"])
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert set(result["exchange"].unique()) == {"SSE", "SZSE"}


def test_fetch_trade_dates_with_date_range(fetcher):
    """测试带有日期范围的交易日历获取"""
    test_dates = [
        {
            "exchange": "SSE",
            "trade_date": "2024-01-02",
            "datestamp": "20240102"
        },
        {
            "exchange": "SSE",
            "trade_date": "2024-01-03",
            "datestamp": "20240103"
        }
    ]
    fetcher.client.trade_date.find_results = [test_dates]

    result = fetcher.fetch_trade_dates(
        exchanges="SSE",
        start_date="2024-01-02",
        end_date="2024-01-03"
    )
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert min(result["datestamp"]) >= "20240102"
    assert max(result["datestamp"]) <= "20240103"


def test_fetch_pre_trade_date_basic(fetcher):
    """测试基本的前一交易日获取功能"""
    test_dates = [
        {
            "exchange": "SSE",
            "trade_date": "2024-01-02",
            "datestamp": "20240102"
        }
    ]
    fetcher.client.trade_date.find_results = [test_dates]

    result = fetcher.fetch_pre_trade_date(exchange="SSE", cursor_date="2024-01-03")
    assert isinstance(result, dict)
    assert result["trade_date"] == "2024-01-02"


def test_fetch_pre_trade_date_with_n(fetcher):
    """测试获取前n个交易日"""
    test_dates = [
        {
            "exchange": "SSE",
            "trade_date": "2024-01-02",
            "datestamp": "20240102"
        }
    ]
    fetcher.client.trade_date.find_results = [test_dates]

    result = fetcher.fetch_pre_trade_date(
        exchange="SSE",
        cursor_date="2024-01-05",
        n=2
    )
    assert isinstance(result, dict)
    assert result["trade_date"] == "2024-01-02"


def test_fetch_next_trade_date_basic(fetcher):
    """测试基本的下一交易日获取功能"""
    test_dates = [
        {
            "exchange": "SSE",
            "trade_date": "2024-01-03",
            "datestamp": "20240103"
        }
    ]
    fetcher.client.trade_date.find_results = [test_dates]

    result = fetcher.fetch_next_trade_date(exchange="SSE", cursor_date="2024-01-02")
    assert isinstance(result, dict)
    assert result["trade_date"] == "2024-01-03"


def test_fetch_next_trade_date_with_n(fetcher):
    """测试获取后n个交易日"""
    test_dates = [
        {
            "exchange": "SSE",
            "trade_date": "2024-01-05",
            "datestamp": "20240105"
        }
    ]
    fetcher.client.trade_date.find_results = [test_dates]

    result = fetcher.fetch_next_trade_date(
        exchange="SSE",
        cursor_date="2024-01-02",
        n=2
    )
    assert isinstance(result, dict)
    assert result["trade_date"] == "2024-01-05"


def test_fetch_future_contracts_basic(fetcher):
    """测试基本的期货合约获取功能"""
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

    result = fetcher.fetch_future_contracts(symbol="m2405")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result.iloc[0]["symbol"] == "m2405"
    assert result.iloc[0]["exchange"] == "DCE"


def test_fetch_future_contracts_by_exchange(fetcher):
    """测试按交易所获取期货合约"""
    test_contracts = [
        {
            "symbol": "m2405",
            "exchange": "DCE",
            "name": "豆粕2405",
            "chinese_name": "豆粕"
        },
        {
            "symbol": "m2407",
            "exchange": "DCE",
            "name": "豆粕2407",
            "chinese_name": "豆粕"
        }
    ]
    fetcher.client.future_contracts.find_results = [test_contracts]

    result = fetcher.fetch_future_contracts(exchanges="DCE")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert all(result["exchange"] == "DCE")


def test_fetch_future_contracts_by_spec_name(fetcher):
    """测试按品种名称获取期货合约"""
    test_contracts = [
        {
            "symbol": "m2405",
            "exchange": "DCE",
            "name": "豆粕2405",
            "chinese_name": "豆粕"
        },
        {
            "symbol": "m2407",
            "exchange": "DCE",
            "name": "豆粕2407",
            "chinese_name": "豆粕"
        }
    ]
    fetcher.client.future_contracts.find_results = [test_contracts]

    result = fetcher.fetch_future_contracts(spec_name="豆粕")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert all(result["chinese_name"] == "豆粕")


def test_fetch_future_contracts_with_cursor_date(fetcher):
    """测试使用日期过滤获取期货合约"""
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

    result = fetcher.fetch_future_contracts(cursor_date="2024-01-21")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result.iloc[0]["symbol"] == "m2405"


"""
Test cases for trade date fetcher
"""
import pytest
import pandas as pd
import datetime
from quantbox.fetchers.local_fetcher import LocalFetcher


@pytest.fixture
def fetcher():
    """创建 LocalFetcher 实例"""
    return LocalFetcher()


def test_fetch_trade_dates(fetcher):
    """测试获取交易日期"""
    # 测试默认参数
    df = fetcher.fetch_trade_dates()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert "exchange" in df.columns
    assert "datestamp" in df.columns

    # 测试指定交易所
    df = fetcher.fetch_trade_dates(exchanges="SSE")
    assert all(df["exchange"] == "SSE")

    # 测试指定日期范围
    start_date = "2023-01-01"
    end_date = "2023-12-31"
    df = fetcher.fetch_trade_dates(start_date=start_date, end_date=end_date)
    assert len(df) > 0
    assert all(df["datestamp"] >= 20230101)
    assert all(df["datestamp"] <= 20231231)


def test_fetch_pre_trade_date(fetcher):
    """测试获取前一交易日"""
    # 测试默认参数
    result = fetcher.fetch_pre_trade_date()
    assert isinstance(result, dict)
    assert "exchange" in result
    assert "datestamp" in result

    # 测试指定日期
    result = fetcher.fetch_pre_trade_date(
        exchange="SSE",
        cursor_date="2023-12-31",
        n=1,
        include=False
    )
    assert result["exchange"] == "SSE"
    assert result["datestamp"] < 20231231

    # 测试包含当天
    result = fetcher.fetch_pre_trade_date(
        exchange="SSE",
        cursor_date="2023-12-31",
        n=1,
        include=True
    )
    assert result["exchange"] == "SSE"
    assert result["datestamp"] <= 20231231


def test_fetch_next_trade_date(fetcher):
    """测试获取下一交易日"""
    # 测试默认参数
    result = fetcher.fetch_next_trade_date()
    assert isinstance(result, dict)
    assert "exchange" in result
    assert "datestamp" in result

    # 测试指定日期
    result = fetcher.fetch_next_trade_date(
        exchange="SSE",
        cursor_date="2023-01-01",
        n=1,
        include=False
    )
    assert result["exchange"] == "SSE"
    assert result["datestamp"] > 20230101

    # 测试包含当天
    result = fetcher.fetch_next_trade_date(
        exchange="SSE",
        cursor_date="2023-01-01",
        n=1,
        include=True
    )
    assert result["exchange"] == "SSE"
    assert result["datestamp"] >= 20230101


def test_fetch_future_contracts(fetcher):
    """测试获取期货合约信息"""
    # 测试默认参数
    df = fetcher.fetch_future_contracts()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert "symbol" in df.columns
    assert "exchange" in df.columns

    # 测试指定合约
    symbol = "IF2401"
    df = fetcher.fetch_future_contracts(symbol=symbol)
    assert len(df) > 0
    assert all(df["symbol"] == symbol)

    # 测试指定交易所
    exchanges = ["CFFEX"]
    df = fetcher.fetch_future_contracts(exchanges=exchanges)
    assert len(df) > 0
    assert all(df["exchange"].isin(exchanges))

    # 测试指定品种
    spec_name = "沪深300"
    df = fetcher.fetch_future_contracts(spec_name=spec_name)
    assert len(df) > 0
    assert all(df["chinese_name"] == spec_name)

    # 测试指定日期
    cursor_date = "2023-12-31"
    df = fetcher.fetch_future_contracts(cursor_date=cursor_date)
    assert len(df) > 0
    datestamp = int(datetime.datetime.strptime(cursor_date, "%Y-%m-%d").strftime("%Y%m%d"))
    assert all(df["list_datestamp"] <= datestamp)
    assert all(df["delist_datestamp"] >= datestamp)

    # 测试指定字段
    fields = ["symbol", "exchange", "chinese_name"]
    df = fetcher.fetch_future_contracts(fields=fields)
    assert len(df) > 0
    assert all(col in df.columns for col in fields)
    assert len(df.columns) == len(fields)
