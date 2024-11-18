"""
数据保存脚本

此脚本用于从多个数据源（如 Tushare、掘金等）获取市场数据并保存到本地数据库。
使用 MarketDataSaver 类来处理数据保存，确保正确的增量更新。
"""
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from quantbox.savers.data_saver import MarketDataSaver


def main():
    """
    主函数，执行数据保存操作。
    使用 MarketDataSaver 类来处理各类数据的保存，
    它会自动处理增量更新、错误重试等机制。
    """
    # 初始化数据保存器
    saver = MarketDataSaver()

    # 保存交易日期数据
    print("正在保存交易日期数据...")
    saver.save_trade_dates()
    
    # 保存期货合约信息
    print("正在保存期货合约信息...")
    saver.save_future_contracts()
    
    # 保存期货持仓数据
    print("正在保存期货持仓数据...")
    saver.save_future_holdings()

    # 保存期货日线数据
    print("正在保存期货日线数据...")
    saver.save_future_daily()

    print("数据保存完成！")


if __name__ == "__main__":
    main()
