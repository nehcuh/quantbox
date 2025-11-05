import click
from quantbox.services.data_saver_service import DataSaverService
from quantbox.savers.data_saver import MarketDataSaver  # 仅用于 save_stock_list
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
    Quantbox CLI 工具 (新架构)

    所有命令默认使用新的三层架构（DataSaverService）和 Tushare 数据源
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
@handle_errors
def save_all():
    """
    保存所有数据，包括交易日期、期货合约、期货持仓数据、期货日线数据和股票列表

    注意：使用新架构（DataSaverService），默认使用 Tushare 数据源
    股票列表数据使用旧架构（新架构暂未实现此功能）
    """
    saver = DataSaverService()
    legacy_saver = MarketDataSaver()

    click.echo("开始保存所有数据...")

    # 保存交易日历
    result1 = saver.save_trade_calendar()
    click.echo(f"✓ 交易日历: 插入 {result1.inserted_count} 条，更新 {result1.modified_count} 条")

    # 保存期货合约
    result2 = saver.save_future_contracts()
    click.echo(f"✓ 期货合约: 插入 {result2.inserted_count} 条，更新 {result2.modified_count} 条")

    # 保存股票列表（使用旧架构）
    click.echo("✓ 股票列表: 使用旧架构保存...")
    legacy_saver.save_stock_list()

    # 保存期货持仓
    result3 = saver.save_future_holdings()
    click.echo(f"✓ 期货持仓: 插入 {result3.inserted_count} 条，更新 {result3.modified_count} 条")

    # 保存期货日线
    result4 = saver.save_future_daily()
    click.echo(f"✓ 期货日线: 插入 {result4.inserted_count} 条，更新 {result4.modified_count} 条")

    click.echo("\n所有数据保存完成！")

@click.command()
@handle_errors
def save_trade_dates():
    """
    保存交易日期数据

    注意：使用新架构（DataSaverService），默认使用 Tushare 数据源
    """
    saver = DataSaverService()
    result = saver.save_trade_calendar()
    click.echo(f"交易日期数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")

@click.command()
@handle_errors
def save_future_contracts():
    """
    保存期货合约数据

    注意：使用新架构（DataSaverService），默认使用 Tushare 数据源
    """
    saver = DataSaverService()
    result = saver.save_future_contracts()
    click.echo(f"期货合约数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")

@click.command()
@handle_errors
def save_future_holdings():
    """
    保存期货持仓数据

    注意：使用新架构（DataSaverService），默认使用 Tushare 数据源
    """
    saver = DataSaverService()
    result = saver.save_future_holdings()
    click.echo(f"期货持仓数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")

@click.command()
@handle_errors
def save_future_daily():
    """
    保存期货日线数据

    注意：使用新架构（DataSaverService），默认使用 Tushare 数据源
    """
    saver = DataSaverService()
    result = saver.save_future_daily()
    click.echo(f"期货日线数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")

@click.command()
@handle_errors
def save_stock_list():
    """
    保存股票列表数据

    注意：使用旧架构（MarketDataSaver），新架构暂未实现此功能
    """
    click.echo("注意：save_stock_list 使用旧架构（新架构暂未实现此功能）")
    saver = MarketDataSaver()
    saver.save_stock_list()
    click.echo("股票列表数据保存完成")

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
