from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class CacheConfig:
    """缓存配置"""
    type: str = "memory"  # memory or redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    expire: int = 3600  # 缓存过期时间（秒）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": self.type,
            "redis_host": self.redis_host,
            "redis_port": self.redis_port,
            "redis_db": self.redis_db,
            "redis_password": self.redis_password,
            "expire": self.expire
        }
    
    @property
    def redis_uri(self) -> Optional[str]:
        """获取Redis连接URI"""
        if self.type != "redis":
            return None
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
