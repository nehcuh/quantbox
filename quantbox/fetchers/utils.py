"""
Utility functions for fetchers
"""
from typing import Union, List, Dict, Any, Optional
import datetime
from quantbox.util.basic import DATABASE, EXCHANGES, STOCK_EXCHANGES, FUTURE_EXCHANGES
from quantbox.util.date_utils import util_make_date_stamp


class QueryBuilder:
    """查询构建器，用于构建 MongoDB 查询条件"""
    
    @staticmethod
    def normalize_exchanges(exchanges: Union[str, List[str], None]) -> List[str]:
        """
        标准化交易所参数

        Args:
            exchanges: 交易所列表或字符串

        Returns:
            List[str]: 标准化后的交易所列表
        """
        if exchanges is None:
            return EXCHANGES.copy()
        if isinstance(exchanges, str):
            return exchanges.split(",")
        return exchanges

    @staticmethod
    def build_exchange_query(exchanges: Union[str, List[str], None]) -> Dict[str, Any]:
        """
        构建交易所查询条件

        Args:
            exchanges: 交易所列表或字符串

        Returns:
            Dict: MongoDB 查询条件
        """
        exchanges = QueryBuilder.normalize_exchanges(exchanges)
        return {"exchange": {"$in": exchanges}} if exchanges else {}

    @staticmethod
    def build_date_range_query(
        start_date: Union[str, int, datetime.datetime, None] = None,
        end_date: Union[str, int, datetime.datetime, None] = None,
        date_field: str = "datestamp"
    ) -> Dict[str, Any]:
        """
        构建日期范围查询条件

        Args:
            start_date: 起始日期
            end_date: 结束日期
            date_field: 日期字段名

        Returns:
            Dict: MongoDB 查询条件
        """
        query = {}
        if start_date or end_date:
            query[date_field] = {}
            if start_date:
                query[date_field]["$gte"] = util_make_date_stamp(start_date)
            if end_date:
                query[date_field]["$lte"] = util_make_date_stamp(end_date)
        return query

    @staticmethod
    def build_single_date_query(
        cursor_date: Union[str, int, datetime.datetime],
        include: bool,
        before: bool,
        date_field: str = "datestamp"
    ) -> Dict[str, Any]:
        """
        构建单个日期查询条件

        Args:
            cursor_date: 指定日期
            include: 是否包含当天
            before: True 表示查询之前的日期，False 表示之后的日期
            date_field: 日期字段名

        Returns:
            Dict: MongoDB 查询条件
        """
        datestamp = util_make_date_stamp(cursor_date)
        operator = "$lte" if before else "$gte"
        if not include:
            operator = "$lt" if before else "$gt"
        return {date_field: {operator: datestamp}}

    @staticmethod
    def build_projection(fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        构建字段投影

        Args:
            fields: 需要返回的字段列表

        Returns:
            Dict: MongoDB 投影条件
        """
        projection = {"_id": 0}
        if fields:
            projection.update({field: 1 for field in fields})
        return projection


class DateRangeValidator:
    """日期范围验证器"""

    @staticmethod
    def validate_date_range(
        start_date: Union[str, int, datetime.datetime, None],
        end_date: Union[str, int, datetime.datetime, None]
    ) -> None:
        """
        验证日期范围是否有效

        Args:
            start_date: 起始日期
            end_date: 结束日期

        Raises:
            ValueError: 日期范围无效时抛出异常
        """
        if start_date and end_date:
            start_stamp = util_make_date_stamp(start_date)
            end_stamp = util_make_date_stamp(end_date)
            if start_stamp > end_stamp:
                raise ValueError("起始日期不能大于结束日期")


class ExchangeValidator:
    """交易所验证器"""

    @staticmethod
    def validate_stock_exchange(exchange: str) -> None:
        """
        验证股票交易所是否有效

        Args:
            exchange: 交易所代码

        Raises:
            ValueError: 交易所无效时抛出异常
        """
        if exchange not in STOCK_EXCHANGES:
            raise ValueError(f"无效的股票交易所: {exchange}")

    @staticmethod
    def validate_future_exchange(exchange: str) -> None:
        """
        验证期货交易所是否有效

        Args:
            exchange: 交易所代码

        Raises:
            ValueError: 交易所无效时抛出异常
        """
        if exchange not in FUTURE_EXCHANGES:
            raise ValueError(f"无效的期货交易所: {exchange}")

    @staticmethod
    def validate_exchanges(exchanges: List[str]) -> None:
        """
        验证交易所列表是否有效

        Args:
            exchanges: 交易所列表

        Raises:
            ValueError: 交易所无效时抛出异常
        """
        invalid_exchanges = set(exchanges) - set(EXCHANGES)
        if invalid_exchanges:
            raise ValueError(f"无效的交易所: {invalid_exchanges}")
