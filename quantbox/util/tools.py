from typing import Union, Dict
import datetime
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
