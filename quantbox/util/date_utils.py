"""
Trading date utilities
"""
import datetime
import time
from typing import Union, Dict, Any, Optional
from functools import lru_cache

import pandas as pd

from quantbox.util.basic import DATABASE


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
        cursor_date = str(cursor_date)
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
        exchange: 交易所代码
                默认为 "SHSE"（上海证券交易所）
                支持：SHSE, SZSE, DCE, INE 等

    Returns：
        bool: 是否为交易日
    """
    if cursor_date is None:
        cursor_date = datetime.date.today()
    
    datestamp = util_make_date_stamp(cursor_date)
    
    try:
        result = DATABASE.trade_date.find_one(
            {
                "exchange": exchange,
                "datestamp": datestamp
            },
            {"_id": 0}
        )
        return result is not None
    except Exception as e:
        raise Exception(f"检查交易日失败: {str(e)}")


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
    """
    if cursor_date is None:
        cursor_date = datetime.date.today()
    
    datestamp = util_make_date_stamp(cursor_date)
    
    try:
        # 首先检查输入日期是否为交易日
        is_input_trade_date = is_trade_date(cursor_date, exchange)
        
        # 构建查询条件
        query = {
            "exchange": exchange,
            "datestamp": {"$lt": datestamp} if not include_input else {"$lte": datestamp}
        }
        
        # 如果输入日期是交易日且include_input为True，需要调整跳过的记录数
        skip_count = n - 1 if (is_input_trade_date and include_input) else n
        
        # 如果输入日期是非交易日且include_input为True，我们需要从最近的前一个交易日开始计数
        if not is_input_trade_date and include_input:
            skip_count = n
        
        # 特殊情况：如果是交易日且include_input为True且n>1，我们需要从前一个交易日开始计数
        if is_input_trade_date and include_input and n > 1:
            skip_count = n - 1
            query["datestamp"] = {"$lt": datestamp}
        
        # 执行查询
        result = DATABASE.trade_date.find_one(
            query,
            {"_id": 0},
            sort=[("datestamp", -1)],
            skip=max(0, skip_count - 1)  # 调整skip数量
        )
        
        return result
    except Exception as e:
        raise Exception(f"获取前一交易日失败: {str(e)}")


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
    """
    if cursor_date is None:
        cursor_date = datetime.date.today()
    
    datestamp = util_make_date_stamp(cursor_date)
    
    try:
        # 首先检查输入日期是否为交易日
        is_input_trade_date = is_trade_date(cursor_date, exchange)
        
        # 构建查询条件
        query = {
            "exchange": exchange,
            "datestamp": {"$gt": datestamp} if not include_input else {"$gte": datestamp}
        }
        
        # 如果输入日期是交易日且include_input为True，需要调整跳过的记录数
        skip_count = n - 1 if (is_input_trade_date and include_input) else n
        
        # 如果输入日期是非交易日且include_input为True，我们需要从最近的下一个交易日开始计数
        if not is_input_trade_date and include_input:
            skip_count = n - 1
        
        # 特殊情况：如果是交易日且include_input为True且n>1，我们需要从下一个交易日开始计数
        if is_input_trade_date and include_input and n > 1:
            skip_count = n - 1
            query["datestamp"] = {"$gt": datestamp}
        
        # 执行查询
        result = DATABASE.trade_date.find_one(
            query,
            {"_id": 0},
            sort=[("datestamp", 1)],
            skip=max(0, skip_count - 1)  # 调整skip数量
        )
        
        return result
    except Exception as e:
        raise Exception(f"获取下一交易日失败: {str(e)}")


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
    if end_date is None:
        end_date = datetime.date.today()
    
    start_stamp = util_make_date_stamp(start_date) if start_date is not None else None
    end_stamp = util_make_date_stamp(end_date)
    
    try:
        query = {
            "exchange": exchange,
            "datestamp": {"$lte": end_stamp}
        }
        if start_stamp is not None:
            query["datestamp"]["$gte"] = start_stamp
        
        cursor = DATABASE.trade_date.find(
            query,
            {"_id": 0},
            sort=[("datestamp", 1)]
        )
        
        result = pd.DataFrame(list(cursor))
        return result
    except Exception as e:
        raise Exception(f"获取交易日历失败: {str(e)}")
