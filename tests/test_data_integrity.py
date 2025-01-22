import pytest
import pandas as pd
import datetime
from unittest.mock import MagicMock, patch
from pymongo.collection import Collection
from pymongo.database import Database
from bson import ObjectId

from quantbox.savers.data_saver import DataIntegrityChecker, SaveResult


@pytest.fixture
def mock_mongo_client():
    client = MagicMock()
    db = MagicMock(spec=Database)
    trade_date_collection = MagicMock(spec=Collection)
    future_contracts_collection = MagicMock(spec=Collection)
    
    client.trade_date = trade_date_collection
    client.future_contracts = future_contracts_collection
    return client


@pytest.fixture
def checker(mock_mongo_client):
    config = {"saver": {"default_start_date": "1990-12-19"}}
    return DataIntegrityChecker(mock_mongo_client, config)


def test_check_trade_dates_no_data(checker):
    """测试没有数据的情况"""
    checker.client.trade_date.aggregate.return_value = []
    
    result = checker.check_trade_dates("SHSE")
    
    assert not result.success
    assert len(result.errors) == 1
    assert result.errors[0]["type"] == "NO_DATA"
    assert "SHSE" in result.errors[0]["message"]


def test_check_trade_dates_weekend_trades(checker):
    """测试包含周末交易的情况（国内市场不应该有周末交易）"""
    # 生成包含周末的交易日数据
    dates = pd.date_range(
        start="2024-01-01",
        end="2024-01-07"
    ).strftime("%Y-%m-%d").tolist()
    
    checker.client.trade_date.aggregate.return_value = [{
        "dates": dates,
        "count": len(dates),
        "min_date": dates[0],
        "max_date": dates[-1]
    }]
    
    checker.client.trade_date.find.return_value = []
    
    result = checker.check_trade_dates("SHSE")  # 测试上交所
    
    assert not result.success
    assert any(error["type"] == "WEEKEND_TRADES" for error in result.errors)
    weekend_dates = [
        "2024-01-06",  # 周六
        "2024-01-07"   # 周日
    ]
    weekend_trades = next(error["data"] for error in result.errors 
                         if error["type"] == "WEEKEND_TRADES")
    assert all(date in weekend_trades for date in weekend_dates)


def test_check_trade_dates_normal_month(checker):
    """测试正常月份的交易日数量（国内市场）"""
    # 生成一个月的正常交易日数据（周一到周五，20天）
    dates = pd.date_range(
        start="2024-01-01",
        periods=20,
        freq="B"
    ).strftime("%Y-%m-%d").tolist()
    
    checker.client.trade_date.aggregate.return_value = [{
        "dates": dates,
        "count": len(dates),
        "min_date": dates[0],
        "max_date": dates[-1]
    }]
    
    checker.client.trade_date.find.return_value = []
    
    result = checker.check_trade_dates("SHFE")  # 测试上期所
    
    assert result.success
    assert not any(error["type"] == "LOW_TRADING_DAYS" for error in result.errors)


def test_check_trade_dates_spring_festival(checker):
    """测试春节月份的交易日数量（国内市场）"""
    # 生成春节月份的交易日数据（15天，刚好达到最小要求）
    dates = pd.date_range(
        start="2024-02-01",
        periods=15,
        freq="B"
    ).strftime("%Y-%m-%d").tolist()
    
    checker.client.trade_date.aggregate.return_value = [{
        "dates": dates,
        "count": len(dates),
        "min_date": dates[0],
        "max_date": dates[-1]
    }]
    
    checker.client.trade_date.find.return_value = []
    
    result = checker.check_trade_dates("DCE")  # 测试大商所
    
    assert result.success
    assert not any(error["type"] == "LOW_TRADING_DAYS" for error in result.errors)


