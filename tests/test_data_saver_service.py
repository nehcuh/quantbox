"""
DataSaverService 单元测试

测试数据保存服务的核心功能：
- SaveResult 结果追踪
- 数据获取和保存流程
- 索引创建
- 批量 upsert 操作
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import pandas as pd
import datetime
import pymongo

from quantbox.services.data_saver_service import DataSaverService, SaveResult
from quantbox.adapters.base import BaseDataAdapter


class MockAdapter(BaseDataAdapter):
    """测试用的 Mock 适配器"""

    def __init__(self, name: str, return_empty: bool = False):
        super().__init__(name)
        self.return_empty = return_empty
        self.call_history = []

    def check_availability(self) -> bool:
        return True

    def get_trade_calendar(self, exchanges=None, start_date=None, end_date=None):
        """模拟交易日历查询"""
        self.call_history.append(('get_trade_calendar', exchanges, start_date, end_date))
        if self.return_empty:
            return pd.DataFrame()
        return pd.DataFrame({
            'date': [20250101, 20250102],
            'exchange': ['SHSE', 'SHSE'],
            'is_open': [True, True]
        })

    def get_future_contracts(self, exchanges=None, symbols=None, spec_names=None, date=None):
        """模拟期货合约查询"""
        self.call_history.append(('get_future_contracts', exchanges, symbols, spec_names, date))
        if self.return_empty:
            return pd.DataFrame()
        return pd.DataFrame({
            'symbol': ['SHFE.rb2501'],
            'exchange': ['SHFE'],
            'spec_name': ['rb'],
            'name': ['螺纹钢2501'],
            'list_date': [20241101],
            'delist_date': [20250115]
        })

    def get_future_daily(self, symbols=None, exchanges=None, start_date=None, end_date=None, date=None, **kwargs):
        """模拟日线数据查询"""
        self.call_history.append(('get_future_daily', symbols, exchanges, start_date, end_date, date))
        if self.return_empty:
            return pd.DataFrame()
        return pd.DataFrame({
            'symbol': ['SHFE.rb2501'],
            'exchange': ['SHFE'],
            'date': [20250101],
            'open': [3800.0],
            'high': [3900.0],
            'low': [3750.0],
            'close': [3850.0],
            'volume': [100000],
            'amount': [385000000.0]
        })

    def get_future_holdings(self, symbols=None, exchanges=None, spec_names=None, start_date=None, end_date=None, date=None, **kwargs):
        """模拟持仓数据查询"""
        self.call_history.append(('get_future_holdings', symbols, exchanges, spec_names, start_date, end_date, date))
        if self.return_empty:
            return pd.DataFrame()
        return pd.DataFrame({
            'symbol': ['SHFE.rb2501'],
            'exchange': ['SHFE'],
            'date': [20250101],
            'broker': ['永安期货'],
            'vol': [1000],
            'vol_chg': [100],
            'long_hld': [500],
            'short_hld': [500]
        })


class TestSaveResult(unittest.TestCase):
    """测试 SaveResult 类"""

    def test_initialization(self):
        """测试初始化"""
        result = SaveResult()

        self.assertTrue(result.success)
        self.assertEqual(result.inserted_count, 0)
        self.assertEqual(result.modified_count, 0)
        self.assertEqual(result.error_count, 0)
        self.assertEqual(result.errors, [])
        self.assertIsNotNone(result.start_time)
        self.assertIsNone(result.end_time)

    def test_add_error(self):
        """测试添加错误"""
        result = SaveResult()
        result.add_error("TEST_ERROR", "这是一个测试错误", data={"key": "value"})

        self.assertFalse(result.success)
        self.assertEqual(result.error_count, 1)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0]["type"], "TEST_ERROR")
        self.assertEqual(result.errors[0]["message"], "这是一个测试错误")
        self.assertEqual(result.errors[0]["data"], {"key": "value"})

    def test_complete(self):
        """测试完成操作"""
        result = SaveResult()
        self.assertIsNone(result.end_time)

        result.complete()
        self.assertIsNotNone(result.end_time)

    def test_duration(self):
        """测试持续时间计算"""
        result = SaveResult()

        # 未完成时应该返回当前时间差
        duration_before = result.duration
        self.assertIsInstance(duration_before, datetime.timedelta)

        # 完成后应该返回固定的时间差
        result.complete()
        duration_after = result.duration
        self.assertIsInstance(duration_after, datetime.timedelta)

    def test_to_dict(self):
        """测试转换为字典"""
        result = SaveResult()
        result.inserted_count = 10
        result.modified_count = 5
        result.add_error("TEST_ERROR", "测试错误")
        result.complete()

        dict_result = result.to_dict()

        self.assertIsInstance(dict_result, dict)
        self.assertFalse(dict_result["success"])
        self.assertEqual(dict_result["inserted_count"], 10)
        self.assertEqual(dict_result["modified_count"], 5)
        self.assertEqual(dict_result["error_count"], 1)
        self.assertEqual(len(dict_result["errors"]), 1)
        self.assertIsNotNone(dict_result["start_time"])
        self.assertIsNotNone(dict_result["end_time"])
        self.assertIsNotNone(dict_result["duration"])


class TestDataSaverServiceInit(unittest.TestCase):
    """测试 DataSaverService 初始化"""

    def test_custom_adapters(self):
        """测试自定义适配器"""
        remote = MockAdapter("RemoteMock")
        local = MockAdapter("LocalMock")
        mock_db = MagicMock()

        service = DataSaverService(
            remote_adapter=remote,
            local_adapter=local,
            database=mock_db
        )

        self.assertEqual(service.remote_adapter, remote)
        self.assertEqual(service.local_adapter, local)
        self.assertEqual(service.database, mock_db)


class TestCreateIndex(unittest.TestCase):
    """测试索引创建"""

    def test_create_index_success(self):
        """测试成功创建索引"""
        remote = MockAdapter("RemoteMock")
        mock_db = MagicMock()
        mock_collection = MagicMock()

        service = DataSaverService(remote_adapter=remote, database=mock_db)
        service._create_index(
            mock_collection,
            [("exchange", pymongo.ASCENDING), ("date", pymongo.ASCENDING)],
            unique=True
        )

        # 验证调用了 create_index
        mock_collection.create_index.assert_called_once()

    def test_create_index_duplicate_key_error(self):
        """测试重复键错误时不抛出异常"""
        remote = MockAdapter("RemoteMock")
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_collection.create_index.side_effect = pymongo.errors.DuplicateKeyError("duplicate key")

        service = DataSaverService(remote_adapter=remote, database=mock_db)

        # 应该不抛出异常
        try:
            service._create_index(
                mock_collection,
                [("exchange", pymongo.ASCENDING)],
                unique=True
            )
        except Exception:
            self.fail("不应该抛出异常")


class TestBulkUpsert(unittest.TestCase):
    """测试批量 upsert"""

    def test_bulk_upsert_empty_data(self):
        """测试空数据"""
        remote = MockAdapter("RemoteMock")
        mock_db = MagicMock()
        mock_collection = MagicMock()

        service = DataSaverService(remote_adapter=remote, database=mock_db)
        result = service._bulk_upsert(mock_collection, [], ["key"])

        self.assertEqual(result["upserted_count"], 0)
        self.assertEqual(result["modified_count"], 0)

    def test_bulk_upsert_with_data(self):
        """测试有数据的 upsert"""
        remote = MockAdapter("RemoteMock")
        mock_db = MagicMock()
        mock_collection = MagicMock()

        # Mock bulk_write 返回值
        mock_result = MagicMock()
        mock_result.upserted_count = 3
        mock_result.modified_count = 2
        mock_collection.bulk_write.return_value = mock_result

        service = DataSaverService(remote_adapter=remote, database=mock_db)

        data = [
            {"exchange": "SHSE", "date": 20250101},
            {"exchange": "SHSE", "date": 20250102},
            {"exchange": "SZSE", "date": 20250101},
        ]

        result = service._bulk_upsert(mock_collection, data, ["exchange", "date"])

        self.assertEqual(result["upserted_count"], 3)
        self.assertEqual(result["modified_count"], 2)
        mock_collection.bulk_write.assert_called_once()


class TestSaveTradeCalendar(unittest.TestCase):
    """测试保存交易日历"""

    def test_save_success(self):
        """测试成功保存"""
        remote = MockAdapter("RemoteMock", return_empty=False)
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.trade_date = mock_collection

        # Mock bulk_write 返回值
        mock_result = MagicMock()
        mock_result.upserted_count = 2
        mock_result.modified_count = 0
        mock_collection.bulk_write.return_value = mock_result

        service = DataSaverService(remote_adapter=remote, database=mock_db)
        result = service.save_trade_calendar(exchanges='SHSE')

        # 验证结果
        self.assertTrue(result.success)
        self.assertEqual(result.inserted_count, 2)
        self.assertEqual(result.modified_count, 0)
        self.assertEqual(result.error_count, 0)
        self.assertIsNotNone(result.end_time)

        # 验证调用了远程适配器
        self.assertEqual(len(remote.call_history), 1)

    def test_save_empty_data(self):
        """测试保存空数据"""
        remote = MockAdapter("RemoteMock", return_empty=True)
        mock_db = MagicMock()

        service = DataSaverService(remote_adapter=remote, database=mock_db)
        result = service.save_trade_calendar(exchanges='SHSE')

        # 验证结果
        self.assertFalse(result.success)
        self.assertEqual(result.error_count, 1)
        self.assertEqual(result.errors[0]["type"], "NO_DATA")


class TestSaveFutureContracts(unittest.TestCase):
    """测试保存期货合约"""

    def test_save_success(self):
        """测试成功保存"""
        remote = MockAdapter("RemoteMock", return_empty=False)
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.future_contracts = mock_collection

        # Mock bulk_write 返回值
        mock_result = MagicMock()
        mock_result.upserted_count = 1
        mock_result.modified_count = 0
        mock_collection.bulk_write.return_value = mock_result

        service = DataSaverService(remote_adapter=remote, database=mock_db)
        result = service.save_future_contracts(exchanges='SHFE')

        self.assertTrue(result.success)
        self.assertEqual(result.inserted_count, 1)
        self.assertEqual(len(remote.call_history), 1)


class TestSaveFutureDaily(unittest.TestCase):
    """测试保存期货日线数据"""

    def test_save_success(self):
        """测试成功保存"""
        remote = MockAdapter("RemoteMock", return_empty=False)
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.future_daily = mock_collection

        # Mock bulk_write 返回值
        mock_result = MagicMock()
        mock_result.upserted_count = 1
        mock_result.modified_count = 0
        mock_collection.bulk_write.return_value = mock_result

        service = DataSaverService(remote_adapter=remote, database=mock_db)
        result = service.save_future_daily(symbols='SHFE.rb2501')

        self.assertTrue(result.success)
        self.assertEqual(result.inserted_count, 1)
        self.assertEqual(len(remote.call_history), 1)

    def test_save_with_date_range(self):
        """测试带日期范围的保存"""
        remote = MockAdapter("RemoteMock", return_empty=False)
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.future_daily = mock_collection

        mock_result = MagicMock()
        mock_result.upserted_count = 1
        mock_result.modified_count = 0
        mock_collection.bulk_write.return_value = mock_result

        service = DataSaverService(remote_adapter=remote, database=mock_db)
        result = service.save_future_daily(
            symbols='SHFE.rb2501',
            start_date=20250101,
            end_date=20250131
        )

        self.assertTrue(result.success)
        call = remote.call_history[0]
        self.assertEqual(call[3], 20250101)  # start_date
        self.assertEqual(call[4], 20250131)  # end_date


class TestSaveFutureHoldings(unittest.TestCase):
    """测试保存期货持仓数据"""

    def test_save_success(self):
        """测试成功保存"""
        remote = MockAdapter("RemoteMock", return_empty=False)
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.future_holdings = mock_collection

        # Mock bulk_write 返回值
        mock_result = MagicMock()
        mock_result.upserted_count = 1
        mock_result.modified_count = 0
        mock_collection.bulk_write.return_value = mock_result

        service = DataSaverService(remote_adapter=remote, database=mock_db)
        result = service.save_future_holdings(symbols='SHFE.rb2501')

        self.assertTrue(result.success)
        self.assertEqual(result.inserted_count, 1)
        self.assertEqual(len(remote.call_history), 1)


class TestErrorHandling(unittest.TestCase):
    """测试错误处理"""

    def test_save_with_exception(self):
        """测试保存过程中的异常"""
        remote = MockAdapter("RemoteMock", return_empty=False)
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.trade_date = mock_collection

        # Mock bulk_write 抛出异常
        mock_collection.bulk_write.side_effect = Exception("数据库错误")

        service = DataSaverService(remote_adapter=remote, database=mock_db)
        result = service.save_trade_calendar(exchanges='SHSE')

        # 验证错误被捕获
        self.assertFalse(result.success)
        self.assertEqual(result.error_count, 1)
        self.assertEqual(result.errors[0]["type"], "SAVE_ERROR")
        self.assertIn("数据库错误", result.errors[0]["message"])


if __name__ == '__main__':
    unittest.main()
