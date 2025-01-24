"""Test trade date utils"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock

from quantbox.utils.trade_date import TradeDateUtils
from quantbox.data.fetcher.tushare_fetcher import TushareFetcher


class TestTradeDateUtils(unittest.TestCase):
    """Test trade date utils"""
    
    def setUp(self):
        """Set up test fixtures"""
        # 创建一个 mock 的 data_fetcher
        self.mock_fetcher = Mock()
        self.utils = TradeDateUtils(self.mock_fetcher)
        
        # 设置当前日期为 2024-01-24
        self.current_date = datetime(2024, 1, 24)
        
    def test_get_previous_trade_date_with_default_date(self):
        """测试获取前一个交易日（使用默认日期）"""
        # 设置 mock 返回值
        self.mock_fetcher.get_previous_trade_date.return_value = 20240123
        
        # 测试获取前一个交易日
        result = self.utils.get_previous_trade_date()
        self.assertEqual(result, 20240123)
        
        # 验证 mock 被正确调用
        self.mock_fetcher.get_previous_trade_date.assert_called_with(
            date=self.current_date.strftime("%Y-%m-%d"),
            n=1,
            include_input_date=False,
            exchange="SSE",
            start_date=None,
            end_date=None
        )
        
    def test_get_previous_trade_date_with_specified_date(self):
        """测试获取前一个交易日（使用指定日期）"""
        # 设置 mock 返回值
        self.mock_fetcher.get_previous_trade_date.return_value = 20240123
        
        # 测试获取前一个交易日
        result = self.utils.get_previous_trade_date("2024-01-24")
        self.assertEqual(result, 20240123)
        
        # 验证 mock 被正确调用
        self.mock_fetcher.get_previous_trade_date.assert_called_with(
            date="2024-01-24",
            n=1,
            include_input_date=False,
            exchange="SSE",
            start_date=None,
            end_date=None
        )
        
    def test_get_previous_trade_date_with_n(self):
        """测试获取前N个交易日"""
        # 设置 mock 返回值
        self.mock_fetcher.get_previous_trade_date.return_value = 20240119
        
        # 测试获取前N个交易日
        result = self.utils.get_previous_trade_date("2024-01-24", n=3)
        self.assertEqual(result, 20240119)
        
        # 验证 mock 被正确调用
        self.mock_fetcher.get_previous_trade_date.assert_called_with(
            date="2024-01-24",
            n=3,
            include_input_date=False,
            exchange="SSE",
            start_date=None,
            end_date=None
        )
        
    def test_get_next_trade_date_with_default_date(self):
        """测试获取后一个交易日（使用默认日期）"""
        # 设置 mock 返回值
        self.mock_fetcher.get_next_trade_date.return_value = 20240125
        
        # 测试获取后一个交易日
        result = self.utils.get_next_trade_date()
        self.assertEqual(result, 20240125)
        
        # 验证 mock 被正确调用
        self.mock_fetcher.get_next_trade_date.assert_called_with(
            date=self.current_date.strftime("%Y-%m-%d"),
            n=1,
            include_input_date=False,
            exchange="SSE",
            start_date=None,
            end_date=None
        )
        
    def test_get_next_trade_date_with_specified_date(self):
        """测试获取后一个交易日（使用指定日期）"""
        # 设置 mock 返回值
        self.mock_fetcher.get_next_trade_date.return_value = 20240125
        
        # 测试获取后一个交易日
        result = self.utils.get_next_trade_date("2024-01-24")
        self.assertEqual(result, 20240125)
        
        # 验证 mock 被正确调用
        self.mock_fetcher.get_next_trade_date.assert_called_with(
            date="2024-01-24",
            n=1,
            include_input_date=False,
            exchange="SSE",
            start_date=None,
            end_date=None
        )
        
    def test_get_next_trade_date_with_n(self):
        """测试获取后N个交易日"""
        # 设置 mock 返回值
        self.mock_fetcher.get_next_trade_date.return_value = 20240129
        
        # 测试获取后N个交易日
        result = self.utils.get_next_trade_date("2024-01-24", n=3)
        self.assertEqual(result, 20240129)
        
        # 验证 mock 被正确调用
        self.mock_fetcher.get_next_trade_date.assert_called_with(
            date="2024-01-24",
            n=3,
            include_input_date=False,
            exchange="SSE",
            start_date=None,
            end_date=None
        )
        
    def test_is_trade_date_with_default_date(self):
        """测试判断是否为交易日（使用默认日期）"""
        # 设置 mock 返回值
        self.mock_fetcher.is_trade_date.return_value = True
        
        # 测试判断是否为交易日
        result = self.utils.is_trade_date()
        self.assertTrue(result)
        
        # 验证 mock 被正确调用
        self.mock_fetcher.is_trade_date.assert_called_with(
            date=self.current_date.strftime("%Y-%m-%d"),
            exchange="SSE"
        )
        
    def test_is_trade_date_with_specified_date(self):
        """测试判断是否为交易日（使用指定日期）"""
        # 设置 mock 返回值
        self.mock_fetcher.is_trade_date.return_value = True
        
        # 测试判断是否为交易日
        result = self.utils.is_trade_date("2024-01-24")
        self.assertTrue(result)
        
        # 验证 mock 被正确调用
        self.mock_fetcher.is_trade_date.assert_called_with(
            date="2024-01-24",
            exchange="SSE"
        )
        
    def test_batch_is_trade_date(self):
        """测试批量判断是否为交易日"""
        # 设置 mock 返回值
        self.mock_fetcher.batch_is_trade_date.return_value = {
            "2024-01-24": True,
            "2024-01-25": True,
            "2024-01-27": False  # 周六
        }
        
        # 测试批量判断是否为交易日
        dates = ["2024-01-24", "2024-01-25", "2024-01-27"]
        result = self.utils.batch_is_trade_date(dates)
        self.assertEqual(result, {
            "2024-01-24": True,
            "2024-01-25": True,
            "2024-01-27": False
        })
        
        # 验证 mock 被正确调用
        self.mock_fetcher.batch_is_trade_date.assert_called_with(
            dates=dates,
            exchange="SSE"
        )
        
    def test_default_fetcher(self):
        """测试默认使用 TushareFetcher"""
        # 创建一个不指定 fetcher 的实例
        utils = TradeDateUtils()
        
        # 验证使用了 TushareFetcher
        self.assertIsInstance(utils._fetcher, TushareFetcher)


if __name__ == '__main__':
    unittest.main()
