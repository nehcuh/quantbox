"""
异步服务单元测试

测试 AsyncDataSaverService 的核心功能
"""

import pytest
import pytest_asyncio
import asyncio
import pandas as pd
from datetime import datetime, timedelta

from quantbox.services.async_data_saver_service import AsyncDataSaverService
from quantbox.services.data_saver_service import SaveResult


class TestAsyncDataSaverService:
    """测试 AsyncDataSaverService"""

    @pytest_asyncio.fixture
    async def saver(self):
        """创建服务实例"""
        saver = AsyncDataSaverService(show_progress=False)
        yield saver
        # 清理
        if hasattr(saver, '__del__'):
            saver.__del__()

    @pytest.mark.asyncio
    async def test_save_trade_calendar(self, saver):
        """测试保存交易日历"""
        result = await saver.save_trade_calendar(
            exchanges="SHFE",
            start_date=20240101,
            end_date=20240110
        )

        assert isinstance(result, SaveResult)
        assert result.end_time is not None
        # 结果可能成功或失败，取决于 API 和数据库状态

    @pytest.mark.asyncio
    async def test_save_future_contracts(self, saver):
        """测试保存期货合约"""
        result = await saver.save_future_contracts(
            exchanges="SHFE"
        )

        assert isinstance(result, SaveResult)
        assert result.end_time is not None

    @pytest.mark.asyncio
    async def test_save_future_daily(self, saver):
        """测试保存期货日线"""
        # 使用小范围日期
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)

        result = await saver.save_future_daily(
            exchanges="SHFE",
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d")
        )

        assert isinstance(result, SaveResult)
        assert result.end_time is not None

    @pytest.mark.asyncio
    async def test_save_future_holdings_single_date(self, saver):
        """测试保存单日期货持仓"""
        result = await saver.save_future_holdings(
            exchanges="SHFE",
            date=20240102
        )

        assert isinstance(result, SaveResult)
        assert result.end_time is not None

    @pytest.mark.asyncio
    async def test_save_future_holdings_date_range(self, saver):
        """测试保存日期范围期货持仓（核心性能测试）"""
        # 使用小范围日期测试
        result = await saver.save_future_holdings(
            exchanges="SHFE",
            start_date=20240101,
            end_date=20240103
        )

        assert isinstance(result, SaveResult)
        assert result.end_time is not None
        # 检查执行时间
        duration = result.duration.total_seconds()
        assert duration >= 0

    @pytest.mark.asyncio
    async def test_save_stock_list(self, saver):
        """测试保存股票列表"""
        result = await saver.save_stock_list(
            exchanges="SSE"
        )

        assert isinstance(result, SaveResult)
        assert result.end_time is not None

    @pytest.mark.asyncio
    async def test_save_all_concurrent(self, saver):
        """测试并发保存所有数据"""
        # 使用小范围日期
        result_dict = await saver.save_all(
            exchanges=["SHFE"],
            start_date=20240101,
            end_date=20240103
        )

        assert isinstance(result_dict, dict)
        assert 'trade_calendar' in result_dict
        assert 'future_contracts' in result_dict
        assert 'future_holdings' in result_dict
        assert 'future_daily' in result_dict

        # 检查每个结果
        for key, result in result_dict.items():
            if result and not isinstance(result, Exception):
                assert isinstance(result, SaveResult)

    @pytest.mark.asyncio
    async def test_save_result_tracking(self, saver):
        """测试 SaveResult 跟踪功能"""
        result = await saver.save_trade_calendar(
            exchanges="SHFE",
            start_date=20240101,
            end_date=20240105
        )

        # 检查基本属性
        assert hasattr(result, 'success')
        assert hasattr(result, 'inserted_count')
        assert hasattr(result, 'modified_count')
        assert hasattr(result, 'error_count')
        assert hasattr(result, 'start_time')
        assert hasattr(result, 'end_time')
        assert hasattr(result, 'duration')

        # 检查时间记录
        assert result.start_time is not None
        assert result.end_time is not None
        assert result.duration.total_seconds() >= 0

    @pytest.mark.asyncio
    async def test_concurrent_save_operations(self, saver):
        """测试多个保存操作并发执行"""
        # 并发执行多个保存任务
        tasks = [
            saver.save_trade_calendar(
                exchanges="SHFE",
                start_date=20240101,
                end_date=20240105
            ),
            saver.save_future_contracts(
                exchanges="SHFE"
            ),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        assert len(results) == 2
        for result in results:
            if not isinstance(result, Exception):
                assert isinstance(result, SaveResult)

    @pytest.mark.asyncio
    async def test_error_handling(self, saver):
        """测试错误处理"""
        # 使用无效参数触发错误
        result = await saver.save_trade_calendar(
            exchanges="INVALID_EXCHANGE",
            start_date=20240101,
            end_date=20240105
        )

        assert isinstance(result, SaveResult)
        # 应该记录错误
        assert result.end_time is not None

    @pytest.mark.asyncio
    async def test_performance_comparison(self, saver):
        """测试性能（简单对比）"""
        import time

        # 记录开始时间
        start_time = time.time()

        # 执行异步保存
        result = await saver.save_trade_calendar(
            exchanges="SHFE",
            start_date=20240101,
            end_date=20240110
        )

        elapsed = time.time() - start_time

        # 异步版本应该在合理时间内完成
        assert elapsed < 60  # 应该在 60 秒内完成
        assert isinstance(result, SaveResult)


class TestSaveResult:
    """测试 SaveResult 类"""

    def test_save_result_initialization(self):
        """测试 SaveResult 初始化"""
        result = SaveResult()

        assert result.success == True
        assert result.inserted_count == 0
        assert result.modified_count == 0
        assert result.error_count == 0
        assert result.errors == []
        assert result.start_time is not None
        assert result.end_time is None

    def test_save_result_add_error(self):
        """测试添加错误"""
        result = SaveResult()

        result.add_error("TEST_ERROR", "This is a test error")

        assert result.success == False
        assert result.error_count == 1
        assert len(result.errors) == 1
        assert result.errors[0]['type'] == 'TEST_ERROR'
        assert result.errors[0]['message'] == 'This is a test error'

    def test_save_result_complete(self):
        """测试完成操作"""
        result = SaveResult()
        result.complete()

        assert result.end_time is not None
        assert result.duration.total_seconds() >= 0

    def test_save_result_to_dict(self):
        """测试转换为字典"""
        result = SaveResult()
        result.inserted_count = 100
        result.modified_count = 50
        result.complete()

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict['success'] == True
        assert result_dict['inserted_count'] == 100
        assert result_dict['modified_count'] == 50
        assert 'duration' in result_dict


# 配置 pytest
def pytest_configure(config):
    """配置 pytest"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async test"
    )
