#!/usr/bin/env python3

import cmd
import sys
import shlex
from typing import Optional, Callable, Any
from functools import wraps
import logging

from quantbox.savers.data_saver import MarketDataSaver
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
    """Quantbox 交互式命令行环境
    
    支持的命令：
    - save_all [engine]: 保存所有数据 (engine: ts 或 gm，默认 ts)
    - save_trade_dates [engine]: 保存交易日期数据 (engine: ts 或 gm，默认 ts)
    - save_future_contracts: 保存期货合约数据 (仅支持 Tushare)
    - save_future_holdings [engine]: 保存期货持仓数据 (engine: ts 或 gm，默认 ts)
    - save_future_daily [engine]: 保存期货日线数据 (engine: ts 或 gm，默认 ts)
    - save_stock_list: 保存股票列表数据 (仅支持 Tushare)
    - quit/exit: 退出程序
    """
    
    intro = """
Welcome to Quantbox Shell!
输入 help 或 ? 查看支持的命令
输入 quit 或 exit 退出程序

对于支持多数据源的命令，可以通过参数指定数据源引擎：
例如：save_trade_dates gm  # 使用掘金数据源
     save_future_holdings ts  # 使用 Tushare 数据源
    """
    prompt = 'quantbox> '
    
    def __init__(self):
        super().__init__()
        self.saver = MarketDataSaver()
        
    @handle_errors
    def do_save_all(self, arg: str):
        """保存所有数据，包括交易日期、期货合约、期货持仓数据等
        
        用法: save_all [engine]
        engine: 数据源引擎，可选 'ts' (Tushare) 或 'gm' (掘金)，默认为 'ts'
        注意：期货合约数据和股票列表数据仅支持 Tushare 数据源
        """
        engine = parse_engine(arg)
        self.saver.save_trade_dates(engine=engine)
        if engine == 'ts':
            self.saver.save_future_contracts()
            self.saver.save_stock_list()
        self.saver.save_future_holdings(engine=engine)
        self.saver.save_future_daily(engine=engine)
        logger.info("所有数据保存完成")
        print("所有数据保存完成")
            
    @handle_errors
    def do_save_trade_dates(self, arg: str):
        """保存交易日期数据
        
        用法: save_trade_dates [engine]
        engine: 数据源引擎，可选 'ts' (Tushare) 或 'gm' (掘金)，默认为 'ts'
        """
        engine = parse_engine(arg)
        self.saver.save_trade_dates(engine=engine)
        logger.info("交易日期数据保存完成")
        print("交易日期数据保存完成")
            
    @handle_errors
    def do_save_future_contracts(self, arg: str):
        """保存期货合约数据 (仅支持 Tushare 数据源)
        
        用法: save_future_contracts
        """
        if arg:
            print("警告：期货合约数据仅支持 Tushare 数据源，忽略引擎参数")
        self.saver.save_future_contracts()
        logger.info("期货合约数据保存完成")
        print("期货合约数据保存完成")
            
    @handle_errors
    def do_save_future_holdings(self, arg: str):
        """保存期货持仓数据
        
        用法: save_future_holdings [engine]
        engine: 数据源引擎，可选 'ts' (Tushare) 或 'gm' (掘金)，默认为 'ts'
        """
        engine = parse_engine(arg)
        self.saver.save_future_holdings(engine=engine)
        logger.info("期货持仓数据保存完成")
        print("期货持仓数据保存完成")
            
    @handle_errors
    def do_save_future_daily(self, arg: str):
        """保存期货日线数据
        
        用法: save_future_daily [engine]
        engine: 数据源引擎，可选 'ts' (Tushare) 或 'gm' (掘金)，默认为 'ts'
        """
        engine = parse_engine(arg)
        self.saver.save_future_daily(engine=engine)
        logger.info("期货日线数据保存完成")
        print("期货日线数据保存完成")
            
    @handle_errors
    def do_save_stock_list(self, arg: str):
        """保存股票列表数据 (仅支持 Tushare 数据源)
        
        用法: save_stock_list
        """
        if arg:
            print("警告：股票列表数据仅支持 Tushare 数据源，忽略引擎参数")
        self.saver.save_stock_list()
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
