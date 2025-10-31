"""
交易所工具模块单元测试
"""
import pytest
import sys
import os

# 为了测试新模块，临时导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quantbox.util.exchange_utils import (
    normalize_exchange,
    denormalize_exchange,
    validate_exchange,
    validate_exchanges,
    is_stock_exchange,
    is_futures_exchange,
    get_exchange_info,
    get_all_exchanges,
    STOCK_EXCHANGES,
    FUTURES_EXCHANGES,
    ALL_EXCHANGES,
)


class TestNormalizeExchange:
    """测试 normalize_exchange 函数"""
    
    def test_standard_codes(self):
        """测试标准代码"""
        assert normalize_exchange("SHSE") == "SHSE"
        assert normalize_exchange("SZSE") == "SZSE"
        assert normalize_exchange("SHFE") == "SHFE"
        assert normalize_exchange("DCE") == "DCE"
        assert normalize_exchange("CZCE") == "CZCE"
        assert normalize_exchange("CFFEX") == "CFFEX"
        assert normalize_exchange("INE") == "INE"
        assert normalize_exchange("BSE") == "BSE"
    
    def test_aliases(self):
        """测试别名转换"""
        assert normalize_exchange("SSE") == "SHSE"
        assert normalize_exchange("SHF") == "SHFE"
        assert normalize_exchange("ZCE") == "CZCE"
    
    def test_case_insensitive(self):
        """测试大小写不敏感"""
        assert normalize_exchange("sse") == "SHSE"
        assert normalize_exchange("Sse") == "SHSE"
        assert normalize_exchange("shfe") == "SHFE"
    
    def test_whitespace_handling(self):
        """测试空格处理"""
        assert normalize_exchange(" SHSE ") == "SHSE"
        assert normalize_exchange("\tSSE\t") == "SHSE"
    
    def test_invalid_exchange(self):
        """测试无效的交易所代码"""
        with pytest.raises(ValueError, match="Invalid exchange code"):
            normalize_exchange("INVALID")
        with pytest.raises(ValueError, match="Invalid exchange code"):
            normalize_exchange("XYZ")
    
    def test_empty_exchange(self):
        """测试空字符串"""
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_exchange("")
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_exchange("   ")


class TestDenormalizeExchange:
    """测试 denormalize_exchange 函数"""
    
    def test_tushare_target(self):
        """测试 TuShare 目标格式"""
        # Tushare 使用简称：SH/SZ/BJ
        assert denormalize_exchange("SHSE", "tushare") == "SH"
        assert denormalize_exchange("SZSE", "tushare") == "SZ"
        assert denormalize_exchange("BSE", "tushare") == "BJ"
        # 期货交易所
        assert denormalize_exchange("SHFE", "tushare") == "SHF"
        assert denormalize_exchange("CZCE", "tushare") == "ZCE"
        assert denormalize_exchange("DCE", "tushare") == "DCE"
    
    def test_goldminer_target(self):
        """测试掘金量化目标格式"""
        assert denormalize_exchange("SHSE", "goldminer") == "SHSE"
        assert denormalize_exchange("SHFE", "goldminer") == "SHFE"
        assert denormalize_exchange("DCE", "goldminer") == "DCE"
    
    def test_invalid_target(self):
        """测试无效的目标"""
        with pytest.raises(ValueError, match="Unsupported target"):
            denormalize_exchange("SHSE", "unknown")
    
    def test_invalid_exchange(self):
        """测试无效的交易所代码"""
        with pytest.raises(ValueError, match="Invalid standard exchange code"):
            denormalize_exchange("SSE", "tushare")  # SSE 是别名，不是标准代码


class TestValidateExchanges:
    """测试 validate_exchanges 函数"""
    
    def test_none_default_all(self):
        """测试 None 输入，默认所有交易所"""
        result = validate_exchanges(None, "all")
        assert len(result) == 8
        assert set(result) == set(ALL_EXCHANGES)
    
    def test_none_default_stock(self):
        """测试 None 输入，默认股票交易所"""
        result = validate_exchanges(None, "stock")
        assert len(result) == 3
        assert set(result) == set(STOCK_EXCHANGES)
    
    def test_none_default_futures(self):
        """测试 None 输入，默认期货交易所"""
        result = validate_exchanges(None, "futures")
        assert len(result) == 5
        assert set(result) == set(FUTURES_EXCHANGES)
    
    def test_single_string(self):
        """测试单个字符串输入"""
        result = validate_exchanges("SSE")
        assert result == ["SHSE"]
    
    def test_list_input(self):
        """测试列表输入"""
        result = validate_exchanges(["SSE", "SZSE", "SHFE"])
        assert result == ["SHSE", "SZSE", "SHFE"]
    
    def test_comma_separated_string(self):
        """测试逗号分隔的字符串"""
        result = validate_exchanges("SSE, SZSE, SHFE")
        assert result == ["SHSE", "SZSE", "SHFE"]
    
    def test_deduplication(self):
        """测试去重功能"""
        result = validate_exchanges(["SSE", "SHSE", "SSE"])
        assert result == ["SHSE"]
    
    def test_empty_string_filtering(self):
        """测试过滤空字符串"""
        result = validate_exchanges(["SSE", "", "SZSE", "  "])
        assert "SHSE" in result
        assert "SZSE" in result
    
    def test_invalid_default_type(self):
        """测试无效的 default_type"""
        with pytest.raises(ValueError, match="Invalid default_type"):
            validate_exchanges(None, "invalid")


