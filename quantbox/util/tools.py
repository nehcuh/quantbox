import datetime
import json
import re
import time
from functools import lru_cache
from typing import Dict, List, Union, Optional

import numpy as np
import pandas as pd

from quantbox.util.basic import DATABASE, EXCHANGES


def util_make_date_stamp(
    cursor_date: Union[int, str, datetime.date, None] = None, format: str = "%Y-%m-%d"
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


def util_to_json_from_pandas(data: pd.DataFrame) -> Dict:
    """将 pandas DataFrame 转换为 JSON 格式

    将 pandas DataFrame 转换为 JSON 格式，同时处理特定的日期列。
    支持处理的日期列包括：datetime、date、trade_date、cal_date。

    Args：
        data: 需要转换的 pandas DataFrame

    Returns：
        Dict: 转换后的 JSON 数据
    """
    if "datetime" in data.columns:
        data.datetime = data.datetime.apply(str)
    if "date" in data.columns:
        if np.issubdtype(data["date"].dtype, np.datetime64):
            data.date = data["date"].dt.strftime("%Y-%m-%d")
        else:
            data.date = data.date.apply(str)
    if "trade_date" in data.columns:
        if np.issubdtype(data["trade_date"].dtype, np.datetime64):
            data.trade_date = data.trade_date.dt.strftime("%Y-%m-%d")
        else:
            data.trade_date = data.trade_date.apply(str)
    if "cal_date" in data.columns:
        if np.issubdtype(data["cal_date"].dtype, np.datetime64):
            data.cal_date = data.cal_date.dt.strftime("%Y-%m-%d")
        else:
            data.cal_date = data.cal_date.apply(str)
    return json.loads(data.to_json(orient="records"))


def util_format_stock_symbols(
    symbols: Union[str, List[str]], format: str = "standard"
) -> List[str]:
    """格式化股票代码

    将股票代码转换为指定的格式。支持单个代码或代码列表，
    可以在不同的格式之间转换（如通用格式、掘金格式、Wind格式等）。

    Args：
        symbols: 股票代码或股票代码列表
                支持格式：["SZSE.000001", "000001.SZ", "000001"]
        format: 目标格式
                - "normal/number": 仅代码（如 "600000"）
                - "standard/gm": 掘金格式（如 "SHSE.600000"）
                - "wd/wind/ts/tushare": Wind/Tushare格式（如 "000001.SZ"）
                - "jq/joinquant": 聚宽格式（如 "000001.XSHG"）

    Returns：
        List[str]: 格式化后的股票代码列表
    """
    if isinstance(symbols, str):
        symbols = symbols.split(",")
    numbers = [re.search(r"\d+", item).group() for item in symbols]

    gm_exchange_map = {
        "6": "SHSE",
        "0": "SZSE",
        "3": "SZSE",
        "4": "BJSE",
        "8": "BJSE",
        "9": "BJSE",
    }

    jq_exchange_map = {
        "6": "XSHG",
        "0": "XSHE",
        "3": "XSHE",
        "9": "BJSE",
        "4": "BJSE",
        "8": "BJSE",
    }

    ts_exchange_map = {"6": "SH", "0": "SZ", "3": "SZ", "9": "BJ", "4": "BJ", "8": "BJ"}

    if format in ["normal", "number"]:
        return numbers
    elif format in ["standard", "gm", "goldminer", "掘金"]:
        return [f"{gm_exchange_map[code[0]]}.{code}" for code in numbers]
    elif format in ["wd", "wind", "ts", "tushare"]:
        return [f"{code}.{ts_exchange_map[code[0]]}" for code in numbers]
    elif format in ["jq", "joinquant", "聚宽"]:
        return [f"{code}.{jq_exchange_map[code[0]]}" for code in numbers]


# 格式类型常量
FORMAT_GOLDMINER = ["gm", "goldminer", "掘金"]
FORMAT_TUSHARE = ["ts", "tushare"]
_FUTURE_CODE_PATTERN = re.compile(r"^[A-Za-z]+")

def _normalize_exchange(exchange: str, format_type: str) -> str:
    """标准化交易所名称

    根据指定的格式类型标准化交易所名称。

    参数：
        exchange: 交易所名称
        format_type: 目标格式类型

    返回：
        str: 标准化后的交易所名称
    """
    if format_type in FORMAT_GOLDMINER:
        if exchange == "SHF":
            return "SHFE"
        elif exchange == "ZCE":
            return "CZCE"
    elif format_type in FORMAT_TUSHARE:
        if exchange == "SHFE":
            return "SHF"
        elif exchange == "CZCE":
            return "ZCE"
    return exchange

def _format_contract(exchange: str, contract: str, format_type: str) -> str:
    """格式化合约代码

    根据交易所和格式类型格式化合约代码。

    参数：
        exchange: 交易所名称
        contract: 合约代码
        format_type: 目标格式类型

    返回：
        str: 格式化后的合约代码
    """
    if exchange in ["CZCE", "ZCE"]:
        if len(contract) > 4:
            if format_type in FORMAT_GOLDMINER and contract[2:6].isdigit():
                contract = contract[:2] + contract[3:]
            elif format_type in FORMAT_TUSHARE and contract[3:5].isdigit():
                contract = contract[:2] + contract[3:]
        return f"{exchange}.{contract.upper()}"
    return f"{exchange}.{contract.lower()}"

def util_format_future_symbols(
    symbols: Union[str, List[str]],
    format: Optional[str] = None,
    include_exchange: Optional[bool] = False
) -> List[str]:
    """格式化期货合约代码

    将期货合约代码转换为标准格式。支持单个代码或代码列表，
    可以选择是否包含交易所前缀。

    Args：
        symbols: 期货合约代码或代码列表
        format: 目标格式
                - None: 标准格式
                - "ts"/"tushare": Tushare格式
        include_exchange: 是否在返回结果中包含交易所前缀

    Returns：
        List[str]: 格式化后的期货合约代码列表

    Examples：
        >>> util_format_future_symbols("M2501")
        ['DCE.m2501']
        >>> util_format_future_symbols("SHFE.rb2501", format="ts")
        ['SHF.rb2501']
    """
    if isinstance(symbols, str):
        symbols = symbols.split(",")
    
    formatted_symbols = []
    fut_code_exchange_map = load_contract_exchange_mapper()
    
    for symbol in symbols:
        if "." in symbol:  # 包含交易所前缀（如 SHFE.rb2501）
            exchange, contract = symbol.split('.')
            exchange = _normalize_exchange(exchange, format)
            formatted_symbols.append(_format_contract(exchange, contract, format))
        else:  # 不包含交易所前缀
            fut_code = _FUTURE_CODE_PATTERN.match(symbol).group()
            exchange = fut_code_exchange_map[fut_code.upper()]
            exchange = _normalize_exchange(exchange, format)
            formatted_symbols.append(_format_contract(exchange, symbol, format))
    if not include_exchange:
        return [symbol.split('.')[1] for symbol in formatted_symbols] 
    return formatted_symbols


@lru_cache(maxsize=None)
def load_contract_exchange_mapper() -> Dict:
    """加载合约与交易所的映射关系

    从数据库中加载期货合约代码与对应交易所的映射关系。
    使用 LRU 缓存以提高性能。

    Returns：
        Dict: 合约代码到交易所的映射字典
    """
    # 使用聚合管道查询不重复的 fut_code 和对应的 exchange
    pipeline = [
        {"$group": {"_id": "$fut_code", "exchange": {"$first": "$exchange"}}},
        {"$project": {"fut_code": "$_id", "exchange": 1, "_id": 0}},
        {
            "$sort": {"fut_code": 1}  # 按 fut_code 排序（可选）
        },
    ]
    collections = DATABASE.future_contracts
    results = list(collections.aggregate(pipeline))
    return {item["fut_code"]: item["exchange"] for item in results}


def is_trade_date(
    cursor_date: Union[str, int, datetime.date, None] = None,
    exchange: str='SHSE'
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

    collections = DATABASE.trade_date

    if exchange not in EXCHANGES:
        raise ValueError("[ERROR]\t 不支持的交易所类型")

    datestamp = util_make_date_stamp(cursor_date)

    count = collections.count_documents({
        "datestamp": datestamp,
        "exchange": exchange
    })
    if count > 0:
        return True
    else:
        return False
