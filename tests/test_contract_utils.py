"""
contract_utils_new 模块的测试套件

测试合约代码的解析、格式转换、验证等功能
"""

import pytest
from typing import List

from quantbox.util.contract_utils import (
    ContractInfo,
    ContractFormat,
    AssetType,
    parse_contract,
    format_contract,
    format_contracts,
    validate_contract,
    validate_contracts,
    split_contract,
    get_underlying,
    get_contract_month,
    is_main_contract,
    normalize_contract,
    normalize_contracts,
)
# 不需要导入 ExchangeType，直接使用字符串


class TestContractInfo:
    """测试 ContractInfo 类"""
    
    def test_init_futures(self):
        """测试期货合约信息初始化"""
        info = ContractInfo(
            exchange="SHFE",
            symbol="rb2501",
            asset_type=AssetType.FUTURES,
            underlying="rb",
            year=2025,
            month=1,
        )
        assert info.exchange == "SHFE"
        assert info.symbol == "rb2501"
        assert info.asset_type == AssetType.FUTURES
        assert info.underlying == "rb"
        assert info.year == 2025
        assert info.month == 1
    
    def test_init_stock(self):
        """测试股票信息初始化"""
        info = ContractInfo(
            exchange="SHSE",
            symbol="600000",
            asset_type=AssetType.STOCK,
        )
        assert info.exchange == "SHSE"
        assert info.symbol == "600000"
        assert info.asset_type == AssetType.STOCK
        assert info.underlying is None
    
    def test_to_standard(self):
        """测试转换为标准格式"""
        info = ContractInfo(
            exchange="SHFE",
            symbol="rb2501",
            asset_type=AssetType.FUTURES,
        )
        assert info.to_standard() == "SHFE.rb2501"
    
    def test_is_futures(self):
        """测试期货判断"""
        info_futures = ContractInfo(
            exchange="SHFE",
            symbol="rb2501",
            asset_type=AssetType.FUTURES,
        )
        info_stock = ContractInfo(
            exchange="SHSE",
            symbol="600000",
            asset_type=AssetType.STOCK,
        )
        assert info_futures.is_futures() is True
        assert info_stock.is_futures() is False
    
    def test_is_stock(self):
        """测试股票判断"""
        info_futures = ContractInfo(
            exchange="SHFE",
            symbol="rb2501",
            asset_type=AssetType.FUTURES,
        )
        info_stock = ContractInfo(
            exchange="SHSE",
            symbol="600000",
            asset_type=AssetType.STOCK,
        )
        assert info_futures.is_stock() is False
        assert info_stock.is_stock() is True


class TestParseContract:
    """测试 parse_contract 函数"""
    
    def test_parse_standard_futures(self):
        """测试解析标准格式期货合约"""
        info = parse_contract("SHFE.rb2501")
        assert info.exchange == "SHFE"
        assert info.symbol == "rb2501"
        assert info.asset_type == AssetType.FUTURES
        assert info.underlying == "rb"
        assert info.year == 2025
        assert info.month == 1
    
    def test_parse_tushare_futures(self):
        """测试解析 Tushare 格式期货合约"""
        info = parse_contract("rb2501.SHF")
        assert info.exchange == "SHFE"
        assert info.symbol == "rb2501"
        assert info.asset_type == AssetType.FUTURES
        assert info.underlying == "rb"
    
    def test_parse_czce_3digit(self):
        """测试解析郑商所3位年月格式"""
        info = parse_contract("SR501", default_exchange="CZCE")
        assert info.exchange == "CZCE"
        assert info.symbol == "sr2501"  # 标准化为4位
        assert info.underlying == "sr"
        assert info.year == 2025
        assert info.month == 1
    
    def test_parse_czce_4digit(self):
        """测试解析郑商所4位年月格式"""
        info = parse_contract("CZCE.SR2501")
        assert info.exchange == "CZCE"
        assert info.symbol == "sr2501"
        assert info.underlying == "sr"
        assert info.year == 2025
        assert info.month == 1
    
    def test_parse_stock(self):
        """测试解析股票代码"""
        info = parse_contract("SHSE.600000")
        assert info.exchange == "SHSE"
        assert info.symbol == "600000"
        assert info.asset_type == AssetType.STOCK
        assert info.underlying is None
    
    def test_parse_with_default_exchange(self):
        """测试使用默认交易所解析"""
        info = parse_contract("rb2501", default_exchange="SHFE")
        assert info.exchange == "SHFE"
        assert info.symbol == "rb2501"
    
    def test_parse_uppercase_symbol(self):
        """测试解析大写合约代码"""
        info = parse_contract("SHFE.RB2501")
        assert info.symbol == "rb2501"  # 应该被转换为小写
    
    def test_parse_empty_contract(self):
        """测试解析空合约代码"""
        with pytest.raises(ValueError, match="合约代码不能为空"):
            parse_contract("")
    
    def test_parse_no_exchange(self):
        """测试解析无交易所的合约代码且未提供默认值"""
        with pytest.raises(ValueError, match="未包含交易所信息"):
            parse_contract("rb2501")
    
    def test_parse_invalid_format(self):
        """测试解析无效格式"""
        with pytest.raises(ValueError, match="合约代码格式无效|无法识别"):
            parse_contract("invalid.code.format")
    
    def test_parse_invalid_futures_format(self):
        """测试解析无效期货代码格式"""
        with pytest.raises(ValueError, match="期货合约代码格式无效"):
            parse_contract("SHFE.invalid")


