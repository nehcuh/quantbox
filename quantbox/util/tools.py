"""
改进的工具函数模块

提供优化和重构后的工具函数，与其他模块保持一致性。
"""

import datetime
import json
import re
from typing import Dict, List, Union, Optional
from functools import lru_cache

import numpy as np
import pandas as pd

from quantbox.util.date_utils import date_to_int, int_to_date_str, util_make_date_stamp
from quantbox.util.exchange_utils import get_exchange_for_data_source, convert_exchanges_for_data_source
from quantbox.config.config_loader import get_config_loader


@lru_cache(maxsize=256)
def _get_cached_exchange_mapping(exchange: str, data_source: str, usage: str = "api") -> str:
    """带缓存的交易所映射函数

    Args:
        exchange: 交易所代码
        data_source: 数据源名称
        usage: 使用模式，"api" 用于API查询参数，"suffix" 用于返回值后缀

    Returns:
        str: 映射后的交易所代码
    """
    return get_exchange_for_data_source(exchange, data_source, usage)


def warm_tools_cache():
    """预热 tools 模块的缓存

    该函数会在应用启动时被调用来预热关键缓存。
    """
    from quantbox.util.cache_warmup import get_cache_warmer

    cache_warmer = get_cache_warmer()

    # 预热常用交易所映射
    common_exchanges = ["SSE", "SZSE", "BSE", "SHFE", "DCE", "CZCE", "CFFEX", "INE", "GFEX"]
    data_sources = ["tushare", "goldminer", "joinquant"]

    for exchange in common_exchanges:
        for data_source in data_sources:
            # 预热 API 参数映射
            cache_warmer.register_function(_get_cached_exchange_mapping, exchange, data_source, "api")
            # 对于 Tushare，还需要预热后缀映射
            if data_source == "tushare":
                cache_warmer.register_function(_get_cached_exchange_mapping, exchange, data_source, "suffix")

    # 预热合约映射函数
    cache_warmer.register_function(_load_contract_exchange_mapper_from_config)
    cache_warmer.register_function(_load_contract_exchange_mapper_from_db)


def util_to_json_from_pandas(data: pd.DataFrame) -> Dict:
    """将 pandas DataFrame 转换为 JSON 格式（优化版）

    使用统一的日期处理函数替代硬编码的日期列处理。

    Args:
        data: 需要转换的 pandas DataFrame

    Returns:
        Dict: 转换后的 JSON 数据
    """
    # 创建数据副本以避免修改原始数据
    df = data.copy()

    # 统一处理所有日期类型的列
    date_columns = df.select_dtypes(include=[np.datetime64, 'datetime64[ns]']).columns
    for col in date_columns:
        try:
            df[col] = df[col].apply(lambda x: int_to_date_str(x) if pd.notna(x) else None)
        except Exception:
            # 如果转换失败，保留原值
            continue

    # 处理字符串格式的日期列
    str_date_columns = ['trade_date', 'cal_date', 'list_date', 'delist_date']
    for col in str_date_columns:
        if col in df.columns:
            try:
                df[col] = df[col].apply(
                    lambda x: int_to_date_str(date_to_int(x)) if pd.notna(x) and x else x
                )
            except Exception:
                # 如果转换失败，保留原值
                    continue

    return json.loads(df.to_json(orient="records"))


