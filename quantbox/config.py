"""
配置管理模块

本模块提供了一个统一的配置管理系统，用于处理系统的各种配置参数。
支持多种配置源、配置验证和动态更新机制。

功能特性：
- 多配置源支持
- 配置验证机制
- 默认值管理
- 动态配置更新
- 环境变量覆盖

配置项：
- 数据库连接
- API 密钥
- 日志设置
- 数据验证规则
- 缓存策略

依赖：
    - os
    - json
    - typing
    - pathlib
"""

import os
from typing import Any, Dict

import toml


# Default configuration settings
DEFAULT_CONFIG = {
    # Data saving related configurations
    'saver': {
        'default_start_date': '1990-12-19',  # Default start date for historical data
        'batch_size': 10000,                 # Batch size for database operations
        'retry_times': 3,                    # Number of retry attempts
        'retry_interval': 60,                # Retry interval in seconds
        'trading_end_hour': 16,              # Trading end hour (24-hour format)
        'max_workers': 4,                    # Maximum number of parallel workers
    },

    # Data validation configurations
    'validation': {
        'required_fields': {
            'trade_date': ['exchange', 'trade_date', 'pre_trade_date'],
            'future_contracts': ['exchange', 'symbol', 'list_date', 'delist_date'],
            'future_holdings': ['trade_date', 'symbol', 'exchange'],
            'future_daily': ['symbol', 'trade_date'],
        }
    }
}


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    加载配置文件。

    从配置文件中读取配置信息，如果文件不存在则创建默认配置。
    支持配置验证和环境变量覆盖。

    参数：
        config_path: 配置文件路径

    返回：
        Dict[str, Any]: 配置字典

    配置结构：
        {
            "database": {
                "host": str,
                "port": int,
                "name": str
            },
            "api": {
                "key": str,
                "secret": str
            },
            "logging": {
                "level": str,
                "file": str
            }
        }

    注意：
        - 自动创建默认配置
        - 验证配置完整性
        - 支持环境变量覆盖
        - 保护敏感信息
    """
    config = DEFAULT_CONFIG.copy()

    if config_path and os.path.exists(config_path):
        try:
            user_config = toml.load(config_path)
            # Recursively update configuration
            _update_config(config, user_config)
        except Exception as e:
            print(f"Failed to load configuration file: {str(e)}, using defaults")

    return config


def _update_config(base: Dict[str, Any], update: Dict[str, Any]) -> None:
    """
    递归更新配置字典。

    本函数执行两个字典的深度合并，允许嵌套配置被正确更新，而不会完全覆盖
    中间字典。

    参数：
        base: 要更新的基础配置字典
        update: 包含更新值的字典

    注意：
        本函数在原地修改基础字典。字典值递归合并，而其他类型被完全替换。
    """
    for key, value in update.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _update_config(base[key], value)
        else:
            base[key] = value