class TestFormatContract:
    """测试 format_contract 函数"""
    
    def test_format_to_standard(self):
        """测试转换为标准格式"""
        result = format_contract("rb2501.SHF", ContractFormat.STANDARD)
        assert result == "SHFE.rb2501"
    
    def test_format_to_goldminer(self):
        """测试转换为掘金格式"""
        result = format_contract("SHFE.rb2501", ContractFormat.GOLDMINER)
        assert result == "SHFE.RB2501"
    
    def test_format_to_tushare(self):
        """测试转换为 Tushare 格式"""
        result = format_contract("SHFE.rb2501", ContractFormat.TUSHARE)
        assert result == "rb2501.SHF"
    
    def test_format_to_tushare_czce(self):
        """测试转换郑商所合约为 Tushare 格式"""
        result = format_contract("CZCE.SR2501", ContractFormat.TUSHARE)
        assert result == "sr2501.ZCE"
    
    def test_format_to_joinquant(self):
        """测试转换为聚宽格式"""
        result = format_contract("SHFE.rb2501", ContractFormat.JOINQUANT)
        assert result == "rb2501.XSGE"
    
    def test_format_to_plain(self):
        """测试转换为纯代码格式"""
        result = format_contract("SHFE.rb2501", ContractFormat.PLAIN)
        assert result == "rb2501"
    
    def test_format_string_target(self):
        """测试使用字符串指定目标格式"""
        result = format_contract("SHFE.rb2501", "tushare")
        assert result == "rb2501.SHF"
    
    def test_format_with_default_exchange(self):
        """测试带默认交易所的格式转换"""
        result = format_contract("rb2501", ContractFormat.TUSHARE, default_exchange="SHFE")
        assert result == "rb2501.SHF"
    
    def test_format_invalid_target(self):
        """测试无效的目标格式"""
        with pytest.raises(ValueError, match="不支持的格式"):
            format_contract("SHFE.rb2501", "invalid_format")
    
    def test_format_stock_to_tushare(self):
        """测试转换股票代码为 Tushare 格式"""
        result = format_contract("SHSE.600000", ContractFormat.TUSHARE)
        assert result == "600000.SH"


class TestFormatContracts:
    """测试 format_contracts 函数（批量转换）"""
    
    def test_format_list(self):
        """测试批量转换列表"""
        contracts = ["SHFE.rb2501", "DCE.m2505"]
        results = format_contracts(contracts, ContractFormat.TUSHARE)
        assert results == ["rb2501.SHF", "m2505.DCE"]
    
    def test_format_comma_separated_string(self):
        """测试转换逗号分隔的字符串"""
        contracts = "SHFE.rb2501, DCE.m2505, CZCE.SR2509"
        results = format_contracts(contracts, ContractFormat.TUSHARE)
        assert results == ["rb2501.SHF", "m2505.DCE", "sr2509.ZCE"]
    
    def test_format_with_default_exchange(self):
        """测试批量转换时使用默认交易所"""
        contracts = ["rb2501", "hc2505"]
        results = format_contracts(contracts, ContractFormat.STANDARD, default_exchange="SHFE")
        assert results == ["SHFE.rb2501", "SHFE.hc2505"]
    
    def test_format_single_string(self):
        """测试单个合约字符串"""
        results = format_contracts("SHFE.rb2501", ContractFormat.TUSHARE)
        assert results == ["rb2501.SHF"]
    
    def test_format_empty_list(self):
        """测试空列表"""
        results = format_contracts([], ContractFormat.TUSHARE)
        assert results == []
    
    def test_format_with_invalid_contract(self):
        """测试包含无效合约的批量转换"""
        contracts = ["SHFE.rb2501", "invalid"]
        with pytest.raises(ValueError, match="转换合约代码.*失败"):
            format_contracts(contracts, ContractFormat.TUSHARE)