def util_format_stock_symbols(
    symbols: Union[str, List[str]], format: str = "standard"
) -> List[str]:
    """格式化股票代码（优化版）

    使用配置文件进行交易所映射，支持更多数据源格式。
    通过缓存提高性能。

    Args:
        symbols: 股票代码或股票代码列表
        format: 目标格式
                - "standard": 标准格式（如 "SHSE.600000"）
                - "tushare": Tushare格式（如 "000001.SZ"）
                - "goldminer": 掘金格式（如 "SHSE.600000"）
                - "joinquant": 聚宽格式（如 "000001.XSHG"）

    Returns:
        List[str]: 格式化后的股票代码列表
    """
    if isinstance(symbols, str):
        symbols = symbols.split(",")

    # 提取数字部分
    numbers = []
    for symbol in symbols:
        # 匹配各种格式的数字部分
        match = re.search(r"\d+", symbol)
        if match:
            numbers.append(match.group())
        else:
            # 如果没有找到数字，可能是其他格式，直接使用
            numbers.append(symbol)

    # 使用配置文件进行交易所格式转换
    formatted_symbols = []
    for number in numbers:
        # 根据数字第一位推断交易所（基于配置文件中的股票代码规则）
        first_digit = number[0] if number else ""

        # 获取标准交易所代码（基于配置文件中的定义）
        if first_digit == "6":  # 6开头，上海证券交易所
            standard_exchange = "SHSE"  # 标准化的交易所代码
        elif first_digit in ["0", "3"]:  # 0或3开头，深圳证券交易所
            standard_exchange = "SZSE"
        elif first_digit in ["4", "8", "9"]:  # 4、8或9开头，北京证券交易所
            standard_exchange = "BSE"  # 北京证券交易所
        else:
            # 未知交易所，使用数字本身
            standard_exchange = f"UNKNOWN_{first_digit}"

        # 转换为目标格式（使用缓存的数据源映射）
        if format in ["standard", "normal", "goldminer", "gm"]:
            # 掘金格式使用配置文件中的标准格式
            goldminer_exchange = _get_cached_exchange_mapping(standard_exchange, "goldminer")
            formatted_symbols.append(f"{goldminer_exchange}.{number}")
        elif format in ["tushare", "ts"]:
            # Tushare格式 - 使用后缀映射（股票代码后缀）
            tushare_suffix = _get_cached_exchange_mapping(standard_exchange, "tushare", "suffix")
            formatted_symbols.append(f"{number}.{tushare_suffix}")
        elif format in ["joinquant", "jq"]:
            # 聚宽格式
            joinquant_exchange = _get_cached_exchange_mapping(standard_exchange, "joinquant")
            formatted_symbols.append(f"{number}.{joinquant_exchange}")
        else:
            # 默认使用标准格式（掘金格式）
            default_exchange = _get_cached_exchange_mapping(standard_exchange, "goldminer")
            formatted_symbols.append(f"{default_exchange}.{number}")

    return formatted_symbols


def util_format_future_symbols(
    symbols: Union[str, List[str]],
    format: Optional[str] = None,
    include_exchange: Optional[bool] = True
) -> List[str]:
    """格式化期货合约代码（改进版）

    与 exchange_utils 集成，使用标准化的交易所处理。
    添加了配置文件支持和更好的错误处理。

    Args:
        symbols: 期货合约代码或代码列表
        format: 目标格式
        include_exchange: 是否在返回结果中包含交易所前缀

    Returns:
        List[str]: 格式化后的期货合约代码列表

    Examples:
        >>> util_format_future_symbols("M2501")
        ['DCE.m2501']
        >>> util_format_future_symbols("SHFE.rb2501", format="tushare")
        ['rb2501.SHF']
    """
    if isinstance(symbols, str):
        symbols = symbols.split(",")

    formatted_symbols = []

    # 尝试从配置文件加载映射
    try:
        contract_exchange_map = _load_contract_exchange_mapper_from_config()
    except Exception:
        # 配置加载失败，使用数据库备份
        contract_exchange_map = _load_contract_exchange_mapper_from_db()

    for symbol in symbols:
        try:
            if "." in symbol:  # 包含交易所前缀（如 SHFE.rb2501）
                exchange, contract = symbol.split(".", 1)

                # 标准化交易所代码
                from quantbox.util.exchange_utils import normalize_exchange
                standard_exchange = normalize_exchange(exchange)

                # 转换为Tushare格式
                if format == "tushare":
                    tushare_exchange = _get_cached_exchange_mapping(standard_exchange, "tushare")
                    # 使用Tushare格式：contract.exchange
                    formatted_symbol = f"{contract}.{tushare_exchange}"
                else:
                    # 使用标准格式或保持原样
                    formatted_symbol = f"{standard_exchange}.{contract}"

                formatted_symbols.append(formatted_symbol)
            else:  # 不包含交易所前缀
                if not include_exchange:
                    formatted_symbols.append(symbol)
                else:
                    # 从合约代码推断交易所
                    match = re.match(r"([A-Za-z]+)", symbol)
                    if match:
                        fut_code = match.group(1).upper()
                        exchange = contract_exchange_map.get(fut_code, "UNKNOWN")

                        # 标准化交易所代码
                        from quantbox.util.exchange_utils import normalize_exchange
                        standard_exchange = normalize_exchange(exchange)

                        if format == "tushare":
                            tushare_exchange = _get_cached_exchange_mapping(standard_exchange, "tushare")
                            # 使用Tushare格式：contract.exchange
                            formatted_symbol = f"{symbol}.{tushare_exchange}"
                        else:
                            formatted_symbol = f"{standard_exchange}.{symbol}"
                        formatted_symbols.append(formatted_symbol)
                    else:
                        # 无法推断交易所，保持原样
                        formatted_symbols.append(symbol)
        except Exception as e:
            # 单个符号处理失败，跳过并记录警告
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to format symbol '{symbol}': {str(e)}")
            formatted_symbols.append(symbol)

    # 移除交易所前缀（如果需要）
    if not include_exchange and formatted_symbols:
        if format in ["tushare", "ts"]:
            formatted_symbols = [sym.split('.')[0] for sym in formatted_symbols]
        else:
            formatted_symbols = [sym.split('.')[1] if '.' in sym else sym for sym in formatted_symbols]

    return formatted_symbols


