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
        target: 目标数据源，支持 "tushare", "goldminer", "joinquant"
        
    Returns:
        str: 转换后的交易所代码
        
    Raises:
        ValueError: 交易所代码无效或目标数据源不支持
        
    Examples:
        >>> denormalize_exchange("SHSE", "tushare")
        'SH'
        >>> denormalize_exchange("SHFE", "tushare")
        'SHF'
        >>> denormalize_exchange("SHFE", "joinquant")
        'XSGE'
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
        }
        return tushare_mapping.get(exchange, exchange)
    elif target.lower() == "goldminer":
        # 掘金使用标准代码
        return exchange
    elif target.lower() == "joinquant":
        # 聚宽特殊映射：X前缀
        joinquant_mapping = {
            "SHSE": "XSHG",
            "SZSE": "XSHE",
            "BSE": "BJSE",
            "SHFE": "XSGE",
            "CZCE": "XZCE",
            "DCE": "XDCE",
            "CFFEX": "CCFX",
            "INE": "XINE",
        }
        return joinquant_mapping.get(exchange, exchange)
    else:
        raise ValueError(
            f"Unsupported target: '{target}'. "
            f"Supported targets: 'tushare', 'goldminer', 'joinquant'"
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
