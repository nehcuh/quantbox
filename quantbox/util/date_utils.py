"""
Trading date utilities

本模块提供统一的日期处理工具函数，包括：
- 日期格式转换（字符串、整数、datetime 对象互转）
- 时间戳转换
- 交易日查询和计算

所有函数都支持多种日期输入格式，自动进行转换。
"""
import datetime
from typing import Union, Dict, Any, Optional, List
from functools import lru_cache

from quantbox.config.config_loader import get_config_loader

# 日期类型别名，提高代码可读性
DateLike = Union[str, int, datetime.date, datetime.datetime, None]

# 获取数据库连接的辅助函数
def _get_database():
    """获取 MongoDB 数据库连接"""
    return get_config_loader().get_mongodb_client().quantbox


def date_to_int(date: DateLike) -> int:
    """将日期转换为整数格式 (YYYYMMDD)

    支持的输入格式：
    - None: 返回今天的日期
    - int: 如 20240126（8位整数）
    - str: "2024-01-26" 或 "20240126"
    - datetime.date: date 对象
    - datetime.datetime: datetime 对象

    Args:
        date: 需要转换的日期

    Returns:
        int: 整数格式的日期，如 20240126

    Raises:
        ValueError: 日期格式无效或日期值不合法

    Examples:
        >>> date_to_int("2024-01-26")
        20240126
        >>> date_to_int(20240126)
        20240126
        >>> date_to_int(datetime.date(2024, 1, 26))
        20240126
    """
    if date is None:
        return int(datetime.date.today().strftime('%Y%m%d'))

    # 处理整数类型
    if isinstance(date, int):
        date_str = str(date)
        if len(date_str) != 8:
            raise ValueError(f"Integer date must be 8 digits, got {len(date_str)}")
        # 验证日期有效性（会抛出 ValueError 如果无效）
        datetime.datetime.strptime(date_str, '%Y%m%d')
        return date

    # 处理 datetime 对象
    if isinstance(date, datetime.datetime):
        return int(date.strftime('%Y%m%d'))

    # 处理 date 对象
    if isinstance(date, datetime.date):
        return int(date.strftime('%Y%m%d'))

    # 处理字符串类型
    if isinstance(date, str):
        # 移除所有分隔符（支持 '-', '/', '.' 等）
        date_str = date.replace('-', '').replace('/', '').replace('.', '').strip()

        if len(date_str) != 8:
            raise ValueError(f"Date string must result in 8 digits, got '{date}'")

        # 验证日期有效性
        try:
            datetime.datetime.strptime(date_str, '%Y%m%d')
            return int(date_str)
        except ValueError as e:
            raise ValueError(f"Invalid date string '{date}': {str(e)}") from e

    raise ValueError(f"Unsupported date type: {type(date).__name__}")


def int_to_date_str(date_int: int) -> str:
    """将整数格式日期转换为字符串格式 (YYYY-MM-DD)

    Args:
        date_int: 整数格式的日期，如 20240126

    Returns:
        str: 字符串格式的日期，如 '2024-01-26'

    Raises:
        ValueError: 日期格式无效

    Examples:
        >>> int_to_date_str(20240126)
        '2024-01-26'
    """
    date_str = str(date_int)
    if len(date_str) != 8:
        raise ValueError(f"Date integer must be 8 digits, got {len(date_str)}")

    # 验证日期有效性并转换
    try:
        dt = datetime.datetime.strptime(date_str, '%Y%m%d')
        return dt.strftime('%Y-%m-%d')
    except ValueError as e:
        raise ValueError(f"Invalid date integer '{date_int}': {str(e)}") from e


def date_to_str(date: DateLike, format: str = "%Y-%m-%d") -> str:
    """将日期转换为指定格式的字符串

    Args:
        date: 需要转换的日期
        format: 日期格式字符串，默认为 "%Y-%m-%d"

    Returns:
        str: 格式化的日期字符串

    Raises:
        ValueError: 日期格式无效

    Examples:
        >>> date_to_str("2024-01-26")
        '2024-01-26'
        >>> date_to_str(20240126, "%Y/%m/%d")
        '2024/01/26'
    """
    if date is None:
        return datetime.date.today().strftime(format)

    # 直接处理 datetime 对象
    if isinstance(date, datetime.datetime):
        return date.strftime(format)

    # 直接处理 date 对象
    if isinstance(date, datetime.date):
        return date.strftime(format)

    # 处理整数和字符串：先转换为 date 对象
    try:
        if isinstance(date, int):
            date_str = str(date)
            if len(date_str) != 8:
                raise ValueError(f"Integer date must be 8 digits, got {len(date_str)}")
            dt = datetime.datetime.strptime(date_str, '%Y%m%d')
        elif isinstance(date, str):
            # 尝试多种格式
            date_clean = date.replace('-', '').replace('/', '').replace('.', '').strip()
            if len(date_clean) == 8:
                dt = datetime.datetime.strptime(date_clean, '%Y%m%d')
            else:
                # 尝试直接解析
                dt = datetime.datetime.fromisoformat(date.replace('/', '-'))
        else:
            raise ValueError(f"Unsupported date type: {type(date).__name__}")

        return dt.strftime(format)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Failed to convert date '{date}' to string: {str(e)}") from e


