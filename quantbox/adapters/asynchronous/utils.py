"""
异步工具函数

提供异步适配器所需的通用工具函数：
1. 速率限制（防止 API 封禁）
2. 重试机制（处理临时性错误）
3. 并发控制（限制同时进行的请求数）
4. 批处理工具（批量数据并发处理）

Python 3.14+ nogil 兼容性:
- 使用 asyncio 不依赖 GIL
- 可以与多线程结合使用
"""

import asyncio
import functools
import time
from typing import Any, Callable, Coroutine, List, TypeVar, Optional
from collections import deque
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RateLimiter:
    """
    速率限制器

    用于限制 API 调用频率，防止因过快调用而被封禁。
    支持滑动窗口算法，精确控制调用速率。

    示例:
        >>> limiter = RateLimiter(calls_per_second=5, burst=10)
        >>> async with limiter:
        >>>     # 受速率限制的代码
        >>>     result = await api_call()
    """

    def __init__(
        self,
        calls_per_second: float = 5.0,
        burst: int = 10,
    ):
        """
        初始化速率限制器

        Args:
            calls_per_second: 每秒允许的调用次数
            burst: 突发调用数量（允许短时间内的突发请求）
        """
        self.calls_per_second = calls_per_second
        self.burst = burst
        self.min_interval = 1.0 / calls_per_second
        self.timestamps: deque = deque(maxlen=burst)
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        """进入上下文时等待直到可以执行"""
        async with self._lock:
            now = time.time()

            # 如果队列已满，检查最早的请求时间
            if len(self.timestamps) >= self.burst:
                # 计算窗口期（应该容纳 burst 个请求的时间）
                window = self.burst / self.calls_per_second
                earliest = self.timestamps[0]
                elapsed = now - earliest

                if elapsed < window:
                    # 需要等待
                    wait_time = window - elapsed
                    logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    now = time.time()

            # 记录本次请求时间
            self.timestamps.append(now)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        return False


class AsyncRetry:
    """
    异步重试装饰器

    为异步函数添加自动重试功能，处理临时性错误。

    示例:
        >>> @AsyncRetry(max_attempts=3, backoff_factor=2.0)
        >>> async def fetch_data(symbol):
        >>>     return await api.get_data(symbol)
    """

    def __init__(
        self,
        max_attempts: int = 3,
        backoff_factor: float = 2.0,
        exceptions: tuple = (Exception,),
        on_retry: Optional[Callable] = None,
    ):
        """
        初始化重试装饰器

        Args:
            max_attempts: 最大尝试次数
            backoff_factor: 退避因子（每次重试等待时间倍数）
            exceptions: 要捕获的异常类型
            on_retry: 重试时的回调函数
        """
        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
        self.exceptions = exceptions
        self.on_retry = on_retry

    def __call__(self, func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(1, self.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except self.exceptions as e:
                    last_exception = e
                    if attempt == self.max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {self.max_attempts} attempts: {e}"
                        )
                        raise

                    wait_time = self.backoff_factor ** (attempt - 1)
                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{self.max_attempts} failed: {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )

                    if self.on_retry:
                        self.on_retry(attempt, e)

                    await asyncio.sleep(wait_time)

            # 理论上不会执行到这里，但为了类型检查
            raise last_exception

        return wrapper


class ConcurrencyLimiter:
    """
    并发限制器

    限制同时执行的异步任务数量，防止资源耗尽。

    示例:
        >>> limiter = ConcurrencyLimiter(max_concurrent=10)
        >>> async with limiter:
        >>>     result = await expensive_operation()
    """

    def __init__(self, max_concurrent: int = 10):
        """
        初始化并发限制器

        Args:
            max_concurrent: 最大并发数
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def __aenter__(self):
        await self.semaphore.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.semaphore.release()
        return False


async def gather_with_limit(
    *tasks: Coroutine,
    limit: int = 10,
    return_exceptions: bool = False,
) -> List[Any]:
    """
    受限并发的 asyncio.gather

    与 asyncio.gather 类似，但限制同时执行的任务数量。

    Args:
        *tasks: 要执行的协程任务
        limit: 最大并发数
        return_exceptions: 是否返回异常而不是抛出

    Returns:
        任务结果列表

    示例:
        >>> tasks = [fetch_data(symbol) for symbol in symbols]
        >>> results = await gather_with_limit(*tasks, limit=10)
    """
    semaphore = asyncio.Semaphore(limit)

    async def bounded_task(task: Coroutine) -> Any:
        async with semaphore:
            return await task

    return await asyncio.gather(
        *[bounded_task(task) for task in tasks],
        return_exceptions=return_exceptions,
    )


async def batch_process(
    items: List[Any],
    async_func: Callable[[Any], Coroutine[Any, Any, T]],
    batch_size: int = 100,
    max_concurrent: int = 10,
    rate_limiter: Optional[RateLimiter] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> List[T]:
    """
    批量异步处理数据

    将大量数据分批并发处理，支持速率限制和进度跟踪。

    Args:
        items: 要处理的数据列表
        async_func: 异步处理函数
        batch_size: 批次大小
        max_concurrent: 最大并发数
        rate_limiter: 速率限制器（可选）
        progress_callback: 进度回调函数 (completed, total)

    Returns:
        处理结果列表

    示例:
        >>> async def fetch_symbol(symbol):
        >>>     return await api.get_data(symbol)
        >>>
        >>> symbols = ["SHFE.rb2405", "DCE.m2405", ...]
        >>> results = await batch_process(
        >>>     symbols,
        >>>     fetch_symbol,
        >>>     batch_size=50,
        >>>     max_concurrent=10,
        >>> )
    """
    total = len(items)
    results = []
    completed = 0

    # 分批处理
    for i in range(0, total, batch_size):
        batch = items[i : i + batch_size]

        # 创建受限的并发任务
        async def process_with_limit(item: Any) -> T:
            if rate_limiter:
                async with rate_limiter:
                    return await async_func(item)
            else:
                return await async_func(item)

        # 执行批次
        batch_results = await gather_with_limit(
            *[process_with_limit(item) for item in batch],
            limit=max_concurrent,
            return_exceptions=False,
        )

        results.extend(batch_results)
        completed += len(batch)

        # 调用进度回调
        if progress_callback:
            progress_callback(completed, total)

    return results


def async_to_sync(coro: Coroutine[Any, Any, T]) -> T:
    """
    将异步函数转换为同步函数

    用于在同步代码中调用异步函数，保持向后兼容。

    Args:
        coro: 协程对象

    Returns:
        协程的返回值

    示例:
        >>> # 同步代码中调用异步函数
        >>> result = async_to_sync(async_adapter.get_trade_calendar())
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # 没有运行中的事件循环，创建新的
        return asyncio.run(coro)
    else:
        # 已有运行中的事件循环（如在 Jupyter 中）
        import nest_asyncio
        nest_asyncio.apply()
        return asyncio.run(coro)


class AsyncTimer:
    """
    异步计时器上下文管理器

    用于测量异步操作的执行时间。

    示例:
        >>> async with AsyncTimer() as timer:
        >>>     await fetch_data()
        >>> print(f"Took {timer.elapsed:.2f} seconds")
    """

    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.elapsed: float = 0.0

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time
        logger.info(f"{self.name} completed in {self.elapsed:.2f}s")
        return False
