"""Quantbox interactive shell"""

import sys
from typing import Optional, List
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from pathlib import Path

from ..data.fetcher import TushareFetcher
from ..core.config import ExchangeType


class QuantboxShell:
    """Quantbox interactive shell"""
    
    def __init__(self):
        self.commands = {
            'save': {
                'trade_dates': self.save_trade_dates,
                'help': 'Save data to database'
            },
            'help': {
                'func': self.show_help,
                'help': 'Show help message'
            },
            'exit': {
                'func': self.exit_shell,
                'help': 'Exit the shell'
            }
        }
        
        # 创建历史文件目录
        history_dir = Path.home() / '.quantbox' / 'history'
        history_dir.mkdir(parents=True, exist_ok=True)
        history_file = history_dir / 'shell_history'
        
        # 设置命令补全
        words = ['save trade_dates', 'help', 'exit']
        self.completer = WordCompleter(words, ignore_case=True)
        
        # 创建会话
        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=self.completer
        )
    
    def save_trade_dates(self, args: List[str]) -> None:
        """Save trade dates to database"""
        # 解析参数
        exchange = None
        exchange_type = None
        start_date = None
        end_date = None
        
        i = 0
        while i < len(args):
            if args[i] in ['-e', '--exchange']:
                i += 1
                if i < len(args):
                    exchange = args[i]
            elif args[i] in ['-t', '--exchange-type']:
                i += 1
                if i < len(args):
                    exchange_type = args[i]
            elif args[i] in ['-s', '--start-date']:
                i += 1
                if i < len(args):
                    start_date = args[i]
            elif args[i] in ['-d', '--end-date']:  
                i += 1
                if i < len(args):
                    end_date = args[i]
            elif args[i].startswith('-'):
                print(f"Unknown option: {args[i]}")
                return
            i += 1
        
        try:
            # 创建TushareFetcher实例
            fetcher = TushareFetcher()
            
            # 处理exchange_type
            if exchange_type:
                exchange_type = ExchangeType[exchange_type.upper()]
            
            # 获取并保存交易日历
            if exchange:
                # 保存指定交易所的数据
                fetcher.fetch_calendar(
                    exchange=exchange,
                    start_date=start_date,
                    end_date=end_date
                )
                print(f"Successfully saved trade dates for {exchange}")
            else:
                # 根据exchange_type获取交易所列表
                if exchange_type == ExchangeType.STOCK:
                    exchanges = ["SSE", "SZSE"]
                elif exchange_type == ExchangeType.FUTURES:
                    exchanges = ["SHFE", "DCE", "CZCE", "CFFEX", "INE", "GFEX"]
                else:
                    # 如果没有指定类型，则获取所有交易所的数据
                    exchanges = ["SSE", "SZSE", "SHFE", "DCE", "CZCE", "CFFEX", "INE", "GFEX"]
                
                # 保存每个交易所的数据
                for ex in exchanges:
                    fetcher.fetch_calendar(
                        exchange=ex,
                        start_date=start_date,
                        end_date=end_date
                    )
                    print(f"Successfully saved trade dates for {ex}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    def show_help(self, args: List[str]) -> None:
        """Show help message"""
        print("\nAvailable commands:")
        print("  save trade_dates [-e EXCHANGE] [-t {STOCK,FUTURES}] [-s START_DATE] [-d END_DATE]")
        print("    Save trade dates to database")
        print("    -e, --exchange     Exchange code (e.g., SSE, SZSE)")
        print("    -t, --exchange-type Exchange type (STOCK or FUTURES)")
        print("    -s, --start-date   Start date in YYYYMMDD format")
        print("    -d, --end-date     End date in YYYYMMDD format")
        print("\n  help")
        print("    Show this help message")
        print("\n  exit")
        print("    Exit the shell")
        print()
    
    def exit_shell(self, args: List[str]) -> None:
        """Exit the shell"""
        print("\nGoodbye!")
        sys.exit(0)
    
    def process_command(self, command: str) -> None:
        """Process a command"""
        if not command.strip():
            return
            
        parts = command.strip().split()
        cmd = parts[0]
        
        if cmd == 'save' and len(parts) > 1 and parts[1] == 'trade_dates':
            self.save_trade_dates(parts[2:])
        elif cmd in self.commands and 'func' in self.commands[cmd]:
            self.commands[cmd]['func'](parts[1:])
        else:
            print(f"Unknown command: {command}")
            print("Type 'help' for available commands")
    
    def run(self) -> None:
        """Run the shell"""
        print("\nWelcome to Quantbox Shell!")
        print("Type 'help' for available commands\n")
        
        while True:
            try:
                command = self.session.prompt('quantbox> ')
                self.process_command(command)
            except KeyboardInterrupt:
                continue
            except EOFError:
                self.exit_shell([])
            except Exception as e:
                print(f"Error: {str(e)}")


def main():
    """Main entry point for the shell"""
    shell = QuantboxShell()
    shell.run()


if __name__ == '__main__':
    main()
