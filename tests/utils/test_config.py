"""Test configuration manager"""

import os
from typing import Optional, Union, Type, TypeVar
from pathlib import Path

from quantbox.data.fetcher.base import DataFetcher
from quantbox.data.database.base import DatabaseManager
from tests.utils.mock_db import MockDatabaseManager
from tests.utils.mock_fetcher import MockDataFetcher

T = TypeVar('T')


class TestConfig:
    """Test configuration manager"""

    @staticmethod
    def is_ci() -> bool:
        """Check if running in CI environment"""
        return bool(os.getenv('CI') or os.getenv('GITHUB_ACTIONS'))

    @staticmethod
    def get_config_path() -> Optional[str]:
        """Get configuration file path"""
        if TestConfig.is_ci():
            return None
            
        # 按优先级查找配置文件
        search_paths = [
            Path.home() / '.quantbox/config.toml',  # 用户目录
            Path.cwd() / 'config.toml',  # 当前目录
            Path.cwd() / 'example.config.toml',  # 示例配置
        ]
        
        for path in search_paths:
            if path.exists():
                return str(path)
        return None

    @classmethod
    def create_fetcher(cls) -> DataFetcher:
        """Create data fetcher based on environment"""
        # 在测试环境中始终使用 mock 数据获取器
        return MockDataFetcher()

    @classmethod
    def create_db_manager(cls) -> DatabaseManager:
        """Create database manager based on environment"""
        # 在测试环境中始终使用 mock 数据库管理器
        return MockDatabaseManager()
