"""
GMAdapter 单元测试

测试 GMAdapter 的核心功能（使用 mock 模拟掘金 API）
"""

import pytest
import pandas as pd
import platform
from unittest.mock import Mock, MagicMock, patch
import datetime

# Mock 掘金 API 模块
mock_gm_api = MagicMock()
mock_gm_api.set_token = Mock()
mock_gm_api.get_trading_dates_by_year = Mock()
mock_gm_api.fut_get_transaction_rankings = Mock()
mock_gm_api.history = Mock()
mock_gm_api.get_symbol_infos = Mock()


@pytest.fixture(autouse=True)
def mock_gm_imports():
    """自动 mock 掘金 API 导入"""
    with patch.dict('sys.modules', {'gm': mock_gm_api, 'gm.api': mock_gm_api}):
        # 设置 GM_API_AVAILABLE
        with patch('quantbox.adapters.gm_adapter.GM_API_AVAILABLE', True):
            # Mock platform.system 返回非 macOS
            with patch('quantbox.adapters.gm_adapter.platform.system', return_value='Windows'):
                yield


class TestGMAdapterInit:
    """测试 GMAdapter 初始化"""

    @patch('quantbox.adapters.gm_adapter.platform.system', return_value='Darwin')
    def test_init_on_macos_raises_error(self, mock_platform):
        """测试在 macOS 上初始化应该抛出异常"""
        from quantbox.adapters.gm_adapter import GMAdapter

        with pytest.raises(NotImplementedError, match="不支持 macOS"):
            GMAdapter()

    @patch('quantbox.adapters.gm_adapter.GM_API_AVAILABLE', False)
    def test_init_without_sdk_raises_error(self):
        """测试没有安装 SDK 时应该抛出异常"""
        from quantbox.adapters.gm_adapter import GMAdapter

        with pytest.raises(ImportError, match="未安装"):
            GMAdapter()

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    def test_init_with_token(self, mock_set_token, mock_config_loader):
        """测试使用 token 初始化"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.list_exchanges.return_value = ['SHFE', 'DCE']
        mock_config.get_mongodb_client.return_value = Mock()
        mock_config_loader.return_value = mock_config

        adapter = GMAdapter(token="test_token")

        assert adapter.name == "GMAdapter"
        assert adapter.gm_token == "test_token"
        mock_set_token.assert_called_once_with("test_token")

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    def test_init_with_config_token(self, mock_set_token, mock_config_loader):
        """测试从配置文件读取 token"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "config_token"
        mock_config.list_exchanges.return_value = ['SHFE', 'DCE']
        mock_config.get_mongodb_client.return_value = Mock()
        mock_config_loader.return_value = mock_config

        adapter = GMAdapter()

        assert adapter.gm_token == "config_token"
        mock_set_token.assert_called_once_with("config_token")


class TestGMAdapterAvailability:
    """测试数据源可用性检查"""

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    @patch('quantbox.adapters.gm_adapter.get_trading_dates_by_year')
    def test_check_availability_success(self, mock_get_dates, mock_set_token, mock_config_loader):
        """测试可用性检查成功"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SHFE']
        mock_config.get_mongodb_client.return_value = Mock()
        mock_config_loader.return_value = mock_config

        # Mock API 返回
        mock_df = pd.DataFrame({'trade_date': ['2025-01-02', '2025-01-03']})
        mock_get_dates.return_value = mock_df

        adapter = GMAdapter()
        assert adapter.check_availability() is True

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    @patch('quantbox.adapters.gm_adapter.get_trading_dates_by_year')
    def test_check_availability_failure(self, mock_get_dates, mock_set_token, mock_config_loader):
        """测试可用性检查失败"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SHFE']
        mock_config.get_mongodb_client.return_value = Mock()
        mock_config_loader.return_value = mock_config

        # Mock API 抛出异常
        mock_get_dates.side_effect = Exception("API Error")

        adapter = GMAdapter()
        assert adapter.check_availability() is False


