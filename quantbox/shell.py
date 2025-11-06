#!/usr/bin/env python3

import cmd
import sys
import shlex
from typing import Optional, Callable, Any
from functools import wraps
import logging

from quantbox.services.data_saver_service import DataSaverService
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

def parse_args(arg: str) -> dict:
    """解析命令行参数

    支持格式：
        --exchanges SHFE,DCE
        --symbols SHFE.rb2501,DCE.m2505
        --start-date 2025-01-01
        --end-date 2025-01-31
        --date 2025-01-01

    Returns:
        dict: 解析后的参数字典
    """
    args = shlex.split(arg)
    params = {}

    i = 0
    while i < len(args):
        if args[i].startswith('--'):
            key = args[i][2:].replace('-', '_')  # --start-date -> start_date
            if i + 1 < len(args) and not args[i + 1].startswith('--'):
                value = args[i + 1]
                # 处理逗号分隔的列表
                if ',' in value:
                    params[key] = value.split(',')
                else:
                    params[key] = value
                i += 2
            else:
                i += 1
        else:
            i += 1

    return params

class QuantboxShell(cmd.Cmd):
    """Quantbox 交互式命令行环境

    支持的命令：
    - save_all: 保存所有数据（交易日历、期货合约、持仓、日线、股票列表等）
    - save_trade_dates: 保存交易日期数据
    - save_future_contracts: 保存期货合约数据
    - save_future_holdings: 保存期货持仓数据
    - save_future_daily: 保存期货日线数据
    - save_stock_list: 保存股票列表数据
    - quit/exit: 退出程序

    架构：使用三层架构（Services + Adapters + Utils）
    数据源：默认使用 Tushare API
    """

    intro = """
Welcome to Quantbox Shell!
输入 help 或 ? 查看支持的命令
输入 quit 或 exit 退出程序

架构：三层架构（Services + Adapters + Utils）
数据源：Tushare API（默认）
    """
    prompt = 'quantbox> '
    
    def __init__(self):
        super().__init__()
        self.saver = DataSaverService(show_progress=True)
        
    @handle_errors
    def do_save_all(self, arg: str):
        """保存所有数据，包括交易日历、期货合约、股票列表、期货持仓、期货日线等

        用法: save_all
        """
        if arg:
            print("注意：默认使用 Tushare 数据源，参数已忽略")

        print("开始保存所有数据...")

        # 保存交易日历
        result1 = self.saver.save_trade_calendar()
        print(f"✓ 交易日历: 插入 {result1.inserted_count} 条，更新 {result1.modified_count} 条")

        # 保存期货合约
        result2 = self.saver.save_future_contracts()
        print(f"✓ 期货合约: 插入 {result2.inserted_count} 条，更新 {result2.modified_count} 条")

        # 保存股票列表
        result_stock = self.saver.save_stock_list()
        print(f"✓ 股票列表: 插入 {result_stock.inserted_count} 条，更新 {result_stock.modified_count} 条")

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

        用法:
            save_trade_dates                                    # 默认保存今年所有交易所
            save_trade_dates --exchanges SHFE,DCE              # 指定交易所
            save_trade_dates --start-date 2025-01-01           # 指定起始日期
            save_trade_dates --start-date 2025-01-01 --end-date 2025-12-31  # 指定日期范围

        参数:
            --exchanges: 交易所代码，多个用逗号分隔
            --start-date: 起始日期，默认今年年初
            --end-date: 结束日期，默认今天
        """
        params = parse_args(arg)
        result = self.saver.save_trade_calendar(**params)
        logger.info(f"交易日期数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
        print(f"交易日期数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
            
    @handle_errors
    def do_save_future_contracts(self, arg: str):
        """保存期货合约数据

        用法:
            save_future_contracts                    # 默认保存所有期货交易所
            save_future_contracts --exchanges SHFE,DCE   # 指定交易所
            save_future_contracts --symbols SHFE.rb2501  # 指定合约
            save_future_contracts --spec-names rb,cu     # 指定品种

        参数:
            --exchanges: 交易所代码，多个用逗号分隔
            --symbols: 合约代码，多个用逗号分隔
            --spec-names: 品种名称，多个用逗号分隔
            --date: 查询日期
        """
        params = parse_args(arg)
        result = self.saver.save_future_contracts(**params)
        logger.info(f"期货合约数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
        print(f"期货合约数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
            
    @handle_errors
    def do_save_future_holdings(self, arg: str):
        """保存期货持仓数据

        用法:
            save_future_holdings                                 # 默认保存从 1990-01-01 到今天所有期货交易所的历史持仓数据
            save_future_holdings --exchanges SHFE,DCE            # 指定交易所
            save_future_holdings --symbols SHFE.rb2501           # 指定合约
            save_future_holdings --date 2025-01-15               # 指定单日
            save_future_holdings --start-date 2025-01-01 --end-date 2025-01-31  # 指定日期范围

        参数:
            --exchanges: 交易所代码，多个用逗号分隔
            --symbols: 合约代码，多个用逗号分隔
            --spec-names: 品种名称，多个用逗号分隔
            --date: 单日查询
            --start-date: 起始日期（默认 1990-01-01）
            --end-date: 结束日期（默认今天）
        """
        params = parse_args(arg)
        result = self.saver.save_future_holdings(**params)
        logger.info(f"期货持仓数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
        print(f"期货持仓数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
            
    @handle_errors
    def do_save_future_daily(self, arg: str):
        """保存期货日线数据

        用法:
            save_future_daily                                    # 默认保存从 1990-01-01 到今天所有期货交易所的历史数据
            save_future_daily --exchanges SHFE,DCE              # 指定交易所
            save_future_daily --symbols SHFE.rb2501,DCE.m2505  # 指定合约
            save_future_daily --date 2025-01-15                 # 指定单日
            save_future_daily --start-date 2025-01-01 --end-date 2025-01-31  # 指定日期范围

        参数:
            --exchanges: 交易所代码，多个用逗号分隔（如：SHFE,DCE,CZCE）
            --symbols: 合约代码，多个用逗号分隔（如：SHFE.rb2501,DCE.m2505）
            --date: 单日查询（如：2025-01-15 或 20250115）
            --start-date: 起始日期（如：2025-01-01，默认 1990-01-01）
            --end-date: 结束日期（如：2025-01-31，默认今天）
        """
        params = parse_args(arg)
        result = self.saver.save_future_daily(**params)
        logger.info(f"期货日线数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
        print(f"期货日线数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
            
    @handle_errors
    def do_save_stock_list(self, arg: str):
        """保存股票列表数据

        用法:
            save_stock_list                              # 默认保存所有上市股票
            save_stock_list --exchanges SSE,SZSE         # 指定交易所
            save_stock_list --list-status L              # 指定上市状态（L: 上市, D: 退市, P: 暂停）

        参数:
            --exchanges: 交易所代码，多个用逗号分隔（SSE, SZSE, BSE）
            --list-status: 上市状态（L, D, P）
        """
        params = parse_args(arg)
        result = self.saver.save_stock_list(**params)
        logger.info(f"股票列表数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
        print(f"股票列表数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")
    
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
