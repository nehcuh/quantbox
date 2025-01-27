from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class MongoDBConfig:
    """MongoDB配置"""
    host: str
    port: int
    username: str
    password: str
    database: str
    collection_prefix: str = ""  # quantbox前缀
    
    @property
    def uri(self) -> str:
        """获取MongoDB连接URI"""
        if self.username and self.password:
            return f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"mongodb://{self.host}:{self.port}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "database": self.database,
            "collection_prefix": self.collection_prefix
        }
