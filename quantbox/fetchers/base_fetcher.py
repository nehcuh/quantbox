"""
Base fetcher module that defines the interface for all fetchers.
"""
from typing import Union, List, Optional
import datetime
import pandas as pd

from quantbox.util.basic import DATABASE, DEFAULT_START, EXCHANGES, FUTURE_EXCHANGES, STOCK_EXCHANGES


class BaseFetcher:
    """
    Base class for all data fetchers.
    
    This class defines the common interface that all fetchers should implement,
    and provides some basic functionality shared by all fetchers.
    """
    def __init__(self):
        self.exchanges = EXCHANGES
        self.stock_exchanges = STOCK_EXCHANGES
        self.future_exchanges = FUTURE_EXCHANGES
        self.client = DATABASE
        self.default_start = DEFAULT_START

    def fetch_trade_dates(
        self,
        exchanges: Union[str, List[str], None] = None,
        start_date: Union[str, int, datetime.date, None] = None,
        end_date: Union[str, int, datetime.date, None] = None,
    ) -> pd.DataFrame:
        """
        Fetch trading calendar for the specified exchanges and date range.

        Args:
            exchanges: Exchange(s) to fetch trading dates for
            start_date: Start date of the range
            end_date: End date of the range

        Returns:
            DataFrame containing trading dates
        """
        raise NotImplementedError("Subclasses must implement fetch_trade_dates")

    def fetch_future_contracts(
        self,
        symbol: Optional[str] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        spec_name: Optional[str] = None,
        cursor_date: Optional[Union[str, int, datetime.date]] = None,
        fields: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Fetch future contract information.

        Args:
            symbol: Future contract symbol
            exchanges: Exchange(s) to fetch contracts from
            spec_name: Specific contract name
            cursor_date: Reference date
            fields: Fields to fetch

        Returns:
            DataFrame containing future contract information
        """
        raise NotImplementedError("Subclasses must implement fetch_future_contracts")
