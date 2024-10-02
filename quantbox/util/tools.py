from typing import Union, Dict, List
import datetime
import re
import json
import numpy as np
import time
import pandas as pd

def util_make_date_stamp(
    cursor_date: Union[int, str, datetime.date, None] = None,
    format: str="%Y-%m-%d"
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
    return time.mktime(time.strptime(pd.Timestamp(cursor_date).strftime(format), format))


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
    if 'datetime' in data.columns:
        data.datetime = data.datetime.apply(str)
    if 'date' in data.columns:
        if np.issubdtype(data['date'].dtype, np.datetime64):
            data.date = data['date'].dt.strftime("%Y-%m-%d")
        else:
            data.date = data.date.apply(str)
    if 'trade_date' in data.columns:
        if np.issubdtype(data['trade_date'].dtype, np.datetime64):
            data.trade_date = data.trade_date.dt.strftime("%Y-%m-%d")
        else:
            data.trade_date = data.trade_date.apply(str)
    if 'cal_date' in data.columns:
        if np.issubdtype(data['cal_date'].dtype, np.datetime64):
            data.cal_date = data.cal_date.dt.strftime("%Y-%m-%d")
        else:
            data.cal_date = data.cal_date.apply(str)
    return json.loads(data.to_json(orient='records'))


def util_format_stock_symbols(
    symbols: Union[str, List[str]],
    format: str="normal"
) -> List[str]:
    """
    explanation:
        格式化股票代码，注意，如果传入是 str, 传入是 List，返回 都是 List

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
    numbers = [re.search(r'\d+', item).group() for item in symbols]

    gm_exchange_map = {
        "6": "SHSE",
        "0": "SZSE",
        "3": "SZSE",
        "4": "BJSE",
        "8": "BJSE",
        "9": "BJSE"
    }

    jq_exchange_map = {
        "6": "XSHG",
        "0": "XSHE",
        "3": "XSHE",
        "9": "BJSE",
        "4": "BJSE",
        "8": "BJSE"
    }

    ts_exchange_map = {
        "6": "SH",
        "0": "SZ",
        "3": "SZ",
        "9": "BJ",
        "4": "BJ",
        "8": "BJ"
    }

    if format in ["normal", "number"]:
        return numbers
    elif format in ["standard", "gm", "goldminer"]:
        return [f"{gm_exchange_map[code[0]]}.{code}" for code in numbers]
    elif format in ["wd", "wind", "ts", "tushare"]:
        return [f"{code}.{ts_exchange_map[code[0]]}" for code in numbers]
    elif format in ["jq", "joinquant"]:
        return [f"{code}.{jq_exchange_map[code[0]]}" for code in numbers]
