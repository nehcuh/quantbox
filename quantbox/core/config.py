"""Configuration loader"""

import tomli
from dataclasses import dataclass
from typing import Optional


@dataclass
class MongoDBConfig:
    """MongoDB configuration"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    database: str = "quantbox"


@dataclass
class TushareConfig:
    """Tushare configuration"""
    token: str


@dataclass
class Config:
    """Configuration"""
    mongodb: MongoDBConfig
    tushare: TushareConfig


class ConfigLoader:
    """Configuration loader"""
    
    @classmethod
    def load(cls, path: str) -> Config:
        """Load configuration from file"""
        with open(path, "rb") as f:
            data = tomli.load(f)
            
        # 加载 MongoDB 配置
        mongodb_data = data.get("mongodb", {})
        mongodb = MongoDBConfig(
            host=mongodb_data.get("host", "localhost"),
            port=mongodb_data.get("port", 27017),
            username=mongodb_data.get("username"),
            password=mongodb_data.get("password"),
            database=mongodb_data.get("database", "quantbox")
        )
        
        # 加载 Tushare 配置
        tushare_data = data.get("tushare", {})
        tushare = TushareConfig(
            token=tushare_data.get("token", "")
        )
        
        return Config(mongodb=mongodb, tushare=tushare)
