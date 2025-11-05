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
    from quantbox.util.exchange_utils import get_all_exchanges
    from quantbox.config.config_loader import get_config_loader

    cache_warmer = get_cache_warmer()

    try:
        # 从 exchange_utils 获取所有标准交易所
        common_exchanges = get_all_exchanges()

        # 从配置中获取数据源列表
        config_loader = get_config_loader()
        config = config_loader.load_config('exchanges')
        data_sources_config = config.get('data_sources', {})
        data_sources = [
            ds for ds in data_sources_config.keys()
            if not ds.endswith('_suffix')
        ]

        for exchange in common_exchanges:
            for data_source in data_sources:
                # 预热 API 参数映射
                cache_warmer.register_function(_get_cached_exchange_mapping, exchange, data_source, "api")
                # 对于 Tushare，还需要预热后缀映射
                if data_source == "tushare":
                    cache_warmer.register_function(_get_cached_exchange_mapping, exchange, data_source, "suffix")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to load exchanges and data sources from config for cache warming: {e}")
        # 回退到硬编码的默认值（包含 BSE）
        common_exchanges = ["SHSE", "SZSE", "BSE", "SHFE", "DCE", "CZCE", "CFFEX", "INE", "GFEX"]
        data_sources = ["tushare", "goldminer", "vnpy"]

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
    """格式化股票代码

    使用配置文件进行交易所映射，支持更多数据源格式。
    通过缓存提高性能。

    优化：优先使用输入中的交易所信息，避免不必要的推断。

    Args:
        symbols: 股票代码或股票代码列表
        format: 目标格式
                - "standard": 标准格式（如 "SHSE.600000"）
                - "tushare": Tushare格式（如 "000001.SZ"）
                - "goldminer": 掘金格式（如 "SHSE.600000"）
                - "vnpy": vnpy格式（如 "600000.SSE"）

    Returns:
        List[str]: 格式化后的股票代码列表
    """
    if isinstance(symbols, str):
        symbols = symbols.split(",")

    # 预编译正则表达式以提高性能
    digit_pattern = re.compile(r"\d+")

    # 使用配置文件进行交易所格式转换
    formatted_symbols = []
    for symbol in symbols:
        # 提取数字部分
        digit_match = digit_pattern.search(symbol)
        if not digit_match:
            # 如果没有找到数字，直接使用原符号
            formatted_symbols.append(symbol)
            continue

        number = digit_match.group()
        standard_exchange = None

        # 检查是否包含交易所信息
        if '.' in symbol:
            parts = symbol.split('.')
            if len(parts) == 2:
                first_part, second_part = parts[0], parts[1]

                # 尝试识别格式类型
                standard_exchange = None

                # 情况1: 掘金格式 - 交易所.股票代码 (如 SZSE.000001)
                # 检查第一部分是否为有效交易所
                try:
                    from quantbox.util.exchange_utils import normalize_exchange
                    first_as_exchange = normalize_exchange(first_part)
                    if first_as_exchange in ["SHSE", "SZSE", "BSE"]:
                        # 第一部分是有效的股票交易所
                        standard_exchange = first_as_exchange
                        # 确保第二部分是数字
                        if digit_pattern.match(second_part):
                            number = second_part
                except ValueError:
                    pass

                # 情况2: Tushare/vnpy 格式 - 股票代码.后缀 (如 600000.SH 或 600000.SZSE)
                if standard_exchange is None and digit_pattern.match(first_part):
                    # 第一部分是数字，第二部分可能是交易所后缀
                    try:
                        second_as_exchange = normalize_exchange(second_part)
                        if second_as_exchange in ["SHSE", "SZSE", "BSE"]:
                            standard_exchange = second_as_exchange
                            number = first_part
                    except ValueError:
                        pass

        # 如果没有从输入中解析出有效的股票交易所，才进行推断
        if standard_exchange is None:
            standard_exchange = _infer_stock_exchange_from_config(number)

            if standard_exchange is None:
                # 无法推断交易所，记录警告并返回原始代码
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Cannot infer exchange for stock code: {symbol}, returning original")
                formatted_symbols.append(symbol)
                continue

        # 转换为目标格式（使用缓存的数据源映射）
        if format in ["standard", "normal", "goldminer", "gm"]:
            # 掘金格式使用配置文件中的标准格式
            goldminer_exchange = _get_cached_exchange_mapping(standard_exchange, "goldminer")
            formatted_symbols.append(f"{goldminer_exchange}.{number}")
        elif format in ["tushare", "ts"]:
            # Tushare格式 - 使用后缀映射（股票代码后缀）
            tushare_suffix = _get_cached_exchange_mapping(standard_exchange, "tushare", "suffix")
            formatted_symbols.append(f"{number}.{tushare_suffix}")
        elif format in ["vnpy", "vn"]:
            # vnpy格式
            vnpy_exchange = _get_cached_exchange_mapping(standard_exchange, "vnpy")
            formatted_symbols.append(f"{number}.{vnpy_exchange}")
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
        >>> util_format_future_symbols("rb2501", format="vnpy")
        ['rb2501.SHFE']
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
            if "." in symbol:  # 包含交易所前缀（如 SHFE.rb2501 或 TF2212.CFX）
                parts = symbol.split(".", 1)
                first_part, second_part = parts[0], parts[1]

                # 标准化交易所代码
                from quantbox.util.exchange_utils import normalize_exchange

                # 尝试判断哪个部分是交易所代码，哪个部分是合约代码
                # 对于期货合约，通常交易所代码是纯字母，合约代码包含字母+数字
                try:
                    # 方法1：尝试将第一部分作为交易所代码
                    standard_exchange = normalize_exchange(first_part)
                    contract = second_part
                except ValueError:
                    # 方法2：尝试将第二部分作为交易所代码
                    try:
                        standard_exchange = normalize_exchange(second_part)
                        contract = first_part
                    except ValueError:
                        # 方法3：检查是否为 Tushare 返回值后缀格式
                        # 对于一些特殊的 Tushare 后缀，建立映射关系
                        # 注意：这里映射到标准交易所代码是为了内部处理一致性
                        tushare_suffix_to_exchange = {
                            'CFX': 'CFFEX',  # 中金所的旧后缀
                            'SHF': 'SHFE',   # 上期所
                            'DCE': 'DCE',    # 大商所
                            'ZCE': 'CZCE',   # 郑商所
                            'INE': 'INE',    # 上期能源
                            'GFE': 'GFEX',   # 广期所（Tushare返回值后缀）
                            'GFEX': 'GFEX',  # 广期所（保留兼容性）
                            'CFFEX': 'CFFEX',  # 中金所标准后缀
                        }

                        if second_part.upper() in tushare_suffix_to_exchange:
                            standard_exchange = tushare_suffix_to_exchange[second_part.upper()]
                            contract = first_part
                            # 保存原始的 Tushare 后缀，用于输出时保持原格式
                            original_tushare_suffix = second_part.upper()
                            is_tushare_format = True
                        else:
                            # 都无法识别，抛出异常让外层处理
                            raise ValueError(f"Cannot identify exchange in symbol '{symbol}', parts: '{first_part}', '{second_part}'")

                # 根据格式要求进行转换
                if format == "tushare":
                    # 如果输入本身就是 Tushare 格式且包含原始后缀，保持原样
                    if 'is_tushare_format' in locals() and is_tushare_format and 'original_tushare_suffix' in locals():
                        formatted_symbol = f"{contract}.{original_tushare_suffix}"
                    else:
                        # 否则转换为标准 Tushare 格式（使用后缀映射）
                        tushare_exchange = _get_cached_exchange_mapping(standard_exchange, "tushare", "suffix")
                        formatted_symbol = f"{contract}.{tushare_exchange}"
                elif format in ["vnpy", "vn"]:
                    # vnpy格式：contract.exchange
                    vnpy_exchange = _get_cached_exchange_mapping(standard_exchange, "vnpy")
                    formatted_symbol = f"{contract}.{vnpy_exchange}"
                else:
                    # 使用标准格式：exchange.contract
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
                            tushare_exchange = _get_cached_exchange_mapping(standard_exchange, "tushare", "suffix")
                            # 使用Tushare格式：contract.exchange（使用后缀映射）
                            formatted_symbol = f"{symbol}.{tushare_exchange}"
                        elif format in ["vnpy", "vn"]:
                            # vnpy格式：contract.exchange
                            vnpy_exchange = _get_cached_exchange_mapping(standard_exchange, "vnpy")
                            formatted_symbol = f"{symbol}.{vnpy_exchange}"
                        else:
                            # 使用标准格式：exchange.symbol
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
        if format in ["tushare", "ts", "vnpy", "vn"]:
            # 对于 tushare 和 vnpy 格式，交易所代码在后缀，所以取第一个部分
            formatted_symbols = [sym.split('.')[0] for sym in formatted_symbols]
        else:
            # 对于其他格式，交易所代码在前缀，所以取第二个部分
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