def util_make_date_stamp(
    cursor_date: DateLike = None,
    format: str = "%Y-%m-%d"
) -> float:
    """将日期转换为 Unix 时间戳

    将指定格式的日期转换为 Unix 时间戳（秒级精度）。
    时间戳对应当天 00:00:00（本地时间）。

    Args:
        cursor_date: 需要转换的日期，支持多种格式
                    如果为 None，则使用当前日期
        format: 日期格式字符串，默认为 "%Y-%m-%d"（仅在需要格式化输出时使用）

    Returns:
        float: Unix 时间戳（秒）

    Raises:
        ValueError: 日期格式无效

    Examples:
        >>> util_make_date_stamp("2024-01-26")
        1706227200.0
    """
    if cursor_date is None:
        dt = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    elif isinstance(cursor_date, datetime.datetime):
        # 取日期部分，时间设为 00:00:00
        dt = datetime.datetime.combine(cursor_date.date(), datetime.time.min)
    elif isinstance(cursor_date, datetime.date):
        dt = datetime.datetime.combine(cursor_date, datetime.time.min)
    else:
        # 对于整数和字符串，先转换为整数日期，再转为 datetime
        date_int = date_to_int(cursor_date)
        date_str = str(date_int)
        dt = datetime.datetime.strptime(date_str, '%Y%m%d')

    return dt.timestamp()


@lru_cache(maxsize=1024)
def is_trade_date(
    cursor_date: DateLike = None,
    exchange: str = 'SHSE'
) -> bool:
    """判断指定日期是否为交易日

    检查指定日期在指定交易所是否为交易日。

    Args:
        cursor_date: 需要检查的日期
                    支持格式：19981203, "20240910", datetime.date()
                    默认为 None，表示当前日期
        exchange: 交易所代码，默认为上交所

    Returns:
        bool: 是否为交易日

    Examples:
        >>> is_trade_date("2024-01-26", "SHSE")
        True
    """
    # 统一转换为整数格式进行查询（性能更好）
    try:
        date_int = date_to_int(cursor_date)
    except (ValueError, TypeError):
        return False

    query = {
        "exchange": exchange,
        "date_int": date_int
    }

    result = _get_database().trade_date.find_one(query, {"_id": 0})
    return result is not None


