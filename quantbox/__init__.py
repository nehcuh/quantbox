"""
Quantbox - 量化交易工具包

一个功能强大的Python量化交易工具包，提供：
- 多数据源支持（Tushare、掘金等）
- 统一的数据获取和处理接口
- 期货、股票、期权数据支持
- 高性能缓存和预热机制
"""

__version__ = "1.0.0"
__author__ = "Quantbox Team"

import logging
import time
from typing import Optional

# 设置基础日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 导入主要功能模块
from quantbox.util.date_utils import util_make_date_stamp
from quantbox.util.tools import util_to_json_from_pandas
from quantbox.fetchers.local_fetcher import LocalFetcher
from quantbox.fetchers.fetcher_tushare import TSFetcher
from quantbox.fetchers.fetcher_goldminer import GMFetcher

# 全局变量标记预热状态
_cache_warmed = False


def warm_caches(verbose: bool = False) -> dict:
    """预热所有关键缓存

    在应用启动时调用此函数来预热交易所映射、日期处理等关键缓存，
    显著提升运行时性能。

    Args:
        verbose: 是否显示详细信息

    Returns:
        dict: 预热统计信息

    Examples:
        >>> # 在应用启动时预热缓存
        >>> import quantbox
        >>> stats = quantbox.warm_caches()
        >>> print(f"预热完成，耗时: {stats['total_time']:.3f}s")

        >>> # 详细模式
        >>> stats = quantbox.warm_caches(verbose=True)
    """
    global _cache_warmed

    if _cache_warmed and not verbose:
        return {'total_time': 0, 'functions_warmed': 0, 'cache_entries': 0, 'message': 'already_warmed'}

    try:
        # 导入预热模块
        from quantbox.util.cache_warmup import warm_all_caches
        from quantbox.util.tools import warm_tools_cache
        from quantbox.util.exchange_utils import warm_exchange_cache

        if verbose:
            logger.setLevel(logging.DEBUG)

        start_time = time.time()

        # 调用各模块的预热函数
        warm_tools_cache()
        warm_exchange_cache()

        # 执行预热
        stats = warm_all_caches()

        _cache_warmed = True

        if verbose:
            logger.info(f"缓存预热成功完成！")
            logger.info(f"总耗时: {stats['total_time']:.3f}s")
            logger.info(f"预热函数: {stats['functions_warmed']}")
            logger.info(f"缓存条目: {stats['cache_entries']}")

        return stats

    except Exception as e:
        logger.error(f"缓存预热失败: {e}")
        return {
            'total_time': 0,
            'functions_warmed': 0,
            'cache_entries': 0,
            'error': str(e)
        }


def auto_warm_on_import(enable: bool = True):
    """启用/禁用模块导入时的自动缓存预热

    Args:
        enable: 是否启用自动预热

    Examples:
        >>> # 启用自动预热（推荐在应用入口处调用）
        >>> import quantbox
        >>> quantbox.auto_warm_on_import(True)
    """
    if enable:
        # 在后台执行预热，不阻塞导入
        import threading

        def warm_in_background():
            warm_caches(verbose=False)

        thread = threading.Thread(target=warm_in_background, daemon=True)
        thread.start()
        logger.info("后台缓存预热已启动")

        global _cache_warmed
        _cache_warmed = True
    else:
        logger.info("自动缓存预热已禁用")


def get_cache_warm_status() -> dict:
    """获取缓存预热状态

    Returns:
        dict: 预热状态信息
    """
    global _cache_warmed

    try:
        from quantbox.util.cache_warmup import get_cache_warmer
        cache_warmer = get_cache_warmer()

        return {
            'warmed': _cache_warmed,
            'registered_functions': len(cache_warmer.pre_warmed_functions),
            'stats': cache_warmer.get_stats()
        }
    except Exception as e:
        return {
            'warmed': _cache_warmed,
            'error': str(e)
        }


def init(
    auto_warm: bool = True,
    warm_verbose: bool = False,
    log_level: str = "INFO"
) -> dict:
    """初始化 Quantbox

    这是推荐的初始化方式，会自动处理缓存预热和日志配置。

    Args:
        auto_warm: 是否自动预热缓存
        warm_verbose: 是否显示预热详细信息
        log_level: 日志级别

    Returns:
        dict: 初始化统计信息

    Examples:
        >>> # 标准初始化
        >>> import quantbox
        >>> stats = quantbox.init()

        >>> # 详细初始化
        >>> stats = quantbox.init(warm_verbose=True, log_level="DEBUG")
        >>> print(f"Quantbox 初始化完成，预热耗时: {stats['total_time']:.3f}s")
    """
    # 设置日志级别
    logging.getLogger('quantbox').setLevel(getattr(logging, log_level.upper()))

    stats = {}

    if auto_warm:
        stats = warm_caches(verbose=warm_verbose)
        logger.info("Quantbox 初始化完成，缓存已预热")
    else:
        logger.info("Quantbox 初始化完成，缓存未预热")

    return stats


# 模块级别的自动预热（可选）
# 取消注释下面的代码可以在导入 quantbox 时自动预热缓存
# try:
#     auto_warm_on_import(True)
# except Exception:
#     # 静默处理预热失败，不影响模块导入
#     pass
