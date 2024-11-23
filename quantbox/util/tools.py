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
    """
    explanation:
        将日期转换为时间戳

    params:
        * cursor_date ->
            含义：指定转换格式的日期
            类型：str, int, datetime.date
            参数支持: [19901203, "20020923", ...]

    returns:
        时间戳
    """
    if cursor_date is None:
        cursor_date = datetime.date.today()
    if isinstance(cursor_date, int):
        cursor_date = str(cursor_date)
    return time.mktime(
        time.strptime(pd.Timestamp(cursor_date).strftime(format), format)
    )


def util_to_json_from_pandas(data: pd.DataFrame) -> Dict:
    """
    explanation:
        将pandas数据转换成json格式

    params:
        * data ->:
            含义: pandas数据
            类型: pd.DataFrame
    return:
        dict
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
    symbols: Union[str, List[str]], format: str = "normal"
) -> List[str]:
    """
    explanation:
        格式化股票代码，注意，无论传入是 str, 还是 List，返回 都是 List

    params:
        symbols ->
            含义：股票代码或股票代码列表
            类型：Union[str, List[str]]
            参数支持："SZSE.000001", "000001.SZ", "000001"

        format ->
            含义：指定股票代码格式类型
            类型：str
            参数支持："normal/number"("600000"), "standard/gm"("SHSE.600000"), "wd/wind/ts/tushare"("000001.SZ"), "jq/joinquant"("000001.XSHG")
    returns:
        Union[str, List[str]]
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
    elif format in ["standard", "gm", "goldminer"]:
        return [f"{gm_exchange_map[code[0]]}.{code}" for code in numbers]
    elif format in ["wd", "wind", "ts", "tushare"]:
        return [f"{code}.{ts_exchange_map[code[0]]}" for code in numbers]
    elif format in ["jq", "joinquant"]:
        return [f"{code}.{jq_exchange_map[code[0]]}" for code in numbers]


# Constants for format types
FORMAT_GOLDMINER = ["gm", "goldminer", "掘金"]
FORMAT_TUSHARE = ["ts", "tushare"]
_FUTURE_CODE_PATTERN = re.compile(r"^[A-Za-z]+")

def _normalize_exchange(exchange: str, format_type: str) -> str:
    """Normalize exchange name based on format type."""
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
    """Format contract based on exchange and format type."""
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
    """
    Format future symbols to a standardized format.
    
    Args:
        symbols: Single symbol string or list of symbols
        format: Format type ("standard", "wd/wind/ts/tushare")
        include_exchange: Whether to include exchange in the formatted symbol
    
    Returns:
        List of formatted symbols in "exchange.contract" format
    
    Examples:
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
        if "." in symbol:  # Exchange included (e.g., SHFE.rb2501)
            exchange, contract = symbol.split('.')
            exchange = _normalize_exchange(exchange, format)
            formatted_symbols.append(_format_contract(exchange, contract, format))
        else:  # No exchange prefix
            fut_code = _FUTURE_CODE_PATTERN.match(symbol).group()
            exchange = fut_code_exchange_map[fut_code.upper()]
            exchange = _normalize_exchange(exchange, format)
            formatted_symbols.append(_format_contract(exchange, symbol, format))
    if not include_exchange:
        return [symbol.split('.')[1] for symbol in formatted_symbols] 
    return formatted_symbols


@lru_cache(maxsize=None)
def load_contract_exchange_mapper() -> Dict:
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
    """
    explanation:
        判断指定日期是否为交易日，默认为 None，即当期日期的判断，交易所默认为 SSE

    params:
        cursor_date ->
            含义：指定日期，默认为 None，即当期日期
            类型：str, int, datetime.date
            参数支持：19981203, "20240910", datetime.date()
        exchange ->
            含义：指定交易所，默认为上交所
            类型：str
             参数支持：SSE, SZSE, DCE, INE, ...

    returns:
        bool：是否是交易日
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
