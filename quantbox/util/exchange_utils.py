"""
Exchange utilities

本模块提供统一的交易所代码处理工具函数，包括：
- 交易所代码标准化和验证
- 不同数据源的交易所代码映射
- 交易所类型判断（股票、期货等）

所有函数都遵循统一的命名规范和错误处理标准。
"""
from typing import Dict, Set, Optional, Union, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ExchangeType(Enum):
    """交易所类型枚举"""
    STOCK = "stock"      # 股票交易所
    FUTURES = "futures"  # 期货交易所
    OPTIONS = "options"  # 期权交易所


# 标准交易所代码（MongoDB 存储格式）
STANDARD_EXCHANGES = {
    # 股票交易所
    "SHSE": {"name": "上海证券交易所", "type": ExchangeType.STOCK, "aliases": ["SSE", "SH"]},
    "SZSE": {"name": "深圳证券交易所", "type": ExchangeType.STOCK, "aliases": ["SZ"]},
    "BSE": {"name": "北京证券交易所", "type": ExchangeType.STOCK, "aliases": ["BJ"]},
    # 期货交易所
    "SHFE": {"name": "上海期货交易所", "type": ExchangeType.FUTURES, "aliases": ["SHF"]},
    "DCE": {"name": "大连商品交易所", "type": ExchangeType.FUTURES, "aliases": []},
    "CZCE": {"name": "郑州商品交易所", "type": ExchangeType.FUTURES, "aliases": ["ZCE"]},
    "CFFEX": {"name": "中国金融期货交易所", "type": ExchangeType.FUTURES, "aliases": []},
    "INE": {"name": "上海国际能源交易中心", "type": ExchangeType.FUTURES, "aliases": []},
    "GFEX": {"name": "广州期货交易所", "type": ExchangeType.FUTURES, "aliases": []},
}

# 构建完整的交易所代码集合（包括别名）
VALID_EXCHANGES: Set[str] = set(STANDARD_EXCHANGES.keys())
for standard_code, info in STANDARD_EXCHANGES.items():
    VALID_EXCHANGES.update(info["aliases"])

# 别名到标准代码的映射
ALIAS_TO_STANDARD: Dict[str, str] = {}
for standard_code, info in STANDARD_EXCHANGES.items():
    for alias in info["aliases"]:
        ALIAS_TO_STANDARD[alias] = standard_code

# 标准代码到别名的反向映射
STANDARD_TO_ALIAS: Dict[str, str] = {v: k for k, v in ALIAS_TO_STANDARD.items()}

# 股票交易所列表
STOCK_EXCHANGES: List[str] = [
    code for code, info in STANDARD_EXCHANGES.items()
    if info["type"] == ExchangeType.STOCK
]

# 期货交易所列表
FUTURES_EXCHANGES: List[str] = [
    code for code, info in STANDARD_EXCHANGES.items()
    if info["type"] == ExchangeType.FUTURES
]

# 所有交易所列表
ALL_EXCHANGES: List[str] = list(STANDARD_EXCHANGES.keys())


def normalize_exchange(exchange: str) -> str:
    """将交易所代码标准化为 MongoDB 存储格式

    支持的输入：
    - 标准代码：SHSE, SZSE, SHFE, DCE, CZCE, CFFEX, INE, BSE
    - 别名：SSE -> SHSE, SHF -> SHFE, ZCE -> CZCE

    Args:
        exchange: 交易所代码（标准或别名）

    Returns:
        str: 标准化的交易所代码

    Raises:
        ValueError: 交易所代码无效

    Examples:
        >>> normalize_exchange("SSE")
        'SHSE'
        >>> normalize_exchange("SHSE")
        'SHSE'
        >>> normalize_exchange("SHF")
        'SHFE'
    """
    if not exchange or not exchange.strip():
        raise ValueError("Exchange code cannot be empty")

    exchange = exchange.strip().upper()

    if exchange not in VALID_EXCHANGES:
        raise ValueError(
            f"Invalid exchange code: '{exchange}'. "
            f"Valid codes: {', '.join(sorted(ALL_EXCHANGES))}"
        )

    # 如果是别名，转换为标准代码
    return ALIAS_TO_STANDARD.get(exchange, exchange)


