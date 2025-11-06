#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
交易日期查询性能测试脚本

测试场景：
1. 数据库冷启动查询（首次查询，无缓存）
2. 热数据查询（数据已在缓存中）
3. 模拟实际业务场景的查询模式
"""
import time
import random
import datetime
import functools
import pandas as pd
from typing import List, Callable, Dict, Any
from pymongo import MongoClient, ASCENDING

from quantbox.util.date_utils import (
    is_trade_date,
    get_pre_trade_date,
    get_next_trade_date,
    get_trade_calendar
)
from quantbox.adapters.ts_adapter import TSAdapter
from quantbox.adapters.local_adapter import LocalAdapter
from quantbox.config.config_loader import get_config_loader


def clear_lru_cache(func):
    """清除函数的 LRU 缓存"""
    try:
        func.cache_clear()
    except AttributeError:
        pass


def prepare_database():
    """准备数据库环境"""
    # 确保索引存在
    collection = get_config_loader().get_mongodb_client().quantbox['trade_date']

    # 获取现有索引
    existing_indexes = collection.index_information()

    # 创建所需的索引
    required_indexes = [
        [("exchange", ASCENDING), ("datestamp", ASCENDING)],
        [("datestamp", ASCENDING)],
        [("exchange", ASCENDING)]
    ]

    for index in required_indexes:
        index_name = "_".join(f"{field}_{direction}" for field, direction in index)
        if index_name not in existing_indexes:
            print(f"创建索引: {index_name}")
            collection.create_index(index)

    # 如果数据库为空，则从 TuShare 获取数据
    if collection.count_documents({}) == 0:
        print("数据库为空，从 TuShare 获取数据...")
        fetcher = TSAdapter()
        data = ts_fetcher.fetch_trade_dates(
            start_date="2010-01-01",
            end_date="2024-12-31"
        )
        if not data.empty:
            records = data.to_dict('records')
            collection.insert_many(records)
            print(f"插入 {len(records)} 条交易日历数据")


class TradeDateBenchmark:
    """交易日期查询性能测试"""

    def __init__(self):
        """初始化测试环境"""
        self.db = get_config_loader().get_mongodb_client().quantbox
        self.local_fetcher = LocalFetcher()

        # 生成测试数据
        self._prepare_test_data()

    def _prepare_test_data(self):
        """准备测试数据集"""
        # 获取实际的交易日历数据
        self.calendar_df = self.local_fetcher.fetch_trade_dates(
            start_date="2010-01-01",
            end_date="2024-12-31"
        )
        self.trade_dates = self.calendar_df['trade_date'].tolist()

        # 生成非交易日数据
        all_dates = pd.date_range("2010-01-01", "2024-12-31").strftime('%Y-%m-%d').tolist()
        self.non_trade_dates = list(set(all_dates) - set(self.trade_dates))

    def _time_function(
        self,
        func: Callable,
        *args,
        n_times: int = 1,
        clear_cache: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """测量函数执行时间"""
        if clear_cache:
            clear_lru_cache(func)

        times = []
        results = []

        for _ in range(n_times):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            times.append(end_time - start_time)
            results.append(result)

        return {
            'mean_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'total_time': sum(times),
            'n_calls': n_times,
            'results': results
        }

    def benchmark_cold_start(self):
        """测试冷启动性能（首次查询，无缓存）"""
        print("\n=== 冷启动性能测试（首次查询，无缓存）===")

        # 随机选择测试日期
        test_dates = random.sample(self.trade_dates, 5)
        test_dates.extend(random.sample(self.non_trade_dates, 5))

        # 将一半的日期转换为整数格式
        test_dates_int = [int(date.replace('-', '')) for date in test_dates[:5]]
        test_dates = test_dates[5:] + test_dates_int

        for date in test_dates:
            print(f"\n测试日期: {date}")

            # 清除缓存并测试 is_trade_date
            result = self._time_function(is_trade_date, date, n_times=1, clear_cache=True)
            print(f"is_trade_date 冷启动耗时: {result['mean_time']*1000:.2f}ms")

            # 清除缓存并测试 get_pre_trade_date
            result = self._time_function(get_pre_trade_date, date, n_times=1, clear_cache=True)
            print(f"get_pre_trade_date 冷启动耗时: {result['mean_time']*1000:.2f}ms")

            # 清除缓存并测试 get_next_trade_date
            result = self._time_function(get_next_trade_date, date, n_times=1, clear_cache=True)
            print(f"get_next_trade_date 冷启动耗时: {result['mean_time']*1000:.2f}ms")

    def benchmark_hot_data(self, n_times: int = 100):
        """测试热数据性能（数据已在缓存中）"""
        print("\n=== 热数据性能测试（数据已在缓存中）===")

        # 随机选择测试日期
        test_date = random.choice(self.trade_dates)
        print(f"\n测试日期: {test_date}")

        # 预热缓存
        is_trade_date(test_date)
        get_pre_trade_date(test_date)
        get_next_trade_date(test_date)

        # 测试 is_trade_date
        result = self._time_function(is_trade_date, test_date, n_times=n_times)
        print(f"is_trade_date 热数据查询:")
        print(f"  平均耗时: {result['mean_time']*1000:.2f}ms")
        print(f"  最小耗时: {result['min_time']*1000:.2f}ms")
        print(f"  最大耗时: {result['max_time']*1000:.2f}ms")

        # 测试 get_pre_trade_date
        result = self._time_function(get_pre_trade_date, test_date, n_times=n_times)
        print(f"\nget_pre_trade_date 热数据查询:")
        print(f"  平均耗时: {result['mean_time']*1000:.2f}ms")
        print(f"  最小耗时: {result['min_time']*1000:.2f}ms")
        print(f"  最大耗时: {result['max_time']*1000:.2f}ms")

        # 测试 get_next_trade_date
        result = self._time_function(get_next_trade_date, test_date, n_times=n_times)
        print(f"\nget_next_trade_date 热数据查询:")
        print(f"  平均耗时: {result['mean_time']*1000:.2f}ms")
        print(f"  最小耗时: {result['min_time']*1000:.2f}ms")
        print(f"  最大耗时: {result['max_time']*1000:.2f}ms")

    def benchmark_business_scenarios(self):
        """测试实际业务场景"""
        print("\n=== 实际业务场景性能测试 ===")

        # 场景1：连续交易日查询（模拟交易系统）
        print("\n场景1：连续交易日查询（模拟交易系统）")
        start_idx = random.randint(0, len(self.trade_dates) - 100)
        test_dates = self.trade_dates[start_idx:start_idx + 100]

        # 清除缓存
        clear_lru_cache(is_trade_date)
        clear_lru_cache(get_pre_trade_date)
        clear_lru_cache(get_next_trade_date)

        start_time = time.perf_counter()
        for date in test_dates:
            # 模拟交易系统的日常查询
            is_trade = is_trade_date(date)
            if is_trade:
                pre_date = get_pre_trade_date(date)
                next_date = get_next_trade_date(date)
        end_time = time.perf_counter()

        total_time = end_time - start_time
        print(f"总耗时: {total_time*1000:.2f}ms")
        print(f"平均每日耗时: {total_time*1000/len(test_dates):.2f}ms")

        # 场景2：跨期查询（模拟回测系统）
        print("\n场景2：跨期查询（模拟回测系统）")
        # 随机选择一个开始日期
        start_date = random.choice(self.trade_dates[:-365])  # 确保至少有一年的数据
        next_date = get_next_trade_date(start_date, n=250)  # 获取后250个交易日
        end_date = next_date['trade_date'] if next_date else start_date  # 如果没有找到，使用开始日期

        start_time = time.perf_counter()
        calendar = get_trade_calendar(start_date, end_date)
        end_time = time.perf_counter()

        print(f"获取一年交易日历耗时: {(end_time-start_time)*1000:.2f}ms")

        # 场景3：随机日期查询（模拟用户查询）
        print("\n场景3：随机日期查询（模拟用户查询）")
        test_dates = random.sample(self.trade_dates + self.non_trade_dates, 50)

        start_time = time.perf_counter()
        for date in test_dates:
            is_trade = is_trade_date(date)
            if is_trade:
                pre_date = get_pre_trade_date(date)
                next_date = get_next_trade_date(date)
        end_time = time.perf_counter()

        total_time = end_time - start_time
        print(f"总耗时: {total_time*1000:.2f}ms")
        print(f"平均每次查询耗时: {total_time*1000/len(test_dates):.2f}ms")


def main():
    """主函数"""
    # 准备数据库环境
    prepare_database()

    # 初始化本地数据库
    local_fetcher = LocalAdapter()
    local_fetcher.initialize()

    benchmark = TradeDateBenchmark()

    # 运行所有测试
    benchmark.benchmark_cold_start()
    benchmark.benchmark_hot_data()
    benchmark.benchmark_business_scenarios()


if __name__ == "__main__":
    main()
