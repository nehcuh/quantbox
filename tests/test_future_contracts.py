import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from quantbox.data.fetcher.tushare_fetcher import TushareFetcher
from quantbox.core.config import ConfigLoader, ApiConfig

class TestFutureContracts(unittest.TestCase):
    def setUp(self):
        # Mock the config
        mock_config = ApiConfig(tushare_token="test_token")
        with patch.object(ConfigLoader, 'get_api_config', return_value=mock_config):
            self.fetcher = TushareFetcher()

    def test_fetch_get_future_contracts_empty_result(self):
        """测试返回空数据的情况"""
        with patch.object(self.fetcher, 'pro') as mock_pro:
            mock_pro.fut_basic.return_value = pd.DataFrame()
            result = self.fetcher.fetch_get_future_contracts(exchange="DCE")
            
            # 验证返回的空DataFrame包含所有必要的列
            expected_columns = ["qbcode", "symbol", "name", "chinese_name", "list_date", 
                              "delist_date", "list_datestamp", "delist_datestamp", "exchange"]
            self.assertEqual(list(result.columns), expected_columns)
            self.assertTrue(result.empty)

    def test_fetch_get_future_contracts_normal_case(self):
        """测试正常数据处理"""
        mock_data = pd.DataFrame({
            'ts_code': ['M2501.DCE', 'P2501.DCE'],
            'symbol': ['M2501', 'P2501'],
            'name': ['豆粕2501', '棕榈油2501'],
            'list_date': ['20240101', '20240101'],
            'delist_date': ['20251231', '20251231']
        })

        with patch.object(self.fetcher, 'pro') as mock_pro:
            mock_pro.fut_basic.return_value = mock_data
            result = self.fetcher.fetch_get_future_contracts(exchange="DCE")
            
            # 验证基本数据处理
            self.assertEqual(len(result), 2)
            
            # 验证 qbcode 格式转换（从 symbol.exchange 到 exchange.symbol）
            self.assertEqual(result.iloc[0]['qbcode'], 'DCE.M2501')
            self.assertEqual(result.iloc[1]['qbcode'], 'DCE.P2501')
            
            # 验证日期处理
            self.assertEqual(result.iloc[0]['list_date'], 20240101)
            self.assertEqual(result.iloc[0]['delist_date'], 20251231)
            
            # 验证中文名称提取
            self.assertEqual(result.iloc[0]['chinese_name'], '豆粕')
            self.assertEqual(result.iloc[1]['chinese_name'], '棕榈油')

    def test_fetch_get_future_contracts_case_sensitivity(self):
        """测试不同交易所的大小写处理"""
        test_cases = [
            ('SHFE', 'au2406.SHFE', 'au2406'),  # 上期所小写
            ('CZCE', 'CF401.CZCE', 'CF401'),    # 郑商所大写
            ('DCE', 'm2405.DCE', 'm2405'),      # 大商所小写
            ('CFFEX', 'IF2403.CFFEX', 'IF2403'), # 中金所大写
            ('INE', 'sc2403.INE', 'sc2403'),    # 能源所小写
        ]

        for exchange, ts_code, symbol in test_cases:
            mock_data = pd.DataFrame({
                'ts_code': [ts_code],
                'symbol': [symbol],
                'name': ['Test' + symbol],
                'list_date': ['20240101'],
                'delist_date': ['20241231']
            })

            with patch.object(self.fetcher, 'pro') as mock_pro:
                mock_pro.fut_basic.return_value = mock_data
                result = self.fetcher.fetch_get_future_contracts(exchange=exchange)
                
                # 验证 symbol 大小写
                if exchange in ['CZCE', 'CFFEX']:
                    self.assertEqual(result.iloc[0]['symbol'], symbol.upper())
                else:
                    self.assertEqual(result.iloc[0]['symbol'], symbol.lower())

    def test_fetch_get_future_contracts_with_spec_name(self):
        """测试按品种名称过滤"""
        mock_data = pd.DataFrame({
            'ts_code': ['M2501.DCE', 'P2501.DCE', 'Y2501.DCE'],
            'symbol': ['M2501', 'P2501', 'Y2501'],
            'name': ['豆粕2501', '棕榈油2501', '豆油2501'],
            'list_date': ['20240101'] * 3,
            'delist_date': ['20251231'] * 3
        })

        with patch.object(self.fetcher, 'pro') as mock_pro:
            mock_pro.fut_basic.return_value = mock_data
            
            # 测试单个品种过滤
            result = self.fetcher.fetch_get_future_contracts(exchange="DCE", spec_name="豆粕")
            self.assertEqual(len(result), 1)
            self.assertEqual(result.iloc[0]['chinese_name'], '豆粕')
            
            # 测试多个品种过滤
            result = self.fetcher.fetch_get_future_contracts(
                exchange="DCE", 
                spec_name=["豆粕", "棕榈油"]
            )
            self.assertEqual(len(result), 2)
            self.assertSetEqual(
                set(result['chinese_name'].tolist()),
                {'豆粕', '棕榈油'}
            )

    def test_fetch_get_future_contracts_with_cursor_date(self):
        """测试按日期过滤"""
        mock_data = pd.DataFrame({
            'ts_code': ['M2501.DCE', 'M2502.DCE'],
            'symbol': ['M2501', 'M2502'],
            'name': ['豆粕2501', '豆粕2502'],
            'list_date': ['20240101', '20240201'],
            'delist_date': ['20251231', '20260131']
        })

        with patch.object(self.fetcher, 'pro') as mock_pro:
            mock_pro.fut_basic.return_value = mock_data
            
            # 测试整数日期
            result = self.fetcher.fetch_get_future_contracts(
                exchange="DCE", 
                cursor_date=20240115
            )
            self.assertEqual(len(result), 1)
            self.assertEqual(result.iloc[0]['symbol'], 'm2501')
            
            # 测试字符串日期
            result = self.fetcher.fetch_get_future_contracts(
                exchange="DCE", 
                cursor_date='2024-02-15'
            )
            self.assertEqual(len(result), 2)

if __name__ == '__main__':
    unittest.main()
