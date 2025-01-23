"""Test database manager"""

import unittest
from typing import Dict, Any
import pandas as pd

from tests.utils.test_config import TestConfig


class TestDatabaseManager(unittest.TestCase):
    """Test database manager"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        # 创建测试配置管理器
        cls.db = TestConfig.create_db_manager()

    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures"""
        # 删除测试集合
        cls.db.get_collection("calendar").drop()
        # 关闭数据库连接
        cls.db.close()

    def setUp(self):
        """Set up test fixtures"""
        # 清空测试集合
        self.db.get_collection("calendar").delete_many({})

    def test_save_and_get_calendar(self):
        """测试保存和获取交易日历"""
        # 准备数据
        data = pd.DataFrame({
            "exchange": ["SSE", "SZSE"],
            "trade_date": ["20240101", "20240102"],
            "is_open": [1, 1]
        })

        # 保存数据
        self.db.save_calendar(data)

        # 获取数据
        result = self.db.get_calendar()

        # 验证数据
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(all(col in result.columns for col in ["exchange", "trade_date", "is_open"]))

    def test_ensure_calendar_index(self):
        """测试创建交易日历索引"""
        # 确保索引存在
        self.db.ensure_calendar_index()

        # 获取集合
        collection = self.db.get_collection("calendar")

        # 获取索引信息
        index_info = collection.index_information()

        # 验证索引
        self.assertTrue(any(
            all(key == "exchange" or key == "trade_date" for key, _ in spec["key"])
            for spec in index_info.values()
        ))
        self.assertTrue(any(
            all(key == "exchange" or key == "datestamp" for key, _ in spec["key"])
            for spec in index_info.values()
        ))
        self.assertTrue(any(
            all(key == "exchange" or key == "pretrade_date" for key, _ in spec["key"])
            for spec in index_info.values()
        ))

    def test_duplicate_save(self):
        """测试重复保存数据"""
        # 准备数据
        data = pd.DataFrame({
            "exchange": ["SSE", "SZSE"],
            "trade_date": ["20240101", "20240102"],
            "is_open": [1, 1]
        })

        # 第一次保存
        self.db.save_calendar(data)

        # 第二次保存相同数据
        self.db.save_calendar(data)

        # 获取数据
        result = self.db.get_calendar()

        # 验证数据没有重复
        self.assertEqual(len(result), len(data))


if __name__ == "__main__":
    unittest.main()
