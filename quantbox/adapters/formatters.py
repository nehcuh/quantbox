"""
数据格式转换工具模块

提供数据适配器之间共享的格式转换函数，减少代码重复。

功能：
- Tushare 交易所代码映射
- DataFrame 列名标准化
- 符号大小写转换
- ts_code 解析
"""

from typing import Dict, List, Optional
import pandas as pd


# Tushare 期货交易所代码映射
TUSHARE_FUTURES_EXCHANGE_MAP = {
    "SHF": "SHFE",   # 上期所
    "ZCE": "CZCE",   # 郑商所
    "DCE": "DCE",    # 大商所
    "CFX": "CFFEX",  # 中金所
    "INE": "INE",    # 能源中心
}

# Tushare 股票交易所代码映射
TUSHARE_STOCK_EXCHANGE_MAP = {
    "SH": "SSE",     # 上交所
    "SZ": "SZSE",    # 深交所
    "BJ": "BSE",     # 北交所
}

# 需要保持大写的交易所（郑商所、中金所）
UPPERCASE_EXCHANGES = {"CZCE", "CFFEX"}


def normalize_tushare_exchange(
    df: pd.DataFrame,
    ts_exchange_col: str = "ts_exchange",
    target_col: str = "exchange",
    market_type: str = "futures"
) -> pd.DataFrame:
    """
    标准化 Tushare 交易所代码

    将 Tushare 格式的交易所代码（如 SHF, ZCE）转换为标准格式（SHFE, CZCE）

    Args:
        df: 源数据 DataFrame
        ts_exchange_col: Tushare 交易所列名
        target_col: 目标交易所列名
        market_type: 市场类型，"futures" 或 "stock"

    Returns:
        pd.DataFrame: 转换后的 DataFrame

    Examples:
        >>> df = pd.DataFrame({"ts_exchange": ["SHF", "ZCE"]})
        >>> df = normalize_tushare_exchange(df)
        >>> df["exchange"].tolist()
        ['SHFE', 'CZCE']
    """
    if ts_exchange_col not in df.columns:
        return df

    df = df.copy()

    # 选择映射表
    exchange_map = (
        TUSHARE_FUTURES_EXCHANGE_MAP if market_type == "futures"
        else TUSHARE_STOCK_EXCHANGE_MAP
    )

    # 应用映射
    df[target_col] = df[ts_exchange_col].replace(exchange_map)

    return df


def parse_tushare_code(
    df: pd.DataFrame,
    ts_code_col: str = "ts_code",
    symbol_col: str = "symbol",
    exchange_col: str = "exchange",
    market_type: str = "futures"
) -> pd.DataFrame:
    """
    解析 Tushare 代码格式（如 rb2501.SHF）

    将 Tushare 的 ts_code 拆分为 symbol 和 exchange

    Args:
        df: 源数据 DataFrame
        ts_code_col: Tushare 代码列名
        symbol_col: 目标符号列名
        exchange_col: 目标交易所列名
        market_type: 市场类型，"futures" 或 "stock"

    Returns:
        pd.DataFrame: 解析后的 DataFrame

    Examples:
        >>> df = pd.DataFrame({"ts_code": ["rb2501.SHF", "TA501.ZCE"]})
        >>> df = parse_tushare_code(df)
        >>> df[["symbol", "exchange"]].values.tolist()
        [['rb2501', 'SHFE'], ['TA501', 'CZCE']]
    """
    if ts_code_col not in df.columns:
        return df

    df = df.copy()

    # 拆分 ts_code
    split_data = df[ts_code_col].str.split(".", expand=True)
    df[symbol_col] = split_data[0]
    ts_exchange = split_data[1]

    # 选择映射表
    exchange_map = (
        TUSHARE_FUTURES_EXCHANGE_MAP if market_type == "futures"
        else TUSHARE_STOCK_EXCHANGE_MAP
    )

    # 映射交易所代码
    df[exchange_col] = ts_exchange.map(exchange_map).fillna(ts_exchange)

    return df


