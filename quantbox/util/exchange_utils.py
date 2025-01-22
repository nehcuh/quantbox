"""交易所相关的工具函数和常量"""

from typing import Dict, Set, Optional, Union, List

# 交易所代码映射关系
EXCHANGE_MAPPING: Dict[str, str] = {
    'SSE': 'SHSE',  # 上海证券交易所
    # 添加其他映射关系
}

# 反向映射，自动生成
EXCHANGE_MAPPING_REVERSE: Dict[str, str] = {v: k for k, v in EXCHANGE_MAPPING.items()}

# 有效的交易所代码
VALID_EXCHANGES: Set[str] = {
    'SHSE',  # 上海证券交易所
    'SZSE',  # 深圳证券交易所
    'CFFEX',  # 中国金融期货交易所
    'SHFE',  # 上海期货交易所
    'CZCE',  # 郑州商品交易所
    'DCE',  # 大连商品交易所
    'INE',  # 上海国际能源交易中心
    'SSE',  # TuShare原始代码，会被自动转换为SHSE
}

def normalize_exchange(exchange: str) -> str:
    """标准化交易所代码

    将交易所代码转换为标准格式。如果输入的代码无效，
    将引发 ValueError。

    Args:
        exchange: 交易所代码

    Returns:
        str: 标准化后的交易所代码

    Raises:
        ValueError: 当输入的交易所代码无效时
    """
    if exchange not in VALID_EXCHANGES:
        raise ValueError(
            f"无效的交易所代码: {exchange}。"
            f"有效的代码包括: {', '.join(sorted(VALID_EXCHANGES))}"
        )
    
    return EXCHANGE_MAPPING.get(exchange, exchange)

def denormalize_exchange(exchange: str) -> str:
    """将标准化的交易所代码转换回原始格式

    Args:
        exchange: 标准化的交易所代码

    Returns:
        str: 原始格式的交易所代码

    Raises:
        ValueError: 当输入的交易所代码无效时
    """
    if exchange not in VALID_EXCHANGES:
        raise ValueError(
            f"无效的交易所代码: {exchange}。"
            f"有效的代码包括: {', '.join(sorted(VALID_EXCHANGES))}"
        )
    
    return EXCHANGE_MAPPING_REVERSE.get(exchange, exchange)

def validate_exchanges(exchanges: Optional[Union[str, List[str]]] = None) -> List[str]:
    """验证并标准化交易所代码列表

    Args:
        exchanges: 交易所代码或代码列表，如果为 None，则使用默认值

    Returns:
        List[str]: 标准化后的交易所代码列表

    Raises:
        ValueError: 当任何交易所代码无效时
    """
    if exchanges is None:
        return ['SHSE', 'SZSE']  # 默认交易所
    
    if isinstance(exchanges, str):
        exchanges = [exchanges]
    
    return [normalize_exchange(e) for e in exchanges]