def denormalize_exchange(exchange: str, target: str = "tushare") -> str:
    """将标准交易所代码转换为特定数据源的格式

    Args:
        exchange: 标准化的交易所代码
        target: 目标数据源，支持 "tushare", "goldminer", "vnpy"

    Returns:
        str: 转换后的交易所代码

    Raises:
        ValueError: 交易所代码无效或目标数据源不支持

    Examples:
        >>> denormalize_exchange("SHSE", "tushare")
        'SH'
        >>> denormalize_exchange("SHFE", "tushare")
        'SHF'
        >>> denormalize_exchange("SHFE", "vnpy")
        'SHFE'
    """
    if not exchange:
        raise ValueError("Exchange code cannot be empty")

    exchange = exchange.strip().upper()

    if exchange not in STANDARD_EXCHANGES:
        raise ValueError(
            f"Invalid standard exchange code: '{exchange}'. "
            f"Valid codes: {', '.join(sorted(ALL_EXCHANGES))}"
        )

    if target.lower() == "tushare":
        # TuShare 特殊映射：使用简称
        tushare_mapping = {
            "SHSE": "SH",
            "SZSE": "SZ",
            "BSE": "BJ",
            "SHFE": "SHF",
            "CZCE": "ZCE",
            "DCE": "DCE",
            "CFFEX": "CFFEX",
            "INE": "INE",
            "GFEX": "GFEX",
        }
        return tushare_mapping.get(exchange, exchange)
    elif target.lower() == "goldminer":
        # 掘金使用标准代码
        return exchange
    elif target.lower() == "vnpy":
        # vnpy使用标准交易所代码
        return exchange
    else:
        raise ValueError(
            f"Unsupported target: '{target}'. "
            f"Supported targets: 'tushare', 'goldminer', 'vnpy'"
        )


def validate_exchange(exchange: str) -> str:
    """验证单个交易所代码并返回标准格式

    这是 normalize_exchange 的别名，提供更语义化的函数名

    Args:
        exchange: 交易所代码

    Returns:
        str: 标准化的交易所代码

    Raises:
        ValueError: 交易所代码无效
    """
    return normalize_exchange(exchange)


def validate_exchanges(
    exchanges: Optional[Union[str, List[str]]] = None,
    default_type: str = "all"
) -> List[str]:
    """验证并标准化交易所代码列表

    Args:
        exchanges: 交易所代码或代码列表
                  - None: 使用默认值（根据 default_type）
                  - str: 单个交易所代码
                  - List[str]: 交易所代码列表
        default_type: 当 exchanges 为 None 时使用的默认类型
                     - "all": 所有交易所
                     - "stock": 股票交易所
                     - "futures": 期货交易所

    Returns:
        List[str]: 标准化后的交易所代码列表

    Raises:
        ValueError: 任何交易所代码无效或 default_type 无效

    Examples:
        >>> validate_exchanges("SSE")
        ['SHSE']
        >>> validate_exchanges(["SSE", "SZSE"])
        ['SHSE', 'SZSE']
        >>> validate_exchanges(None, "stock")
        ['SHSE', 'SZSE', 'BSE']
    """
    if exchanges is None:
        # 使用默认值
        if default_type == "all":
            return ALL_EXCHANGES.copy()
        elif default_type == "stock":
            return STOCK_EXCHANGES.copy()
        elif default_type == "futures":
            return FUTURES_EXCHANGES.copy()
        else:
            raise ValueError(
                f"Invalid default_type: '{default_type}'. "
                f"Valid types: 'all', 'stock', 'futures'"
            )

    # 处理字符串输入（可能包含逗号分隔）
    if isinstance(exchanges, str):
        if "," in exchanges:
            exchanges = [e.strip() for e in exchanges.split(",")]
        else:
            exchanges = [exchanges]

    # 验证并标准化每个交易所代码
    result = []
    for exchange in exchanges:
        if exchange and exchange.strip():  # 跳过空字符串和空白字符串
            result.append(normalize_exchange(exchange))

    # 去重并保持顺序
    seen = set()
    unique_result = []
    for exchange in result:
        if exchange not in seen:
            seen.add(exchange)
            unique_result.append(exchange)

    return unique_result