def normalize_symbol_case(
    df: pd.DataFrame,
    symbol_col: str = "symbol",
    exchange_col: str = "exchange",
    uppercase_exchanges: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    标准化符号大小写

    根据交易所规则转换符号大小写：
    - 郑商所（CZCE）和中金所（CFFEX）：保持原样（通常大写）
    - 其他交易所：转为小写

    Args:
        df: 源数据 DataFrame
        symbol_col: 符号列名
        exchange_col: 交易所列名
        uppercase_exchanges: 需要保持大写的交易所列表

    Returns:
        pd.DataFrame: 转换后的 DataFrame

    Examples:
        >>> df = pd.DataFrame({
        ...     "symbol": ["RB2501", "TA501", "ni2501"],
        ...     "exchange": ["SHFE", "CZCE", "SHFE"]
        ... })
        >>> df = normalize_symbol_case(df)
        >>> df["symbol"].tolist()
        ['rb2501', 'TA501', 'ni2501']
    """
    if symbol_col not in df.columns or exchange_col not in df.columns:
        return df

    df = df.copy()
    uppercase_set = set(uppercase_exchanges or UPPERCASE_EXCHANGES)

    # 对非大写交易所的符号转小写
    for exchange in df[exchange_col].unique():
        if pd.notna(exchange) and exchange not in uppercase_set:
            mask = df[exchange_col] == exchange
            df.loc[mask, symbol_col] = df.loc[mask, symbol_col].str.lower()

    return df


def standardize_column_names(
    df: pd.DataFrame,
    rename_map: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """
    标准化列名

    将常见的数据源列名转换为标准名称

    Args:
        df: 源数据 DataFrame
        rename_map: 自定义重命名映射，会覆盖默认映射

    Returns:
        pd.DataFrame: 重命名后的 DataFrame

    Examples:
        >>> df = pd.DataFrame({"vol": [100], "oi": [200]})
        >>> df = standardize_column_names(df)
        >>> list(df.columns)
        ['volume', 'open_interest']
    """
    default_rename_map = {
        "vol": "volume",          # 成交量
        "oi": "open_interest",    # 持仓量
        "trade_date": "date",     # 交易日期
        "pre_close": "prev_close", # 前收盘价
        "pre_settle": "prev_settle", # 前结算价
    }

    if rename_map:
        default_rename_map.update(rename_map)

    # 只重命名存在的列
    actual_rename = {
        old: new for old, new in default_rename_map.items()
        if old in df.columns
    }

    return df.rename(columns=actual_rename)


def process_tushare_futures_data(
    df: pd.DataFrame,
    parse_ts_code: bool = True,
    normalize_case: bool = True,
    standardize_columns: bool = True
) -> pd.DataFrame:
    """
    一站式处理 Tushare 期货数据

    整合常用的格式转换步骤：
    1. 解析 ts_code
    2. 标准化符号大小写
    3. 标准化列名

    Args:
        df: 源数据 DataFrame
        parse_ts_code: 是否解析 ts_code
        normalize_case: 是否标准化符号大小写
        standardize_columns: 是否标准化列名

    Returns:
        pd.DataFrame: 处理后的 DataFrame

    Examples:
        >>> df = pd.DataFrame({
        ...     "ts_code": ["RB2501.SHF", "TA501.ZCE"],
        ...     "trade_date": [20240101, 20240101],
        ...     "vol": [1000, 2000]
        ... })
        >>> df = process_tushare_futures_data(df)
        >>> df[["symbol", "exchange", "date", "volume"]].values.tolist()
        [['rb2501', 'SHFE', 20240101, 1000], ['TA501', 'CZCE', 20240101, 2000]]
    """
    result = df.copy()

    if parse_ts_code and "ts_code" in result.columns:
        result = parse_tushare_code(result, market_type="futures")

    if normalize_case and "symbol" in result.columns and "exchange" in result.columns:
        result = normalize_symbol_case(result)

    if standardize_columns:
        result = standardize_column_names(result)

    return result


def process_tushare_stock_data(
    df: pd.DataFrame,
    parse_ts_code: bool = True,
    standardize_columns: bool = True
) -> pd.DataFrame:
    """
    一站式处理 Tushare 股票数据

    整合常用的格式转换步骤：
    1. 解析 ts_code（如 000001.SZ）
    2. 标准化列名

    Args:
        df: 源数据 DataFrame
        parse_ts_code: 是否解析 ts_code
        standardize_columns: 是否标准化列名

    Returns:
        pd.DataFrame: 处理后的 DataFrame

    Examples:
        >>> df = pd.DataFrame({
        ...     "ts_code": ["000001.SZ", "600000.SH"],
        ...     "trade_date": [20240101, 20240101],
        ...     "vol": [1000000, 2000000]
        ... })
        >>> df = process_tushare_stock_data(df)
        >>> df[["symbol", "exchange"]].values.tolist()
        [['000001', 'SZSE'], ['600000', 'SSE']]
    """
    result = df.copy()

    if parse_ts_code and "ts_code" in result.columns:
        result = parse_tushare_code(result, market_type="stock")

    if standardize_columns:
        result = standardize_column_names(result)

    return result