@lru_cache(maxsize=1024)
def _infer_stock_exchange_from_config(stock_code: str) -> Optional[str]:
    """基于配置文件推断股票代码对应的交易所

    使用 exchanges.toml 中的 stock_index_rules 配置进行精确匹配。

    Args:
        stock_code: 6位股票代码

    Returns:
        Optional[str]: 标准交易所代码（SHSE/SZSE/BSE）或 None
    """
    if not stock_code or len(stock_code) != 6:
        return None

    try:
        # 尝试转换为整数进行范围比较
        code_num = int(stock_code)
    except ValueError:
        return None

    try:
        config_loader = get_config_loader()
        config = config_loader.load_config('exchanges')
        rules = config.get('stock_index_rules', {})

        # 检查上交所规则
        shse_stocks = rules.get('shse_stocks', {})
        for market_range in shse_stocks.values():
            if isinstance(market_range, str) and '-' in market_range:
                try:
                    start_str, end_str = market_range.split('-')
                    start, end = int(start_str), int(end_str)
                    if start <= code_num <= end:
                        return "SHSE"
                except (ValueError, TypeError):
                    continue

        # 检查深交所规则
        szse_stocks = rules.get('szse_stocks', {})
        for market_range in szse_stocks.values():
            if isinstance(market_range, str) and '-' in market_range:
                try:
                    start_str, end_str = market_range.split('-')
                    start, end = int(start_str), int(end_str)
                    if start <= code_num <= end:
                        return "SZSE"
                except (ValueError, TypeError):
                    continue

        # 北交所规则（4、8、9开头，但需要更精确的范围）
        # 目前配置文件中没有北交所详细规则，使用简单判断
        if stock_code.startswith(('4', '8', '9')):
            return "BSE"

        return None

    except Exception as e:
        # 配置加载失败时回退到硬编码逻辑
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to load stock exchange config, falling back to hardcoded rules: {e}")
        return _infer_stock_exchange_hardcoded(stock_code)


def _infer_stock_exchange_hardcoded(stock_code: str) -> Optional[str]:
    """硬编码的股票交易所推断（后备方案）"""
    if not stock_code:
        return None

    first_digit = stock_code[0]
    if first_digit == "6":
        return "SHSE"
    elif first_digit in ["0", "3"]:
        return "SZSE"
    elif first_digit in ["4", "8", "9"]:
        return "BSE"
    else:
        return None
