"""
Trading date utilities

本模块提供统一的日期处理工具函数，包括：
- 日期格式转换（字符串、整数、datetime 对象互转）
- 时间戳转换
- 交易日查询和计算

所有函数都支持多种日期输入格式，自动进行转换。
"""
import datetime
import time
from typing import Union, Dict, Any, Optional, List
from functools import lru_cache

import pandas as pd

from quantbox.util.basic import DATABASE

# 日期类型别名，提高代码可读性
DateLike = Union[str, int, datetime.date, datetime.datetime, None]


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
        date = datetime.date.today()
        
    try:
        if isinstance(date, int):
            # 验证整数格式
            date_str = str(date)
            if len(date_str) != 8:
                raise ValueError(f"Integer date must be 8 digits, got {len(date_str)}")
            # 验证日期的有效性
            datetime.datetime.strptime(date_str, '%Y%m%d')
            return date
            
        if isinstance(date, str):
            # 处理 YYYY-MM-DD 格式
            if '-' in date:
                date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
            # 处理 YYYYMMDD 格式
            else:
                date = datetime.datetime.strptime(date, '%Y%m%d').date()
                
        if isinstance(date, datetime.datetime):
            date = date.date()
            
        if isinstance(date, datetime.date):
            return int(date.strftime('%Y%m%d'))
            
        raise ValueError(f"Unsupported date type: {type(date)}")
        
    except ValueError as e:
        raise ValueError(f"Invalid date format for '{date}': {str(e)}") from e


def int_to_date_str(date_int: int) -> str:
    """将整数格式日期转换为字符串格式 (YYYY-MM-DD)

    Args:
        date_int: 整数格式的日期，如 20240126

    Returns:
        str: 字符串格式的日期，如 '2024-01-26'
    """
    date_str = str(date_int)
    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"


def util_make_date_stamp(
    cursor_date: Union[int, str, datetime.date, None] = None,
    format: str = "%Y-%m-%d"
) -> float:
    """将日期转换为时间戳

    将指定格式的日期转换为 Unix 时间戳。

    Args：
        cursor_date: 需要转换的日期，支持整数、字符串或 datetime.date 对象
                    如果为 None，则使用当前日期
        format: 日期格式字符串，默认为 "%Y-%m-%d"

    Returns：
        float: Unix 时间戳
    """
    if cursor_date is None:
        cursor_date = datetime.date.today()
    if isinstance(cursor_date, int):
        # 如果是整数格式的日期，先转换为字符串
        if len(str(cursor_date)) == 8:
            cursor_date = int_to_date_str(cursor_date)
    return time.mktime(
        time.strptime(pd.Timestamp(cursor_date).strftime(format), format)
    )


@lru_cache(maxsize=1024)
def is_trade_date(
    cursor_date: Union[str, int, datetime.date, None] = None,
    exchange: str = 'SHSE'
) -> bool:
    """判断指定日期是否为交易日

    检查指定日期在指定交易所是否为交易日。

    Args：
        cursor_date: 需要检查的日期
                    支持格式：19981203, "20240910", datetime.date()
                    默认为 None，表示当前日期
        exchange: 交易所代码，默认为上交所

    Returns：
        bool: 是否为交易日
    """
    if cursor_date is None:
        cursor_date = datetime.date.today()

    # 如果是整数日期，直接使用整数字段查询
    if isinstance(cursor_date, int) and len(str(cursor_date)) == 8:
        query = {
            "exchange": exchange,
            "date_int": cursor_date
        }
    else:
        # 否则使用时间戳查询
        datestamp = util_make_date_stamp(cursor_date)
        query = {
            "exchange": exchange,
            "datestamp": datestamp
        }

    result = DATABASE.trade_date.find_one(query, {"_id": 0})
    return result is not None


