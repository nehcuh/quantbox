#!/usr/bin/env python3

import cmd
import sys
import shlex
from typing import Optional, Callable, Any
from functools import wraps
import logging

from quantbox.services.data_saver_service import DataSaverService
from quantbox.savers.data_saver import MarketDataSaver  # 仅用于 save_stock_list（新 API 暂未实现）
from quantbox.logger import setup_logger

logger = setup_logger(__name__)

def handle_errors(f: Callable) -> Callable:
    """错误处理装饰器"""
    @wraps(f)
    def wrapper(self, arg: str) -> Any:
        try:
            return f(self, arg)
        except Exception as e:
            error_msg = f"执行 {f.__name__} 时出错: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
    return wrapper

def parse_engine(arg: str) -> Optional[str]:
    """解析引擎参数"""
    args = shlex.split(arg)
    if not args:
        return 'ts'  # 默认使用 Tushare
    if args[0] not in ['ts', 'gm']:
        raise ValueError("引擎参数必须是 'ts' 或 'gm'")
    return args[0]

class QuantboxShell(cmd.Cmd):
    """Quantbox 交互式命令行环境 (新架构)

    支持的命令：
    - save_all: 保存所有数据（交易日历、期货合约、持仓、日线等）
    - save_trade_dates: 保存交易日期数据
    - save_future_contracts: 保存期货合约数据
    - save_future_holdings: 保存期货持仓数据
    - save_future_daily: 保存期货日线数据
    - save_stock_list: 保存股票列表数据 (使用旧架构)
    - quit/exit: 退出程序

    注意：所有命令默认使用 Tushare 数据源（新架构）
    """

    intro = """
Welcome to Quantbox Shell (新架构)!
输入 help 或 ? 查看支持的命令
输入 quit 或 exit 退出程序

注意：Shell 已更新为使用新的三层架构（DataSaverService）
所有命令默认使用 Tushare 数据源
    """
    prompt = 'quantbox> '
    
    def __init__(self):
        super().__init__()
        self.saver = DataSaverService()  # 新架构
        self.legacy_saver = MarketDataSaver()  # 仅用于 save_stock_list
        
    @handle_errors
    def do_save_all(self, arg: str):
        """保存所有数据，包括交易日期、期货合约、期货持仓数据等

        用法: save_all
        注意：新架构默认使用 Tushare 数据源
        """
        if arg:
            print("注意：新架构默认使用 Tushare，engine 参数已忽略")

        print("开始保存所有数据...")

        # 保存交易日历
        result1 = self.saver.save_trade_calendar()
        print(f"✓ 交易日历: 插入 {result1.inserted_count} 条，更新 {result1.modified_count} 条")

        # 保存期货合约
        result2 = self.saver.save_future_contracts()
        print(f"✓ 期货合约: 插入 {result2.inserted_count} 条，更新 {result2.modified_count} 条")

        # 保存股票列表（使用旧架构）
        print("✓ 股票列表: 使用旧架构保存...")
        self.legacy_saver.save_stock_list()

        # 保存期货持仓
        result3 = self.saver.save_future_holdings()
        print(f"✓ 期货持仓: 插入 {result3.inserted_count} 条，更新 {result3.modified_count} 条")

        # 保存期货日线
        result4 = self.saver.save_future_daily()
        print(f"✓ 期货日线: 插入 {result4.inserted_count} 条，更新 {result4.modified_count} 条")

        logger.info("所有数据保存完成")
        print("\n所有数据保存完成！")
            
    @handle_errors
    def do_save_trade_dates(self, arg: str):
        """保存交易日期数据

        用法: save_trade_dates
        注意：新架构默认使用 Tushare 数据源
        """
        if arg:
            print("注意：新架构默认使用 Tushare，engine 参数已忽略")
        result = self.saver.save_trade_calendar()
        logger.info(f"交易日期数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
        print(f"交易日期数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
            
    @handle_errors
    def do_save_future_contracts(self, arg: str):
        """保存期货合约数据 (使用 Tushare 数据源)

        用法: save_future_contracts
        """
        result = self.saver.save_future_contracts()
        logger.info(f"期货合约数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
        print(f"期货合约数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
            
    @handle_errors
    def do_save_future_holdings(self, arg: str):
        """保存期货持仓数据

        用法: save_future_holdings
        注意：新架构默认使用 Tushare 数据源
        """
        if arg:
            print("注意：新架构默认使用 Tushare，engine 参数已忽略")
        result = self.saver.save_future_holdings()
        logger.info(f"期货持仓数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
        print(f"期货持仓数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
            
    @handle_errors
    def do_save_future_daily(self, arg: str):
        """保存期货日线数据

        用法: save_future_daily
        注意：新架构默认使用 Tushare 数据源
        """
        if arg:
            print("注意：新架构默认使用 Tushare，engine 参数已忽略")
        result = self.saver.save_future_daily()
        logger.info(f"期货日线数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
        print(f"期货日线数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
            
    @handle_errors
    def do_save_stock_list(self, arg: str):
        """保存股票列表数据 (使用旧架构，新架构暂未实现)

        用法: save_stock_list
        """
        print("注意：save_stock_list 使用旧架构（新架构暂未实现此功能）")
        self.legacy_saver.save_stock_list()
        logger.info("股票列表数据保存完成")
        print("股票列表数据保存完成")
    
    def do_quit(self, arg: str):
        """退出程序"""
        print("再见！")
        return True
        
    def do_exit(self, arg: str):
        """退出程序"""
        return self.do_quit(arg)
        
    def default(self, line: str):
        """处理未知命令"""
        error_msg = f"未知命令: {line}"
        logger.warning(error_msg)
        print(error_msg)
        print("输入 help 或 ? 查看支持的命令")
        
    def emptyline(self):
        """处理空行输入"""
        pass


def main():
    QuantboxShell().cmdloop()
    
    
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n再见！")
        sys.exit(0)
