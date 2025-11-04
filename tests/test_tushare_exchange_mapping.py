"""
测试 Tushare 交易所映射修复

验证 Tushare API 参数和返回值后缀的正确映射。
"""

import pytest
from quantbox.util.exchange_utils import get_exchange_for_data_source
from quantbox.util.tools import util_format_stock_symbols, _get_cached_exchange_mapping


class TestTushareExchangeMapping:
    """测试 Tushare 交易所映射功能"""

    def test_tushare_api_mapping(self):
        """测试 Tushare API 参数映射"""
        # 上海证券交易所 API 参数应该是 "SSE"
        assert get_exchange_for_data_source("SHSE", "tushare", usage="api") == "SSE"
        # 深圳证券交易所 API 参数应该是 "SZSE"
        assert get_exchange_for_data_source("SZSE", "tushare", usage="api") == "SZSE"
        # 期货交易所应该保持原样
        assert get_exchange_for_data_source("SHFE", "tushare", usage="api") == "SHFE"
        assert get_exchange_for_data_source("DCE", "tushare", usage="api") == "DCE"

    def test_tushare_suffix_mapping(self):
        """测试 Tushare 返回值后缀映射"""
        # 上海股票后缀应该是 "SH"
        assert get_exchange_for_data_source("SHSE", "tushare", usage="suffix") == "SH"
        # 深圳股票后缀应该是 "SZ"
        assert get_exchange_for_data_source("SZSE", "tushare", usage="suffix") == "SZ"
        # 期货合约后缀
        assert get_exchange_for_data_source("SHFE", "tushare", usage="suffix") == "SHF"
        assert get_exchange_for_data_source("DCE", "tushare", usage="suffix") == "DCE"
        assert get_exchange_for_data_source("CZCE", "tushare", usage="suffix") == "ZCE"

    def test_other_data_sources_mapping(self):
        """测试其他数据源映射（应该不受影响）"""
        # 掘金数据源
        assert get_exchange_for_data_source("SHSE", "goldminer", usage="api") == "SHSE"
        assert get_exchange_for_data_source("SZSE", "goldminer", usage="api") == "SZSE"

        # 聚宽数据源
        assert get_exchange_for_data_source("SHSE", "joinquant", usage="api") == "XSHG"
        assert get_exchange_for_data_source("SZSE", "joinquant", usage="api") == "XSHE"

    def test_util_format_stock_symbols_tushare(self):
        """测试股票代码格式化功能 - Tushare 格式"""
        # 清除缓存以确保使用最新配置
        _get_cached_exchange_mapping.cache_clear()

        # 测试上海股票（6开头）
        sh_stocks = util_format_stock_symbols(["600000", "600001"], format="tushare")
        expected_sh = ["600000.SH", "600001.SH"]
        assert sh_stocks == expected_sh, f"Expected {expected_sh}, got {sh_stocks}"

        # 测试深圳股票（0、3开头）
        sz_stocks = util_format_stock_symbols(["000001", "300001"], format="tushare")
        expected_sz = ["000001.SZ", "300001.SZ"]
        assert sz_stocks == expected_sz, f"Expected {expected_sz}, got {sz_stocks}"

    def test_util_format_stock_symbols_other_formats(self):
        """测试股票代码格式化功能 - 其他格式"""
        # 清除缓存
        _get_cached_exchange_mapping.cache_clear()

        # 测试掘金格式
        gm_stocks = util_format_stock_symbols(["600000", "000001"], format="goldminer")
        expected_gm = ["SHSE.600000", "SZSE.000001"]
        assert gm_stocks == expected_gm, f"Expected {expected_gm}, got {gm_stocks}"

        # 测试聚宽格式
        jq_stocks = util_format_stock_symbols(["600000", "000001"], format="joinquant")
        expected_jq = ["600000.XSHG", "000001.XSHE"]
        assert jq_stocks == expected_jq, f"Expected {expected_jq}, got {jq_stocks}"

    def test_cached_mapping_function(self):
        """测试缓存的映射函数"""
        # 清除缓存
        _get_cached_exchange_mapping.cache_clear()

        # 测试 API 参数映射缓存
        api_result1 = _get_cached_exchange_mapping("SHSE", "tushare", "api")
        api_result2 = _get_cached_exchange_mapping("SHSE", "tushare", "api")
        assert api_result1 == "SSE"
        assert api_result2 == "SSE"
        assert _get_cached_exchange_mapping.cache_info().hits > 0

        # 测试后缀映射缓存
        suffix_result1 = _get_cached_exchange_mapping("SHSE", "tushare", "suffix")
        suffix_result2 = _get_cached_exchange_mapping("SHSE", "tushare", "suffix")
        assert suffix_result1 == "SH"
        assert suffix_result2 == "SH"

    def test_backward_compatibility(self):
        """测试向后兼容性（默认 usage="api"）"""
        # 不指定 usage 参数时，应该默认为 "api"
        api_result = get_exchange_for_data_source("SHSE", "tushare")
        assert api_result == "SSE"

        suffix_result = get_exchange_for_data_source("SHSE", "tushare", "suffix")
        assert suffix_result == "SH"

    def test_edge_cases(self):
        """测试边界情况"""
        # 测试不存在的交易所应该抛出异常
        try:
            get_exchange_for_data_source("UNKNOWN", "tushare", "api")
            assert False, "Should raise ValueError for unknown exchange"
        except ValueError:
            pass  # 预期的异常

        # 测试不存在的数据源
        unknown_source = get_exchange_for_data_source("SHSE", "unknown_source", "api")
        assert unknown_source == "SHSE"

        # 测试空字符串
        try:
            get_exchange_for_data_source("", "tushare", "api")
            assert False, "Should raise ValueError for empty exchange"
        except ValueError:
            pass  # 预期的异常


if __name__ == "__main__":
    pytest.main([__file__, "-v"])