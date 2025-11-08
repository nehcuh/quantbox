"""
formatters.py 单元测试

测试公共格式转换工具的所有函数
"""

import pytest
import pandas as pd
import numpy as np

from quantbox.adapters.formatters import (
    normalize_tushare_exchange,
    parse_tushare_code,
    normalize_symbol_case,
    standardize_column_names,
    process_tushare_futures_data,
    process_tushare_stock_data,
    TUSHARE_FUTURES_EXCHANGE_MAP,
    TUSHARE_STOCK_EXCHANGE_MAP,
    UPPERCASE_EXCHANGES,
)


class TestNormalizeTushareExchange:
    """测试 normalize_tushare_exchange 函数"""

    def test_normalize_futures_exchanges(self):
        """测试期货交易所代码标准化"""
        df = pd.DataFrame({"ts_exchange": ["SHF", "ZCE", "DCE", "CFX", "INE"]})
        result = normalize_tushare_exchange(df, market_type="futures")

        assert "exchange" in result.columns
        assert result["exchange"].tolist() == ["SHFE", "CZCE", "DCE", "CFFEX", "INE"]

    def test_normalize_stock_exchanges(self):
        """测试股票交易所代码标准化"""
        df = pd.DataFrame({"ts_exchange": ["SH", "SZ", "BJ"]})
        result = normalize_tushare_exchange(df, market_type="stock")

        assert "exchange" in result.columns
        assert result["exchange"].tolist() == ["SSE", "SZSE", "BSE"]

    def test_missing_column(self):
        """测试缺失列的情况"""
        df = pd.DataFrame({"other_col": [1, 2, 3]})
        result = normalize_tushare_exchange(df)

        # 应该返回原DataFrame，不做修改
        assert "exchange" not in result.columns
        assert result.equals(df)


class TestParseTushareCode:
    """测试 parse_tushare_code 函数"""

    def test_parse_futures_code(self):
        """测试解析期货 ts_code"""
        df = pd.DataFrame({"ts_code": ["rb2501.SHF", "TA501.ZCE", "i2501.DCE"]})
        result = parse_tushare_code(df, market_type="futures")

        assert "symbol" in result.columns
        assert "exchange" in result.columns
        assert result["symbol"].tolist() == ["rb2501", "TA501", "i2501"]
        assert result["exchange"].tolist() == ["SHFE", "CZCE", "DCE"]

    def test_parse_stock_code(self):
        """测试解析股票 ts_code"""
        df = pd.DataFrame({"ts_code": ["000001.SZ", "600000.SH", "430047.BJ"]})
        result = parse_tushare_code(df, market_type="stock")

        assert result["symbol"].tolist() == ["000001", "600000", "430047"]
        assert result["exchange"].tolist() == ["SZSE", "SSE", "BSE"]

    def test_missing_ts_code_column(self):
        """测试缺失 ts_code 列"""
        df = pd.DataFrame({"other_col": [1, 2, 3]})
        result = parse_tushare_code(df)

        # 应该返回原DataFrame
        assert result.equals(df)


class TestNormalizeSymbolCase:
    """测试 normalize_symbol_case 函数"""

    def test_normalize_case_for_non_uppercase_exchanges(self):
        """测试非郑商所/中金所的符号转小写"""
        df = pd.DataFrame({
            "symbol": ["RB2501", "I2501", "NI2501"],
            "exchange": ["SHFE", "DCE", "SHFE"]
        })
        result = normalize_symbol_case(df)

        assert result["symbol"].tolist() == ["rb2501", "i2501", "ni2501"]

    def test_keep_uppercase_for_czce_cffex(self):
        """测试郑商所和中金所保持大写"""
        df = pd.DataFrame({
            "symbol": ["TA501", "IF2501"],
            "exchange": ["CZCE", "CFFEX"]
        })
        result = normalize_symbol_case(df)

        # 郑商所和中金所应该保持不变
        assert result["symbol"].tolist() == ["TA501", "IF2501"]

    def test_custom_uppercase_exchanges(self):
        """测试自定义大写交易所列表"""
        df = pd.DataFrame({
            "symbol": ["RB2501", "I2501"],
            "exchange": ["SHFE", "DCE"]
        })
        result = normalize_symbol_case(df, uppercase_exchanges=["SHFE"])

        # SHFE 保持不变，DCE 转小写
        assert result["symbol"].tolist() == ["RB2501", "i2501"]

    def test_missing_columns(self):
        """测试缺失必需列"""
        df = pd.DataFrame({"other_col": [1, 2, 3]})
        result = normalize_symbol_case(df)

        assert result.equals(df)


