import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from quantbox.fetchers.fetcher_tushare import TSFetcher

@pytest.fixture
def mock_tushare_pro():
    mock_pro = MagicMock()
    sample_data = pd.DataFrame({
        'ts_code': ['CU2306.SHFE', 'RB2306.SHFE'],
        'symbol': ['CU2306', 'RB2306'],
        'name': ['铜2306', '螺纹钢2306'],
        'list_date': ['20230101', '20230101'],
        'delist_date': ['20230630', '20230630']
    })
    mock_pro.fut_basic.return_value = sample_data
    return mock_pro

@pytest.fixture
def ts_fetcher(mock_tushare_pro):
    with patch('tushare.pro_api', return_value=mock_tushare_pro):
        fetcher = TSFetcher(token='dummy_token')
        return fetcher

def test_fetch_get_future_contracts_basic(ts_fetcher):
    """测试基本的期货合约获取功能"""
    df = ts_fetcher.fetch_get_future_contracts(exchange='SHFE')
    
    assert isinstance(df, pd.DataFrame)
    assert 'qbcode' in df.columns
    assert 'chinese_name' in df.columns
    assert len(df) == 2
    assert df['chinese_name'].tolist() == ['铜', '螺纹钢']
    assert df['symbol'].tolist() == ['cu2306', 'rb2306']  # 应该转换为小写

def test_fetch_get_future_contracts_with_spec_name(ts_fetcher):
    """测试指定品种名称的期货合约获取功能"""
    df = ts_fetcher.fetch_get_future_contracts(exchange='SHFE', spec_name='铜')
    
    assert len(df) == 1
    assert df.iloc[0]['chinese_name'] == '铜'

def test_fetch_get_future_contracts_with_cursor_date(ts_fetcher):
    """测试使用日期过滤的期货合约获取功能"""
    df = ts_fetcher.fetch_get_future_contracts(
        exchange='SHFE',
        cursor_date='2023-03-15'
    )
    
    assert len(df) == 2  # 在有效期内的合约
    
    df = ts_fetcher.fetch_get_future_contracts(
        exchange='SHFE',
        cursor_date='2023-07-01'
    )
    
    assert len(df) == 0  # 已经过期的合约

def test_fetch_get_future_contracts_with_fields(ts_fetcher):
    """测试自定义字段的期货合约获取功能"""
    df = ts_fetcher.fetch_get_future_contracts(
        exchange='SHFE',
        fields=['symbol', 'name']
    )
    
    required_fields = ['qbcode', 'symbol', 'name', 'list_date', 'delist_date']
    assert all(field in df.columns for field in required_fields)
