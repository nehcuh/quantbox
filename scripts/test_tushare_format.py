import pandas as pd
import tushare as ts
import time
from typing import Any, Dict, List, Union, Tuple
from quantbox.fetchers.fetcher_tushare import TSFetcher
from quantbox.config.config_loader import get_config_loader

def benchmark_tushare_api(
    pro,
    date_formats: List[Union[int, str]],
    n_times: int = 10
) -> Dict[str, Dict[str, float]]:
    """测试不同日期格式的性能

    Args:
        pro: TuShare API 实例
        date_formats: 要测试的日期格式列表
        n_times: 每个格式测试的次数

    Returns:
        Dict: 每种格式的性能统计
    """
    results = {}
    
    for fmt in date_formats:
        times = []
        print(f"\n测试日期格式: {fmt} (类型: {type(fmt)})")
        
        # 预热一次（避免首次调用的额外开销）
        pro.trade_cal(exchange='', start_date=str(fmt), end_date='20240131', is_open='1')
        
        for _ in range(n_times):
            start_time = time.perf_counter()
            df = pro.trade_cal(exchange='', start_date=str(fmt), end_date='20240131', is_open='1')
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        results[str(fmt)] = {
            'mean_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'total_time': sum(times),
            'n_calls': n_times
        }
        
        print("性能统计:")
        print(f"  平均耗时: {results[str(fmt)]['mean_time']*1000:.2f}ms")
        print(f"  最小耗时: {results[str(fmt)]['min_time']*1000:.2f}ms")
        print(f"  最大耗时: {results[str(fmt)]['max_time']*1000:.2f}ms")
        
        # 显示返回的数据类型
        print("\n返回数据类型:")
        for col in df.columns:
            print(f"- {col}: {df[col].dtype}")
        
        print("\n前两行数据:")
        print(df.head(2))
    
    return results

def test_exchange_validation():
    """测试交易所代码验证功能"""
    print("\n=== 测试交易所代码验证 ===\n")
    
    fetcher = TSFetcher()
    
    # 测试有效的交易所代码
    valid_cases = [
        'SSE',      # 将被转换为 SHSE
        'SHSE',     # 保持不变
        'SZSE',     # 保持不变
        ['SSE', 'SZSE'],  # 列表形式
        None,       # 默认值
    ]
    
    print("1. 测试有效的交易所代码")
    for case in valid_cases:
        try:
            if isinstance(case, (str, list)) or case is None:
                result = fetcher._validate_exchanges(case)
                print(f"输入: {case}")
                print(f"输出: {result}\n")
            else:
                print(f"跳过无效类型: {type(case)}\n")
        except Exception as e:
            print(f"意外错误 - 输入: {case}")
            print(f"错误: {str(e)}\n")
    
    # 测试无效的交易所代码
    invalid_cases = [
        'INVALID',          # 无效的代码
        ['SHSE', 'INVALID'],  # 列表中包含无效代码
        'sse',             # 小写（区分大小写）
        '',               # 空字符串
    ]
    
    print("\n2. 测试无效的交易所代码")
    for case in invalid_cases:
        try:
            result = fetcher._validate_exchanges(case)
            print(f"意外成功 - 输入: {case}")
            print(f"输出: {result}\n")
        except ValueError as e:
            print(f"预期的错误 - 输入: {case}")
            print(f"错误信息: {str(e)}\n")
        except Exception as e:
            print(f"意外错误类型 - 输入: {case}")
            print(f"错误: {str(e)}\n")
    
    # 测试规范化和反规范化
    print("\n3. 测试规范化和反规范化")
    test_cases = [
        'SSE',
        'SHSE',
        'SZSE',
    ]
    
    for case in test_cases:
        try:
            normalized = fetcher._normalize_exchange(case)
            denormalized = fetcher._denormalize_exchange(normalized)
            print(f"原始值: {case}")
            print(f"规范化: {normalized}")
            print(f"反规范化: {denormalized}\n")
        except Exception as e:
            print(f"错误 - 输入: {case}")
            print(f"错误: {str(e)}\n")

def test_tushare_direct():
    """直接使用 TuShare API 测试"""
    print("\n=== 直接使用 TuShare API ===\n")
    
    # 使用配置系统获取 Tushare Pro
    pro = get_config_loader().get_tushare_pro()
    if pro is None:
        print("错误：未找到 TuShare token，请在配置文件中设置")
        return
    
    # 测试不同的日期格式
    date_formats = [
        20240101,  # 整数格式
        "20240101",  # 字符串格式（无连字符）
        "2024-01-01",  # 字符串格式（有连字符）
    ]
    
    results = benchmark_tushare_api(pro, date_formats)
    
    # 分析结果
    print("\n=== 性能分析 ===")
    for fmt, stats in results.items():
        print(f"\n日期格式: {fmt}")
        print(f"平均耗时: {stats['mean_time']*1000:.2f}ms")

