import unittest
from unittest.mock import patch, MagicMock
from quantbox.fetchers.remote_fetch_tushare import TSFetcher
from quantbox.fetchers.remote_fetch_gm import GMFetcher
import pandas as pd
import datetime

class TestTSFetcher(unittest.TestCase):
    @patch('tushare.pro_api')
    def setUp(self, mock_pro_api):
        self.mock_api = MagicMock()
        mock_pro_api.return_value = self.mock_api
        self.fetcher = TSFetcher()

    def test_init(self):
        """Test TSFetcher initialization"""
        self.assertIsNotNone(self.fetcher)
        self.assertIsNotNone(self.fetcher.pro)

    def test_fetch_get_holdings(self):
        """Test fetching future holdings data"""
        # Mock data
        mock_data = pd.DataFrame({
            'trade_date': ['20240101'],
            'symbol': ['IF2401'],
            'vol': [100],
            'vol_chg': [10],
            'long_hld': [50],
            'short_hld': [50]
        })
        self.mock_api.fut_holding.return_value = mock_data

        # Test with default parameters
        result = self.fetcher.fetch_get_holdings('IF2401')
        self.assertIsInstance(result, pd.DataFrame)
        self.mock_api.fut_holding.assert_called_once()

        # Verify the columns are correct
        expected_columns = ['trade_date', 'symbol', 'vol', 'vol_chg', 'long_hld', 'short_hld']
        self.assertTrue(all(col in result.columns for col in expected_columns))

    def test_fetch_get_holdings_with_dates(self):
        """Test fetching future holdings data with date parameters"""
        mock_data = pd.DataFrame({
            'trade_date': ['20240101', '20240102'],
            'symbol': ['IF2401', 'IF2401'],
            'vol': [100, 110],
            'vol_chg': [10, 10],
            'long_hld': [50, 55],
            'short_hld': [50, 55]
        })
        self.mock_api.fut_holding.return_value = mock_data

        start_date = datetime.date(2024, 1, 1)
        end_date = datetime.date(2024, 1, 2)
        result = self.fetcher.fetch_get_holdings(
            symbols='IF2401',
            start_date=start_date,
            end_date=end_date
        )
        
        self.assertEqual(len(result), 2)
        self.mock_api.fut_holding.assert_called_with(
            ts_code='IF2401',
            start_date='20240101',
            end_date='20240102'
        )

class TestGMFetcher(unittest.TestCase):
    @patch('gm.api')
    def setUp(self, mock_gm_api):
        self.mock_api = mock_gm_api
        self.fetcher = GMFetcher()

    def test_init(self):
        """Test GMFetcher initialization"""
        self.assertIsNotNone(self.fetcher)

    def test_fetch_get_holdings(self):
        """Test fetching future holdings data from GM"""
        # Mock data
        mock_data = pd.DataFrame({
            'date': [pd.Timestamp('2024-01-01')],
            'symbol': ['CFFEX.IF2401'],
            'volume': [100],
            'volume_change': [10],
            'long_position': [50],
            'short_position': [50]
        })
        self.mock_api.get_future_holdings.return_value = mock_data

        # Test with default parameters
        result = self.fetcher.fetch_get_holdings('CFFEX.IF2401')
        self.assertIsInstance(result, pd.DataFrame)
        self.mock_api.get_future_holdings.assert_called_once()

        # Verify column mapping
        expected_columns = ['trade_date', 'symbol', 'vol', 'vol_chg', 'long_hld', 'short_hld']
        self.assertTrue(all(col in result.columns for col in expected_columns))

    def test_fetch_get_holdings_with_dates(self):
        """Test fetching future holdings data with date parameters"""
        mock_data = pd.DataFrame({
            'date': [pd.Timestamp('2024-01-01'), pd.Timestamp('2024-01-02')],
            'symbol': ['CFFEX.IF2401', 'CFFEX.IF2401'],
            'volume': [100, 110],
            'volume_change': [10, 10],
            'long_position': [50, 55],
            'short_position': [50, 55]
        })
        self.mock_api.get_future_holdings.return_value = mock_data

        start_date = datetime.date(2024, 1, 1)
        end_date = datetime.date(2024, 1, 2)
        result = self.fetcher.fetch_get_holdings(
            symbols='CFFEX.IF2401',
            start_date=start_date,
            end_date=end_date
        )
        
        self.assertEqual(len(result), 2)
        self.mock_api.get_future_holdings.assert_called_with(
            symbols='CFFEX.IF2401',
            start_date=start_date,
            end_date=end_date
        )

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

if __name__ == '__main__':
    unittest.main()
