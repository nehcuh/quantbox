try:
    from quantbox.fetchers.fetcher_goldminer import GMFetcher
except ImportError:
    GMFetcher = None

try:
    from quantbox.fetchers.fetcher_tushare import TSFetcher
except ImportError:
    TSFetcher = None

from quantbox.fetchers.remote_fetcher import RemoteFetcher

__all__ = ['RemoteFetcher', 'GMFetcher', 'TSFetcher']
