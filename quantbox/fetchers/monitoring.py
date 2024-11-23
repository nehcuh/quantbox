"""
Performance monitoring module for the Remote Data Fetcher
远程数据获取器性能监控模块
"""

import time
import logging
import functools
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)

@dataclass
class PerformanceStats:
    """Performance statistics for data fetching operations"""
    total_requests: int = 0
    total_time: float = 0.0
    successful_requests: int = 0
    failed_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    slow_queries: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    avg_response_time: float = 0.0

    def update_avg_time(self, new_time: float) -> None:
        """Update average response time"""
        if self.total_requests > 0:
            self.avg_response_time = (
                (self.avg_response_time * (self.total_requests - 1) + new_time)
                / self.total_requests
            )
        else:
            self.avg_response_time = new_time

class PerformanceMonitor:
    """Performance monitoring for data fetching operations"""

    def __init__(self, slow_query_threshold: float = 5.0):
        self.stats = PerformanceStats()
        self.slow_query_threshold = slow_query_threshold
        self._lock = threading.Lock()

    def record_request(
        self,
        success: bool,
        response_time: float,
        error_type: Optional[str] = None,
        cache_hit: bool = False
    ) -> None:
        """Record a request's performance metrics"""
        with self._lock:
            self.stats.total_requests += 1
            self.stats.total_time += response_time
            
            if success:
                self.stats.successful_requests += 1
            else:
                self.stats.failed_requests += 1
                if error_type:
                    self.stats.errors_by_type[error_type] += 1

            if cache_hit:
                self.stats.cache_hits += 1
            else:
                self.stats.cache_misses += 1

            if response_time > self.slow_query_threshold:
                self.stats.slow_queries += 1

            self.stats.update_avg_time(response_time)

    def get_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        with self._lock:
            return {
                "total_requests": self.stats.total_requests,
                "successful_requests": self.stats.successful_requests,
                "failed_requests": self.stats.failed_requests,
                "cache_hits": self.stats.cache_hits,
                "cache_misses": self.stats.cache_misses,
                "slow_queries": self.stats.slow_queries,
                "avg_response_time": self.stats.avg_response_time,
                "errors_by_type": dict(self.stats.errors_by_type),
                "success_rate": (
                    self.stats.successful_requests / self.stats.total_requests
                    if self.stats.total_requests > 0 else 0
                ),
                "cache_hit_rate": (
                    self.stats.cache_hits / self.stats.total_requests
                    if self.stats.total_requests > 0 else 0
                )
            }

    def log_stats(self) -> None:
        """Log current performance statistics"""
        stats = self.get_stats()
        logger.info("Performance Statistics:")
        logger.info(f"Total Requests: {stats['total_requests']}")
        logger.info(f"Success Rate: {stats['success_rate']:.2%}")
        logger.info(f"Cache Hit Rate: {stats['cache_hit_rate']:.2%}")
        logger.info(f"Average Response Time: {stats['avg_response_time']:.3f}s")
        logger.info(f"Slow Queries: {stats['slow_queries']}")
        if stats['errors_by_type']:
            logger.info("Errors by Type:")
            for error_type, count in stats['errors_by_type'].items():
                logger.info(f"  {error_type}: {count}")

def monitor_performance(func):
    """装饰器：监控函数性能
    
    Args:
        func: 被装饰的函数
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        try:
            result = func(self, *args, **kwargs)
            success = True
            error_type = None
        except Exception as e:
            success = False
            error_type = type(e).__name__
            raise
        finally:
            response_time = time.time() - start_time
            if hasattr(self, 'monitor'):
                self.monitor.record_request(
                    success=success,
                    response_time=response_time,
                    error_type=error_type,
                    cache_hit=False  # 目前不支持缓存
                )
        return result
    return wrapper
