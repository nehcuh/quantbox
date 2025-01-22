import pytest
from datetime import datetime
from bson import ObjectId
from quantbox.savers.data_saver import DataIntegrityChecker


@pytest.fixture
def checker():
    """创建测试用的完整性检查器"""
    # 创建 MongoDB 客户端的 mock
    class MockCollection:
        def __init__(self):
            self.find_results = []
            self.aggregate_results = []

        def find(self, *args, **kwargs):
            result = self.find_results.pop(0) if self.find_results else []
            if isinstance(result, Exception):
                raise result
            return result

        def aggregate(self, *args, **kwargs):
            result = self.aggregate_results.pop(0) if self.aggregate_results else []
            if isinstance(result, Exception):
                raise result
            return result

    class MockClient:
        def __init__(self):
            self.future_contracts = MockCollection()

    class MockConfig:
        pass

    return DataIntegrityChecker(MockClient(), MockConfig())


def test_check_future_contracts_no_data(checker):
    """测试没有数据的情况"""
    # 设置 mock 返回空数据
    checker.client.future_contracts.find_results = [[], []]  # 两次 find 调用都返回空
    checker.client.future_contracts.aggregate_results = [[]]  # aggregate 返回空

    result = checker.check_future_contracts("SHFE")  # 测试上期所

    assert result.success  # 没有数据不应该被视为错误
    assert "total_count" not in result.metadata  # 没有数据时不应该有统计信息


def test_check_future_contracts_missing_fields(checker):
    """测试缺失必要字段的情况"""
    # 设置 mock 返回缺失字段的数据
    doc_missing_fields = {
        "_id": ObjectId(),
        "exchange": "DCE",  # 测试大商所
        "symbol": "m2405"  # 只有交易所和合约代码
    }
    checker.client.future_contracts.find_results = [
        [doc_missing_fields],  # 第一次 find 调用返回缺失字段的数据
        []  # 第二次 find 调用（检查日期有效性）返回空
    ]
    checker.client.future_contracts.aggregate_results = [[]]

    result = checker.check_future_contracts("DCE")

    assert not result.success
    assert any(error["type"] == "MISSING_FIELD" for error in result.errors)
    error = next(error for error in result.errors if error["type"] == "MISSING_FIELD")
    assert "m2405" in str(error["data"])


def test_check_future_contracts_invalid_dates(checker):
    """测试上市日期晚于退市日期的情况"""
    # 设置 mock 返回日期无效的数据
    doc_invalid_dates = {
        "_id": ObjectId(),
        "exchange": "CZCE",  # 测试郑商所
        "symbol": "CF405",
        "name": "棉花2405",
        "list_date": "2024-05-01",
        "delist_date": "2024-04-01",  # 退市日期早于上市日期
        "datestamp": datetime.now().strftime("%Y-%m-%d")
    }
    checker.client.future_contracts.find_results = [
        [],  # 第一次 find 调用（检查字段完整性）返回空
        [doc_invalid_dates]  # 第二次 find 调用返回日期无效的数据
    ]
    checker.client.future_contracts.aggregate_results = [[]]

    result = checker.check_future_contracts("CZCE")

    assert not result.success
    assert any(error["type"] == "INVALID_DATE" for error in result.errors)
    error = next(error for error in result.errors if error["type"] == "INVALID_DATE")
    assert "CF405" in error["message"]


def test_check_future_contracts_normal_data(checker):
    """测试正常数据的情况"""
    # 设置 mock 返回正常的数据
    stats_data = [{
        "_id": None,
        "total_count": 100,
        "active_count": 30
    }]
    checker.client.future_contracts.find_results = [[], []]  # 两次 find 调用都返回空（没有错误）
    checker.client.future_contracts.aggregate_results = [stats_data]

    result = checker.check_future_contracts("CFFEX")  # 测试中金所

    assert result.success
    assert result.metadata["total_count"] == 100
    assert result.metadata["active_count"] == 30


def test_check_future_contracts_exception_handling(checker):
    """测试异常处理"""
    # 设置 mock 在第一次 find 调用时抛出异常
    checker.client.future_contracts.find_results = [Exception("Database error")]
    checker.client.future_contracts.aggregate_results = [[]]

    result = checker.check_future_contracts("INE")  # 测试上期能源

    assert not result.success
    assert len(result.errors) == 1
    assert result.errors[0]["type"] == "CHECK_ERROR"
    assert "Database error" in result.errors[0]["message"]
