"""
pytest 配置文件

配置异步测试环境
"""

import pytest
import asyncio


def pytest_collection_modifyitems(items):
    """修改测试项"""
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
