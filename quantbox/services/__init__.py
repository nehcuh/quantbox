"""
Quantbox Services

服务层接口，提供统一的数据查询和保存服务
"""

from quantbox.services.market_data_service import MarketDataService
from quantbox.services.data_saver_service import DataSaverService, SaveResult

# 按需导入异步服务
__all_services = [
    "MarketDataService",
    "DataSaverService",
    "SaveResult",
]

try:
    from quantbox.services.async_market_data_service import AsyncMarketDataService
    __all_services.append("AsyncMarketDataService")
except ImportError:
    pass

try:
    from quantbox.services.async_data_saver_service import AsyncDataSaverService
    __all_services.append("AsyncDataSaverService")
except ImportError:
    pass

__all__ = __all_services
