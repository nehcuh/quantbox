"""
LocalAdapter 测试

测试 LocalAdapter 的基本功能（不依赖真实数据库）
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
import datetime

from quantbox.adapters.local_adapter import LocalAdapter


class TestLocalAdapterInit:
    """测试 LocalAdapter 初始化"""
    
    def test_init_with_default_database(self):
        """测试使用默认数据库初始化"""
        with patch('quantbox.adapters.local_adapter.DATABASE') as mock_db:
            adapter = LocalAdapter()
            assert adapter.name == "LocalAdapter"
            assert adapter.database is not None
    
    def test_init_with_custom_database(self):
        """测试使用自定义数据库初始化"""
        mock_db = Mock()
        adapter = LocalAdapter(database=mock_db)
        assert adapter.database is mock_db


class TestLocalAdapterAvailability:
    """测试数据库可用性检查"""
    
    def test_check_availability_success(self):
        """测试数据库可用"""
        mock_db = Mock()
        mock_db.trade_date.find_one.return_value = {"trade_date": "2025-01-01"}
        
        adapter = LocalAdapter(database=mock_db)
        assert adapter.check_availability() is True
    
    def test_check_availability_failure(self):
        """测试数据库不可用"""
        mock_db = Mock()
        mock_db.trade_date.find_one.side_effect = Exception("Connection failed")
        
        adapter = LocalAdapter(database=mock_db)
        assert adapter.check_availability() is False


class TestGetTradeCalendar:
    """测试获取交易日历"""
    
    def test_get_trade_calendar_basic(self):
        """测试基本的交易日历查询"""
        mock_db = Mock()
        mock_cursor = [
            {"trade_date": "2025-01-02", "exchange": "SHSE", "datestamp": datetime.datetime(2025, 1, 2)},
            {"trade_date": "2025-01-03", "exchange": "SHSE", "datestamp": datetime.datetime(2025, 1, 3)},
        ]
        mock_db.trade_date.find.return_value = mock_cursor
        
        adapter = LocalAdapter(database=mock_db)
        df = adapter.get_trade_calendar()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["date", "exchange", "is_open"]
        assert df["date"].tolist() == [20250102, 20250103]
        assert all(df["is_open"])
    
    def test_get_trade_calendar_with_exchanges(self):
        """测试按交易所过滤"""
        mock_db = Mock()
        mock_cursor = [
            {"trade_date": "2025-01-02", "exchange": "SHFE", "datestamp": datetime.datetime(2025, 1, 2)},
        ]
        mock_db.trade_date.find.return_value = mock_cursor
        
        adapter = LocalAdapter(database=mock_db)
        df = adapter.get_trade_calendar(exchanges="SHFE")
        
        assert len(df) == 1
        assert df["exchange"].iloc[0] == "SHFE"
    
    def test_get_trade_calendar_empty(self):
        """测试空结果"""
        mock_db = Mock()
        mock_db.trade_date.find.return_value = []
        
        adapter = LocalAdapter(database=mock_db)
        df = adapter.get_trade_calendar()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert list(df.columns) == ["date", "exchange", "is_open"]


class TestGetFutureContracts:
    """测试获取期货合约信息"""
    
    def test_get_future_contracts_by_exchange(self):
        """测试按交易所查询合约"""
        mock_db = Mock()
        mock_cursor = [
            {
                "symbol": "SHFE.rb2501",
                "exchange": "SHFE",
                "name": "螺纹钢2501",
                "fut_code": "RB",
                "list_date": "2024-09-01",
                "delist_date": "2025-01-15",
            }
        ]
        mock_db.future_contracts.find.return_value = mock_cursor
        
        adapter = LocalAdapter(database=mock_db)
        df = adapter.get_future_contracts(exchanges="SHFE")
        
        assert len(df) == 1
        assert df["symbol"].iloc[0] == "SHFE.rb2501"
        assert df["exchange"].iloc[0] == "SHFE"
        assert "spec_name" in df.columns
    
    def test_get_future_contracts_validation_error(self):
        """测试参数验证"""
        mock_db = Mock()
        adapter = LocalAdapter(database=mock_db)
        
        with pytest.raises(Exception, match="必须至少指定"):
            adapter.get_future_contracts()


class TestGetFutureDaily:
    """测试获取期货日线数据"""
    
    def test_get_future_daily_by_symbol(self):
        """测试按合约查询日线数据"""
        mock_db = Mock()
        mock_cursor = [
            {
                "symbol": "SHFE.rb2501",
                "exchange": "SHFE",
                "trade_date": "2025-01-02",
                "datestamp": datetime.datetime(2025, 1, 2),
                "open": 3800.0,
                "high": 3850.0,
                "low": 3780.0,
                "close": 3820.0,
                "volume": 100000,
                "amount": 380000000,
                "oi": 50000,
            }
        ]
        mock_db.future_daily.find.return_value = mock_cursor
        
        adapter = LocalAdapter(database=mock_db)
        df = adapter.get_future_daily(symbols="SHFE.rb2501")
        
        assert len(df) == 1
        assert df["symbol"].iloc[0] == "SHFE.rb2501"
        assert df["date"].iloc[0] == 20250102
        assert df["open"].iloc[0] == 3800.0
    
    def test_get_future_daily_date_range_validation(self):
        """测试日期范围参数验证"""
        mock_db = Mock()
        adapter = LocalAdapter(database=mock_db)
        
        with pytest.raises(Exception, match="互斥"):
            adapter.get_future_daily(
                symbols="SHFE.rb2501",
                start_date=20250101,
                date=20250102
            )


class TestGetFutureHoldings:
    """测试获取期货持仓数据"""
    
    def test_get_future_holdings_by_symbol(self):
        """测试按合约查询持仓数据"""
        mock_db = Mock()
        mock_cursor = [
            {
                "symbol": "SHFE.rb2501",
                "exchange": "SHFE",
                "trade_date": "2025-01-02",
                "datestamp": datetime.datetime(2025, 1, 2),
                "broker": "中信期货",
                "vol": 10000,
                "vol_chg": 500,
                "rank": 1,
            }
        ]
        mock_db.future_holdings.find.return_value = mock_cursor
        
        adapter = LocalAdapter(database=mock_db)
        df = adapter.get_future_holdings(symbols="SHFE.rb2501")
        
        assert len(df) == 1
        assert df["symbol"].iloc[0] == "SHFE.rb2501"
        assert df["broker"].iloc[0] == "中信期货"
        assert df["rank"].iloc[0] == 1
    
    def test_get_future_holdings_by_spec_name(self):
        """测试按品种名称查询持仓数据"""
        mock_db = Mock()
        
        # Mock 合约查询
        mock_db.future_contracts.find.return_value = [
            {"symbol": "SHFE.rb2501"},
            {"symbol": "SHFE.rb2505"},
        ]
        
        # Mock 持仓查询
        mock_db.future_holdings.find.return_value = [
            {
                "symbol": "SHFE.rb2501",
                "exchange": "SHFE",
                "trade_date": "2025-01-02",
                "datestamp": datetime.datetime(2025, 1, 2),
                "broker": "中信期货",
                "vol": 10000,
                "vol_chg": 500,
                "rank": 1,
            }
        ]
        
        adapter = LocalAdapter(database=mock_db)
        df = adapter.get_future_holdings(spec_names="rb")
        
        assert len(df) == 1
        assert df["symbol"].iloc[0] == "SHFE.rb2501"


class TestErrorHandling:
    """测试错误处理"""
    
    def test_get_trade_calendar_error(self):
        """测试交易日历查询错误"""
        mock_db = Mock()
        mock_db.trade_date.find.side_effect = Exception("Database error")
        
        adapter = LocalAdapter(database=mock_db)
        
        with pytest.raises(Exception, match="获取交易日历失败"):
            adapter.get_trade_calendar()
    
    def test_get_future_contracts_error(self):
        """测试合约查询错误"""
        mock_db = Mock()
        mock_db.future_contracts.find.side_effect = Exception("Database error")
        
        adapter = LocalAdapter(database=mock_db)
        
        with pytest.raises(Exception, match="获取期货合约信息失败"):
            adapter.get_future_contracts(exchanges="SHFE")
    
    def test_get_future_daily_error(self):
        """测试日线数据查询错误"""
        mock_db = Mock()
        mock_db.future_daily.find.side_effect = Exception("Database error")
        
        adapter = LocalAdapter(database=mock_db)
        
        with pytest.raises(Exception, match="获取期货日线数据失败"):
            adapter.get_future_daily(symbols="SHFE.rb2501")
    
    def test_get_future_holdings_error(self):
        """测试持仓数据查询错误"""
        mock_db = Mock()
        mock_db.future_holdings.find.side_effect = Exception("Database error")
        
        adapter = LocalAdapter(database=mock_db)
        
        with pytest.raises(Exception, match="获取期货持仓数据失败"):
            adapter.get_future_holdings(symbols="SHFE.rb2501")
