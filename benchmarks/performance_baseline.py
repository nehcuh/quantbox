"""
性能基准测试脚本

用于记录同步版本的性能基线，并与异步版本进行对比。

测试场景:
1. 单次查询（交易日历）
2. 批量查询（期货持仓，多交易所多日期）
3. 数据保存（MongoDB批量写入）
4. 完整流程（下载 + 处理 + 保存）

运行方式:
    python benchmarks/performance_baseline.py --mode sync
    python benchmarks/performance_baseline.py --mode async
    python benchmarks/performance_baseline.py --mode compare
"""

import time
import asyncio
import argparse
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
from pathlib import Path

# 同步适配器（待导入）
# from quantbox.adapters.ts_adapter import TSAdapter
# from quantbox.adapters.local_adapter import LocalAdapter

# 异步适配器（待实现后导入）
# from quantbox.adapters.async_adapters import AsyncTSAdapter, AsyncLocalAdapter


class BenchmarkTimer:
    """性能计时器"""

    def __init__(self, name: str):
        self.name = name
        self.start_time: float = 0
        self.end_time: float = 0
        self.elapsed: float = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time
        print(f"[{self.name}] 耗时: {self.elapsed:.2f}秒")
        return False


class PerformanceBenchmark:
    """性能基准测试"""

    def __init__(self):
        self.results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
        }

    def run_sync_benchmarks(self) -> Dict[str, float]:
        """运行同步版本的基准测试"""
        print("\n" + "=" * 60)
        print("运行同步版本性能测试")
        print("=" * 60 + "\n")

        results = {}

        # 测试 1: 单次查询 - 交易日历
        print("测试 1: 获取交易日历（最近30天）")
        with BenchmarkTimer("同步-交易日历") as timer:
            # 模拟查询（实际测试时需要取消注释）
            # adapter = TSAdapter()
            # end_date = datetime.now()
            # start_date = end_date - timedelta(days=30)
            # df = adapter.get_trade_calendar(start_date=start_date, end_date=end_date)
            time.sleep(0.5)  # 模拟 API 调用
        results["trade_calendar_single"] = timer.elapsed

        # 测试 2: 批量查询 - 期货持仓（5个交易所 × 30个交易日）
        print("\n测试 2: 获取期货持仓（5个交易所 × 30个交易日）")
        with BenchmarkTimer("同步-期货持仓批量") as timer:
            # 模拟逐个查询
            exchanges = ["SHFE", "DCE", "CZCE", "CFFEX", "INE"]
            days = 30
            total_calls = len(exchanges) * days

            for exchange in exchanges:
                for day in range(days):
                    time.sleep(0.2)  # 模拟每次 API 调用

            print(f"  总计 API 调用: {total_calls} 次")
        results["future_holdings_batch"] = timer.elapsed

        # 测试 3: 数据库批量写入
        print("\n测试 3: MongoDB 批量写入（10,000条记录）")
        with BenchmarkTimer("同步-MongoDB批量写入") as timer:
            # 模拟批量写入
            time.sleep(1.0)  # 模拟数据库操作
        results["mongodb_bulk_write"] = timer.elapsed

        # 测试 4: 完整流程（下载 + 处理 + 保存）
        print("\n测试 4: 完整数据流程（下载 + 处理 + 保存）")
        with BenchmarkTimer("同步-完整流程") as timer:
            # 模拟完整流程
            time.sleep(results["future_holdings_batch"] + results["mongodb_bulk_write"])
        results["full_pipeline"] = timer.elapsed

        self.results["tests"]["sync"] = results
        return results

    def run_async_benchmarks(self) -> Dict[str, float]:
        """运行异步版本的基准测试"""
        print("\n" + "=" * 60)
        print("运行异步版本性能测试")
        print("=" * 60 + "\n")

        results = {}

        # 测试 1: 单次查询 - 交易日历
        print("测试 1: 获取交易日历（最近30天）")
        with BenchmarkTimer("异步-交易日历") as timer:
            asyncio.run(self._async_trade_calendar())
        results["trade_calendar_single"] = timer.elapsed

        # 测试 2: 批量查询 - 期货持仓（5个交易所 × 30个交易日并发）
        print("\n测试 2: 获取期货持仓（5个交易所 × 30个交易日，并发）")
        with BenchmarkTimer("异步-期货持仓批量") as timer:
            asyncio.run(self._async_future_holdings_batch())
        results["future_holdings_batch"] = timer.elapsed

        # 测试 3: 数据库批量写入
        print("\n测试 3: MongoDB 异步批量写入（10,000条记录）")
        with BenchmarkTimer("异步-MongoDB批量写入") as timer:
            asyncio.run(self._async_mongodb_write())
        results["mongodb_bulk_write"] = timer.elapsed

        # 测试 4: 完整流程（下载 + 处理 + 保存，管道化）
        print("\n测试 4: 完整数据流程（下载 + 处理 + 保存，管道化）")
        with BenchmarkTimer("异步-完整流程") as timer:
            asyncio.run(self._async_full_pipeline())
        results["full_pipeline"] = timer.elapsed

        self.results["tests"]["async"] = results
        return results

    async def _async_trade_calendar(self):
        """异步获取交易日历"""
        # 模拟异步 API 调用
        await asyncio.sleep(0.5)

    async def _async_future_holdings_batch(self):
        """异步批量获取期货持仓"""
        exchanges = ["SHFE", "DCE", "CZCE", "CFFEX", "INE"]
        days = 30

        async def fetch_one(exchange: str, day: int):
            await asyncio.sleep(0.2)  # 模拟 API 调用
            return f"{exchange}_{day}"

        # 并发执行所有查询
        tasks = [
            fetch_one(exchange, day)
            for exchange in exchanges
            for day in range(days)
        ]

        # 限制并发数为 10
        semaphore = asyncio.Semaphore(10)

        async def bounded_fetch(task):
            async with semaphore:
                return await task

        results = await asyncio.gather(*[bounded_fetch(task) for task in tasks])
        print(f"  并发完成 {len(results)} 次 API 调用")

    async def _async_mongodb_write(self):
        """异步 MongoDB 写入"""
        await asyncio.sleep(0.8)  # 模拟异步写入（比同步快 20%）

    async def _async_full_pipeline(self):
        """异步完整流程（管道化）"""
        # 下载和保存可以并发进行
        await asyncio.gather(
            self._async_future_holdings_batch(),
            self._async_mongodb_write(),
        )

    def compare_results(self):
        """对比同步和异步性能"""
        print("\n" + "=" * 60)
        print("性能对比分析")
        print("=" * 60 + "\n")

        if "sync" not in self.results["tests"] or "async" not in self.results["tests"]:
            print("错误: 请先运行同步和异步基准测试")
            return

        sync_results = self.results["tests"]["sync"]
        async_results = self.results["tests"]["async"]

        print(f"{'测试场景':<30} {'同步(秒)':<12} {'异步(秒)':<12} {'加速比':<10} {'提升':<10}")
        print("-" * 74)

        comparison = {}
        for test_name in sync_results.keys():
            sync_time = sync_results[test_name]
            async_time = async_results[test_name]
            speedup = sync_time / async_time if async_time > 0 else 0
            improvement = ((sync_time - async_time) / sync_time * 100) if sync_time > 0 else 0

            comparison[test_name] = {
                "sync": sync_time,
                "async": async_time,
                "speedup": speedup,
                "improvement_pct": improvement,
            }

            print(
                f"{test_name:<30} {sync_time:<12.2f} {async_time:<12.2f} "
                f"{speedup:<10.2f}x {improvement:<10.1f}%"
            )

        self.results["comparison"] = comparison

        # 计算总体提升
        total_sync = sum(sync_results.values())
        total_async = sum(async_results.values())
        total_speedup = total_sync / total_async if total_async > 0 else 0

        print("-" * 74)
        print(
            f"{'总计':<30} {total_sync:<12.2f} {total_async:<12.2f} "
            f"{total_speedup:<10.2f}x"
        )

    def save_results(self, output_path: str = "benchmarks/results.json"):
        """保存测试结果到文件"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"\n结果已保存到: {output_file}")

    def load_results(self, input_path: str = "benchmarks/results.json"):
        """从文件加载测试结果"""
        input_file = Path(input_path)
        if not input_file.exists():
            print(f"错误: 结果文件不存在: {input_file}")
            return False

        with open(input_file, "r", encoding="utf-8") as f:
            self.results = json.load(f)

        print(f"已加载结果: {input_file}")
        return True


def main():
    parser = argparse.ArgumentParser(description="性能基准测试")
    parser.add_argument(
        "--mode",
        choices=["sync", "async", "compare", "all"],
        default="all",
        help="测试模式: sync(同步), async(异步), compare(对比), all(全部)",
    )
    parser.add_argument(
        "--output",
        default="benchmarks/results.json",
        help="结果输出文件",
    )

    args = parser.parse_args()

    benchmark = PerformanceBenchmark()

    if args.mode in ["sync", "all"]:
        benchmark.run_sync_benchmarks()

    if args.mode in ["async", "all"]:
        benchmark.run_async_benchmarks()

    if args.mode in ["compare", "all"]:
        if args.mode == "compare":
            # 对比模式：加载已有结果
            if not benchmark.load_results(args.output):
                print("提示: 请先运行 --mode sync 和 --mode async")
                return
        benchmark.compare_results()

    # 保存结果
    benchmark.save_results(args.output)

    print("\n" + "=" * 60)
    print("基准测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
