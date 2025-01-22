"""
性能监控模块
"""
import functools
import time
import logging
from typing import Any, Callable


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, slow_query_threshold: float = 2.0):
        """
        初始化性能监控器

        Args:
            slow_query_threshold: 慢查询阈值（秒）
        """
        self.slow_query_threshold = slow_query_threshold
        self.logger = logging.getLogger(__name__)

    def log_slow_query(self, func_name: str, duration: float):
        """记录慢查询"""
        self.logger.warning(
            f"慢查询: {func_name} 执行时间 {duration:.2f} 秒，超过阈值 {self.slow_query_threshold} 秒"
        )


def monitor_performance(func: Callable) -> Callable:
    """
    性能监控装饰器

    Args:
        func: 要监控的函数

    Returns:
        装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> Any:
        start_time = time.time()
        try:
            result = func(self, *args, **kwargs)
            duration = time.time() - start_time
            if hasattr(self, "monitor") and duration > self.monitor.slow_query_threshold:
                self.monitor.log_slow_query(func.__name__, duration)
            return result
        except Exception as e:
            duration = time.time() - start_time
            if hasattr(self, "monitor"):
                self.monitor.log_slow_query(func.__name__, duration)
            raise e

    return wrapper