@lru_cache(maxsize=1024)
def get_pre_trade_date(
    cursor_date: DateLike = None,
    exchange: str = 'SHSE',
    n: int = 1,
    include_input: bool = False
) -> Optional[Dict[str, Any]]:
    """获取指定日期之前的第n个交易日

    Args:
        cursor_date: 指定日期，默认为当前日期
        exchange: 交易所代码，默认为上交所
        n: 往前回溯的天数，默认为 1
        include_input: 是否将输入日期考虑在内（如果输入日期是交易日），默认为 False
                      True: 如果输入日期是交易日，则将其计入n个交易日中
                      False: 不论输入日期是否为交易日，都从比输入日期更早的日期开始计数

    Returns:
        Optional[Dict[str, Any]]: 交易日信息，如果没有找到则返回 None
        返回字段包括：
        - exchange: 交易所代码
        - trade_date: 交易日期
        - pretrade_date: 前一交易日
        - datestamp: 日期时间戳
        - date_int: 整数格式的日期 (YYYYMMDD)

    Examples:
        >>> get_pre_trade_date("2024-01-26", "SHSE", 1)
        {'exchange': 'SHSE', 'trade_date': '2024-01-25', ...}
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")

    date_int = date_to_int(cursor_date)

    # 构建查询条件
    if include_input and is_trade_date(date_int, exchange):
        query = {
            "exchange": exchange,
            "date_int": {"$lte": date_int}
        }
    else:
        query = {
            "exchange": exchange,
            "date_int": {"$lt": date_int}
        }

    # 查询前n个交易日
    cursor = _get_database().trade_date.find(
        query,
        {"_id": 0}
    ).sort("date_int", -1).skip(n - 1).limit(1)

    try:
        return cursor[0]
    except (IndexError, KeyError):
        return None


@lru_cache(maxsize=1024)
def get_next_trade_date(
    cursor_date: DateLike = None,
    exchange: str = 'SHSE',
    n: int = 1,
    include_input: bool = False
) -> Optional[Dict[str, Any]]:
    """获取指定日期之后的第n个交易日

    Args:
        cursor_date: 指定日期，默认为当前日期
        exchange: 交易所代码，默认为上交所
        n: 往后推进的天数，默认为 1
        include_input: 是否将输入日期考虑在内（如果输入日期是交易日），默认为 False
                      True: 如果输入日期是交易日，则将其计入n个交易日中
                      False: 不论输入日期是否为交易日，都从比输入日期更晚的日期开始计数

    Returns:
        Optional[Dict[str, Any]]: 交易日信息，如果没有找到则返回 None
        返回字段包括：
        - exchange: 交易所代码
        - trade_date: 交易日期
        - pretrade_date: 前一交易日
        - datestamp: 日期时间戳
        - date_int: 整数格式的日期 (YYYYMMDD)

    Examples:
        >>> get_next_trade_date("2024-01-26", "SHSE", 1)
        {'exchange': 'SHSE', 'trade_date': '2024-01-29', ...}
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")

    date_int = date_to_int(cursor_date)

    # 构建查询条件
    if include_input and is_trade_date(date_int, exchange):
        query = {
            "exchange": exchange,
            "date_int": {"$gte": date_int}
        }
    else:
        query = {
            "exchange": exchange,
            "date_int": {"$gt": date_int}
        }

    # 查询后n个交易日
    cursor = _get_database().trade_date.find(
        query,
        {"_id": 0}
    ).sort("date_int", 1).skip(n - 1).limit(1)

    try:
        return cursor[0]
    except (IndexError, KeyError):
        return None


def get_trade_calendar(
    start_date: DateLike = None,
    end_date: DateLike = None,
    exchange: str = 'SHSE'
) -> List[Dict[str, Any]]:
    """获取指定日期范围内的交易日历

    Args:
        start_date: 起始日期，默认为 None
        end_date: 结束日期，默认为当前日期
        exchange: 交易所代码，默认为上交所

    Returns:
        List[Dict[str, Any]]: 交易日历数据列表，每个字典包含以下字段：
        - exchange: 交易所代码
        - trade_date: 交易日期
        - pretrade_date: 前一交易日
        - datestamp: 日期时间戳
        - date_int: 整数格式的日期

    Examples:
        >>> calendar = get_trade_calendar("2024-01-01", "2024-01-31", "SHSE")
        >>> len(calendar)
        21
    """
    # 设置默认日期
    if start_date is None:
        start_date = datetime.date(2010, 1, 1)
    if end_date is None:
        end_date = datetime.date.today()

    # 转换为整数格式（使用整数查询比时间戳更高效）
    start_int = date_to_int(start_date)
    end_int = date_to_int(end_date)

    # 构建查询条件
    query = {
        'exchange': exchange,
        'date_int': {
            '$gte': start_int,
            '$lte': end_int
        }
    }

    # 执行查询
    cursor = _get_database().trade_date.find(
        query,
        {'_id': 0}
    ).sort('date_int', 1)

    return list(cursor)


def get_trade_dates(
    start_date: DateLike = None,
    end_date: DateLike = None,
    exchange: str = 'SHSE'
) -> List[str]:
    """获取指定日期范围内的交易日期列表（仅返回日期字符串）

    这是一个便捷函数，返回交易日期字符串列表而不是完整的字典信息。

    Args:
        start_date: 起始日期，默认为 None
        end_date: 结束日期，默认为当前日期
        exchange: 交易所代码，默认为上交所

    Returns:
        List[str]: 交易日期字符串列表，格式为 'YYYY-MM-DD'

    Examples:
        >>> dates = get_trade_dates("2024-01-01", "2024-01-05", "SHSE")
        >>> print(dates)
        ['2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05']
    """
    calendar = get_trade_calendar(start_date, end_date, exchange)
    return [item['trade_date'] for item in calendar]