class TestStandardizeColumnNames:
    """测试 standardize_column_names 函数"""

    def test_standard_column_rename(self):
        """测试标准列名重命名"""
        df = pd.DataFrame({
            "vol": [1000, 2000],
            "oi": [100, 200],
            "trade_date": [20240101, 20240102],
            "pre_close": [100.0, 101.0]
        })
        result = standardize_column_names(df)

        assert "volume" in result.columns
        assert "open_interest" in result.columns
        assert "date" in result.columns
        assert "prev_close" in result.columns
        assert "vol" not in result.columns

    def test_custom_rename_map(self):
        """测试自定义重命名映射"""
        df = pd.DataFrame({"custom_col": [1, 2]})
        result = standardize_column_names(df, rename_map={"custom_col": "renamed_col"})

        assert "renamed_col" in result.columns
        assert "custom_col" not in result.columns

    def test_partial_columns(self):
        """测试部分列存在的情况"""
        df = pd.DataFrame({
            "vol": [1000],
            "other_col": ["data"]
        })
        result = standardize_column_names(df)

        # vol 应该被重命名，other_col 保持不变
        assert "volume" in result.columns
        assert "other_col" in result.columns
        assert "vol" not in result.columns


class TestProcessTushareFuturesData:
    """测试 process_tushare_futures_data 函数"""

    def test_full_process(self):
        """测试完整的期货数据处理流程"""
        df = pd.DataFrame({
            "ts_code": ["RB2501.SHF", "TA501.ZCE", "i2501.DCE"],
            "trade_date": [20240101, 20240101, 20240101],
            "vol": [1000, 2000, 3000],
            "oi": [100, 200, 300]
        })
        result = process_tushare_futures_data(df)

        # 检查解析后的列
        assert "symbol" in result.columns
        assert "exchange" in result.columns
        assert "date" in result.columns
        assert "volume" in result.columns
        assert "open_interest" in result.columns

        # 检查符号大小写
        assert result["symbol"].tolist() == ["rb2501", "TA501", "i2501"]

        # 检查交易所映射
        assert result["exchange"].tolist() == ["SHFE", "CZCE", "DCE"]

        # 检查日期转换
        assert result["date"].tolist() == [20240101, 20240101, 20240101]

    def test_skip_parse(self):
        """测试跳过 ts_code 解析"""
        df = pd.DataFrame({
            "symbol": ["rb2501"],
            "exchange": ["SHFE"],
            "vol": [1000]
        })
        result = process_tushare_futures_data(df, parse_ts_code=False)

        assert "symbol" in result.columns
        assert result["symbol"].tolist() == ["rb2501"]

    def test_skip_normalize_case(self):
        """测试跳过大小写标准化"""
        df = pd.DataFrame({
            "ts_code": ["RB2501.SHF"],
            "trade_date": [20240101]
        })
        result = process_tushare_futures_data(df, normalize_case=False)

        # 符号应该保持大写
        assert result["symbol"].iloc[0] == "RB2501"


class TestProcessTushareStockData:
    """测试 process_tushare_stock_data 函数"""

    def test_full_process(self):
        """测试完整的股票数据处理流程"""
        df = pd.DataFrame({
            "ts_code": ["000001.SZ", "600000.SH"],
            "trade_date": [20240101, 20240101],
            "vol": [1000000, 2000000]
        })
        result = process_tushare_stock_data(df)

        # 检查解析后的列
        assert "symbol" in result.columns
        assert "exchange" in result.columns
        assert "date" in result.columns
        assert "volume" in result.columns

        # 检查符号
        assert result["symbol"].tolist() == ["000001", "600000"]

        # 检查交易所映射
        assert result["exchange"].tolist() == ["SZSE", "SSE"]

    def test_skip_standardize_columns(self):
        """测试跳过列名标准化"""
        df = pd.DataFrame({
            "ts_code": ["000001.SZ"],
            "vol": [1000000]
        })
        result = process_tushare_stock_data(df, standardize_columns=False)

        # vol 应该保持不变
        assert "vol" in result.columns
        assert "volume" not in result.columns


class TestConstants:
    """测试常量定义"""

    def test_futures_exchange_map(self):
        """测试期货交易所映射表"""
        assert TUSHARE_FUTURES_EXCHANGE_MAP["SHF"] == "SHFE"
        assert TUSHARE_FUTURES_EXCHANGE_MAP["ZCE"] == "CZCE"
        assert TUSHARE_FUTURES_EXCHANGE_MAP["DCE"] == "DCE"
        assert TUSHARE_FUTURES_EXCHANGE_MAP["CFX"] == "CFFEX"
        assert TUSHARE_FUTURES_EXCHANGE_MAP["INE"] == "INE"

    def test_stock_exchange_map(self):
        """测试股票交易所映射表"""
        assert TUSHARE_STOCK_EXCHANGE_MAP["SH"] == "SSE"
        assert TUSHARE_STOCK_EXCHANGE_MAP["SZ"] == "SZSE"
        assert TUSHARE_STOCK_EXCHANGE_MAP["BJ"] == "BSE"

    def test_uppercase_exchanges(self):
        """测试大写交易所集合"""
        assert "CZCE" in UPPERCASE_EXCHANGES
        assert "CFFEX" in UPPERCASE_EXCHANGES
        assert "SHFE" not in UPPERCASE_EXCHANGES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
