"""Test tushare fetcher"""

import unittest
from datetime import datetime

from tests.utils.test_config import TestConfig


class TestDataFetcher(unittest.TestCase):
    """Test tushare fetcher"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.fetcher = TestConfig.create_fetcher()
        
    def test_fetch_stock_calendar(self):
        """测试获取股票交易日历"""
        # 获取数据
        result = self.fetcher.fetch_stock_calendar()
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)
        self.assertEqual(result["exchange"].iloc[0], "SSE")
        
    def test_fetch_futures_calendar(self):
        """测试获取期货交易日历"""
        # 获取数据
        result = self.fetcher.fetch_futures_calendar()
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)
        self.assertEqual(result["exchange"].iloc[0], "CFFEX")
        
    def test_fetch_stock_basic(self):
        """测试获取股票基本信息"""
        # 获取数据
        result = self.fetcher.fetch_stock_basic()
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)
        self.assertIn("ts_code", result.columns)
        self.assertIn("name", result.columns)
        
    def test_is_trade_date(self):
        """测试判断交易日期"""
        # 测试一个工作日
        self.assertTrue(self.fetcher.is_trade_date("2024-01-02"))
        
        # 测试一个周末
        self.assertFalse(self.fetcher.is_trade_date("2024-01-01"))
        
    def test_batch_is_trade_date(self):
        """测试批量判断交易日期"""
        dates = ["2024-01-01", "2024-01-02"]
        result = self.fetcher.batch_is_trade_date(dates)
        
        # 验证结果
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), len(dates))
        self.assertFalse(result["2024-01-01"])  # 元旦节
        self.assertTrue(result["2024-01-02"])  # 工作日
        
    def test_get_next_trade_date_n(self):
        """测试获取下n个交易日"""
        # 测试获取下一个交易日
        result = self.fetcher.get_next_trade_date_n("2024-01-01", 1)
        self.assertEqual(result, "2024-01-02")
        
        # 测试获取下两个交易日
        result = self.fetcher.get_next_trade_date_n("2024-01-01", 2)
        self.assertEqual(result, "2024-01-03")
        
    def test_get_previous_trade_date_n(self):
        """测试获取前n个交易日"""
        # 测试获取前一个交易日
        result = self.fetcher.get_previous_trade_date_n("2024-01-02", 1)
        self.assertEqual(result, "2023-12-29")
        
        # 测试获取前两个交易日
        result = self.fetcher.get_previous_trade_date_n("2024-01-02", 2)
        self.assertEqual(result, "2023-12-28")

    def test_fetch_get_future_contracts(self):
        """测试获取期货合约信息"""
        # 测试默认参数
        result = self.fetcher.fetch_get_future_contracts()
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)
        self.assertTrue(all(col in result.columns for col in ["ts_code", "symbol", "exchange"]))

        # 测试指定交易所
        dce_result = self.fetcher.fetch_get_future_contracts(exchange="DCE")
        self.assertTrue(all(row["exchange"] == "DCE" for _, row in dce_result.iterrows()))

        # 测试日期过滤
        date_result = self.fetcher.fetch_get_future_contracts(trade_date=20240102)
        self.assertIsNotNone(date_result)
        
        # 测试符号格式转换
        if len(result) > 0:
            sample_row = result.iloc[0]
            self.assertTrue("." in sample_row["ts_code"])
            symbol_parts = sample_row["ts_code"].split(".")
            self.assertEqual(len(symbol_parts), 2)

if __name__ == '__main__':
    unittest.main()