class TestGetTradeCalendar:
    """测试获取交易日历"""

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    @patch('quantbox.adapters.gm_adapter.get_trading_dates_by_year')
    def test_get_trade_calendar_basic(self, mock_get_dates, mock_set_token, mock_config_loader):
        """测试基本的交易日历查询"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SHFE', 'DCE']
        mock_config.get_mongodb_client.return_value = Mock()
        mock_config_loader.return_value = mock_config

        # Mock API 返回
        mock_df = pd.DataFrame({
            'trade_date': pd.to_datetime(['2025-01-02', '2025-01-03'])
        })
        mock_get_dates.return_value = mock_df

        adapter = GMAdapter()
        df = adapter.get_trade_calendar(
            exchanges='SHFE',
            start_date='2025-01-02',
            end_date='2025-01-03'
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ['date', 'exchange', 'is_open']
        assert df['date'].tolist() == [20250102, 20250103]
        assert all(df['is_open'])
        assert df['exchange'].iloc[0] == 'SHFE'

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    @patch('quantbox.adapters.gm_adapter.get_trading_dates_by_year')
    def test_get_trade_calendar_multiple_exchanges(self, mock_get_dates, mock_set_token, mock_config_loader):
        """测试多个交易所"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SHFE', 'DCE']
        mock_config.get_mongodb_client.return_value = Mock()
        mock_config_loader.return_value = mock_config

        # Mock API 返回
        mock_df = pd.DataFrame({
            'trade_date': pd.to_datetime(['2025-01-02'])
        })
        mock_get_dates.return_value = mock_df

        adapter = GMAdapter()
        df = adapter.get_trade_calendar(
            exchanges=['SHFE', 'DCE'],
            start_date='2025-01-02',
            end_date='2025-01-02'
        )

        assert len(df) == 2  # 两个交易所
        exchanges = df['exchange'].unique()
        assert 'SHFE' in exchanges
        assert 'DCE' in exchanges

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    @patch('quantbox.adapters.gm_adapter.get_trading_dates_by_year')
    def test_get_trade_calendar_empty(self, mock_get_dates, mock_set_token, mock_config_loader):
        """测试空结果"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SHFE']
        mock_config.get_mongodb_client.return_value = Mock()
        mock_config_loader.return_value = mock_config

        # Mock API 返回空 DataFrame
        mock_get_dates.return_value = pd.DataFrame()

        adapter = GMAdapter()
        df = adapter.get_trade_calendar(exchanges='SHFE')

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert list(df.columns) == ['date', 'exchange', 'is_open']


class TestGetFutureContracts:
    """测试获取期货合约信息"""

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    def test_get_future_contracts_returns_empty(self, mock_set_token, mock_config_loader):
        """测试期货合约查询返回空（API 不支持）"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SHFE']
        mock_config.get_mongodb_client.return_value = Mock()
        mock_config_loader.return_value = mock_config

        adapter = GMAdapter()

        with pytest.warns(UserWarning, match="不支持获取历史期货合约信息"):
            df = adapter.get_future_contracts(exchanges='SHFE')

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestGetFutureDaily:
    """测试获取期货日线数据"""

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    @patch('quantbox.adapters.gm_adapter.history')
    def test_get_future_daily_single_symbol(self, mock_history, mock_set_token, mock_config_loader):
        """测试获取单个合约日线数据"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SHFE']
        mock_config_loader.return_value = mock_config

        # Mock MongoDB
        mock_db = Mock()
        mock_coll = Mock()
        mock_coll.find_one.return_value = {'fut_code': 'RB', 'exchange': 'SHFE'}
        mock_db.future_contracts = mock_coll
        mock_config.get_mongodb_client.return_value = Mock()

        # Mock API 返回
        mock_df = pd.DataFrame({
            'symbol': ['SHFE.rb2501'] * 2,
            'eob': pd.to_datetime(['2025-01-02', '2025-01-03']),
            'open': [3800.0, 3820.0],
            'high': [3850.0, 3870.0],
            'low': [3780.0, 3800.0],
            'close': [3820.0, 3840.0],
            'volume': [100000, 110000],
            'amount': [380000000, 420000000],
            'position': [50000, 52000],
        })
        mock_history.return_value = mock_df

        adapter = GMAdapter()
        adapter.db = mock_db

        df = adapter.get_future_daily(
            symbols='SHFE.rb2501',
            start_date='2025-01-02',
            end_date='2025-01-03'
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert 'date' in df.columns
        assert 'symbol' in df.columns
        assert 'open' in df.columns
        assert df['date'].tolist() == [20250102, 20250103]
        assert df['open'].iloc[0] == 3800.0

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    @patch('quantbox.adapters.gm_adapter.history')
    def test_get_future_daily_multiple_symbols(self, mock_history, mock_set_token, mock_config_loader):
        """测试获取多个合约日线数据"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SHFE']
        mock_config_loader.return_value = mock_config

        # Mock MongoDB
        mock_db = Mock()
        mock_coll = Mock()
        mock_coll.find_one.side_effect = [
            {'fut_code': 'RB', 'exchange': 'SHFE'},
            {'fut_code': 'HC', 'exchange': 'SHFE'}
        ]
        mock_db.future_contracts = mock_coll
        mock_config.get_mongodb_client.return_value = Mock()

        # Mock API 返回
        def mock_history_side_effect(*args, **kwargs):
            symbol = kwargs.get('symbol', args[0] if args else '')
            if 'rb' in symbol.lower():
                return pd.DataFrame({
                    'symbol': ['SHFE.rb2501'],
                    'eob': pd.to_datetime(['2025-01-02']),
                    'open': [3800.0],
                    'high': [3850.0],
                    'low': [3780.0],
                    'close': [3820.0],
                    'volume': [100000],
                    'amount': [380000000],
                    'position': [50000],
                })
            else:
                return pd.DataFrame({
                    'symbol': ['SHFE.hc2501'],
                    'eob': pd.to_datetime(['2025-01-02']),
                    'open': [3500.0],
                    'high': [3550.0],
                    'low': [3480.0],
                    'close': [3520.0],
                    'volume': [80000],
                    'amount': [280000000],
                    'position': [40000],
                })

        mock_history.side_effect = mock_history_side_effect

        adapter = GMAdapter()
        adapter.db = mock_db

        df = adapter.get_future_daily(
            symbols=['SHFE.rb2501', 'SHFE.hc2501'],
            start_date='2025-01-02',
            end_date='2025-01-02'
        )

        assert len(df) == 2
        symbols = df['symbol'].unique()
        assert len(symbols) == 2

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    def test_get_future_daily_without_symbols_raises_error(self, mock_set_token, mock_config_loader):
        """测试不提供合约代码应该抛出异常"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SHFE']
        mock_config.get_mongodb_client.return_value = Mock()
        mock_config_loader.return_value = mock_config

        adapter = GMAdapter()

        with pytest.raises(Exception, match="必须指定 symbols"):
            adapter.get_future_daily()


class TestGetFutureHoldings:
    """测试获取期货持仓数据"""

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    @patch('quantbox.adapters.gm_adapter.fut_get_transaction_rankings')
    def test_get_future_holdings_by_symbol(self, mock_get_holdings, mock_set_token, mock_config_loader):
        """测试按合约查询持仓数据"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SHFE']
        mock_config_loader.return_value = mock_config

        # Mock MongoDB
        mock_db = Mock()
        mock_coll = Mock()
        mock_coll.find_one.return_value = {'fut_code': 'RB', 'exchange': 'SHFE'}
        mock_db.future_contracts = mock_coll
        mock_config.get_mongodb_client.return_value = Mock()

        # Mock API 返回
        mock_df = pd.DataFrame({
            'symbol': ['SHFE.rb2501', 'SHFE.rb2501', 'SHFE.rb2501'],
            'trade_date': ['2025-01-02', '2025-01-02', '2025-01-02'],
            'member_name': ['中信期货', '永安期货', '国泰君安'],
            'indicator': ['volume', 'volume', 'volume'],
            'indicator_number': [10000, 9000, 8000],
            'indicator_change': [500, 400, 300],
        })
        mock_get_holdings.return_value = mock_df

        adapter = GMAdapter()
        adapter.db = mock_db

        df = adapter.get_future_holdings(
            symbols='SHFE.rb2501',
            date='2025-01-02'
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert 'date' in df.columns
        assert 'symbol' in df.columns
        assert 'broker' in df.columns
        assert 'vol' in df.columns

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    def test_get_future_holdings_without_params_raises_error(self, mock_set_token, mock_config_loader):
        """测试不提供参数应该抛出异常"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SHFE']
        mock_config.get_mongodb_client.return_value = Mock()
        mock_config_loader.return_value = mock_config

        adapter = GMAdapter()

        with pytest.raises(Exception, match="必须指定"):
            adapter.get_future_holdings()


class TestGetStockList:
    """测试获取股票列表"""

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    def test_get_stock_list_returns_empty(self, mock_set_token, mock_config_loader):
        """测试股票列表查询返回空（未实现）"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SSE']
        mock_config.get_mongodb_client.return_value = Mock()
        mock_config_loader.return_value = mock_config

        adapter = GMAdapter()

        with pytest.warns(UserWarning, match="尚未实现"):
            df = adapter.get_stock_list(exchanges='SSE')

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestFormatContractMethods:
    """测试合约格式化方法"""

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    def test_format_contract_by_exchange_shfe(self, mock_set_token, mock_config_loader):
        """测试上期所合约格式化（小写）"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SHFE']
        mock_config.get_mongodb_client.return_value = Mock()
        mock_config_loader.return_value = mock_config

        adapter = GMAdapter()
        result = adapter._format_contract_by_exchange('SHFE', 'RB2501')

        assert result == 'SHFE.rb2501'

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    def test_format_contract_by_exchange_cffex(self, mock_set_token, mock_config_loader):
        """测试中金所合约格式化（大写）"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['CFFEX']
        mock_config.get_mongodb_client.return_value = Mock()
        mock_config_loader.return_value = mock_config

        adapter = GMAdapter()
        result = adapter._format_contract_by_exchange('CFFEX', 'if2501')

        assert result == 'CFFEX.IF2501'

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    def test_format_contract_by_exchange_czce(self, mock_set_token, mock_config_loader):
        """测试郑商所合约格式化（3位年月格式）"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['CZCE']
        mock_config.get_mongodb_client.return_value = Mock()
        mock_config_loader.return_value = mock_config

        adapter = GMAdapter()
        result = adapter._format_contract_by_exchange('CZCE', 'SR2501')

        # 郑商所应该转换为 3 位年月格式
        assert result == 'CZCE.SR501'


class TestErrorHandling:
    """测试错误处理"""

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    @patch('quantbox.adapters.gm_adapter.get_trading_dates_by_year')
    def test_get_trade_calendar_error_warning(self, mock_get_dates, mock_set_token, mock_config_loader):
        """测试交易日历查询错误（发出警告，返回空结果）"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SHFE']
        mock_config.get_mongodb_client.return_value = Mock()
        mock_config_loader.return_value = mock_config

        # Mock API 抛出异常
        mock_get_dates.side_effect = Exception("API Error")

        adapter = GMAdapter()

        # 应该发出警告而不是抛出异常
        with pytest.warns(UserWarning, match="获取交易所 SHFE 的交易日历失败"):
            df = adapter.get_trade_calendar(exchanges='SHFE')

        # 返回空结果
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    @patch('quantbox.adapters.gm_adapter.history')
    def test_get_future_daily_error_warning(self, mock_history, mock_set_token, mock_config_loader):
        """测试日线数据查询错误（发出警告，返回空结果）"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SHFE']
        mock_config_loader.return_value = mock_config

        # Mock MongoDB
        mock_db = Mock()
        mock_coll = Mock()
        mock_coll.find_one.return_value = {'fut_code': 'RB', 'exchange': 'SHFE'}
        mock_db.future_contracts = mock_coll
        mock_config.get_mongodb_client.return_value = Mock()

        # Mock API 抛出异常
        mock_history.side_effect = Exception("API Error")

        adapter = GMAdapter()
        adapter.db = mock_db

        # 应该发出警告而不是抛出异常
        with pytest.warns(UserWarning, match="获取合约 SHFE.rb2501 数据失败"):
            df = adapter.get_future_daily(symbols='SHFE.rb2501')

        # 返回空结果
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    @patch('quantbox.adapters.gm_adapter.fut_get_transaction_rankings')
    def test_get_future_holdings_error_warning(self, mock_get_holdings, mock_set_token, mock_config_loader):
        """测试持仓数据查询错误（发出警告，返回空结果）"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SHFE']
        mock_config_loader.return_value = mock_config

        # Mock MongoDB
        mock_db = Mock()
        mock_coll = Mock()
        mock_coll.find_one.return_value = {'fut_code': 'RB', 'exchange': 'SHFE'}
        mock_db.future_contracts = mock_coll
        mock_config.get_mongodb_client.return_value = Mock()

        # Mock API 抛出异常
        mock_get_holdings.side_effect = Exception("API Error")

        adapter = GMAdapter()
        adapter.db = mock_db

        # 应该发出警告而不是抛出异常
        with pytest.warns(UserWarning, match="获取持仓数据失败"):
            df = adapter.get_future_holdings(symbols='SHFE.rb2501')

        # 返回空结果
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    @patch('quantbox.adapters.gm_adapter.get_config_loader')
    @patch('quantbox.adapters.gm_adapter.set_token')
    def test_get_trade_calendar_date_range_error(self, mock_set_token, mock_config_loader):
        """测试日期范围错误（应该抛出异常）"""
        from quantbox.adapters.gm_adapter import GMAdapter

        # Mock 配置
        mock_config = Mock()
        mock_config.get_gm_token.return_value = "test_token"
        mock_config.list_exchanges.return_value = ['SHFE']
        mock_config.get_mongodb_client.return_value = Mock()
        mock_config_loader.return_value = mock_config

        adapter = GMAdapter()

        # 起始日期晚于结束日期应该抛出异常（被包装在 Exception 中）
        with pytest.raises(Exception, match="获取交易日历失败.*起始日期.*必须早于结束日期"):
            adapter.get_trade_calendar(
                exchanges='SHFE',
                start_date='2025-12-31',
                end_date='2025-01-01'
            )
