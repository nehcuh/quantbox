"""
Data validation script to compare data from different sources
数据验证脚本，用于比较不同来源的数据
"""

from quantbox.adapters.ts_adapter import TSAdapter
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from quantbox.config.config_loader import get_config_loader
import os
import toml
import json

def get_tushare_data(adapter, source_name):
    """获取Tushare数据"""
    # 获取最近3天的历史数据
    end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d')

    print(f"\nFetching data from {source_name}...")
    print(f"Time range: {start_date} to {end_date}")

    # 获取期货日线数据
    daily_data = adapter.get_future_daily(
        exchanges=['SHFE'],
        start_date=start_date,
        end_date=end_date
    )

    if daily_data.empty:
        print(f"No data returned from {source_name}")
        return None

    print(f"Got {len(daily_data)} records from {source_name}")
    return daily_data

def get_gm_data(source_name, token=None):
    """获取掘金数据（简化版，仅用于演示）"""
    print(f"\nNote: {source_name} validation is disabled in this example")
    print("This script now focuses on Tushare data validation only.")
    return None

def compare_data(data1, data2, source1, source2):
    """比较两个数据源的数据"""
    if data1 is None and data2 is None:
        print("Both data sources returned no data")
        return False
    elif data1 is None:
        print(f"Only {source2} returned data")
        return False
    elif data2 is None:
        print(f"Only {source1} returned data")
        return False

    # 基本数据验证
    print(f"\nData validation results:")
    print(f"- {source1}: {len(data1)} records")
    print(f"- {source2}: {len(data2)} records")

    # 检查关键字段是否存在
    required_fields = ['symbol', 'exchange', 'date', 'open', 'high', 'low', 'close', 'volume']
    for field in required_fields:
        if field not in data1.columns:
            print(f"❌ Missing field '{field}' in {source1} data")
            return False

    print("✅ Basic data structure validation passed")
    return True

def create_temp_config():
    """创建临时配置文件"""
    config = get_config_loader().load_user_config()
    temp_config = {
        "TSPRO": {"token": config.get("TSPRO", {}).get("token", "")},
        "GM": {"token": config.get("GM", {}).get("token", "")}
    }

    temp_config_file = "temp_validation_config.json"
    with open(temp_config_file, 'w') as f:
        json.dump(temp_config, f, indent=2)

    return temp_config_file, temp_config

def main():
    """主函数"""
    print("QuantBox Data Validation Script")
    print("=" * 50)

    try:
        # 创建临时配置
        temp_config_file, config = create_temp_config()

        # 初始化Tushare适配器
        ts_adapter = TSAdapter()

        # 获取数据
        ts_data = get_tushare_data(ts_adapter, "TuShare")
        gm_data = get_gm_data("GoldMiner", config["GM"]["token"])

        # 比较数据
        validation_passed = compare_data(ts_data, gm_data, "TuShare", "GoldMiner")

        if validation_passed:
            print("\n✅ Data validation completed successfully!")
        else:
            print("\n⚠️  Data validation completed with warnings")

    except Exception as e:
        print(f"\n❌ Error during validation: {str(e)}")
        return False
    finally:
        # 清理临时文件
        if os.path.exists("temp_validation_config.json"):
            os.remove("temp_validation_config.json")

    return True

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
