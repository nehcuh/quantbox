"""
缓存装饰器模块
"""
import functools
import time
from typing import Any, Callable, Dict, Optional


class Cache:
    """简单的内存缓存实现"""

    def __init__(self):
        """初始化缓存"""
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            Optional[Dict[str, Any]]: 缓存的值和过期时间
        """
        if key in self._cache:
            item = self._cache[key]
            if item["expire_time"] > time.time():
                return item
            del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
        """
        self._cache[key] = {
            "value": value,
            "expire_time": time.time() + ttl
        }

    def clear(self) -> None:
        """清除所有缓存"""
        self._cache.clear()


# 全局缓存实例
_cache = Cache()


def cache_result(ttl: int = 300) -> Callable:
    """
    缓存函数结果的装饰器

    Args:
        ttl: 缓存过期时间（秒），默认 5 分钟

    Returns:
        装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 生成缓存键
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试从缓存获取
            cached = _cache.get(cache_key)
            if cached is not None:
                return cached["value"]
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            _cache.set(cache_key, result, ttl)
            return result
            
        return wrapper
    return decorator
