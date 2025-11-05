"""
缓存预热模块

在应用启动时预热关键缓存，提升运行时性能。
包括交易所映射缓存、日期处理缓存等。
"""

import logging
import time
from typing import List, Dict, Set
from functools import lru_cache

# 设置日志
logger = logging.getLogger(__name__)


class CacheWarmer:
    """缓存预热器

    负责在应用启动时预热各种缓存，提升运行时性能。
    """

    def __init__(self):
        self.pre_warmed_functions = []
        self.stats = {
            'total_time': 0,
            'functions_warmed': 0,
            'cache_entries': 0
        }

    def register_function(self, func, *args, **kwargs):
        """注册需要预热的函数

        Args:
            func: 需要预热的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
        """
        self.pre_warmed_functions.append((func, args, kwargs))

    def warm_all(self):
        """预热所有注册的函数"""
        logger.info("开始缓存预热...")
        start_time = time.time()

        for func, args, kwargs in self.pre_warmed_functions:
            try:
                func_name = getattr(func, '__name__', str(func))
                logger.debug(f"预热函数: {func_name}")

                # 调用函数以填充缓存
                result = func(*args, **kwargs)

                # 如果函数有缓存信息，记录缓存条目数
                if hasattr(func, 'cache_info'):
                    cache_info = func.cache_info()
                    self.stats['cache_entries'] += cache_info.hits + cache_info.misses
                    logger.debug(f"  缓存信息: {cache_info}")

                self.stats['functions_warmed'] += 1

            except Exception as e:
                logger.warning(f"预热函数 {getattr(func, '__name__', 'unknown')} 失败: {e}")

        self.stats['total_time'] = time.time() - start_time
        logger.info(f"缓存预热完成！耗时: {self.stats['total_time']:.3f}s, "
                   f"预热函数: {self.stats['functions_warmed']}, "
                   f"缓存条目: {self.stats['cache_entries']}")

    def get_stats(self) -> Dict:
        """获取预热统计信息"""
        return self.stats.copy()


# 全局缓存预热器实例
_cache_warmer = CacheWarmer()


def get_cache_warmer() -> CacheWarmer:
    """获取全局缓存预热器实例"""
    return _cache_warmer


def warm_exchange_caches():
    """预热交易所映射缓存"""
    from quantbox.util.exchange_utils import get_exchange_for_data_source, normalize_exchange

    # 标准交易所列表
    standard_exchanges = [
        "SHFE", "DCE", "CZCE", "CFFEX", "INE", "GFEX",  # 期货
        "SSE", "SZSE", "BSE"  # 股票
    ]

    # 数据源列表
    data_sources = ["tushare", "goldminer", "vnpy"]

    # 预热交易所标准化
    for exchange in standard_exchanges:
        _cache_warmer.register_function(normalize_exchange, exchange)

    # 预热数据源映射
    for exchange in standard_exchanges:
        for data_source in data_sources:
            _cache_warmer.register_function(get_exchange_for_data_source, exchange, data_source)

    logger.debug(f"已注册 {len(standard_exchanges)} 个交易所标准化缓存")
    logger.debug(f"已注册 {len(standard_exchanges) * len(data_sources)} 个数据源映射缓存")


def warm_tools_caches():
    """预热 tools 模块的缓存"""
    from quantbox.util.tools import _get_cached_exchange_mapping

    # 标准交易所列表（对应配置文件中的名称）
    standard_exchanges = [
        "SSE", "SZSE", "BSE",  # 股票交易所（配置文件中的名称）
        "SHFE", "DCE", "CZCE", "CFFEX", "INE", "GFEX"  # 期货交易所
    ]

    # 数据源列表
    data_sources = ["tushare", "goldminer", "vnpy"]

    # 预热工具函数的交易所映射缓存
    for exchange in standard_exchanges:
        for data_source in data_sources:
            _cache_warmer.register_function(_get_cached_exchange_mapping, exchange, data_source)

    logger.debug(f"已注册 {len(standard_exchanges) * len(data_sources)} 个工具函数映射缓存")


def warm_date_caches():
    """预热日期处理缓存"""
    from quantbox.util.date_utils import date_to_int, int_to_date_str, util_make_date_stamp

    # 常用日期格式
    test_dates = [
        "2024-01-01", "2024-12-31", "2024-06-30",  # 标准格式
        "20240101", "20241231", "20240630",          # 数字格式
    ]

    # 预热日期转换缓存
    for date_str in test_dates:
        _cache_warmer.register_function(date_to_int, date_str)

    # 预热整数日期转字符串缓存
    test_int_dates = [20240101, 20241231, 20240630]
    for date_int in test_int_dates:
        _cache_warmer.register_function(int_to_date_str, date_int)

    logger.debug(f"已注册 {len(test_dates) + len(test_int_dates)} 个日期处理缓存")


def warm_contract_mapping_caches():
    """预热期货合约映射缓存"""
    from quantbox.util.tools import _load_contract_exchange_mapper_from_config, _load_contract_exchange_mapper_from_db

    # 预热配置文件映射缓存
    _cache_warmer.register_function(_load_contract_exchange_mapper_from_config)

    # 预热数据库映射缓存
    _cache_warmer.register_function(_load_contract_exchange_mapper_from_db)

    logger.debug("已注册期货合约映射缓存")


def warm_all_caches():
    """预热所有缓存

    这是主要的预热入口函数，建议在应用启动时调用。
    """
    logger.info("开始预热所有缓存...")

    # 注册各种缓存预热
    warm_exchange_caches()
    warm_tools_caches()
    warm_date_caches()
    warm_contract_mapping_caches()

    # 执行预热
    _cache_warmer.warm_all()

    # 返回统计信息
    return _cache_warmer.get_stats()


def auto_warm_on_import():
    """在模块导入时自动预热

    这个函数可以在模块导入时自动调用，
    适合在关键模块的 __init__.py 中使用。
    """
    try:
        warm_all_caches()
        return True
    except Exception as e:
        logger.warning(f"自动缓存预热失败: {e}")
        return False


# 装饰器：自动注册函数到预热列表
def auto_warm(*args, **kwargs):
    """自动预热装饰器

    用法:
    @auto_warm("arg1", kwarg1="value")
    def my_function(arg1, kwarg1=None):
        pass
    """
    def decorator(func):
        _cache_warmer.register_function(func, *args, **kwargs)
        return func
    return decorator


if __name__ == "__main__":
    # 测试缓存预热
    logging.basicConfig(level=logging.INFO)

    print("测试缓存预热功能...")
    stats = warm_all_caches()

    print(f"\n预热统计:")
    print(f"  总耗时: {stats['total_time']:.3f}s")
    print(f"  预热函数数: {stats['functions_warmed']}")
    print(f"  缓存条目数: {stats['cache_entries']}")