class TestValidateContract:
    """测试 validate_contract 函数"""
    
    def test_validate_valid_futures(self):
        """测试验证有效期货合约"""
        assert validate_contract("SHFE.rb2501") is True
        assert validate_contract("DCE.m2505") is True
        assert validate_contract("CZCE.SR2509") is True
    
    def test_validate_valid_stock(self):
        """测试验证有效股票代码"""
        assert validate_contract("SHSE.600000") is True
        assert validate_contract("SZSE.000001") is True
    
    def test_validate_with_exchange_match(self):
        """测试验证交易所匹配"""
        assert validate_contract("SHFE.rb2501", exchange="SHFE") is True
        assert validate_contract("SHFE.rb2501", exchange="SHF") is True  # 别名也应该工作
    
    def test_validate_with_exchange_mismatch(self):
        """测试验证交易所不匹配"""
        assert validate_contract("SHFE.rb2501", exchange="DCE") is False
    
    def test_validate_with_asset_type_match(self):
        """测试验证资产类型匹配"""
        assert validate_contract("SHFE.rb2501", asset_type=AssetType.FUTURES) is True
        assert validate_contract("SHSE.600000", asset_type=AssetType.STOCK) is True
    
    def test_validate_with_asset_type_mismatch(self):
        """测试验证资产类型不匹配"""
        assert validate_contract("SHFE.rb2501", asset_type=AssetType.STOCK) is False
    
    def test_validate_invalid_format(self):
        """测试验证无效格式"""
        assert validate_contract("invalid.code") is False
        assert validate_contract("") is False
        assert validate_contract("no_dot") is False


class TestValidateContracts:
    """测试 validate_contracts 函数（批量验证）"""
    
    def test_validate_all_valid(self):
        """测试验证全部有效"""
        contracts = ["SHFE.rb2501", "DCE.m2505", "CZCE.SR2509"]
        results = validate_contracts(contracts)
        assert results == [True, True, True]
    
    def test_validate_mixed(self):
        """测试验证混合有效和无效"""
        contracts = ["SHFE.rb2501", "invalid", "DCE.m2505"]
        results = validate_contracts(contracts)
        assert results == [True, False, True]
    
    def test_validate_with_skip_invalid(self):
        """测试跳过无效合约"""
        contracts = ["SHFE.rb2501", "invalid"]
        result = validate_contracts(contracts, skip_invalid=True)
        assert result is True  # 至少有一个有效
    
    def test_validate_all_invalid_with_skip(self):
        """测试全部无效且跳过"""
        contracts = ["invalid1", "invalid2"]
        result = validate_contracts(contracts, skip_invalid=True)
        assert result is False
    
    def test_validate_comma_separated(self):
        """测试验证逗号分隔的字符串"""
        contracts = "SHFE.rb2501, invalid, DCE.m2505"
        results = validate_contracts(contracts)
        assert results == [True, False, True]


class TestSplitContract:
    """测试 split_contract 函数"""
    
    def test_split_standard(self):
        """测试分离标准格式合约"""
        exchange, symbol = split_contract("SHFE.rb2501")
        assert exchange == "SHFE"
        assert symbol == "rb2501"
    
    def test_split_tushare(self):
        """测试分离 Tushare 格式合约"""
        exchange, symbol = split_contract("rb2501.SHF")
        assert exchange == "SHFE"
        assert symbol == "rb2501"
    
    def test_split_stock(self):
        """测试分离股票代码"""
        exchange, symbol = split_contract("SHSE.600000")
        assert exchange == "SHSE"
        assert symbol == "600000"
    
    def test_split_invalid(self):
        """测试分离无效格式"""
        with pytest.raises(ValueError):
            split_contract("invalid")


class TestGetUnderlying:
    """测试 get_underlying 函数"""
    
    def test_get_futures_underlying(self):
        """测试获取期货标的"""
        assert get_underlying("SHFE.rb2501") == "rb"
        assert get_underlying("DCE.m2505") == "m"
        assert get_underlying("CZCE.SR2509") == "sr"
    
    def test_get_stock_underlying(self):
        """测试获取股票标的（应返回 None）"""
        assert get_underlying("SHSE.600000") is None
    
    def test_get_invalid_underlying(self):
        """测试获取无效合约标的"""
        assert get_underlying("invalid") is None


class TestGetContractMonth:
    """测试 get_contract_month 函数"""
    
    def test_get_futures_month(self):
        """测试获取期货合约年月"""
        assert get_contract_month("SHFE.rb2501") == (2025, 1)
        assert get_contract_month("DCE.m2505") == (2025, 5)
        assert get_contract_month("CZCE.SR2509") == (2025, 9)
    
    def test_get_stock_month(self):
        """测试获取股票年月（应返回 None）"""
        assert get_contract_month("SHSE.600000") is None
    
    def test_get_invalid_month(self):
        """测试获取无效合约年月"""
        assert get_contract_month("invalid") is None


