import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import datetime
from quantbox.savers.data_saver import TSSaver
from quantbox.fetchers.remote_fetch_tushare import TSFetcher
from quantbox.fetchers.remote_fetch_gm import GMFetcher
from pymongo.collection import Collection

class TestTSSaver(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.mock_collection = MagicMock(spec=Collection)
        self.test_data = pd.DataFrame({
            'trade_date': ['20240101'],
            'symbol': ['IF2401'],
            'vol': [100],
            'vol_chg': [10],
            'long_hld': [50],
            'short_hld': [50]
        })

    @patch('quantbox.fetchers.remote_fetch_tushare.TSFetcher')
    def test_save_holdings_tushare(self, mock_ts_fetcher):
        """Test saving future holdings data using Tushare engine"""
        # Setup mock
        mock_instance = mock_ts_fetcher.return_value
        mock_instance.fetch_get_holdings.return_value = self.test_data

        # Create saver instance
        saver = TSSaver()
        saver.ts_fetcher = mock_instance

        # Test saving data
        saver.save_holdings(
            symbol='IF2401',
            collection=self.mock_collection
        )

        # Verify the fetcher was called correctly
        mock_instance.fetch_get_holdings.assert_called_once_with(
            symbols='IF2401',
            start_date=None,
            end_date=None
        )

        # Verify data was saved to MongoDB
        self.mock_collection.insert_many.assert_called_once()
        inserted_data = self.mock_collection.insert_many.call_args[0][0]
        self.assertEqual(len(inserted_data), 1)
        self.assertEqual(inserted_data[0]['symbol'], 'IF2401')

    @patch('quantbox.fetchers.remote_fetch_gm.GMFetcher')
    def test_save_holdings_gm(self, mock_gm_fetcher):
        """Test saving future holdings data using GM engine"""
        # Setup mock
        mock_instance = mock_gm_fetcher.return_value
        gm_data = pd.DataFrame({
            'date': [pd.Timestamp('2024-01-01')],
            'symbol': ['CFFEX.IF2401'],
            'volume': [100],
            'volume_change': [10],
            'long_position': [50],
            'short_position': [50]
        })
        mock_instance.fetch_get_holdings.return_value = gm_data

        # Create saver instance
        saver = TSSaver()
        saver.gm_fetcher = mock_instance

        # Test saving data
        saver.save_holdings(
            symbol='IF2401',
            collection=self.mock_collection,
            engine='gm'
        )

        # Verify the fetcher was called correctly
        mock_instance.fetch_get_holdings.assert_called_once_with(
            symbols='CFFEX.IF2401',
            start_date=None,
            end_date=None
        )

        # Verify data was saved to MongoDB
        self.mock_collection.insert_many.assert_called_once()

    def test_save_holdings_invalid_engine(self):
        """Test saving future holdings data with invalid engine"""
        saver = TSSaver()
        with self.assertRaises(ValueError):
            saver.save_holdings(
                symbol='IF2401',
                collection=self.mock_collection,
                engine='invalid_engine'
            )

    @patch('quantbox.fetchers.remote_fetch_tushare.TSFetcher')
    def test_save_holdings_with_dates(self, mock_ts_fetcher):
        """Test saving future holdings data with date range"""
        # Setup mock
        mock_instance = mock_ts_fetcher.return_value
        mock_instance.fetch_get_holdings.return_value = self.test_data

        # Create saver instance
        saver = TSSaver()
        saver.ts_fetcher = mock_instance

        # Test saving data with date range
        start_date = datetime.date(2024, 1, 1)
        end_date = datetime.date(2024, 1, 2)
        saver.save_holdings(
            symbol='IF2401',
            collection=self.mock_collection,
            start_date=start_date,
            end_date=end_date
        )

        # Verify the fetcher was called with correct dates
        mock_instance.fetch_get_holdings.assert_called_once_with(
            symbols='IF2401',
            start_date=start_date,
            end_date=end_date
        )

    @patch('quantbox.fetchers.remote_fetch_tushare.TSFetcher')
    def test_save_holdings_empty_data(self, mock_ts_fetcher):
        """Test handling empty data from fetcher"""
        # Setup mock to return empty DataFrame
        mock_instance = mock_ts_fetcher.return_value
        mock_instance.fetch_get_holdings.return_value = pd.DataFrame()

        # Create saver instance
        saver = TSSaver()
        saver.ts_fetcher = mock_instance

        # Test saving empty data
        saver.save_holdings(
            symbol='IF2401',
            collection=self.mock_collection
        )

        # Verify no data was saved
        self.mock_collection.insert_many.assert_not_called()

if __name__ == '__main__':
    unittest.main()
