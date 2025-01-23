from enum import Enum
from typing import List


class ExchangeType(str, Enum):
    """交易所类型"""
    STOCK = "stock"      # 股票
    FUTURES = "futures"  # 期货
    ALL = "all"         # 所有


class ExchangeCodes:
    """交易所代码管理"""
    
    # 股票交易所
    STOCK_EXCHANGES = [
        "SSE",   # 上海证券交易所
        "SZSE",  # 深圳证券交易所
    ]
    
    # 期货交易所
    FUTURES_EXCHANGES = [
        "SHFE",  # 上海期货交易所
        "DCE",   # 大连商品交易所
        "CZCE",  # 郑州商品交易所
        "CFFEX", # 中国金融期货交易所
        "INE",   # 上海国际能源交易中心
        "GFEX",  # 广州期货交易所
    ]
    
    @classmethod
    def get_exchanges(cls, exchange_type: ExchangeType = ExchangeType.ALL) -> List[str]:
        """获取交易所代码列表
        
        Args:
            exchange_type: 交易所类型，默认为全部
            
        Returns:
            List[str]: 交易所代码列表
        """
        if exchange_type == ExchangeType.STOCK:
            return cls.STOCK_EXCHANGES
        elif exchange_type == ExchangeType.FUTURES:
            return cls.FUTURES_EXCHANGES
        else:  # ExchangeType.ALL
            return cls.STOCK_EXCHANGES + cls.FUTURES_EXCHANGES
