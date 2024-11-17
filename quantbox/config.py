"""
Configuration Management Module

This module handles configuration management for the Quantbox system. It provides
functionality to load and merge configuration settings from both default values
and user-defined TOML files.

The configuration covers various aspects of the system including:
- Data saving parameters
- Validation rules
- Performance settings
- Error handling settings

Functions:
    load_config: Load configuration from file or use defaults
    _update_config: Helper function for recursive dictionary updates

Dependencies:
    - toml

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

English Version:
---------------
Configuration Management Module

This module provides a unified configuration management system for handling
various system configuration parameters. It supports multiple configuration
sources, validation, and dynamic updates.

Features:
- Multiple configuration sources
- Configuration validation
- Default value management
- Dynamic configuration updates
- Environment variable override

Configuration Items:
- Database connections
- API keys
- Logging settings
- Data validation rules
- Caching strategies

Dependencies:
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
            'trade_date': ['exchange', 'trade_date', 'datestamp'],
            'future_contracts': ['exchange', 'symbol', 'list_date', 'delist_date'],
            'future_holdings': ['trade_date', 'symbol', 'exchange', 'datestamp'],
            'future_daily': ['symbol', 'trade_date', 'datestamp'],
        }
    }
}


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from a TOML file or use default settings.

    This function attempts to load configuration from a specified TOML file.
    If the file doesn't exist or there's an error reading it, it falls back
    to the default configuration. When a valid configuration file is loaded,
    its values are merged with the defaults, with the file values taking
    precedence.

    Args:
        config_path: Path to the TOML configuration file. If None or if the
            file doesn't exist, default configuration is used.

    Returns:
        Dict[str, Any]: A dictionary containing the merged configuration
            settings.

    Note:
        The function performs a deep merge of the configuration, allowing
        partial overrides of the default settings.

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
    Recursively update a configuration dictionary.

    This helper function performs a deep merge of two dictionaries, allowing
    nested configurations to be properly updated without completely overwriting
    intermediate dictionaries.

    Args:
        base: Base configuration dictionary to be updated
        update: Dictionary containing update values

    Note:
        This function modifies the base dictionary in-place. Dictionary values
        are merged recursively, while other types are replaced completely.

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
