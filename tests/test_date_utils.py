"""
Test cases for date utilities
"""
import datetime
import pytest
from unittest.mock import patch
from pymongo import MongoClient
from quantbox.util.date_utils import (
    is_trade_date,
    get_pre_trade_date,
    get_next_trade_date,
    get_trade_calendar
)


@pytest.fixture(scope="module")
def database():
    """创建数据库连接"""
    client = MongoClient("mongodb://localhost:27018")
    return client.quantbox


@pytest.mark.parametrize("test_date,expected", [
    ("2024-01-02", True),   # 交易日
    ("2024-01-03", True),   # 交易日
    ("2024-01-04", True),   # 交易日
    ("2024-01-05", True),   # 交易日
    ("2024-01-08", True),   # 交易日
    ("2024-01-09", True),   # 交易日
    ("2024-01-10", True),   # 交易日
    ("2024-01-06", False),  # 周六
    ("2024-01-07", False),  # 周日
    (None, None),           # 当前日期
])
def test_is_trade_date(database, test_date, expected):
    """测试是否为交易日的判断"""
    with patch("quantbox.util.date_utils.DATABASE", database):
        if test_date is None:
            # 当输入为None时，使用当前日期，这里我们跳过具体测试
            return
            
        result = is_trade_date(test_date, "SHSE")
        if expected is None:
            assert result is not None
        else:
            assert result == expected


@pytest.mark.parametrize("test_case", [
    {
        "cursor_date": "2024-01-08",
        "n": 1,
        "include_input": False,
        "expected_date": "2024-01-05"
    },
    {
        "cursor_date": "2024-01-08",
        "n": 1,
        "include_input": True,
        "expected_date": "2024-01-08"
    },
    {
        "cursor_date": "2024-01-07",  # 非交易日
        "n": 1,
        "include_input": False,
        "expected_date": "2024-01-05"
    },
    {
        "cursor_date": "2024-01-07",  # 非交易日
        "n": 1,
        "include_input": True,
        "expected_date": "2024-01-05"
    },
    {
        "cursor_date": "2024-01-08",
        "n": 2,
        "include_input": False,
        "expected_date": "2024-01-04"
    },
    {
        "cursor_date": "2024-01-08",
        "n": 2,
        "include_input": True,
        "expected_date": "2024-01-05"
    }
])
def test_get_pre_trade_date(database, test_case):
    """测试获取前一交易日"""
    with patch("quantbox.util.date_utils.DATABASE", database):
        result = get_pre_trade_date(
            test_case["cursor_date"],
            "SHSE",
            test_case["n"],
            test_case["include_input"]
        )
        assert result is not None
        assert result["trade_date"] == test_case["expected_date"]


@pytest.mark.parametrize("test_case", [
    {
        "cursor_date": "2024-01-05",
        "n": 1,
        "include_input": False,
        "expected_date": "2024-01-08"
    },
    {
        "cursor_date": "2024-01-05",
        "n": 1,
        "include_input": True,
        "expected_date": "2024-01-05"
    },
    {
        "cursor_date": "2024-01-06",  # 非交易日
        "n": 1,
        "include_input": False,
        "expected_date": "2024-01-08"
    },
    {
        "cursor_date": "2024-01-06",  # 非交易日
        "n": 1,
        "include_input": True,
        "expected_date": "2024-01-08"
    },
    {
        "cursor_date": "2024-01-05",
        "n": 2,
        "include_input": False,
        "expected_date": "2024-01-09"
    },
    {
        "cursor_date": "2024-01-08",
        "n": 2,
        "include_input": True,
        "expected_date": "2024-01-09"
    }
])
def test_get_next_trade_date(database, test_case):
    """测试获取下一交易日"""
    with patch("quantbox.util.date_utils.DATABASE", database):
        result = get_next_trade_date(
            test_case["cursor_date"],
            "SHSE",
            test_case["n"],
            test_case["include_input"]
        )
        assert result is not None
        assert result["trade_date"] == test_case["expected_date"]


def test_get_trade_calendar(database):
    """测试获取交易日历"""
    with patch("quantbox.util.date_utils.DATABASE", database):
        result = get_trade_calendar(
            start_date="2024-01-01",
            end_date="2024-01-10",
            exchange="SHSE"
        )
        assert len(result) > 0
        assert "trade_date" in result.columns
        assert "exchange" in result.columns