def test_check_trade_dates_abnormal_month(checker):
    """测试交易日异常少的月份（国内市场）"""
    # 生成交易日异常少的月份数据（只有10天）
    dates = pd.date_range(
        start="2024-01-01",
        periods=10,
        freq="B"
    ).strftime("%Y-%m-%d").tolist()
    
    checker.client.trade_date.aggregate.return_value = [{
        "dates": dates,
        "count": len(dates),
        "min_date": dates[0],
        "max_date": dates[-1]
    }]
    
    checker.client.trade_date.find.return_value = []
    
    result = checker.check_trade_dates("CFFEX")  # 测试中金所
    
    assert not result.success
    assert any(error["type"] == "LOW_TRADING_DAYS" for error in result.errors)
    error = next(error for error in result.errors 
                if error["type"] == "LOW_TRADING_DAYS")
    assert error["data"]["count"] == 10
    assert error["data"]["year"] == 2024
    assert error["data"]["month"] == 1


def test_check_trade_dates_missing_fields(checker):
    """测试缺失必要字段的情况"""
    dates = pd.date_range(
        start="2024-01-01",
        periods=5,
        freq="B"
    ).strftime("%Y-%m-%d").tolist()
    
    checker.client.trade_date.aggregate.return_value = [{
        "dates": dates,
        "count": len(dates),
        "min_date": dates[0],
        "max_date": dates[-1]
    }]
    
    # 模拟一条缺失字段的数据
    checker.client.trade_date.find.return_value = [{
        "_id": ObjectId(),
        "exchange": "SHSE",
        "trade_date": "2024-01-01"
        # 缺失 pretrade_date 和 datestamp
    }]
    
    result = checker.check_trade_dates("SHSE")
    
    assert not result.success
    assert any(error["type"] == "MISSING_FIELD" for error in result.errors)


def test_check_trade_dates_invalid_pretrade(checker):
    """测试前一交易日晚于交易日的情况"""
    dates = pd.date_range(
        start="2024-01-01",
        periods=5,
        freq="B"
    ).strftime("%Y-%m-%d").tolist()
    
    checker.client.trade_date.aggregate.return_value = [{
        "dates": dates,
        "count": len(dates),
        "min_date": dates[0],
        "max_date": dates[-1]
    }]
    
    # 模拟一条 pretrade_date 晚于 trade_date 的数据
    checker.client.trade_date.find.side_effect = [
        [],  # 第一次调用返回空（检查缺失字段）
        [{  # 第二次调用返回无效的 pretrade_date 数据
            "_id": ObjectId(),
            "exchange": "SHSE",
            "trade_date": "2024-01-01",
            "pretrade_date": "2024-01-02"
        }]
    ]
    
    result = checker.check_trade_dates("SHSE")
    
    assert not result.success
    assert any(error["type"] == "INVALID_PRETRADE_DATE" for error in result.errors)


def test_check_trade_dates_exception_handling(checker):
    """测试异常处理"""
    checker.client.trade_date.aggregate.side_effect = Exception("Database error")
    
    result = checker.check_trade_dates("SHSE")
    
    assert not result.success
    assert len(result.errors) == 1
    assert result.errors[0]["type"] == "CHECK_ERROR"
    assert "Database error" in result.errors[0]["message"]


def test_save_result_duration(checker):
    """测试 SaveResult 的持续时间计算"""
    result = SaveResult()
    
    # 模拟操作耗时
    result.start_time = datetime.datetime.now() - datetime.timedelta(seconds=5)
    result.complete()
    
    duration = result.duration
    assert isinstance(duration, datetime.timedelta)
    assert 4.5 <= duration.total_seconds() <= 5.5  # 允许0.5秒的误差


def test_save_result_to_dict(checker):
    """测试 SaveResult 的字典转换"""
    result = SaveResult()
    result.add_error("TEST_ERROR", "Test message", {"test": "data"})
    result.metadata["test_meta"] = "test_value"
    result.complete()
    
    result_dict = result.to_dict()
    
    assert not result_dict["success"]
    assert result_dict["error_count"] == 1
    assert len(result_dict["errors"]) == 1
    assert result_dict["errors"][0]["type"] == "TEST_ERROR"
    assert result_dict["metadata"]["test_meta"] == "test_value"
    assert isinstance(result_dict["duration"], str)