@lru_cache(maxsize=1024)
def get_pre_trade_date(
    cursor_date: Union[str, int, datetime.date, None] = None,
    exchange: str = 'SHSE',
    n: int = 1,
    include_input: bool = False
) -> Optional[Dict[str, Any]]:
    """获取指定日期之前的第n个交易日

    Args：
        cursor_date: 指定日期，默认为当前日期
        exchange: 交易所代码，默认为上交所
        n: 往前回溯的天数，默认为 1
        include_input: 是否将输入日期考虑在内（如果输入日期是交易日），默认为 False
                      True: 如果输入日期是交易日，则将其计入n个交易日中
                      False: 不论输入日期是否为交易日，都从比输入日期更早的日期开始计数

    Returns：
        Optional[Dict[str, Any]]: 交易日信息，如果没有找到则返回 None
        返回字段包括：
        - exchange: 交易所代码
        - trade_date: 交易日期
        - pretrade_date: 前一交易日
        - datestamp: 日期时间戳
        - date_int: 整数格式的日期 (YYYYMMDD)
    """
    if cursor_date is None:
        cursor_date = datetime.date.today()

    # 如果是整数日期，直接使用整数字段查询
    if isinstance(cursor_date, int) and len(str(cursor_date)) == 8:
        query = {
            "exchange": exchange,
            "date_int": {"$lt": cursor_date}
        }
        if include_input and is_trade_date(cursor_date, exchange):
            query["date_int"]["$lte"] = cursor_date
            n -= 1
    else:
        # 否则使用时间戳查询
        datestamp = util_make_date_stamp(cursor_date)
        query = {
            "exchange": exchange,
            "datestamp": {"$lt": datestamp}
        }
        if include_input and is_trade_date(cursor_date, exchange):
            query["datestamp"]["$lte"] = datestamp
            n -= 1

    # 获取前n个交易日
    result = DATABASE.trade_date.find(
        query,
        {"_id": 0},
        sort=[("datestamp", -1)],
        skip=n-1,
        limit=1
    )

    # 返回结果
    try:
        return result[0]
    except (IndexError, KeyError):
        return None


@lru_cache(maxsize=1024)
def get_next_trade_date(
    cursor_date: Union[str, int, datetime.date, None] = None,
    exchange: str = 'SHSE',
    n: int = 1,
    include_input: bool = False
) -> Optional[Dict[str, Any]]:
    """获取指定日期之后的第n个交易日

    Args：
        cursor_date: 指定日期，默认为当前日期
        exchange: 交易所代码，默认为上交所
        n: 往后推进的天数，默认为 1
        include_input: 是否将输入日期考虑在内（如果输入日期是交易日），默认为 False
                      True: 如果输入日期是交易日，则将其计入n个交易日中
                      False: 不论输入日期是否为交易日，都从比输入日期更晚的日期开始计数

    Returns：
        Optional[Dict[str, Any]]: 交易日信息，如果没有找到则返回 None
        返回字段包括：
        - exchange: 交易所代码
        - trade_date: 交易日期
        - pretrade_date: 前一交易日
        - datestamp: 日期时间戳
        - date_int: 整数格式的日期 (YYYYMMDD)
    """
    if cursor_date is None:
        cursor_date = datetime.date.today()

    # 如果是整数日期，直接使用整数字段查询
    if isinstance(cursor_date, int) and len(str(cursor_date)) == 8:
        query = {
            "exchange": exchange,
            "date_int": {"$gt": cursor_date}
        }
        if include_input and is_trade_date(cursor_date, exchange):
            query["date_int"]["$gte"] = cursor_date
            n -= 1
    else:
        # 否则使用时间戳查询
        datestamp = util_make_date_stamp(cursor_date)
        query = {
            "exchange": exchange,
            "datestamp": {"$gt": datestamp}
        }
        if include_input and is_trade_date(cursor_date, exchange):
            query["datestamp"]["$gte"] = datestamp
            n -= 1

    # 获取后n个交易日
    result = DATABASE.trade_date.find(
        query,
        {"_id": 0},
        sort=[("datestamp", 1)],
        skip=n-1,
        limit=1
    )

    # 返回结果
    try:
        return result[0]
    except (IndexError, KeyError):
        return None


def get_trade_calendar(
    start_date: Union[str, int, datetime.date, None] = None,
    end_date: Union[str, int, datetime.date, None] = None,
    exchange: str = 'SHSE'
) -> pd.DataFrame:
    """获取指定日期范围内的交易日历

    Args：
        start_date: 起始日期，默认为 None
        end_date: 结束日期，默认为当前日期
        exchange: 交易所代码，默认为上交所

    Returns：
        pd.DataFrame: 交易日历数据，包含以下字段：
        - exchange: 交易所代码
        - trade_date: 交易日期
        - pretrade_date: 前一交易日
        - datestamp: 日期时间戳
    """
    if start_date is None:
        start_date = datetime.date(2010, 1, 1)
    if end_date is None:
        end_date = datetime.date.today()

    # 将日期转换为时间戳
    start_stamp = util_make_date_stamp(start_date)
    end_stamp = util_make_date_stamp(end_date)

    # 构建查询条件
    query = {
        'exchange': exchange,
        'datestamp': {
            '$gte': start_stamp,
            '$lte': end_stamp
        }
    }

    # 执行查询
    cursor = DATABASE.trade_date.find(
        query,
        {'_id': 0},
        sort=[('datestamp', 1)]
    )

    # 将结果转换为 DataFrame
    df = pd.DataFrame(list(cursor))
    if df.empty:
        return pd.DataFrame(columns=['exchange', 'trade_date', 'pretrade_date', 'datestamp'])
    return df
