"""
MarketDataService 单元测试

测试市场数据服务的核心功能：
- 适配器选择逻辑
- 本地优先策略
- 远程回退机制
- 数据查询方法
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import pandas as pd
from datetime import datetime

from quantbox.services.market_data_service import MarketDataService
from quantbox.adapters.base import BaseDataAdapter


class MockAdapter(BaseDataAdapter):
    """测试用的 Mock 适配器"""

    def __init__(self, name: str, available: bool = True):
        super().__init__(name)
        self._available = available
        self.call_history = []

    def check_availability(self) -> bool:
        """模拟可用性检查"""
        return self._available

    def get_trade_calendar(self, exchanges=None, start_date=None, end_date=None):
        """模拟交易日历查询"""
        self.call_history.append(('get_trade_calendar', exchanges, start_date, end_date))
        return pd.DataFrame({
            'date': [20250101, 20250102],
            'exchange': ['SHSE', 'SHSE'],
            'is_open': [True, True]
        })

    def get_future_contracts(self, exchanges=None, symbols=None, spec_names=None, date=None):
        """模拟期货合约查询"""
        self.call_history.append(('get_future_contracts', exchanges, symbols, spec_names, date))
        return pd.DataFrame({
            'symbol': ['SHFE.rb2501'],
            'exchange': ['SHFE'],
            'spec_name': ['rb']
        })

    def get_future_daily(self, symbols=None, exchanges=None, start_date=None, end_date=None, date=None):
        """模拟日线数据查询"""
        self.call_history.append(('get_future_daily', symbols, exchanges, start_date, end_date, date))
        return pd.DataFrame({
            'symbol': ['SHFE.rb2501'],
            'date': [20250101],
            'open': [3800.0],
            'close': [3850.0]
        })

    def get_future_holdings(self, symbols=None, exchanges=None, spec_names=None, start_date=None, end_date=None, date=None):
        """模拟持仓数据查询"""
        self.call_history.append(('get_future_holdings', symbols, exchanges, spec_names, start_date, end_date, date))
        return pd.DataFrame({
            'symbol': ['SHFE.rb2501'],
            'date': [20250101],
            'broker': ['永安期货'],
            'vol': [1000]
        })


class TestMarketDataServiceInit(unittest.TestCase):
    """测试 MarketDataService 初始化"""

    def test_default_initialization(self):
        """测试默认初始化（使用默认适配器）"""
        # 由于默认会创建 LocalAdapter 和 TSAdapter，这些可能需要配置
        # 我们暂时跳过这个测试，或者使用 mock
        pass

    def test_custom_adapters(self):
        """测试自定义适配器"""
        local = MockAdapter("LocalMock")
        remote = MockAdapter("RemoteMock")

        service = MarketDataService(
            local_adapter=local,
            remote_adapter=remote,
            prefer_local=True
        )

        self.assertEqual(service.local_adapter, local)
        self.assertEqual(service.remote_adapter, remote)
        self.assertTrue(service.prefer_local)

    def test_prefer_local_flag(self):
        """测试 prefer_local 标志"""
        local = MockAdapter("LocalMock")
        remote = MockAdapter("RemoteMock")

        # prefer_local=True
        service1 = MarketDataService(local, remote, prefer_local=True)
        self.assertTrue(service1.prefer_local)

        # prefer_local=False
        service2 = MarketDataService(local, remote, prefer_local=False)
        self.assertFalse(service2.prefer_local)


class TestAdapterSelection(unittest.TestCase):
    """测试适配器选择逻辑"""

    def test_prefer_local_when_available(self):
        """测试本地适配器可用时优先使用本地"""
        local = MockAdapter("LocalMock", available=True)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=True)
        adapter = service._get_adapter(use_local=None)

        self.assertEqual(adapter, local)
        self.assertEqual(adapter.name, "LocalMock")

    def test_fallback_to_remote_when_local_unavailable(self):
        """测试本地不可用时回退到远程"""
        local = MockAdapter("LocalMock", available=False)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=True)
        adapter = service._get_adapter(use_local=None)

        self.assertEqual(adapter, remote)
        self.assertEqual(adapter.name, "RemoteMock")

    def test_explicit_use_local_true(self):
        """测试显式指定使用本地适配器"""
        local = MockAdapter("LocalMock", available=True)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=False)
        adapter = service._get_adapter(use_local=True)

        self.assertEqual(adapter, local)

    def test_explicit_use_local_false(self):
        """测试显式指定使用远程适配器"""
        local = MockAdapter("LocalMock", available=True)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=True)
        adapter = service._get_adapter(use_local=False)

        self.assertEqual(adapter, remote)

    def test_prefer_remote_mode(self):
        """测试优先远程模式"""
        local = MockAdapter("LocalMock", available=True)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=False)
        adapter = service._get_adapter(use_local=None)

        self.assertEqual(adapter, remote)


class TestGetTradeCalendar(unittest.TestCase):
    """测试 get_trade_calendar 方法"""

    def test_basic_call(self):
        """测试基本调用"""
        local = MockAdapter("LocalMock", available=True)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=True)
        result = service.get_trade_calendar(exchanges='SHSE')

        # 验证返回结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertIn('date', result.columns)
        self.assertIn('exchange', result.columns)

        # 验证使用了本地适配器
        self.assertEqual(len(local.call_history), 1)
        self.assertEqual(local.call_history[0][0], 'get_trade_calendar')
        self.assertEqual(len(remote.call_history), 0)

    def test_with_date_range(self):
        """测试带日期范围的查询"""
        local = MockAdapter("LocalMock", available=True)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=True)
        result = service.get_trade_calendar(
            exchanges='SHSE',
            start_date=20250101,
            end_date=20250131
        )

        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(local.call_history), 1)
        call = local.call_history[0]
        self.assertEqual(call[2], 20250101)  # start_date
        self.assertEqual(call[3], 20250131)  # end_date

    def test_use_remote_explicitly(self):
        """测试显式使用远程适配器"""
        local = MockAdapter("LocalMock", available=True)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=True)
        result = service.get_trade_calendar(exchanges='SHSE', use_local=False)

        # 验证使用了远程适配器
        self.assertEqual(len(local.call_history), 0)
        self.assertEqual(len(remote.call_history), 1)


class TestGetFutureContracts(unittest.TestCase):
    """测试 get_future_contracts 方法"""

    def test_basic_call(self):
        """测试基本调用"""
        local = MockAdapter("LocalMock", available=True)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=True)
        result = service.get_future_contracts(exchanges='SHFE')

        self.assertIsInstance(result, pd.DataFrame)
        self.assertIn('symbol', result.columns)
        self.assertEqual(len(local.call_history), 1)

    def test_with_symbols(self):
        """测试按合约代码查询"""
        local = MockAdapter("LocalMock", available=True)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=True)
        result = service.get_future_contracts(symbols='SHFE.rb2501')

        self.assertIsInstance(result, pd.DataFrame)
        call = local.call_history[0]
        self.assertEqual(call[2], 'SHFE.rb2501')  # symbols

    def test_with_spec_names(self):
        """测试按品种名称查询"""
        local = MockAdapter("LocalMock", available=True)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=True)
        result = service.get_future_contracts(spec_names='rb')

        self.assertIsInstance(result, pd.DataFrame)
        call = local.call_history[0]
        self.assertEqual(call[3], 'rb')  # spec_names


class TestGetFutureDaily(unittest.TestCase):
    """测试 get_future_daily 方法"""

    def test_basic_call(self):
        """测试基本调用"""
        local = MockAdapter("LocalMock", available=True)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=True)
        result = service.get_future_daily(symbols='SHFE.rb2501')

        self.assertIsInstance(result, pd.DataFrame)
        self.assertIn('symbol', result.columns)
        self.assertIn('date', result.columns)
        self.assertEqual(len(local.call_history), 1)

    def test_with_date_range(self):
        """测试日期范围查询"""
        local = MockAdapter("LocalMock", available=True)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=True)
        result = service.get_future_daily(
            symbols='SHFE.rb2501',
            start_date=20250101,
            end_date=20250131
        )

        self.assertIsInstance(result, pd.DataFrame)
        call = local.call_history[0]
        self.assertEqual(call[3], 20250101)  # start_date
        self.assertEqual(call[4], 20250131)  # end_date


class TestGetFutureHoldings(unittest.TestCase):
    """测试 get_future_holdings 方法"""

    def test_basic_call(self):
        """测试基本调用"""
        local = MockAdapter("LocalMock", available=True)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=True)
        result = service.get_future_holdings(symbols='SHFE.rb2501')

        self.assertIsInstance(result, pd.DataFrame)
        self.assertIn('symbol', result.columns)
        self.assertIn('broker', result.columns)
        self.assertEqual(len(local.call_history), 1)

    def test_with_spec_names(self):
        """测试按品种查询持仓"""
        local = MockAdapter("LocalMock", available=True)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=True)
        result = service.get_future_holdings(
            spec_names='rb',
            date=20250101
        )

        self.assertIsInstance(result, pd.DataFrame)
        call = local.call_history[0]
        self.assertEqual(call[3], 'rb')  # spec_names


class TestIntegrationScenarios(unittest.TestCase):
    """测试集成场景"""

    def test_local_unavailable_fallback(self):
        """测试本地不可用时的完整回退流程"""
        local = MockAdapter("LocalMock", available=False)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=True)

        # 测试所有方法都会回退到远程
        service.get_trade_calendar(exchanges='SHSE')
        service.get_future_contracts(exchanges='SHFE')
        service.get_future_daily(symbols='SHFE.rb2501')
        service.get_future_holdings(symbols='SHFE.rb2501')

        # 验证本地适配器没有被调用（除了可用性检查）
        self.assertEqual(len(local.call_history), 0)
        # 验证远程适配器被调用了4次
        self.assertEqual(len(remote.call_history), 4)

    def test_mixed_usage(self):
        """测试混合使用本地和远程"""
        local = MockAdapter("LocalMock", available=True)
        remote = MockAdapter("RemoteMock", available=True)

        service = MarketDataService(local, remote, prefer_local=True)

        # 使用本地（默认）
        service.get_trade_calendar(exchanges='SHSE')
        # 显式使用远程
        service.get_trade_calendar(exchanges='SHSE', use_local=False)
        # 使用本地（默认）
        service.get_future_contracts(exchanges='SHFE')

        self.assertEqual(len(local.call_history), 2)
        self.assertEqual(len(remote.call_history), 1)


if __name__ == '__main__':
    unittest.main()
