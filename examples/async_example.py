"""
异步适配器使用示例

演示如何使用异步适配器进行高性能数据查询。

运行方式:
    python examples/async_example.py
"""

import asyncio
import time
from datetime import datetime, timedelta

# 同步适配器
from quantbox.adapters.ts_adapter import TSAdapter

# 异步适配器
from quantbox.adapters.async_adapters import AsyncTSAdapter


async def example_async_trade_calendar():
    """示例1: 异步获取交易日历"""
    print("\n" + "=" * 60)
    print("示例1: 异步获取交易日历")
    print("=" * 60)

    adapter = AsyncTSAdapter()

    start_time = time.time()
    data = await adapter.get_trade_calendar(
        exchanges=["SHFE", "DCE", "CZCE"],
        start_date=20240101,
        end_date=20240131,
    )
    elapsed = time.time() - start_time

    print(f"获取数据: {len(data)} 条记录")
    print(f"耗时: {elapsed:.2f} 秒")
    print(data.head())


async def example_async_future_holdings():
    """示例2: 异步获取期货持仓（核心优化点）"""
    print("\n" + "=" * 60)
    print("示例2: 异步获取期货持仓（并发查询）")
    print("=" * 60)

    adapter = AsyncTSAdapter(max_concurrent=10, rate_limit=5.0)

    # 查询最近5个交易日的期货持仓
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    start_time = time.time()
    data = await adapter.get_future_holdings(
        exchanges=["SHFE", "DCE"],
        start_date=start_date,
        end_date=end_date,
        show_progress=True,
    )
    elapsed = time.time() - start_time

    print(f"获取数据: {len(data)} 条记录")
    print(f"耗时: {elapsed:.2f} 秒")
    if not data.empty:
        print(data.head())


def example_sync_vs_async():
    """示例3: 同步 vs 异步性能对比"""
    print("\n" + "=" * 60)
    print("示例3: 同步 vs 异步性能对比")
    print("=" * 60)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    # 同步版本
    print("\n[同步版本] 获取期货持仓...")
    sync_adapter = TSAdapter()
    sync_start = time.time()
    try:
        sync_data = sync_adapter.get_future_holdings(
            exchanges=["SHFE"],
            start_date=start_date,
            end_date=end_date,
            show_progress=False,
        )
        sync_elapsed = time.time() - sync_start
        print(f"同步耗时: {sync_elapsed:.2f} 秒")
        print(f"获取记录: {len(sync_data)} 条")
    except Exception as e:
        print(f"同步查询失败: {e}")
        sync_elapsed = 0

    # 异步版本
    print("\n[异步版本] 获取期货持仓...")

    async def async_fetch():
        async_adapter = AsyncTSAdapter(max_concurrent=10)
        data = await async_adapter.get_future_holdings(
            exchanges=["SHFE"],
            start_date=start_date,
            end_date=end_date,
            show_progress=False,
        )
        return data

    async_start = time.time()
    try:
        async_data = asyncio.run(async_fetch())
        async_elapsed = time.time() - async_start
        print(f"异步耗时: {async_elapsed:.2f} 秒")
        print(f"获取记录: {len(async_data)} 条")
    except Exception as e:
        print(f"异步查询失败: {e}")
        async_elapsed = 0

    # 性能对比
    if sync_elapsed > 0 and async_elapsed > 0:
        speedup = sync_elapsed / async_elapsed
        print("\n" + "-" * 60)
        print(f"性能提升: {speedup:.2f}x")
        print(f"时间节省: {sync_elapsed - async_elapsed:.2f} 秒")
        print("-" * 60)


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Quantbox 异步适配器示例")
    print("=" * 60)

    try:
        # 示例1: 交易日历
        await example_async_trade_calendar()

        # 示例2: 期货持仓（异步）
        await example_async_future_holdings()

        # 示例3: 性能对比（需要注释掉以避免重复运行）
        # example_sync_vs_async()

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
