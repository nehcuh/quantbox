"""
数据验证装饰器模块

本模块提供用于数据验证和错误处理的装饰器函数。包含 DataFrame 验证和自动重试机制，
用于确保数据的完整性和操作的可靠性。

功能特性：
- DataFrame 字段验证
- 数据类型验证
- 自动失败重试
- 可配置的验证规则
- 完整的错误日志

装饰器：
    validate_dataframe: DataFrame 结构和内容验证
    retry: 失败操作重试逻辑

依赖：
    - pandas
    - functools
    - quantbox.config
    - quantbox.logger
"""

import functools
from typing import Any, Callable, Dict, List, Optional, Union

import pandas as pd

from quantbox.config import load_config
from quantbox.logger import setup_logger


logger = setup_logger(__name__)


def validate_dataframe(collection_name: str) -> Callable:
    """
    DataFrame 数据验证装饰器。

    对装饰函数返回的 DataFrame 对象执行验证检查。验证内容包括必需字段的存在性
    和基本的数据类型验证。

    参数：
        collection_name: 集合名称，用于从配置中确定必需字段

    返回：
        Callable: 装饰器函数

    注意：
        - 必需字段从配置文件中获取
        - 验证所有必需字段的存在性
        - 自动进行日期字段类型转换
        - 验证失败时返回 None
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Optional[pd.DataFrame]:
            # 获取函数返回的 DataFrame
            df = func(*args, **kwargs)

            if df is None or df.empty:
                logger.warning(f"{func.__name__} 返回空数据")
                return df

            # 获取必需字段配置
            config = load_config()
            required_fields = config['validation']['required_fields'].get(collection_name, [])

            # 验证必需字段
            missing_fields = [field for field in required_fields if field not in df.columns]
            if missing_fields:
                logger.error(
                    f"{func.__name__} 缺少必需字段: {missing_fields}"
                )
                return None

            # 验证和转换数据类型
            try:
                if 'trade_date' in df.columns:
                    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime("%Y-%m-%d")
                if 'list_date' in df.columns:
                    df['list_date'] = pd.to_datetime(df['list_date']).dt.strftime("%Y-%m-%d")
                if 'delist_date' in df.columns:
                    df['delist_date'] = pd.to_datetime(df['delist_date']).dt.strftime("%Y-%m-%d")
            except Exception as e:
                logger.error(f"{func.__name__} 日期字段转换失败: {str(e)}")
                return None

            return df
        return wrapper
    return decorator


def retry(
    max_attempts: int = 3,
    delay: int = 60,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    重试装饰器。

    为可能由于临时问题（如网络问题、速率限制）而失败的函数添加自动重试功能。
    支持配置重试次数、延迟时间和特定的异常类型。

    参数：
        max_attempts: 最大重试次数，默认为 3
        delay: 重试间隔秒数，默认为 60
        exceptions: 需要重试的异常类型元组，默认为 (Exception,)

    返回：
        Callable: 装饰器函数

    注意：
        - 仅对指定的异常类型进行重试
        - 实现指数退避延迟
        - 记录每次重试尝试和最终失败
        - 保留原函数的签名和文档字符串
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = Exception("No error occurred")

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1} failed: {str(e)}, "
                            f"retrying in {delay} seconds"
                        )
                        import time
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {str(e)}"
                        )

            raise last_exception

        return wrapper
    return decorator
