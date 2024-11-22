import pytest
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict

from quantbox.fetchers.fetcher_tushare import TSFetcher
from quantbox.fetchers.fetcher_goldminer import GMFetcher

class TestHoldingsFetchers:
    """测试期货持仓数据获取功能"""

    @pytest.fixture(scope="class")
    def ts_fetcher(self):
        """创建 TSFetcher 实例"""
        return TSFetcher()

    @pytest.fixture(scope="class")
    def gm_fetcher(self):
        """创建 GMFetcher 实例"""
        return GMFetcher()

    @pytest.fixture
    def sample_date(self):
        """获取最近的交易日"""
        today = datetime.today()
        if today.weekday() >= 5:  # 周末
            return (today - timedelta(days=today.weekday()-4)).strftime('%Y-%m-%d')
        return today.strftime('%Y-%m-%d')

    def verify_holdings_data(self, df: pd.DataFrame):
        """验证持仓数据格式"""
        # 检查必需字段
        required_fields = [
            'trade_date', 'symbol', 'broker',
            'vol', 'vol_chg',
            'long_hld', 'long_chg',
            'short_hld', 'short_chg',
            'exchange', 'datestamp'
        ]
        assert all(field in df.columns for field in required_fields)

        # 检查数据类型
        assert pd.api.types.is_datetime64_any_dtype(pd.to_datetime(df['trade_date']))
        assert pd.api.types.is_string_dtype(df['symbol'])
        assert pd.api.types.is_string_dtype(df['broker'])
        assert pd.api.types.is_numeric_dtype(df['vol'])
        assert pd.api.types.is_numeric_dtype(df['long_hld'])
        assert pd.api.types.is_numeric_dtype(df['short_hld'])
        assert pd.api.types.is_string_dtype(df['exchange'])
        assert pd.api.types.is_numeric_dtype(df['datestamp'])

        # 检查数值范围
        assert (df['vol'] >= 0).all()
        assert (df['long_hld'] >= 0).all()
        assert (df['short_hld'] >= 0).all()

        # 检查日期格式
        assert all(pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d') == df['trade_date'])

    def test_basic_fetch(self, ts_fetcher, gm_fetcher, sample_date):
        """测试基本的数据获取功能"""
        # 测试单个交易所
        exchanges = ['DCE']
        symbols = ['M2501']

        # 测试 TSFetcher
        ts_df = ts_fetcher.fetch_get_holdings(
            exchanges=exchanges,
            cursor_date=sample_date,
            symbols=symbols
        )
        assert not ts_df.empty
        self.verify_holdings_data(ts_df)

        # 测试 GMFetcher
        gm_df = gm_fetcher.fetch_get_holdings(
            exchanges=exchanges,
            cursor_date=sample_date,
            symbols=symbols
        )
        assert not gm_df.empty
        self.verify_holdings_data(gm_df)

        # 比较两个数据源的结果
        assert ts_df.shape[1] == gm_df.shape[1]  # 列数相同
        assert set(ts_df.columns) == set(gm_df.columns)  # 字段名相同

    def test_multiple_exchanges(self, ts_fetcher, gm_fetcher, sample_date):
        """测试多交易所数据获取"""
        exchanges = ['DCE', 'SHFE']

        ts_df = ts_fetcher.fetch_get_holdings(
            exchanges=exchanges,
            cursor_date=sample_date
        )
        assert not ts_df.empty
        assert set(ts_df['exchange'].unique()) == set(exchanges)
        self.verify_holdings_data(ts_df)

        gm_df = gm_fetcher.fetch_get_holdings(
            exchanges=exchanges,
            cursor_date=sample_date
        )
        assert not gm_df.empty
        assert set(gm_df['exchange'].unique()) == set(exchanges)
        self.verify_holdings_data(gm_df)

    def test_date_range(self, ts_fetcher, gm_fetcher):
        """测试日期范围数据获取"""
        end_date = datetime.today()
        start_date = end_date - timedelta(days=5)

        ts_df = ts_fetcher.fetch_get_holdings(
            exchanges=['DCE'],
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        assert not ts_df.empty
        self.verify_holdings_data(ts_df)

        gm_df = gm_fetcher.fetch_get_holdings(
            exchanges=['DCE'],
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        assert not gm_df.empty
        self.verify_holdings_data(gm_df)

    @pytest.mark.parametrize("invalid_input", [
        {'exchanges': ['INVALID']},
        {'cursor_date': 'INVALID'},
        {'symbols': ['INVALID']},
    ])
    def test_invalid_inputs(self, ts_fetcher, gm_fetcher, invalid_input):
        """测试无效输入处理"""
        with pytest.raises(Exception):
            ts_fetcher.fetch_get_holdings(**invalid_input)

        with pytest.raises(Exception):
            gm_fetcher.fetch_get_holdings(**invalid_input)

    def test_empty_result_handling(self, ts_fetcher, gm_fetcher):
        """测试空结果处理"""
        # 使用不太可能有数据的日期
        old_date = "1990-01-01"

        ts_df = ts_fetcher.fetch_get_holdings(
            exchanges=['DCE'],
            cursor_date=old_date
        )
        assert ts_df.empty or len(ts_df) == 0

        gm_df = gm_fetcher.fetch_get_holdings(
            exchanges=['DCE'],
            cursor_date=old_date
        )
        assert gm_df.empty or len(gm_df) == 0

    def test_data_consistency(self, ts_fetcher, gm_fetcher, sample_date):
        """测试数据一致性"""
        exchanges = ['DCE']
        symbols = ['M2501']

        # 获取两个数据源的数据
        ts_df = ts_fetcher.fetch_get_holdings(
            exchanges=exchanges,
            cursor_date=sample_date,
            symbols=symbols
        )
        gm_df = gm_fetcher.fetch_get_holdings(
            exchanges=exchanges,
            cursor_date=sample_date,
            symbols=symbols
        )

        if not ts_df.empty and not gm_df.empty:
            # 对比关键字段的统计值
            ts_stats = ts_df.agg({
                'vol': ['sum', 'mean'],
                'long_hld': ['sum', 'mean'],
                'short_hld': ['sum', 'mean']
            })
            gm_stats = gm_df.agg({
                'vol': ['sum', 'mean'],
                'long_hld': ['sum', 'mean'],
                'short_hld': ['sum', 'mean']
            })

            # 允许一定的误差范围
            pd.testing.assert_frame_equal(
                ts_stats.round(2),
                gm_stats.round(2),
                check_exact=False,
                rtol=0.1  # 允许10%的相对误差
            )

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, ts_fetcher, gm_fetcher, sample_date):
        """测试并发请求处理"""
        import asyncio

        async def fetch_data(fetcher, exchange):
            return fetcher.fetch_get_holdings(
                exchanges=[exchange],
                cursor_date=sample_date
            )

        exchanges = ['DCE', 'SHFE', 'CZCE']

        # 测试 TSFetcher 并发
        ts_tasks = [fetch_data(ts_fetcher, ex) for ex in exchanges]
        ts_results = await asyncio.gather(*ts_tasks)

        for df in ts_results:
            assert not df.empty
            self.verify_holdings_data(df)

        # 测试 GMFetcher 并发
        gm_tasks = [fetch_data(gm_fetcher, ex) for ex in exchanges]
        gm_results = await asyncio.gather(*gm_tasks)

        for df in gm_results:
            assert not df.empty
            self.verify_holdings_data(df)

    def test_large_data_handling(self, ts_fetcher, gm_fetcher):
        """测试大数据量处理"""
        # 获取较长时间范围的数据
        end_date = datetime.today()
        start_date = end_date - timedelta(days=30)

        ts_df = ts_fetcher.fetch_get_holdings(
            exchanges=['DCE', 'SHFE'],
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        assert len(ts_df) > 1000  # 确保数据量足够大
        self.verify_holdings_data(ts_df)

        gm_df = gm_fetcher.fetch_get_holdings(
            exchanges=['DCE', 'SHFE'],
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        assert len(gm_df) > 1000
        self.verify_holdings_data(gm_df)

if __name__ == '__main__':
    pytest.main(['-v', 'test_fetchers.py'])