class TestIsMainContract:
    """测试 is_main_contract 函数"""
    
    def test_is_main_888(self):
        """测试888主力合约"""
        assert is_main_contract("SHFE.rb888") is True
        assert is_main_contract("DCE.m888") is True
    
    def test_is_main_000(self):
        """测试000主力合约"""
        assert is_main_contract("SHFE.rb000") is True
        assert is_main_contract("DCE.m000") is True
    
    def test_is_not_main(self):
        """测试非主力合约"""
        assert is_main_contract("SHFE.rb2501") is False
        assert is_main_contract("SHSE.600000") is False
    
    def test_is_main_uppercase(self):
        """测试大写主力合约标识"""
        assert is_main_contract("SHFE.RB888") is True
    
    def test_is_main_invalid(self):
        """测试无效合约"""
        assert is_main_contract("invalid") is False


class TestNormalizeContract:
    """测试 normalize_contract 函数"""
    
    def test_normalize_standard(self):
        """测试标准化已经是标准格式的合约"""
        result = normalize_contract("SHFE.rb2501")
        assert result == "SHFE.rb2501"
    
    def test_normalize_tushare(self):
        """测试标准化 Tushare 格式"""
        result = normalize_contract("rb2501.SHF")
        assert result == "SHFE.rb2501"
    
    def test_normalize_uppercase(self):
        """测试标准化大写合约"""
        result = normalize_contract("SHFE.RB2501")
        assert result == "SHFE.rb2501"
    
    def test_normalize_czce_3digit(self):
        """测试标准化郑商所3位格式"""
        result = normalize_contract("SR501", default_exchange="CZCE")
        assert result == "CZCE.sr2501"
    
    def test_normalize_stock(self):
        """测试标准化股票代码"""
        result = normalize_contract("600000.SH")
        assert result == "SHSE.600000"


class TestNormalizeContracts:
    """测试 normalize_contracts 函数（批量标准化）"""
    
    def test_normalize_list(self):
        """测试批量标准化列表"""
        contracts = ["rb2501.SHF", "m2505.DCE", "SR2509.ZCE"]
        results = normalize_contracts(contracts)
        assert results == ["SHFE.rb2501", "DCE.m2505", "CZCE.sr2509"]
    
    def test_normalize_comma_separated(self):
        """测试批量标准化逗号分隔字符串"""
        contracts = "rb2501.SHF, m2505.DCE, SR2509.ZCE"
        results = normalize_contracts(contracts)
        assert results == ["SHFE.rb2501", "DCE.m2505", "CZCE.sr2509"]
    
    def test_normalize_with_default(self):
        """测试批量标准化使用默认交易所"""
        contracts = ["rb2501", "hc2505"]
        results = normalize_contracts(contracts, default_exchange="SHFE")
        assert results == ["SHFE.rb2501", "SHFE.hc2505"]
    
    def test_normalize_mixed_formats(self):
        """测试批量标准化混合格式"""
        contracts = ["SHFE.rb2501", "m2505.DCE", "CZCE.SR2509"]
        results = normalize_contracts(contracts)
        assert results == ["SHFE.rb2501", "DCE.m2505", "CZCE.sr2509"]


class TestIntegration:
    """集成测试"""
    
    def test_round_trip_conversion(self):
        """测试往返转换（标准->Tushare->标准）"""
        original = "SHFE.rb2501"
        tushare = format_contract(original, ContractFormat.TUSHARE)
        back_to_standard = normalize_contract(tushare)
        assert back_to_standard == original
    
    def test_parse_and_format_consistency(self):
        """测试解析和格式化的一致性"""
        contract = "SHFE.rb2501"
        info = parse_contract(contract)
        formatted = info.to_standard()
        assert formatted == contract
    
    def test_multiple_formats_same_contract(self):
        """测试同一合约的多种格式表示"""
        contracts = [
            "SHFE.rb2501",
            "rb2501.SHF",
            "SHFE.RB2501",
        ]
        normalized = [normalize_contract(c) for c in contracts]
        assert all(n == "SHFE.rb2501" for n in normalized)
    
    def test_batch_operations(self):
        """测试批量操作的综合应用"""
        # 输入多种格式
        contracts = "SHFE.rb2501, m2505.DCE, CZCE.SR2509"
        
        # 标准化
        normalized = normalize_contracts(contracts)
        assert normalized == ["SHFE.rb2501", "DCE.m2505", "CZCE.sr2509"]
        
        # 转换为 Tushare 格式
        tushare_format = format_contracts(normalized, ContractFormat.TUSHARE)
        assert tushare_format == ["rb2501.SHF", "m2505.DCE", "sr2509.ZCE"]
        
        # 验证
        assert all(validate_contracts(normalized))
        assert all(validate_contracts(tushare_format))
