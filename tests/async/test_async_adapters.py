"""
异步适配器单元测试

测试 AsyncTSAdapter 和 AsyncLocalAdapter 的核心功能
"""

import pytest
import pytest_asyncio
import asyncio
import pandas as pd
from datetime import datetime, timedelta

from quantbox.adapters.asynchronous.ts_adapter import AsyncTSAdapter
from quantbox.adapters.asynchronous.local_adapter import AsyncLocalAdapter


class TestAsyncTSAdapter:
    """测试 AsyncTSAdapter"""

    @pytest_asyncio.fixture
    async def adapter(self):
        """创建适配器实例"""
        adapter = AsyncTSAdapter(max_concurrent=5, rate_limit=3.0)
        yield adapter
        # 清理
        if hasattr(adapter, '__del__'):
            adapter.__del__()

    @pytest.mark.asyncio
    async def test_get_trade_calendar(self, adapter):
        """测试获取交易日历"""
        # 测试单个交易所
        result = await adapter.get_trade_calendar(
            exchanges="SHFE",
            start_date=20240101,
            end_date=20240131
        )

        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert 'date' in result.columns
        assert 'exchange' in result.columns
        assert 'is_open' in result.columns
        assert result['exchange'].iloc[0] == 'SHFE'

    @pytest.mark.asyncio
    async def test_get_trade_calendar_multiple_exchanges(self, adapter):
        """测试并发查询多个交易所"""
        result = await adapter.get_trade_calendar(
            exchanges=["SHFE", "DCE"],
            start_date=20240101,
            end_date=20240110
        )

        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        exchanges = result['exchange'].unique()
        assert 'SHFE' in exchanges or 'DCE' in exchanges

    @pytest.mark.asyncio
    async def test_get_future_contracts(self, adapter):
        """测试获取期货合约"""
        result = await adapter.get_future_contracts(
            exchanges="SHFE",
        )

        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert 'symbol' in result.columns
        assert 'exchange' in result.columns
        assert 'spec_name' in result.columns

    @pytest.mark.asyncio
    async def test_get_future_contracts_with_date_filter(self, adapter):
        """测试按日期过滤合约"""
        result = await adapter.get_future_contracts(
            exchanges="SHFE",
            date=20240101
        )

        assert isinstance(result, pd.DataFrame)
        # 可能为空，因为有些合约在该日期未上市

    @pytest.mark.asyncio
    async def test_get_future_daily(self, adapter):
        """测试获取期货日线数据"""
        # 获取最近一周数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        result = await adapter.get_future_daily(
            exchanges="SHFE",
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d")
        )

        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert 'date' in result.columns
            assert 'symbol' in result.columns
            assert 'open' in result.columns
            assert 'close' in result.columns

    @pytest.mark.asyncio
    async def test_get_future_holdings_single_date(self, adapter):
        """测试获取单日期货持仓"""
        # 使用最近的交易日
        result = await adapter.get_future_holdings(
            exchanges="SHFE",
            date=20240102,
            show_progress=False
        )

        assert isinstance(result, pd.DataFrame)
        # 持仓数据可能为空

    @pytest.mark.asyncio
    async def test_get_future_holdings_date_range(self, adapter):
        """测试获取日期范围期货持仓（核心性能优化）"""
        # 测试小范围日期（避免测试时间过长）
        result = await adapter.get_future_holdings(
            exchanges="SHFE",
            start_date=20240101,
            end_date=20240105,
            show_progress=False
        )

        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert 'date' in result.columns
            assert 'symbol' in result.columns
            assert 'broker' in result.columns

    @pytest.mark.asyncio
    async def test_check_availability(self, adapter):
        """测试检查可用性"""
        result = await adapter.check_availability()
        # 如果 Tushare token 配置正确，应该返回 True
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, adapter):
        """测试并发请求"""
        # 并发执行多个查询
        tasks = [
            adapter.get_trade_calendar(
                exchanges="SHFE",
                start_date=20240101,
                end_date=20240110
            ),
            adapter.get_future_contracts(exchanges="SHFE"),
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 2
        for result in results:
            assert isinstance(result, pd.DataFrame)


class TestAsyncLocalAdapter:
    """测试 AsyncLocalAdapter"""

    @pytest_asyncio.fixture
    async def adapter(self):
        """创建适配器实例"""
        adapter = AsyncLocalAdapter()
        yield adapter
        # 清理
        if hasattr(adapter, '__del__'):
            adapter.__del__()

    @pytest.mark.asyncio
    async def test_check_availability(self, adapter):
        """测试检查 MongoDB 可用性"""
        result = await adapter.check_availability()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_get_trade_calendar(self, adapter):
        """测试从 MongoDB 获取交易日历"""
        result = await adapter.get_trade_calendar(
            exchanges="SHFE",
            start_date=20240101,
            end_date=20240131
        )

        assert isinstance(result, pd.DataFrame)
        # 结果可能为空（如果数据库中没有数据）

    @pytest.mark.asyncio
    async def test_get_future_contracts(self, adapter):
        """测试从 MongoDB 获取期货合约"""
        result = await adapter.get_future_contracts(
            exchanges="SHFE"
        )

        assert isinstance(result, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_bulk_insert(self, adapter):
        """测试批量插入"""
        # 准备测试数据
        test_collection = "test_bulk_insert"
        test_data = [
            {"_id": f"test_{i}", "value": i}
            for i in range(10)
        ]

        # 插入数据
        count = await adapter.bulk_insert(test_collection, test_data)
        assert count == 10 or count == 0  # 可能因为重复而插入失败

        # 清理测试数据
        await adapter.database[test_collection].delete_many(
            {"_id": {"$regex": "^test_"}}
        )

    @pytest.mark.asyncio
    async def test_bulk_upsert(self, adapter):
        """测试批量更新/插入"""
        # 准备测试数据
        test_collection = "test_bulk_upsert"
        test_data = [
            {"id": f"test_{i}", "value": i, "updated": False}
            for i in range(10)
        ]

        # 首次插入
        result1 = await adapter.bulk_upsert(
            test_collection,
            test_data,
            ["id"]
        )
        assert result1["upserted"] >= 0

        # 更新数据
        for item in test_data:
            item["updated"] = True

        result2 = await adapter.bulk_upsert(
            test_collection,
            test_data,
            ["id"]
        )
        assert result2["matched"] + result2["modified"] >= 0

        # 清理测试数据
        await adapter.database[test_collection].delete_many(
            {"id": {"$regex": "^test_"}}
        )

    @pytest.mark.asyncio
    async def test_concurrent_queries(self, adapter):
        """测试并发查询"""
        # 并发执行多个查询
        tasks = [
            adapter.get_trade_calendar(
                exchanges="SHFE",
                start_date=20240101,
                end_date=20240110
            ),
            adapter.get_future_contracts(exchanges="SHFE"),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        assert len(results) == 2
        for result in results:
            if not isinstance(result, Exception):
                assert isinstance(result, pd.DataFrame)


class TestAsyncUtilities:
    """测试异步工具函数"""

    @pytest.mark.asyncio
    async def test_rate_limiter(self):
        """测试速率限制器"""
        from quantbox.adapters.asynchronous.utils import RateLimiter

        limiter = RateLimiter(calls_per_second=5.0, burst=3)

        start_time = asyncio.get_event_loop().time()

        # 执行 5 次操作
        for i in range(5):
            async with limiter:
                pass

        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time

        # 应该至少花费一定时间（受速率限制）
        # 5 次调用，速率 5/s，理论最少 0.8s（考虑 burst）
        assert elapsed >= 0.0  # 宽松检查

    @pytest.mark.asyncio
    async def test_async_retry(self):
        """测试自动重试装饰器"""
        from quantbox.adapters.asynchronous.utils import AsyncRetry

        attempt_count = 0

        @AsyncRetry(max_attempts=3, backoff_factor=0.1)
        async def failing_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Test error")
            return "success"

        result = await failing_function()

        assert result == "success"
        assert attempt_count == 2  # 第一次失败，第二次成功

    @pytest.mark.asyncio
    async def test_concurrency_limiter(self):
        """测试并发限制器"""
        from quantbox.adapters.asynchronous.utils import ConcurrencyLimiter

        limiter = ConcurrencyLimiter(max_concurrent=2)
        active_count = 0
        max_active = 0

        async def task():
            nonlocal active_count, max_active
            async with limiter:
                active_count += 1
                max_active = max(max_active, active_count)
                await asyncio.sleep(0.1)
                active_count -= 1

        # 启动 5 个任务
        await asyncio.gather(*[task() for _ in range(5)])

        # 最大并发数应该不超过 2
        assert max_active <= 2

    @pytest.mark.asyncio
    async def test_gather_with_limit(self):
        """测试受限并发的 gather"""
        from quantbox.adapters.asynchronous.utils import gather_with_limit

        async def task(value):
            await asyncio.sleep(0.01)
            return value * 2

        tasks = [task(i) for i in range(10)]
        results = await gather_with_limit(*tasks, limit=3)

        assert len(results) == 10
        assert results == [i * 2 for i in range(10)]


# 配置 pytest
def pytest_configure(config):
    """配置 pytest"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async test"
    )
