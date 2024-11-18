"""
数据保存脚本

此脚本用于从多个数据源（如 Tushare、掘金等）获取市场数据并保存到本地数据库。
使用 MarketDataSaver 类来处理数据保存，确保正确的增量更新。
"""
import os
import sys
import platform
import warnings
import importlib.util

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from quantbox.savers.data_saver import MarketDataSaver


def check_gm_sdk():
    """
    检查是否安装了掘金量化SDK
    
    Returns:
        bool: 是否存在掘金SDK
    """
    return importlib.util.find_spec("gm") is not None


def get_default_engine():
    """
    根据系统环境确定默认的数据引擎
    
    Returns:
        str: 数据引擎名称 ('ts' 或 'gm')
    """
    # 检查操作系统
    is_macos = platform.system().lower() == 'darwin'
    
    if is_macos:
        return 'ts'  # macOS 默认使用 Tushare
    
    # 非 macOS 系统，检查掘金SDK
    has_gm = check_gm_sdk()
    if not has_gm:
        warnings.warn(
            "未检测到掘金量化SDK，将使用Tushare作为数据源。"
            "如需使用掘金数据源，请先安装掘金SDK。",
            RuntimeWarning
        )
        return 'ts'
    
    return 'gm'  # 使用掘金数据源


def main():
    """
    主函数，执行数据保存操作。
    使用 MarketDataSaver 类来处理各类数据的保存，
    它会自动处理增量更新、错误重试等机制。
    """
    # 初始化数据保存器
    saver = MarketDataSaver()
    
    # 获取默认数据引擎
    engine = get_default_engine()
    print(f"使用数据源: {'Tushare' if engine == 'ts' else '掘金量化'}")

    # 保存交易日期数据
    print("正在保存交易日期数据...")
    saver.save_trade_dates(engine=engine)
    
    # 保存期货合约信息
    print("正在保存期货合约信息...")
    saver.save_future_contracts()
    
    # 保存期货持仓数据
    print("正在保存期货持仓数据...")
    saver.save_future_holdings(engine=engine)

    # 保存期货日线数据
    print("正在保存期货日线数据...")
    saver.save_future_daily()

    print("数据保存完成！")


if __name__ == "__main__":
    main()