def test_tsfetcher():
    """测试 TSFetcher 的性能和功能"""
    print("\n=== 使用 TSFetcher ===\n")
    
    fetcher = TSFetcher()
    
    # 测试不同的日期格式
    date_formats = [
        20240101,  # 整数格式
        "20240101",  # 字符串格式（无连字符）
        "2024-01-01",  # 字符串格式（有连字符）
    ]
    
    # 测试单个查询（无缓存）
    print("\n1. 测试单个查询（无缓存）")
    for fmt in date_formats:
        times = []
        print(f"\n测试日期格式: {fmt} (类型: {type(fmt)})")
        
        # 预热一次
        fetcher.fetch_get_trade_dates(start_date=fmt, end_date=20240131, use_cache=False)
        
        for _ in range(10):
            start_time = time.perf_counter()
            df = fetcher.fetch_get_trade_dates(start_date=fmt, end_date=20240131, use_cache=False)
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        print("性能统计:")
        print(f"  平均耗时: {(sum(times) / len(times))*1000:.2f}ms")
        print(f"  最小耗时: {min(times)*1000:.2f}ms")
        print(f"  最大耗时: {max(times)*1000:.2f}ms")
        
        if not df.empty:
            print("\n返回数据类型:")
            for col in df.columns:
                print(f"- {col}: {df[col].dtype}")
            
            print("\n前两行数据:")
            print(df.head(2))
            
            # 验证交易所代码
            print("\n交易所代码统计:")
            print(df['exchange'].value_counts())
    
    # 测试单个查询（使用缓存）
    print("\n2. 测试单个查询（使用缓存）")
    for fmt in date_formats:
        times = []
        print(f"\n测试日期格式: {fmt} (类型: {type(fmt)})")
        
        # 预热缓存
        fetcher.fetch_get_trade_dates(start_date=fmt, end_date=20240131, use_cache=True)
        
        for _ in range(10):
            start_time = time.perf_counter()
            df = fetcher.fetch_get_trade_dates(start_date=fmt, end_date=20240131, use_cache=True)
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        print("性能统计:")
        print(f"  平均耗时: {(sum(times) / len(times))*1000:.2f}ms")
        print(f"  最小耗时: {min(times)*1000:.2f}ms")
        print(f"  最大耗时: {max(times)*1000:.2f}ms")
        
        if not df.empty:
            print("\n交易所代码统计:")
            print(df['exchange'].value_counts())
    
    # 测试批量查询
    print("\n3. 测试批量查询")
    date_ranges = [
        (20240101, 20240131),
        (20240201, 20240229),
        (20240301, 20240331),
    ]
    
    # 预热一次
    fetcher.fetch_get_trade_dates_batch(date_ranges, use_cache=False)
    
    times = []
    results = None
    for _ in range(5):
        start_time = time.perf_counter()
        results = fetcher.fetch_get_trade_dates_batch(date_ranges, use_cache=False)
        end_time = time.perf_counter()
        times.append(end_time - start_time)
    
    print("\n批量查询性能统计（无缓存）:")
    print(f"  平均耗时: {(sum(times) / len(times))*1000:.2f}ms")
    print(f"  最小耗时: {min(times)*1000:.2f}ms")
    print(f"  最大耗时: {max(times)*1000:.2f}ms")
    
    if results:
        print("\n批量查询结果示例（第一个日期范围）:")
        df = results[(20240101, 20240131)]
        print("\n交易所代码统计:")
        print(df['exchange'].value_counts())
    
    # 测试带缓存的批量查询
    times = []
    results = None
    for _ in range(5):
        start_time = time.perf_counter()
        results = fetcher.fetch_get_trade_dates_batch(date_ranges, use_cache=True)
        end_time = time.perf_counter()
        times.append(end_time - start_time)
    
    print("\n批量查询性能统计（使用缓存）:")
    print(f"  平均耗时: {(sum(times) / len(times))*1000:.2f}ms")
    print(f"  最小耗时: {min(times)*1000:.2f}ms")
    print(f"  最大耗时: {max(times)*1000:.2f}ms")
    
    if results:
        print("\n批量查询结果示例（第一个日期范围）:")
        df = results[(20240101, 20240131)]
        print("\n交易所代码统计:")
        print(df['exchange'].value_counts())

if __name__ == "__main__":
    test_exchange_validation()
    test_tushare_direct()
    test_tsfetcher()
