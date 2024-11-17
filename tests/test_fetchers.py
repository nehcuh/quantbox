import unittest
from unittest.mock import patch, MagicMock
from quantbox.fetchers.remote_fetch_tushare import TSFetcher
from quantbox.fetchers.remote_fetch_gm import GMFetcher
import pandas as pd
import datetime
from quantbox.util.tools import util_make_date_stamp

class TestTSFetcher(unittest.TestCase):
    """Test TSFetcher class"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a mock for tushare pro
        self.mock_pro = MagicMock()
        self.mock_pro.fut_holding = MagicMock()
        
        # Create a mock for LocalFetcher
        self.mock_local = MagicMock()
        self.mock_local.fetch_pre_trade_date = MagicMock()
        self.mock_local.fetch_future_contracts = MagicMock()
        
        # Create patchers
        self.patcher1 = patch('quantbox.fetchers.remote_fetch_tushare.TSPRO', self.mock_pro)
        self.patcher2 = patch('quantbox.fetchers.remote_fetch_tushare.LocalFetcher', return_value=self.mock_local)
        
        # Start patchers
        self.patcher1.start()
        self.patcher2.start()
        
        # Create TSFetcher instance
        self.fetcher = TSFetcher()

    def tearDown(self):
        """Tear down test fixtures"""
        self.patcher1.stop()
        self.patcher2.stop()

    def test_init(self):
        """Test TSFetcher initialization"""
        self.assertIsNotNone(self.fetcher)

    def test_fetch_get_holdings(self):
        """Test fetching future holdings data"""
        # Mock LocalFetcher responses
        self.mock_local.fetch_pre_trade_date.return_value = {
            'trade_date': '2024-01-01'
        }
        self.mock_local.fetch_future_contracts.return_value = pd.DataFrame({
            'symbol': ['IF2401']
        })
        
        # Mock tushare pro response
        mock_holdings = pd.DataFrame({
            'trade_date': ['20240101'],
            'symbol': ['IF2401'],
            'vol': [1000],
            'vol_chg': [100],
            'long_hld': [500],
            'short_hld': [500]
        })
        self.mock_pro.fut_holding.return_value = mock_holdings
        
        # Call function
        result = self.fetcher.fetch_get_holdings('IF2401')
        
        # Verify mock calls
        self.mock_local.fetch_pre_trade_date.assert_called_once()
        self.mock_pro.fut_holding.assert_called_once()
        
        # Verify result
        self.assertGreater(len(result), 0)
        self.assertTrue('trade_date' in result.columns)
        self.assertTrue('symbol' in result.columns)
        self.assertTrue('vol' in result.columns)

    def test_fetch_get_holdings_with_dates(self):
        """Test fetching future holdings data with date parameters"""
        # Mock tushare pro response
        mock_holdings = pd.DataFrame({
            'trade_date': ['20240101', '20240102'],
            'symbol': ['IF2401', 'IF2401'],
            'vol': [1000, 1200],
            'vol_chg': [100, 200],
            'long_hld': [500, 600],
            'short_hld': [500, 600]
        })
        self.mock_pro.fut_holding.return_value = mock_holdings
        
        # Call function with date parameters
        result = self.fetcher.fetch_get_holdings(
            symbols='IF2401',
            start_date='20240101',
            end_date='20240102'
        )
        
        # Verify result
        self.assertEqual(len(result), 10)  # 每个交易日有 5 个席位数据，共 2 天
        self.assertTrue('trade_date' in result.columns)
        self.assertTrue('symbol' in result.columns)
        self.assertTrue('vol' in result.columns)

class TestGMFetcher(unittest.TestCase):
    """Test GMFetcher class"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a mock for gm.api
        self.mock_api = MagicMock()
        self.mock_api.get_symbol_infos = MagicMock()
        self.mock_api.get_future_holdings = MagicMock()
        self.mock_api.get_trading_dates = MagicMock()
        
        # Create a mock for LocalFetcher
        self.mock_local = MagicMock()
        self.mock_local.fetch_pre_trade_date = MagicMock()
        self.mock_local.fetch_future_contracts = MagicMock()
        
        # Create patchers
        self.patcher1 = patch('gm.api.get_symbol_infos', self.mock_api.get_symbol_infos)
        self.patcher2 = patch('gm.api.fut_get_transaction_rankings', self.mock_api.get_future_holdings)
        self.patcher3 = patch('quantbox.fetchers.remote_fetch_gm.LocalFetcher', return_value=self.mock_local)
        self.patcher4 = patch('gm.api.get_trading_dates', self.mock_api.get_trading_dates)
        
        # Start patchers
        self.patcher1.start()
        self.patcher2.start()
        self.patcher3.start()
        self.patcher4.start()
        
        # Create GMFetcher instance
        self.fetcher = GMFetcher()

    def tearDown(self):
        """Tear down test fixtures"""
        self.patcher1.stop()
        self.patcher2.stop()
        self.patcher3.stop()
        self.patcher4.stop()

    def test_init(self):
        """Test GMFetcher initialization"""
        self.assertIsNotNone(self.fetcher)

    def test_fetch_get_holdings(self):
        """Test fetching future holdings data from GM"""
        # Mock get_future_holdings
        mock_holdings = pd.DataFrame({
            'symbol': ['CFFEX.IF2401'],
            'volume': [1000],
            'trade_date': ['20240101']
        })
        self.mock_api.get_future_holdings.return_value = mock_holdings
        
        # Call function
        result = self.fetcher.fetch_get_holdings('CFFEX.IF2401')
        
        # Verify mock was called
        self.mock_api.get_future_holdings.assert_called_once()
        
        # Verify result
        self.assertGreater(len(result), 0)
        self.assertTrue('symbol' in result.columns)
        self.assertTrue('volume' in result.columns)
        self.assertTrue('trade_date' in result.columns)

    def test_fetch_get_holdings_with_dates(self):
        """Test fetching future holdings data with date parameters"""
        # Mock get_future_holdings
        mock_holdings = pd.DataFrame({
            'symbol': ['CFFEX.IF2401', 'CFFEX.IF2401'],
            'volume': [1000, 1200],
            'trade_date': ['20240101', '20240102']
        })
        self.mock_api.get_future_holdings.return_value = mock_holdings
        
        # Call function with date parameters
        result = self.fetcher.fetch_get_holdings(
            symbols=['CFFEX.IF2401'],
            start_date='20240101',
            end_date='20240102'
        )
        
        # Verify mock was called
        self.mock_api.get_future_holdings.assert_called_once()
        
        # Verify result
        self.assertEqual(len(result), 2)
        self.assertTrue('symbol' in result.columns)
        self.assertTrue('volume' in result.columns)
        self.assertTrue('trade_date' in result.columns)

    def test_format_symbol(self):
        """Test symbol formatting for GM API"""
        test_cases = [
            ('IF2401', 'CFFEX.IF2401'),
            ('CFFEX.IF2401', 'CFFEX.IF2401'),
            ('cu2401', 'SHFE.cu2401'),
            ('SHFE.cu2401', 'SHFE.cu2401')
        ]
        
        for input_symbol, expected_output in test_cases:
            result = self.fetcher._format_symbol(input_symbol)
            self.assertEqual(result, expected_output)

    def test_fetch_get_future_contracts(self):
        """Test fetching future contracts information"""
        # 设置 mock 返回值
        mock_data = pd.DataFrame({
            'sec_id': ['SHFE.cu2401', 'SHFE.au2402'],
            'sec_name': ['沪铜2401', '黄金2402'],
            'listed_date': ['2023-01-01', '2023-02-01'],
            'delisted_date': ['2024-12-31', '2024-12-31']
        })
        self.mock_api.get_symbol_infos.return_value = mock_data
        
        # 调用函数
        result = self.fetcher.fetch_get_future_contracts(exchange='SHFE')
        
        # 验证 mock 调用
        self.mock_api.get_symbol_infos.assert_called_with(sec_type1=1040, exchanges='SHFE', df=True)
        
        # 验证结果结构
        self.assertGreater(len(result), 0)
        self.assertTrue('symbol' in result.columns)
        self.assertTrue('name' in result.columns)
        self.assertTrue('list_date' in result.columns)
        self.assertTrue('delist_date' in result.columns)
        self.assertTrue('list_datestamp' in result.columns)
        self.assertTrue('delist_datestamp' in result.columns)
        self.assertTrue('chinese_name' in result.columns)

    def test_fetch_get_future_contracts_with_spec_name(self):
        """Test fetching future contracts with specific name filter"""
        # Mock data
        mock_data = pd.DataFrame({
            'sec_id': ['SHFE.cu2401'],
            'sec_name': ['沪铜2401'],
            'listed_date': ['2023-01-01'],
            'delisted_date': ['2024-12-31']
        })
        self.mock_api.get_symbol_infos.return_value = mock_data
        
        # Call function with spec_name
        result = self.fetcher.fetch_get_future_contracts(
            exchange='SHFE',
            spec_name='沪铜'
        )
        
        # Verify mock was called
        self.mock_api.get_symbol_infos.assert_called_with(sec_type1=1040, exchanges='SHFE', df=True)
        
        # Verify result
        self.assertEqual(len(result), 1)
        self.assertTrue('symbol' in result.columns)
        self.assertTrue('name' in result.columns)
        self.assertTrue('list_date' in result.columns)
        self.assertTrue('delist_date' in result.columns)

    def test_fetch_get_future_contracts_with_cursor_date(self):
        """Test fetching future contracts with cursor date filter"""
        # Mock data
        mock_data = pd.DataFrame({
            'sec_id': ['SHFE.cu2401'],
            'sec_name': ['沪铜2401'],
            'listed_date': ['2023-01-01'],
            'delisted_date': ['2024-12-31']
        })
        self.mock_api.get_symbol_infos.return_value = mock_data
        
        # Call function with cursor_date
        result = self.fetcher.fetch_get_future_contracts(
            exchange='SHFE',
            cursor_date='20240101'
        )
        
        # Verify mock was called
        self.mock_api.get_symbol_infos.assert_called_with(sec_type1=1040, exchanges='SHFE', df=True)
        
        # Verify result
        self.assertGreater(len(result), 0)
        self.assertTrue('symbol' in result.columns)
        self.assertTrue('name' in result.columns)
        self.assertTrue('list_date' in result.columns)
        self.assertTrue('delist_date' in result.columns)

if __name__ == '__main__':
    unittest.main()
