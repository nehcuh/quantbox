#!/usr/bin/env python3

import cmd
import sys

from quantbox.savers.market_data_saver import MarketDataSaver


class QuantboxShell(cmd.Cmd):
    """Quantbox 交互式命令行环境"""
    
    intro = """
Welcome to Quantbox Shell!
输入 help 或 ? 查看支持的命令
输入 quit 或 exit 退出程序
    """
    prompt = 'quantbox> '
    
    def __init__(self):
        super().__init__()
        self.saver = MarketDataSaver()
        
    def do_save_all(self, arg):
        """保存所有数据，包括交易日期、期货合约、期货持仓数据等"""
        try:
            self.saver.save_trade_dates()
            self.saver.save_future_contracts()
            self.saver.save_future_holdings()
            self.saver.save_future_daily()
            print("所有数据保存完成")
        except Exception as e:
            print(f"保存数据时出错: {e}")
            
    def do_save_trade_dates(self, arg):
        """保存交易日期数据"""
        try:
            self.saver.save_trade_dates()
            print("交易日期数据保存完成")
        except Exception as e:
            print(f"保存交易日期数据时出错: {e}")
            
    def do_save_future_contracts(self, arg):
        """保存期货合约数据"""
        try:
            self.saver.save_future_contracts()
            print("期货合约数据保存完成")
        except Exception as e:
            print(f"保存期货合约数据时出错: {e}")
            
    def do_save_future_holdings(self, arg):
        """保存期货持仓数据"""
        try:
            self.saver.save_future_holdings()
            print("期货持仓数据保存完成")
        except Exception as e:
            print(f"保存期货持仓数据时出错: {e}")
            
    def do_save_future_daily(self, arg):
        """保存期货日线数据"""
        try:
            self.saver.save_future_daily()
            print("期货日线数据保存完成")
        except Exception as e:
            print(f"保存期货日线数据时出错: {e}")
            
    def do_save_stock_list(self, arg):
        """保存股票列表数据"""
        try:
            self.saver.save_stock_list()
            print("股票列表数据保存完成")
        except Exception as e:
            print(f"保存股票列表数据时出错: {e}")
    
    def do_quit(self, arg):
        """退出程序"""
        print("再见！")
        return True
        
    def do_exit(self, arg):
        """退出程序"""
        return self.do_quit(arg)
        
    def default(self, line):
        """处理未知命令"""
        print(f"未知命令: {line}")
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