@lru_cache(maxsize=128)
def _load_contract_exchange_mapper_from_config() -> Dict[str, str]:
    """从配置文件加载合约交易所映射（新增）

    从配置文件中加载期货合约代码与对应交易所的映射关系，
    如果配置文件不存在则返回空字典。

    Returns:
        Dict[str, str]: 合约代码到交易所的映射字典
    """
    try:
        from pathlib import Path
        import toml

        config_path = Path(__file__).parent / "contract_exchange_mapping.toml"
        if not config_path.exists():
            return {}

        config = toml.load(config_path)
        return config.get("contract_mappings", {})

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to load contract mapping from config: {e}")
        return {}


@lru_cache(maxsize=128)
def _load_contract_exchange_mapper_from_db() -> Dict[str, str]:
    """从数据库加载合约交易所映射（原有逻辑的优化版）"""
    try:
        # 使用聚合管道查询不重复的 fut_code 和对应的 exchange
        pipeline = [
            {"$group": {"_id": "$fut_code", "exchange": {"$first": "$exchange"}}},
            {"$project": {"fut_code": "$_id", "exchange": 1, "_id": 0}},
        ]

        collections = get_config_loader().get_mongodb_client().quantbox.future_contracts
        results = list(collections.aggregate(pipeline))
        return {item["fut_code"]: item["exchange"] for item in results}

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to load contract mapping from database: {e}")
        return {}


@lru_cache(maxsize=None)
def load_contract_exchange_mapper() -> Dict:
    """加载合约与交易所的映射关系

    从数据库中加载期货合约代码与对应交易所的映射关系。
    使用 LRU 缓存以提高性能。

    Returns：
        Dict: 合约代码到交易所的映射字典
    """
    # 尝试从配置文件加载映射
    try:
        return _load_contract_exchange_mapper_from_config()
    except Exception:
        # 配置加载失败，使用数据库备份
        return _load_contract_exchange_mapper_from_db()


def util_make_dataframe_consistent(df: pd.DataFrame) -> pd.DataFrame:
    """使DataFrame数据格式一致

    标准化DataFrame中的日期格式、交易所代码等，
    确保数据的一致性。

    Args:
        df: 输入的DataFrame

    Returns:
        pd.DataFrame: 格式化后的DataFrame
    """
    df = df.copy()

    # 标准化日期列
    date_columns = ['trade_date', 'cal_date', 'list_date', 'delist_date', 'created_at', 'updated_at']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # 标准化交易所代码
    if 'exchange' in df.columns:
        from quantbox.util.exchange_utils import normalize_exchange
        df['exchange'] = df['exchange'].apply(
            lambda x: normalize_exchange(x) if pd.notna(x) else x
        )

    return df
