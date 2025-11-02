"""
Data validation script to compare data from different sources
数据验证脚本，用于比较不同来源的数据
"""

from quantbox.fetchers import RemoteFetcher
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from gm.api import history, set_token
from quantbox.config.config_loader import get_config_loader
import os
import toml
import json

def get_tushare_data(fetcher, source_name):
    """获取Tushare数据"""
    # 获取最近3天的历史数据
    end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d')
    
    print(f"\nFetching data from {source_name}...")
    print(f"Time range: {start_date} to {end_date}")
    
    # 获取期货日线数据
    daily_data = fetcher.fetch_get_future_daily(
        exchanges=['SHFE'],
        start_date=start_date,
        end_date=end_date
    )
    
    # 分析合约代码
    if not daily_data.empty:
        print("\nAnalyzing contract codes...")
        for symbol in daily_data['symbol'].unique():
            symbol_data = daily_data[daily_data['symbol'] == symbol]
            print(f"Contract: {symbol}, Records: {len(symbol_data)}")
    
    return daily_data

def get_gm_data(source_name, gm_token):
    """获取掘金量化数据"""
    # 获取最近3天的历史数据
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=3)
    
    print(f"\nFetching data from {source_name}...")
    print(f"Time range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    try:
        # 设置掘金量化token
        print(f"Setting GM token: {gm_token}")
        set_token(gm_token)
        
        # 测试多个合约
        symbols = [
            'SHFE.RB',  # 螺纹钢
            'SHFE.CU',  # 铜
            'SHFE.AL',  # 铝
            'SHFE.ZN',  # 锌
            'SHFE.NI',  # 镍
            'SHFE.SN',  # 锡
            'SHFE.PB',  # 铅
            'SHFE.AU',  # 黄金
            'SHFE.AG',  # 白银
            'SHFE.SS',  # 不锈钢
            'SHFE.BU',  # 沥青
            'SHFE.RU',  # 橡胶
            'SHFE.SP',  # 纸浆
            'SHFE.FU',  # 燃料油
            'SHFE.HC',  # 热轧卷板
            'SHFE.WR',  # 线材
        ]
        
        all_data = []
        for symbol in symbols:
            print(f"Fetching data for {symbol}...")
            try:
                data = history(symbol=symbol, 
                            frequency='1d',
                            start_time=start_date,
                            end_time=end_date,
                            fields=['bob','symbol','open','high','low','close','volume','amount','position'],
                            df=True)  # 直接返回DataFrame
                
                if not data.empty:
                    # 从symbol中提取交易所信息
                    data['exchange'] = data['symbol'].apply(lambda x: x.split('.')[0])
                    # 添加trade_date列，使用bob (beginning of bar)作为交易日期
                    data['trade_date'] = data['bob'].dt.strftime('%Y-%m-%d')
                    # 提取合约代码
                    data['symbol'] = data['symbol'].apply(lambda x: x.split('.')[1])
                    # 将金额单位从元转换为万元
                    data['amount'] = data['amount'] / 10000
                    # 重命名列以匹配TuShare格式
                    data = data.rename(columns={
                        'volume': 'vol',
                        'position': 'oi'
                    })
                    # 删除bob列
                    data = data.drop(columns=['bob'])
                    
                    all_data.append(data)
                else:
                    print(f"No data available for {symbol}")
            except Exception as e:
                print(f"Error fetching data for {symbol}: {str(e)}")
                continue
                
        if all_data:
            final_data = pd.concat(all_data, ignore_index=True)
            print("\nProcessed data from GM:")
            print(final_data)
            return final_data
        else:
            print("No data available from any symbol")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Error initializing GoldMiner API: {str(e)}")
        return pd.DataFrame()

def compare_dataframes(df1, df2, source1_name, source2_name):
    """比较两个数据源的数据"""
    print(f"\nComparing data between {source1_name} and {source2_name}...")
    
    if df1.empty or df2.empty:
        print("One or both dataframes are empty. Cannot perform comparison.")
        return
    
    # 打印原始数据信息
    print(f"\n{source1_name} data info:")
    print(df1.info())
    print(f"\nSample data from {source1_name}:")
    print(df1.head())
    
    print(f"\n{source2_name} data info:")
    print(df2.info())
    print(f"\nSample data from {source2_name}:")
    print(df2.head())
    
    # 确保两个数据框有相同的列
    common_columns = list(set(df1.columns) & set(df2.columns))
    print(f"\nCommon columns: {common_columns}")
    
    if not common_columns:
        print("No common columns found between the two data sources.")
        return
        
    if 'symbol' not in common_columns or 'trade_date' not in common_columns:
        print("Required columns 'symbol' and/or 'trade_date' not found in both data sources.")
        return
    
    df1 = df1[common_columns].sort_values(['symbol', 'trade_date'])
    df2 = df2[common_columns].sort_values(['symbol', 'trade_date'])
    
    # 检查数据条数
    print(f"{source1_name} records: {len(df1)}")
    print(f"{source2_name} records: {len(df2)}")
    
    # 按合约和日期对数据进行分组比较
    common_symbols = set(df1['symbol']) & set(df2['symbol'])
    print(f"\nCommon symbols: {len(common_symbols)}")
    
    for symbol in common_symbols:
        df1_symbol = df1[df1['symbol'] == symbol]
        df2_symbol = df2[df2['symbol'] == symbol]
        
        common_dates = set(df1_symbol['trade_date']) & set(df2_symbol['trade_date'])
        print(f"\nAnalyzing {symbol} - Common dates: {len(common_dates)}")
        
        if not common_dates:
            continue
            
        df1_aligned = df1_symbol[df1_symbol['trade_date'].isin(common_dates)].sort_values('trade_date')
        df2_aligned = df2_symbol[df2_symbol['trade_date'].isin(common_dates)].sort_values('trade_date')
        
        print(f"\nAligned data for {symbol}:")
        print(f"\n{source1_name} data:")
        print(df1_aligned)
        print(f"\n{source2_name} data:")
        print(df2_aligned)
        
        # 比较数值型列
        numeric_columns = df1_aligned.select_dtypes(include=[np.number]).columns
        numeric_columns = [col for col in numeric_columns if col in df2_aligned.columns]
        
        print(f"\nNumeric columns comparison for {symbol}:")
        for col in numeric_columns:
            if col in ['amount', 'oi']:  # 这些字段可能有较大差异
                continue
                
            df1_values = df1_aligned[col].values
            df2_values = df2_aligned[col].values
            
            if len(df1_values) == len(df2_values):
                diff = df1_values - df2_values
                max_diff = np.nanmax(np.abs(diff))
                mean_diff = np.nanmean(np.abs(diff))
                
                print(f"\nColumn: {col}")
                print(f"Max absolute difference: {max_diff:.6f}")
                print(f"Mean absolute difference: {mean_diff:.6f}")
                
                # 检查是否有显著差异
                threshold = 0.01
                if col in ['vol', 'amount', 'oi']:
                    threshold = 1.0  # 交易量和持仓量可以有更大的差异
                    
                if max_diff > threshold:
                    print("WARNING: Significant differences found!")
                    # 显示差异最大的几条记录
                    diff_series = pd.Series(diff)
                    largest_diff_idx = diff_series.abs().nlargest(3).index
                    print("\nLargest differences:")
                    for idx in largest_diff_idx:
                        print(f"Date: {df1_aligned.iloc[idx]['trade_date']}")
                        print(f"{source1_name}: {df1_aligned.iloc[idx][col]}")
                        print(f"{source2_name}: {df2_aligned.iloc[idx][col]}")
            else:
                print(f"Warning: Different number of records for {col}")

def main():
    # 加载配置
    config_file = os.path.join(os.path.expanduser("~"), ".quantbox", "settings", "config.toml")
    
    # 读取TOML配置文件
    with open(config_file, 'r') as f:
        config = toml.load(f)
    
    # 创建临时JSON配置文件
    temp_json_config = {
        "cache_type": "local",
        "cache_dir": ".cache",
        "cache_expire_hours": 24,
        "validate_data": True,
        "enable_monitoring": True,
        "rate_limit_enabled": True,
        "requests_per_minute": 60,
        "required_fields": {
            "future_daily": ["symbol", "trade_date", "open", "high", "low", "close", "vol"],
            "future_list": ["symbol", "exchange"],
            "trade_dates": ["exchange", "date"]
        }
    }
    
    temp_config_file = "temp_config.json"
    with open(temp_config_file, 'w') as f:
        json.dump(temp_json_config, f)
    
    try:
        # 初始化Tushare数据获取器
        ts_fetcher = RemoteFetcher(
            engine='ts',
            config_file=temp_config_file
        )
        
        # 设置Tushare token
        ts_fetcher.pro = config["TSPRO"]["token"]
        
        # 获取数据
        ts_data = get_tushare_data(ts_fetcher, "TuShare")
        gm_data = get_gm_data("GoldMiner", config["GM"]["token"])
        
        # 数据比对
        print("\n=== Comparing TuShare vs GoldMiner ===")
        compare_dataframes(ts_data, gm_data, "TuShare", "GoldMiner")
        
        # 输出性能统计
        print("\nPerformance Statistics:")
        print("\nTuShare Stats:")
        ts_fetcher.log_performance_stats()
    
    finally:
        # 清理临时配置文件
        if os.path.exists(temp_config_file):
            os.remove(temp_config_file)

if __name__ == '__main__':
    main()
