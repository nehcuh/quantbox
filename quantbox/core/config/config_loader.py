import os
import tomli
from pathlib import Path
from typing import Dict, Any, Optional

from .database_config import MongoDBConfig
from .api_config import ApiConfig
from .log_config import LogConfig
from .cache_config import CacheConfig
from .trade_config import TradeConfig
from .exchange_config import ExchangeConfig

class ConfigLoader:
    """配置加载器"""
    
    DEFAULT_CONFIG_PATH = "~/.quantbox/settings/config.toml"
    
    _instance: Optional["ConfigLoader"] = None
    _api_config: Optional[ApiConfig] = None
    _cache_config: Optional[CacheConfig] = None
    _database_config: Optional[MongoDBConfig] = None
    
    def __new__(cls) -> "ConfigLoader":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化配置加载器"""
        if self._api_config is None:
            self._load_config()
    
    @classmethod
    def _load_config(cls):
        """加载配置文件"""
        config_path = os.path.expanduser(cls.DEFAULT_CONFIG_PATH)
        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"配置文件不存在: {config_path}\n"
                f"请参考 example.config.toml 创建配置文件"
            )
        
        with open(config_path, "rb") as f:
            config = tomli.load(f)
        
        # 加载API配置
        api_config = config.get("api", {})
        tspro_config = config.get("TSPRO", {})
        api_config["tushare_token"] = tspro_config.get("token", "")
        cls._api_config = ApiConfig(**api_config)
        
        # 加载缓存配置
        cache_config = config.get("cache", {})
        cls._cache_config = CacheConfig(**cache_config)
        
        # 加载数据库配置
        database_config = config.get("database", {})
        cls._database_config = MongoDBConfig(
            host=database_config.get("host", "localhost"),
            port=database_config.get("port", 27018),
            username=database_config.get("username", ""),
            password=database_config.get("password", ""),
            database=database_config.get("database", "quantbox"),
            collection_prefix=database_config.get("collection_prefix", "qb_")
        )
    
    @classmethod
    def load_config(cls, config_path: Optional[str] = None) -> Dict[str, Any]:
        """加载配置文件
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        # 如果未指定配置文件路径，使用默认路径
        if config_path is None:
            config_path = cls.DEFAULT_CONFIG_PATH
            
        # 展开用户主目录
        config_path = os.path.expanduser(config_path)
        
        # 检查配置文件是否存在
        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"配置文件不存在: {config_path}\n"
                f"请参考 example.config.toml 创建配置文件"
            )
            
        # 读取配置文件
        with open(config_path, "rb") as f:
            return tomli.load(f)
    
    @classmethod
    def create_config_dir(cls) -> None:
        """创建配置文件目录"""
        config_dir = os.path.expanduser("~/.quantbox")
        os.makedirs(config_dir, exist_ok=True)
        
        # 创建配置目录
        settings_dir = os.path.join(config_dir, "settings")
        os.makedirs(settings_dir, exist_ok=True)
        
        # 创建日志目录
        log_dir = os.path.join(config_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # 创建数据目录
        data_dir = os.path.join(config_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        # 创建缓存目录
        cache_dir = os.path.join(config_dir, "cache")
        os.makedirs(cache_dir, exist_ok=True)
    
    @classmethod
    def get_api_config(
        cls,
        config_path: Optional[str] = None
    ) -> ApiConfig:
        """获取API配置"""
        if cls._api_config is None:
            cls._load_config()
        return cls._api_config
    
    @classmethod
    def get_cache_config(
        cls,
        config_path: Optional[str] = None
    ) -> CacheConfig:
        """获取缓存配置"""
        if cls._cache_config is None:
            cls._load_config()
        return cls._cache_config
    
    @classmethod
    def get_database_config(
        cls,
        config_path: Optional[str] = None
    ) -> MongoDBConfig:
        """获取数据库配置"""
        if cls._database_config is None:
            cls._load_config()
        return cls._database_config
    
    @classmethod
    def get_log_config(
        cls,
        config_path: Optional[str] = None
    ) -> LogConfig:
        """获取日志配置"""
        return LogConfig(
            level="INFO",
            file="~/.quantbox/logs/quantbox.log",
            console=True,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            max_size=10,
            backup_count=5
        )
    
    @classmethod
    def get_trade_config(
        cls,
        config_path: Optional[str] = None
    ) -> TradeConfig:
        """获取交易配置"""
        # 使用默认交易配置
        exchanges = {
            "SSE": ExchangeConfig(
                name="上海证券交易所",
                code="SSE",
                timezone="Asia/Shanghai",
                open_time=["09:30:00", "13:00:00"],
                close_time=["11:30:00", "15:00:00"],
                trading_days="1,2,3,4,5",
                commission_type="rate",
                commission_open=0.0003,
                commission_close=0.0003,
                commission_close_today=0.0003,
                commission_min=5.0,
                slippage_type="rate",
                slippage_value=0.0001
            ),
            "SZSE": ExchangeConfig(
                name="深圳证券交易所",
                code="SZSE",
                timezone="Asia/Shanghai",
                open_time=["09:30:00", "13:00:00"],
                close_time=["11:30:00", "15:00:00"],
                trading_days="1,2,3,4,5",
                commission_type="rate",
                commission_open=0.0003,
                commission_close=0.0003,
                commission_close_today=0.0003,
                commission_min=5.0,
                slippage_type="rate",
                slippage_value=0.0001
            )
        }
            
        return TradeConfig(
            timezone="Asia/Shanghai",
            default_exchange="SSE",
            exchanges=exchanges
        )
