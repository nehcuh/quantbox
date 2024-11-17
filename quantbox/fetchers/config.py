"""
Configuration module for the Remote Data Fetcher
远程数据获取器配置模块
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import json
from pathlib import Path

@dataclass
class FetcherConfig:
    """
    Configuration class for RemoteFetcher
    远程数据获取器配置类
    """
    # Cache settings 缓存设置
    cache_type: str = "local"  # "local" or "redis"
    cache_dir: str = ".cache"
    cache_expire_hours: int = 24
    redis_host: Optional[str] = None
    redis_port: Optional[int] = None
    redis_db: Optional[int] = None

    # Retry settings 重试设置
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0

    # Data validation settings 数据验证设置
    validate_data: bool = True
    schema_dir: str = "schemas"
    required_fields: Dict[str, list] = None

    # Performance monitoring 性能监控
    enable_monitoring: bool = True
    slow_query_threshold: float = 5.0  # seconds
    log_performance_stats: bool = True

    # Rate limiting 速率限制
    rate_limit_enabled: bool = True
    requests_per_minute: int = 60

    @classmethod
    def from_file(cls, config_file: str) -> 'FetcherConfig':
        """Load configuration from a JSON file"""
        try:
            with open(config_file, 'r') as f:
                config_dict = json.load(f)
            return cls(**config_dict)
        except Exception as e:
            raise ValueError(f"Failed to load config from {config_file}: {str(e)}")

    @classmethod
    def default(cls) -> 'FetcherConfig':
        """Create default configuration"""
        return cls(
            required_fields={
                "trade_dates": ["date", "exchange"],
                "future_contracts": ["symbol", "exchange"],
                "holdings": ["symbol", "exchange", "date"],
                "future_daily": ["symbol", "date", "open", "high", "low", "close"]
            }
        )

    def to_file(self, config_file: str) -> None:
        """Save configuration to a JSON file"""
        config_dict = {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }
        with open(config_file, 'w') as f:
            json.dump(config_dict, f, indent=4)
