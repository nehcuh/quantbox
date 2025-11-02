"""
配置系统模块

该模块提供统一的配置管理功能，支持：
- TOML 格式的配置文件加载
- 交易所信息管理
- 交易品种信息管理
- 交易时间配置
- 手续费和保证金配置

使用示例:
    from quantbox.config.config_loader import get_exchange_info

    # 获取上期所信息
    info = get_exchange_info("SHFE")
    print(info['name'])
"""

from .config_loader import (
    ConfigLoader,
    get_config_loader,
    get_exchange_info,
    get_instrument_info,
    get_trading_hours,
    get_fee_config,
    get_margin_config,
    get_data_source_mapping,
    list_futures_exchanges,
    list_stock_exchanges,
    list_instruments,
    validate_instrument,
    reload_configs,
)

__all__ = [
    'ConfigLoader',
    'get_config_loader',
    'get_exchange_info',
    'get_instrument_info',
    'get_trading_hours',
    'get_fee_config',
    'get_margin_config',
    'get_data_source_mapping',
    'list_futures_exchanges',
    'list_stock_exchanges',
    'list_instruments',
    'validate_instrument',
    'reload_configs',
]

__version__ = "1.0.0"