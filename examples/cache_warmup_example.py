"""
缓存预热使用示例

演示如何使用 Quantbox 的缓存预热功能来提升应用性能。
"""

import time
import logging

# 设置日志级别
logging.basicConfig(level=logging.INFO)

def example_basic_warmup():
    """基础缓存预热示例"""
    print("=== 基础缓存预热示例 ===")

    import quantbox

    # 方法1：使用推荐的 init() 函数
    print("1. 使用 quantbox.init() 进行初始化和预热...")
    start_time = time.time()
    stats = quantbox.init(auto_warm=True, warm_verbose=True)
    end_time = time.time()

    print(f"   预热统计: {stats}")
    print(f"   总耗时: {end_time - start_time:.3f}s")

    # 测试预热后的性能
    print("\n2. 测试预热后的性能...")
    from quantbox.util.tools import util_format_stock_symbols

    # 批量转换股票代码
    symbols = ["000001", "000002", "600000", "600001", "300001"]
    start_time = time.time()
    formatted = util_format_stock_symbols(symbols, format="tushare")
    end_time = time.time()

    print(f"   转换结果: {formatted}")
    print(f"   转换耗时: {(end_time - start_time) * 1000:.3f}ms")


def example_manual_warmup():
    """手动缓存预热示例"""
    print("\n=== 手动缓存预热示例 ===")

    import quantbox

    # 方法2：手动控制预热
    print("1. 手动预热缓存...")
    stats = quantbox.warm_caches(verbose=True)
    print(f"   预热完成: {stats}")

    # 检查预热状态
    print("\n2. 检查预热状态...")
    status = quantbox.get_cache_warm_status()
    print(f"   预热状态: {status}")


def example_background_warmup():
    """后台缓存预热示例"""
    print("\n=== 后台缓存预热示例 ===")

    import quantbox

    # 方法3：后台预热（不阻塞应用启动）
    print("1. 启动后台预热...")
    quantbox.auto_warm_on_import(enable=True)

    # 应用可以继续执行其他初始化
    print("2. 应用继续其他初始化...")

    # 等待一段时间让预热完成
    time.sleep(2)

    # 检查预热状态
    status = quantbox.get_cache_warm_status()
    print(f"   后台预热状态: {status}")


def example_performance_comparison():
    """性能对比示例"""
    print("\n=== 性能对比示例 ===")

    # 测试数据
    test_symbols = ["000001", "000002", "600000", "600001", "300001"] * 100  # 500个股票代码
    data_sources = ["tushare", "goldminer", "joinquant"]

    # 测试1：未预热的性能
    print("1. 测试未预热性能...")
    from quantbox.util.tools import util_format_stock_symbols
    from quantbox.util.cache_warmup import get_cache_warmer

    # 清除缓存
    cache_warmer = get_cache_warmer()
    util_format_stock_symbols.__wrapped__.cache_clear()  # 清除缓存

    start_time = time.time()
    for data_source in data_sources:
        util_format_stock_symbols(test_symbols, format=data_source)
    no_warm_time = time.time() - start_time
    print(f"   未预热耗时: {no_warm_time:.3f}s")

    # 测试2：预热后的性能
    print("2. 测试预热后性能...")
    import quantbox
    quantbox.warm_caches(verbose=False)

    start_time = time.time()
    for data_source in data_sources:
        util_format_stock_symbols(test_symbols, format=data_source)
    warm_time = time.time() - start_time
    print(f"   预热后耗时: {warm_time:.3f}s")

    # 计算性能提升
    improvement = ((no_warm_time - warm_time) / no_warm_time) * 100
    print(f"   性能提升: {improvement:.1f}%")


def example_production_usage():
    """生产环境使用示例"""
    print("\n=== 生产环境使用示例 ===")

    print("""
在生产环境中，推荐的使用方式：

1. 应用启动时（推荐）：
   import quantbox
   stats = quantbox.init(auto_warm=True, warm_verbose=False)

2. 在应用配置文件中：
   # config.py
   import quantbox

   def init_app():
       quantbox.init(
           auto_warm=True,
           warm_verbose=False,  # 生产环境关闭详细日志
           log_level="INFO"
       )

3. 在 Web 框架中（如 FastAPI）：
   from fastapi import FastAPI
   import quantbox

   app = FastAPI()

   @app.on_event("startup")
   async def startup_event():
       stats = quantbox.init(auto_warm=True)
       print(f"应用启动完成，缓存预热耗时: {stats['total_time']:.3f}s")

4. 在命令行工具中：
   import quantbox

   def main():
       quantbox.init(auto_warm=True)
       # 应用逻辑

   if __name__ == "__main__":
       main()
""")


if __name__ == "__main__":
    print("Quantbox 缓存预热功能演示")
    print("=" * 50)

    # 运行所有示例
    example_basic_warmup()
    example_manual_warmup()
    example_background_warmup()
    example_performance_comparison()
    example_production_usage()

    print("\n" + "=" * 50)
    print("演示完成！")
    print("更多信息请参考 quantbox.util.cache_warmup 模块文档。")