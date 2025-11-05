"""
数据适配器模块

提供统一的数据访问接口，支持多种数据源（MongoDB、Tushare、掘金等）
"""

from quantbox.adapters.base import IDataAdapter, BaseDataAdapter
from quantbox.adapters.local_adapter import LocalAdapter
from quantbox.adapters.ts_adapter import TSAdapter
from quantbox.adapters.gm_adapter import GMAdapter

__all__ = [
    "IDataAdapter",
    "BaseDataAdapter",
    "LocalAdapter",
    "TSAdapter",
    "GMAdapter",
]
