"""
测试不同数据源的期货合约数据一致性

此脚本用于测试 Tushare 期货合约数据的完整性。
主要测试：
1. 合约基本信息的完整性（代码、名称等）
2. 合约日期信息的完整性（上市日期、退市日期等）
3. 不同交易所、不同时间范围下的数据完整性
"""

import pandas as pd
from datetime import datetime, timedelta

from quantbox.fetchers.fetcher_tushare import TSFetcher
from quantbox.util.basic import FUTURE_EXCHANGES


def get_future_contracts(fetcher, exchange, spec_name=None):
    """获取指定数据源的期货合约数据"""
    df = fetcher.fetch_get_future_contracts(
        exchange=exchange,
        spec_name=spec_name
    )
    if df is not None and not df.empty:
        # 标准化列名，确保数据可比较
        required_columns = {
            'symbol',  # 合约代码
            'name',    # 合约名称
            'list_date',  # 上市日期
            'delist_date'  # 退市日期
        }
        
        # 检查并选择可用的列
        available_columns = set(df.columns)
        if not required_columns.issubset(available_columns):
            print(f"警告: 数据源缺少必需的列。可用列: {available_columns}")
            return pd.DataFrame()
            
        return df[list(required_columns)]
    return pd.DataFrame()


def check_future_contracts(exchange, spec_name=None):
    """检查期货合约数据的完整性"""
    ts_fetcher = TSFetcher()
    
    # 获取数据
    ts_data = get_future_contracts(ts_fetcher, exchange, spec_name)
    
    # 计算基本统计信息
    ts_count = len(ts_data)
    
    # 检查数据完整性
    if ts_data.empty:
        print(f"\n{'='*80}")
        print(f"交易所: {exchange}")
        if spec_name:
            print(f"品种: {spec_name}")
        print(f"{'='*80}")
        print("警告: 未能获取到任何合约数据")
        return
    
    # 检查日期格式
    date_columns = ['list_date', 'delist_date']
    for col in date_columns:
        if col in ts_data.columns:
            invalid_dates = ts_data[~pd.to_datetime(ts_data[col], errors='coerce').notna()][col]
            if not invalid_dates.empty:
                print(f"\n无效的{col}格式:")
                print(invalid_dates.to_string())
    
    # 检查必需字段的空值
    for col in ts_data.columns:
        null_count = ts_data[col].isna().sum()
        if null_count > 0:
            print(f"\n字段 '{col}' 有 {null_count} 个空值")
    
    # 输出结果
    print(f"\n{'='*80}")
    print(f"交易所: {exchange}")
    if spec_name:
        print(f"品种: {spec_name}")
    print(f"{'='*80}")
    print(f"合约数量: {ts_count}")


def main():
    """主函数"""
    # 测试场景列表
    test_cases = [
        # 测试所有交易所的所有合约
        {'exchange': exchange, 'spec_name': None}
        for exchange in FUTURE_EXCHANGES
    ]
    
    # 测试特定品种的合约
    specific_cases = [
        {'exchange': 'SHFE', 'spec_name': 'cu'},  # 上期所铜期货
        {'exchange': 'DCE', 'spec_name': 'm'},    # 大商所豆粕期货
        {'exchange': 'CZCE', 'spec_name': 'CF'},  # 郑商所棉花期货
    ]
    test_cases.extend(specific_cases)
    
    # 执行测试
    for case in test_cases:
        check_future_contracts(**case)


if __name__ == "__main__":
    main()
