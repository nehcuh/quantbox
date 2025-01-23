from typing import Dict, Any, Optional
from dataclasses import dataclass
from .exchange_config import ExchangeConfig


@dataclass
class TradeConfig:
    """交易配置"""
    timezone: str                                  # 默认时区
    default_exchange: str                          # 默认交易所
    exchanges: Dict[str, ExchangeConfig]           # 交易所配置字典
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "timezone": self.timezone,
            "default_exchange": self.default_exchange,
            "exchanges": {
                code: exchange.to_dict()
                for code, exchange in self.exchanges.items()
            }
        }
    
    def get_exchange(self, code: Optional[str] = None) -> ExchangeConfig:
        """获取交易所配置
        
        Args:
            code: 交易所代码，如果为None则返回默认交易所配置
            
        Returns:
            ExchangeConfig: 交易所配置
            
        Raises:
            KeyError: 交易所代码不存在
        """
        if code is None:
            code = self.default_exchange
        
        if code not in self.exchanges:
            raise KeyError(f"交易所代码不存在: {code}")
            
        return self.exchanges[code]
    
    def calculate_commission(
        self,
        price: float,
        volume: int,
        exchange_code: Optional[str] = None,
        is_open: bool = True,
        is_close_today: bool = False
    ) -> float:
        """计算手续费
        
        Args:
            price: 成交价格
            volume: 成交数量
            exchange_code: 交易所代码，如果为None则使用默认交易所
            is_open: 是否开仓
            is_close_today: 是否平今
            
        Returns:
            float: 手续费
        """
        exchange = self.get_exchange(exchange_code)
        return exchange.calculate_commission(
            price=price,
            volume=volume,
            is_open=is_open,
            is_close_today=is_close_today
        )
    
    def calculate_slippage(
        self,
        price: float,
        volume: int,
        exchange_code: Optional[str] = None
    ) -> float:
        """计算滑点成本
        
        Args:
            price: 目标价格
            volume: 成交数量
            exchange_code: 交易所代码，如果为None则使用默认交易所
            
        Returns:
            float: 滑点成本
        """
        exchange = self.get_exchange(exchange_code)
        return exchange.calculate_slippage(price=price, volume=volume)