class TestExchangeTypeCheckers:
    """测试交易所类型判断函数"""
    
    def test_is_stock_exchange(self):
        """测试股票交易所判断"""
        assert is_stock_exchange("SHSE") is True
        assert is_stock_exchange("SSE") is True
        assert is_stock_exchange("SZSE") is True
        assert is_stock_exchange("BSE") is True
        assert is_stock_exchange("SHFE") is False
        assert is_stock_exchange("DCE") is False
    
    def test_is_futures_exchange(self):
        """测试期货交易所判断"""
        assert is_futures_exchange("SHFE") is True
        assert is_futures_exchange("SHF") is True
        assert is_futures_exchange("DCE") is True
        assert is_futures_exchange("CZCE") is True
        assert is_futures_exchange("CFFEX") is True
        assert is_futures_exchange("INE") is True
        assert is_futures_exchange("SHSE") is False
        assert is_futures_exchange("SZSE") is False


class TestGetExchangeInfo:
    """测试 get_exchange_info 函数"""
    
    def test_stock_exchange_info(self):
        """测试股票交易所信息"""
        info = get_exchange_info("SSE")
        assert info["code"] == "SHSE"
        assert info["name"] == "上海证券交易所"
        assert info["type"] == "stock"
        assert "SSE" in info["aliases"]
    
    def test_futures_exchange_info(self):
        """测试期货交易所信息"""
        info = get_exchange_info("SHFE")
        assert info["code"] == "SHFE"
        assert info["name"] == "上海期货交易所"
        assert info["type"] == "futures"
    
    def test_exchange_with_no_aliases(self):
        """测试没有别名的交易所"""
        info = get_exchange_info("DCE")
        assert info["code"] == "DCE"
        assert info["aliases"] == []
    
    def test_invalid_exchange(self):
        """测试无效交易所"""
        with pytest.raises(ValueError):
            get_exchange_info("INVALID")


class TestGetAllExchanges:
    """测试 get_all_exchanges 函数"""
    
    def test_all_exchanges(self):
        """测试获取所有交易所"""
        result = get_all_exchanges()
        assert len(result) == 8
        assert "SHSE" in result
        assert "SZSE" in result
        assert "SHFE" in result
    
    def test_stock_exchanges(self):
        """测试获取股票交易所"""
        result = get_all_exchanges("stock")
        assert len(result) == 3
        assert all(is_stock_exchange(e) for e in result)
    
    def test_futures_exchanges(self):
        """测试获取期货交易所"""
        result = get_all_exchanges("futures")
        assert len(result) == 5
        assert all(is_futures_exchange(e) for e in result)
    
    def test_invalid_type(self):
        """测试无效类型"""
        with pytest.raises(ValueError, match="Invalid exchange_type"):
            get_all_exchanges("invalid")


class TestIntegration:
    """集成测试"""
    
    def test_round_trip_normalization(self):
        """测试标准化和反标准化的往返转换"""
        # SH -> SHSE -> SH
        normalized = normalize_exchange("SH")
        assert normalized == "SHSE"
        denormalized = denormalize_exchange(normalized, "tushare")
        assert denormalized == "SH"
    
    def test_validate_and_normalize_consistency(self):
        """测试 validate_exchange 和 normalize_exchange 的一致性"""
        test_codes = ["SSE", "SHSE", "SHF", "SHFE", "ZCE", "CZCE"]
        for code in test_codes:
            assert validate_exchange(code) == normalize_exchange(code)
    
    def test_exchange_lists_consistency(self):
        """测试交易所列表的一致性"""
        all_ex = set(get_all_exchanges())
        stock_ex = set(get_all_exchanges("stock"))
        futures_ex = set(get_all_exchanges("futures"))
        
        # 股票和期货交易所不应有重叠
        assert len(stock_ex & futures_ex) == 0
        
        # 股票 + 期货 = 所有
        assert stock_ex | futures_ex == all_ex


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
