"""
基础适配器接口测试

测试 IDataAdapter 接口和 BaseDataAdapter 基类
"""

import pytest
import pandas as pd
from typing import Optional, Union, List

from quantbox.adapters.base import IDataAdapter, BaseDataAdapter
from quantbox.util.date_utils import DateLike


class MockAdapter(BaseDataAdapter):
    """用于测试的模拟适配器"""
    
    def __init__(self):
        super().__init__("MockAdapter")
        self._available = True
    
    def get_trade_calendar(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        # 简单实现用于测试
        return pd.DataFrame({
            "date": [20250101, 20250102],
            "exchange": ["SHSE", "SHSE"],
            "is_open": [False, True],
        })
    
    def get_future_contracts(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        symbols: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        return pd.DataFrame({
            "symbol": ["SHFE.rb2501"],
            "exchange": ["SHFE"],
            "name": ["螺纹钢2501"],
            "spec_name": ["rb"],
        })
    
    def get_future_daily(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
        show_progress: bool = False,
    ) -> pd.DataFrame:
        return pd.DataFrame({
            "date": [20250101],
            "symbol": ["SHFE.rb2501"],
            "exchange": ["SHFE"],
            "open": [3800.0],
            "high": [3850.0],
            "low": [3780.0],
            "close": [3820.0],
            "volume": [100000],
            "amount": [380000000],
            "oi": [50000],
        })
    
    def get_future_holdings(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
        show_progress: bool = False,
    ) -> pd.DataFrame:
        return pd.DataFrame({
            "date": [20250101],
            "symbol": ["SHFE.rb2501"],
            "exchange": ["SHFE"],
            "broker": ["中信期货"],
            "vol": [10000],
            "vol_chg": [500],
            "rank": [1],
        })
    
    def check_availability(self) -> bool:
        return self._available


class TestBaseDataAdapter:
    """测试 BaseDataAdapter 基类"""
    
    def test_name_property(self):
        """测试适配器名称属性"""
        adapter = MockAdapter()
        assert adapter.name == "MockAdapter"
    
    def test_validate_date_range_success(self):
        """测试日期范围验证 - 正常情况"""
        adapter = MockAdapter()
        # 不应该抛出异常
        adapter._validate_date_range(20250101, 20250110, None)
        adapter._validate_date_range(None, None, 20250101)
        adapter._validate_date_range(None, 20250110, None)
    
    def test_validate_date_range_conflict(self):
        """测试日期范围验证 - 参数冲突"""
        adapter = MockAdapter()
        with pytest.raises(ValueError, match="互斥"):
            adapter._validate_date_range(20250101, 20250110, 20250105)
        
        with pytest.raises(ValueError, match="互斥"):
            adapter._validate_date_range(20250101, None, 20250105)
    
    def test_validate_symbol_params_success(self):
        """测试合约参数验证 - 正常情况"""
        adapter = MockAdapter()
        # 不应该抛出异常
        adapter._validate_symbol_params(["SHFE.rb2501"], None, None)
        adapter._validate_symbol_params(None, ["SHFE"], None)
        adapter._validate_symbol_params(None, None, ["rb"])
        adapter._validate_symbol_params(["SHFE.rb2501"], ["SHFE"], ["rb"])
    
    def test_validate_symbol_params_all_none(self):
        """测试合约参数验证 - 全部为空"""
        adapter = MockAdapter()
        with pytest.raises(ValueError, match="必须至少指定"):
            adapter._validate_symbol_params(None, None, None)
    
    def test_check_availability_default(self):
        """测试默认可用性检查"""
        adapter = MockAdapter()
        assert adapter.check_availability() is True


class TestIDataAdapter:
    """测试 IDataAdapter 接口"""
    
    def test_interface_implementation(self):
        """测试接口是否正确实现"""
        adapter = MockAdapter()
        
        # 验证适配器实现了接口
        assert isinstance(adapter, IDataAdapter)
        
        # 验证所有方法都可调用
        df = adapter.get_trade_calendar()
        assert isinstance(df, pd.DataFrame)
        assert "date" in df.columns
        
        df = adapter.get_future_contracts(exchanges=["SHFE"])
        assert isinstance(df, pd.DataFrame)
        assert "symbol" in df.columns
        
        df = adapter.get_future_daily(symbols=["SHFE.rb2501"])
        assert isinstance(df, pd.DataFrame)
        assert "open" in df.columns
        
        df = adapter.get_future_holdings(symbols=["SHFE.rb2501"])
        assert isinstance(df, pd.DataFrame)
        assert "broker" in df.columns
        
        available = adapter.check_availability()
        assert isinstance(available, bool)
        
        name = adapter.name
        assert isinstance(name, str)


class TestMockAdapter:
    """测试模拟适配器的具体功能"""
    
    def test_get_trade_calendar(self):
        """测试获取交易日历"""
        adapter = MockAdapter()
        df = adapter.get_trade_calendar()
        
        assert len(df) > 0
        assert "date" in df.columns
        assert "exchange" in df.columns
        assert "is_open" in df.columns
        
        # 验证数据类型
        assert df["date"].dtype == int
        assert df["is_open"].dtype == bool
    
    def test_get_future_contracts(self):
        """测试获取期货合约信息"""
        adapter = MockAdapter()
        df = adapter.get_future_contracts()
        
        assert len(df) > 0
        assert "symbol" in df.columns
        assert "exchange" in df.columns
        assert "spec_name" in df.columns
    
    def test_get_future_daily(self):
        """测试获取期货日线数据"""
        adapter = MockAdapter()
        df = adapter.get_future_daily()
        
        assert len(df) > 0
        required_columns = ["date", "symbol", "open", "high", "low", "close", "volume"]
        for col in required_columns:
            assert col in df.columns
    
    def test_get_future_holdings(self):
        """测试获取期货持仓数据"""
        adapter = MockAdapter()
        df = adapter.get_future_holdings()
        
        assert len(df) > 0
        required_columns = ["date", "symbol", "broker", "vol", "rank"]
        for col in required_columns:
            assert col in df.columns


class TestNotImplementedAdapter:
    """测试未实现方法的适配器"""
    
    def test_not_implemented_methods(self):
        """测试基类未实现的方法抛出 NotImplementedError"""
        
        class IncompleteAdapter(BaseDataAdapter):
            def __init__(self):
                super().__init__("IncompleteAdapter")
        
        adapter = IncompleteAdapter()
        
        with pytest.raises(NotImplementedError, match="未实现 get_trade_calendar"):
            adapter.get_trade_calendar()
        
        with pytest.raises(NotImplementedError, match="未实现 get_future_contracts"):
            adapter.get_future_contracts()
        
        with pytest.raises(NotImplementedError, match="未实现 get_future_daily"):
            adapter.get_future_daily()
        
        with pytest.raises(NotImplementedError, match="未实现 get_future_holdings"):
            adapter.get_future_holdings()
