"""
Base classes for data fetchers.
基础数据获取器类。

This module provides abstract base classes that define the interface for all data fetchers
in the system. It ensures consistency across different data sources and provides common
utility functions.

本模块提供了定义所有数据获取器接口的抽象基类。它确保了不同数据源之间的一致性，
并提供了常用的工具函数。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Union, Dict, Any
import pandas as pd
from datetime import datetime


class DataValidator:
    """
    Data validation utility class
    数据验证工具类
    """

    @staticmethod
    def validate_dates(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        cursor_date: Optional[str] = None
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Validate and normalize date inputs
        验证和标准化日期输入

        Args:
            start_date: Start date string / 开始日期字符串
            end_date: End date string / 结束日期字符串
            cursor_date: Single reference date / 单个参考日期

        Returns:
            Tuple of validated start and end dates
            验证后的开始和结束日期元组

        Raises:
            ValueError: If date parameters are invalid
                      当日期参数无效时抛出
        """
        if cursor_date and (start_date or end_date):
            raise ValueError("Cannot specify both cursor_date and start_date/end_date")

        if cursor_date:
            return cursor_date, cursor_date
        return start_date, end_date

    @staticmethod
    def validate_symbols(symbols: Optional[List[str]]) -> List[str]:
        """
        Validate symbol inputs
        验证交易代码输入

        Args:
            symbols: List of trading symbols / 交易代码列表

        Returns:
            List of validated symbols / 验证后的交易代码列表
        """
        if not symbols:
            return []
        return [str(symbol).strip().upper() for symbol in symbols]


class BaseFetcher(ABC):
    """
    Abstract base class for all data fetchers
    所有数据获取器的抽象基类

    This class defines the standard interface that all data fetchers must implement.
    本类定义了所有数据获取器必须实现的标准接口。
    """

    def __init__(self):
        """
        Initialize base fetcher
        初始化基础获取器
        """
        self.validator = DataValidator()

    def _format_response(
        self,
        data: pd.DataFrame,
        required_columns: List[str]
    ) -> pd.DataFrame:
        """
        Format and validate response data
        格式化和验证响应数据

        Args:
            data: Raw response data / 原始响应数据
            required_columns: List of required columns / 必需列的列表

        Returns:
            Formatted DataFrame / 格式化后的DataFrame

        Raises:
            ValueError: If required columns are missing / 当缺少必需列时抛出
        """
        if data.empty:
            return pd.DataFrame(columns=required_columns)

        # Ensure all required columns exist / 确保所有必需列都存在
        missing_cols = set(required_columns) - set(data.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        return data[required_columns]

    def _handle_error(self, error: Exception, context: str) -> None:
        """
        Handle and log errors
        处理和记录错误

        Args:
            error: The exception that occurred / 发生的异常
            context: Context where the error occurred / 错误发生的上下文

        Raises:
            The original exception with additional context / 带有额外上下文的原始异常
        """
        error_msg = f"Error in {context}: {str(error)}"
        # TODO: Add proper logging / 添加适当的日志记录
        raise type(error)(error_msg) from error