def is_stock_exchange(exchange: str) -> bool:
    """判断是否为股票交易所

    Args:
        exchange: 交易所代码（标准或别名）

    Returns:
        bool: 是否为股票交易所

    Examples:
        >>> is_stock_exchange("SHSE")
        True
        >>> is_stock_exchange("SHFE")
        False
    """
    standard_code = normalize_exchange(exchange)
    return STANDARD_EXCHANGES[standard_code]["type"] == ExchangeType.STOCK


def is_futures_exchange(exchange: str) -> bool:
    """判断是否为期货交易所

    Args:
        exchange: 交易所代码（标准或别名）

    Returns:
        bool: 是否为期货交易所

    Examples:
        >>> is_futures_exchange("SHFE")
        True
        >>> is_futures_exchange("SHSE")
        False
    """
    standard_code = normalize_exchange(exchange)
    return STANDARD_EXCHANGES[standard_code]["type"] == ExchangeType.FUTURES


def get_exchange_info(exchange: str) -> Dict[str, any]:
    """获取交易所的详细信息

    Args:
        exchange: 交易所代码（标准或别名）

    Returns:
        Dict: 交易所信息，包含以下字段：
            - code: 标准代码
            - name: 中文名称
            - type: 交易所类型
            - aliases: 别名列表

    Raises:
        ValueError: 交易所代码无效

    Examples:
        >>> info = get_exchange_info("SSE")
        >>> info["code"]
        'SHSE'
        >>> info["name"]
        '上海证券交易所'
    """
    standard_code = normalize_exchange(exchange)
    exchange_data = STANDARD_EXCHANGES[standard_code]

    return {
        "code": standard_code,
        "name": exchange_data["name"],
        "type": exchange_data["type"].value,
        "aliases": exchange_data["aliases"].copy()
    }


def get_all_exchanges(exchange_type: Optional[str] = None) -> List[str]:
    """获取所有交易所代码列表

    Args:
        exchange_type: 交易所类型过滤
                      - None: 返回所有交易所
                      - "stock": 只返回股票交易所
                      - "futures": 只返回期货交易所

    Returns:
        List[str]: 交易所代码列表

    Examples:
        >>> len(get_all_exchanges())
        8
        >>> len(get_all_exchanges("stock"))
        3
    """
    if exchange_type is None:
        return ALL_EXCHANGES.copy()
    elif exchange_type == "stock":
        return STOCK_EXCHANGES.copy()
    elif exchange_type == "futures":
        return FUTURES_EXCHANGES.copy()
    else:
        raise ValueError(
            f"Invalid exchange_type: '{exchange_type}'. "
            f"Valid types: None, 'stock', 'futures'"
        )


