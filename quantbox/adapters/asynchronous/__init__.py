"""
异步数据适配器模块

提供异步版本的数据适配器，用于高性能并发数据获取。
支持多数据源并发查询，显著提升数据下载效率。

主要组件:
- AsyncBaseDataAdapter: 异步适配器基类
- AsyncTSAdapter: Tushare 异步适配器
- AsyncGMAdapter: 掘金量化异步适配器
- AsyncLocalAdapter: MongoDB 异步适配器

示例:
    >>> import asyncio
    >>> from quantbox.adapters.async_adapters import AsyncTSAdapter
    >>>
    >>> async def main():
    >>>     adapter = AsyncTSAdapter()
    >>>     data = await adapter.get_trade_calendar()
    >>>     print(data)
    >>>
    >>> asyncio.run(main())
"""

from quantbox.adapters.asynchronous.base import (
    IAsyncDataAdapter,
    AsyncBaseDataAdapter,
)
from quantbox.adapters.asynchronous.utils import (
    RateLimiter,
    AsyncRetry,
    ConcurrencyLimiter,
    gather_with_limit,
    batch_process,
    async_to_sync,
    AsyncTimer,
)

# 按需导入适配器（避免未安装对应库时导入失败）
__all_adapters = []

try:
    from quantbox.adapters.asynchronous.ts_adapter import AsyncTSAdapter
    __all_adapters.append("AsyncTSAdapter")
except ImportError:
    pass

try:
    from quantbox.adapters.asynchronous.local_adapter import AsyncLocalAdapter
    __all_adapters.append("AsyncLocalAdapter")
except ImportError:
    pass

try:
    from quantbox.adapters.asynchronous.gm_adapter import AsyncGMAdapter
    __all_adapters.append("AsyncGMAdapter")
except ImportError:
    pass

__all__ = [
    "IAsyncDataAdapter",
    "AsyncBaseDataAdapter",
    "RateLimiter",
    "AsyncRetry",
    "ConcurrencyLimiter",
    "gather_with_limit",
    "batch_process",
    "async_to_sync",
    "AsyncTimer",
] + __all_adapters
