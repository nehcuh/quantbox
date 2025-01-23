from dataclasses import dataclass
from typing import Dict, Any, List
from datetime import time
from enum import Enum


class CommissionType(str, Enum):
    """手续费类型"""
    RATE = "rate"    # 费率
    FIXED = "fixed"  # 固定费用


class SlippageType(str, Enum):
    """滑点类型"""
    RATE = "rate"  # 比率
    TICK = "tick"  # 跳数


@dataclass
class ExchangeConfig:
    """交易所配置"""
    name: str                    # 交易所名称
    code: str                    # 交易所代码
    timezone: str               # 交易所时区
    open_time: List[str]        # 开市时间列表
    close_time: List[str]       # 收市时间列表
    trading_days: str           # 交易日（1-7，逗号分隔）
    commission_type: str        # 手续费类型
    commission_open: float      # 开仓手续费
    commission_close: float     # 平仓手续费
    commission_close_today: float  # 平今手续费
    commission_min: float       # 最小手续费
    slippage_type: str         # 滑点类型
    slippage_value: float      # 滑点值

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "code": self.code,
            "timezone": self.timezone,
            "open_time": self.open_time,
            "close_time": self.close_time,
            "trading_days": self.trading_days,
            "commission_type": self.commission_type,
            "commission_open": self.commission_open,
            "commission_close": self.commission_close,
            "commission_close_today": self.commission_close_today,
            "commission_min": self.commission_min,
            "slippage_type": self.slippage_type,
            "slippage_value": self.slippage_value
        }

    def calculate_commission(
        self,
        price: float,
        volume: int,
        is_open: bool = True,
        is_close_today: bool = False
    ) -> float:
        """计算手续费
        
        Args:
            price: 成交价格
            volume: 成交数量
            is_open: 是否开仓
            is_close_today: 是否平今
            
        Returns:
            float: 手续费
        """
        # 获取手续费率或固定手续费
        if is_open:
            commission = self.commission_open
        elif is_close_today:
            commission = self.commission_close_today
        else:
            commission = self.commission_close
            
        # 计算手续费
        if self.commission_type == CommissionType.RATE:
            fee = price * volume * commission
            # 检查最小手续费
            if fee < self.commission_min:
                fee = self.commission_min
        else:  # CommissionType.FIXED
            fee = commission * volume
            
        return fee
    
    def calculate_slippage(self, price: float, volume: int) -> float:
        """计算滑点成本
        
        Args:
            price: 目标价格
            volume: 成交数量
            
        Returns:
            float: 滑点成本
        """
        if self.slippage_type == SlippageType.RATE:
            return price * self.slippage_value * volume
        else:  # SlippageType.TICK
            return self.slippage_value * volume