def get_exchange_for_data_source(exchange: str, data_source: str = "tushare", usage: str = "api") -> str:
    """
    获取特定数据源的交易所代码格式

    Args:
        exchange: 标准交易所代码（如 'SHSE', 'SZSE'）
        data_source: 数据源名称，默认为 'tushare'
        usage: 使用模式，"api" 用于API查询参数，"suffix" 用于返回值后缀，默认为 "api"

    Returns:
        str: 特定数据源的交易所代码

    Raises:
        ValueError: 当交易所代码无效或数据源不支持时

    Examples:
        >>> get_exchange_for_data_source("SHSE", "tushare", usage="api")
        'SSE'
        >>> get_exchange_for_data_source("SHSE", "tushare", usage="suffix")
        'SH'
        >>> get_exchange_for_data_source("SHFE", "tushare", usage="suffix")
        'SHF'
        >>> get_exchange_for_data_source("SHFE", "joinquant", usage="api")
        'XSGE'
    """
    try:
        import toml
        from pathlib import Path

        # 标准化交易所代码
        standard_exchange = normalize_exchange(exchange)

        # 加载数据源映射配置
        config_path = Path(__file__).parent.parent / "config" / "exchanges.toml"
        if not config_path.exists():
            # 如果配置文件不存在，返回标准代码
            logger.warning(f"Data source config file not found: {config_path}")
            return standard_exchange

        config = toml.load(config_path)
        data_sources = config.get('data_sources', {})

        if data_source not in data_sources:
            logger.warning(f"Data source '{data_source}' not found in config")
            return standard_exchange

        # 对于 Tushare，需要区分 API 参数和返回值后缀
        if data_source == "tushare" and usage == "suffix":
            # 使用后缀映射配置
            suffix_key = f"data_sources.{data_source}_suffix"

            # 检查后缀映射配置是否存在
            if 'data_sources' in config and f"{data_source}_suffix" in config['data_sources']:
                suffix_mappings = config['data_sources'][f"{data_source}_suffix"]
                if standard_exchange in suffix_mappings:
                    return suffix_mappings[standard_exchange]
                else:
                    # 如果没有后缀映射，尝试使用默认映射
                    logger.debug(f"No suffix mapping for {standard_exchange} in {suffix_key}")
                    source_mappings = data_sources[data_source]
                    if standard_exchange in source_mappings:
                        return source_mappings[standard_exchange]
            else:
                logger.warning(f"Tushare suffix config '{suffix_key}' not found in config file")
        else:
            # 使用标准映射配置
            source_mappings = data_sources[data_source]
            if standard_exchange in source_mappings:
                return source_mappings[standard_exchange]

        # 如果没有特定映射，返回标准代码
        logger.debug(f"No specific mapping for {standard_exchange} in {data_source} (usage: {usage})")
        return standard_exchange

    except Exception as e:
        logger.error(f"Error getting exchange for data source '{data_source}' (usage: {usage}): {e}")
        # 发生错误时返回标准代码
        return normalize_exchange(exchange)


def convert_exchanges_for_data_source(
    exchanges: Union[str, List[str]],
    data_source: str = "tushare"
) -> List[str]:
    """
    将交易所代码列表转换为特定数据源的格式

    Args:
        exchanges: 交易所代码或代码列表
        data_source: 数据源名称，默认为 'tushare'

    Returns:
        List[str]: 转换后的交易所代码列表

    Examples:
        >>> convert_exchanges_for_data_source(["SHFE", "DCE"], "tushare")
        ['SHF', 'DCE']
        >>> convert_exchanges_for_data_source("SHFE,DCE", "tushare")
        ['SHF', 'DCE']
    """
    if isinstance(exchanges, str):
        if "," in exchanges:
            exchanges = [e.strip() for e in exchanges.split(",")]
        else:
            exchanges = [exchanges]

    # 验证并标准化交易所代码
    validated_exchanges = validate_exchanges(exchanges)

    # 转换为特定数据源格式
    converted_exchanges = []
    for exchange in validated_exchanges:
        converted_exchange = get_exchange_for_data_source(exchange, data_source)
        converted_exchanges.append(converted_exchange)

    return converted_exchanges


def warm_exchange_cache():
    """预热 exchange_utils 模块的缓存

    该函数会在应用启动时被调用来预热关键缓存。
    """
    from quantbox.util.cache_warmup import get_cache_warmer

    cache_warmer = get_cache_warmer()

    # 预热常用交易所标准化
    common_exchanges = [
        "SHSE", "SZSE", "BSE",  # 股票交易所
        "SHFE", "DCE", "CZCE", "CFFEX", "INE", "GFEX",  # 期货交易所
        "SSE", "SH", "SZ", "BJ", "SHF", "ZCE"  # 常用别名
    ]

    for exchange in common_exchanges:
        cache_warmer.register_function(normalize_exchange, exchange)

    # 预热常用数据源映射
    standard_exchanges = ["SHFE", "DCE", "CZCE", "CFFEX", "INE", "GFEX", "SSE", "SZSE", "BSE"]
    data_sources = ["tushare", "goldminer", "joinquant"]

    for exchange in standard_exchanges:
        for data_source in data_sources:
            cache_warmer.register_function(get_exchange_for_data_source, exchange, data_source)

    # 预热批量转换
    cache_warmer.register_function(convert_exchanges_for_data_source, "SHFE,DCE,CZCE", "tushare")
    cache_warmer.register_function(convert_exchanges_for_data_source, "SSE,SZSE", "tushare")
