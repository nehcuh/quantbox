import click
from quantbox.savers.data_saver import MarketDataSaver
import logging
from functools import wraps
from typing import Optional

def handle_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logging.error(f"执行 {f.__name__} 时发生错误: {str(e)}")
            raise click.ClickException(str(e))
    return wrapper

@click.group()
def cli():
    """
    Quantbox CLI 工具
    """
    pass

def engine_option(required: bool = True, help_text: Optional[str] = None):
    """创建引擎选项装饰器"""
    if help_text is None:
        help_text = "数据源引擎 ('ts' 或 'gm')"
    return click.option(
        '--engine',
        type=click.Choice(['ts', 'gm']),
        default='ts' if not required else None,
        required=required,
        help=help_text
    )

@click.command()
@engine_option(required=False)
@handle_errors
def save_all(engine):
    """
    保存所有数据，包括交易日期、期货合约、期货持仓数据、期货日线数据和股票列表

    注意：期货合约数据和股票列表数据仅支持 Tushare 数据源
    """
    saver = MarketDataSaver()
    saver.save_trade_dates(engine=engine)
    if engine == 'ts':
        saver.save_future_contracts()
        saver.save_stock_list()
    saver.save_future_holdings(engine=engine)
    saver.save_future_daily(engine=engine)

@click.command()
@engine_option()
@handle_errors
def save_trade_dates(engine):
    """
    保存交易日期数据
    """
    saver = MarketDataSaver()
    saver.save_trade_dates(engine=engine)

@click.command()
@handle_errors
def save_future_contracts():
    """
    保存期货合约数据 (仅支持 Tushare 数据源)
    """
    saver = MarketDataSaver()
    saver.save_future_contracts()

@click.command()
@engine_option()
@handle_errors
def save_future_holdings(engine):
    """
    保存期货持仓数据
    """
    saver = MarketDataSaver()
    saver.save_future_holdings(engine=engine)

@click.command()
@engine_option(required=False, help_text="数据源引擎 ('ts' 或 'gm')，默认使用 Tushare")
@handle_errors
def save_future_daily(engine):
    """
    保存期货日线数据
    """
    saver = MarketDataSaver()
    saver.save_future_daily(engine=engine)

@click.command()
@handle_errors
def save_stock_list():
    """
    保存股票列表数据 (仅支持 Tushare 数据源)
    """
    saver = MarketDataSaver()
    saver.save_stock_list()

# 注册所有命令
commands = [
    save_all,
    save_trade_dates,
    save_future_contracts,
    save_future_holdings,
    save_future_daily,
    save_stock_list,
]

for cmd in commands:
    cli.add_command(cmd)

if __name__ == "__main__":
    cli()
