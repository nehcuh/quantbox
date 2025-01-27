"""Quantbox interactive shell"""

import sys
from typing import Optional, List
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from pathlib import Path

from ..data.fetcher import TushareFetcher
from ..data.database import MongoDBManager
from ..core.config import ExchangeType, ConfigLoader


class QuantboxShell:
    """Quantbox interactive shell"""
    
    def __init__(self):
        self.commands = {
            'save': {
                'trade_dates': self.save_trade_dates,
                'future_contracts': self.save_future_contracts,
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
        
        # 初始化数据库管理器
        self.db = MongoDBManager(ConfigLoader.get_database_config())
        
        # 创建历史文件目录
        history_dir = Path.home() / '.quantbox' / 'history'
        history_dir.mkdir(parents=True, exist_ok=True)
        history_file = history_dir / 'shell_history'
        
        # 设置命令补全
        words = ['save trade_dates', 'save future_contracts', 'help', 'exit']
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
    
    def save_future_contracts(self, args: List[str]) -> None:
        """Save future contracts to database
        
        Usage:
            save future_contracts [-e EXCHANGE] [-s SPEC_NAME] [-d CURSOR_DATE]
            
        Options:
            -e, --exchange    Exchange code (SHFE/DCE/CZCE/CFFEX/INE)
            -s, --spec-name   Future specification name (e.g., "豆粕")
            -d, --date        Reference date (YYYYMMDD or YYYY-MM-DD)
        """
        # 解析参数
        exchange = None
        spec_name = None
        cursor_date = None
        
        i = 0
        while i < len(args):
            if args[i] in ['-e', '--exchange']:
                i += 1
                if i < len(args):
                    exchange = args[i]
            elif args[i] in ['-s', '--spec-name']:
                i += 1
                if i < len(args):
                    spec_name = args[i]
            elif args[i] in ['-d', '--date']:
                i += 1
                if i < len(args):
                    cursor_date = args[i]
            elif args[i].startswith('-'):
                print(f"Unknown option: {args[i]}")
                return
            i += 1
            
        try:
            # 创建TushareFetcher实例
            fetcher = TushareFetcher()
            
            # 获取并保存期货合约数据
            if exchange:
                # 保存指定交易所的数据
                data = fetcher.fetch_get_future_contracts(
                    exchange=exchange,
                    spec_name=spec_name,
                    cursor_date=cursor_date
                )
                if data is not None and not data.empty:
                    inserted, updated = self.db.save_future_contracts(data, exchange)
                    print(f"Successfully saved future contracts for {exchange}: "
                          f"inserted {inserted}, updated {updated}")
                else:
                    print(f"No data found for exchange {exchange}")
            else:
                # 保存所有交易所的数据
                exchanges = ["SHFE", "DCE", "CZCE", "CFFEX", "INE"]
                total_inserted = 0
                total_updated = 0
                
                for exch in exchanges:
                    data = fetcher.fetch_get_future_contracts(
                        exchange=exch,
                        spec_name=spec_name,
                        cursor_date=cursor_date
                    )
                    if data is not None and not data.empty:
                        inserted, updated = self.db.save_future_contracts(data, exch)
                        total_inserted += inserted
                        total_updated += updated
                        print(f"Saved future contracts for {exch}: "
                              f"inserted {inserted}, updated {updated}")
                    else:
                        print(f"No data found for exchange {exch}")
                
                print(f"\nTotal: inserted {total_inserted}, updated {total_updated}")
                
        except Exception as e:
            print(f"Error saving future contracts: {str(e)}")
    
    def show_help(self, args: List[str]) -> None:
        """Show help message"""
        print("\nAvailable commands:")
        print("  save trade_dates [-e EXCHANGE] [-t {STOCK,FUTURES}] [-s START_DATE] [-d END_DATE]")
        print("    Save trade dates to database")
        print("    -e, --exchange     Exchange code (e.g., SSE, SZSE)")
        print("    -t, --exchange-type Exchange type (STOCK or FUTURES)")
        print("    -s, --start-date   Start date in YYYYMMDD format")
        print("    -d, --end-date     End date in YYYYMMDD format")
        print("\n  save future_contracts [-e EXCHANGE] [-s SPEC_NAME] [-d CURSOR_DATE]")
        print("    Save future contracts to database")
        print("    -e, --exchange    Exchange code (SHFE/DCE/CZCE/CFFEX/INE)")
        print("    -s, --spec-name   Future specification name (e.g., \"豆粕\")")
        print("    -d, --date        Reference date (YYYYMMDD or YYYY-MM-DD)")
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
        elif cmd == 'save' and len(parts) > 1 and parts[1] == 'future_contracts':
            self.save_future_contracts(parts[2:])
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
