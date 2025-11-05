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
@click.option('--exchanges', help='交易所代码，多个用逗号分隔（如：SHFE,DCE,CZCE）')
@click.option('--start-date', help='起始日期（如：2025-01-01 或 20250101）')
@click.option('--end-date', help='结束日期（如：2025-12-31 或 20251231）')
@handle_errors
def save_trade_dates(exchanges, start_date, end_date):
    """
    保存交易日期数据

    默认保存今年所有交易所的数据
    """
    saver = DataSaverService()

    # 处理逗号分隔的交易所列表
    if exchanges:
        exchanges = exchanges.split(',')

    result = saver.save_trade_calendar(
        exchanges=exchanges,
        start_date=start_date,
        end_date=end_date
    )
    click.echo(f"交易日期数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")

@click.command()
@click.option('--exchanges', help='交易所代码，多个用逗号分隔（如：SHFE,DCE,CZCE）')
@click.option('--symbols', help='合约代码，多个用逗号分隔（如：SHFE.rb2501,DCE.m2505）')
@click.option('--spec-names', help='品种名称，多个用逗号分隔（如：rb,cu,al）')
@click.option('--date', help='查询日期（如：2025-01-15 或 20250115）')
@handle_errors
def save_future_contracts(exchanges, symbols, spec_names, date):
    """
    保存期货合约数据

    默认保存所有期货交易所的合约
    """
    saver = DataSaverService()

    # 处理逗号分隔的列表
    if exchanges:
        exchanges = exchanges.split(',')
    if symbols:
        symbols = symbols.split(',')
    if spec_names:
        spec_names = spec_names.split(',')

    result = saver.save_future_contracts(
        exchanges=exchanges,
        symbols=symbols,
        spec_names=spec_names,
        date=date
    )
    click.echo(f"期货合约数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")

@click.command()
@click.option('--exchanges', help='交易所代码，多个用逗号分隔')
@click.option('--symbols', help='合约代码，多个用逗号分隔')
@click.option('--spec-names', help='品种名称，多个用逗号分隔')
@click.option('--date', help='单日查询（如：2025-01-15）')
@click.option('--start-date', help='起始日期（如：2025-01-01）')
@click.option('--end-date', help='结束日期（如：2025-01-31）')
@handle_errors
def save_future_holdings(exchanges, symbols, spec_names, date, start_date, end_date):
    """
    保存期货持仓数据

    默认保存今天所有期货交易所的持仓数据
    """
    saver = DataSaverService()

    # 处理逗号分隔的列表
    if exchanges:
        exchanges = exchanges.split(',')
    if symbols:
        symbols = symbols.split(',')
    if spec_names:
        spec_names = spec_names.split(',')

    result = saver.save_future_holdings(
        exchanges=exchanges,
        symbols=symbols,
        spec_names=spec_names,
        date=date,
        start_date=start_date,
        end_date=end_date
    )
    click.echo(f"期货持仓数据保存完成: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")

@click.command()
@click.option('--exchanges', help='交易所代码，多个用逗号分隔（如：SHFE,DCE,CZCE）')
@click.option('--symbols', help='合约代码，多个用逗号分隔（如：SHFE.rb2501,DCE.m2505）')
@click.option('--date', help='单日查询（如：2025-01-15 或 20250115）')
@click.option('--start-date', help='起始日期（如：2025-01-01）')
@click.option('--end-date', help='结束日期（如：2025-01-31）')
@handle_errors
def save_future_daily(exchanges, symbols, date, start_date, end_date):
    """
    保存期货日线数据

    默认保存今天所有期货交易所的数据
    """
    saver = DataSaverService()

    # 处理逗号分隔的列表
    if exchanges:
        exchanges = exchanges.split(',')
    if symbols:
        symbols = symbols.split(',')

    result = saver.save_future_daily(
        exchanges=exchanges,
        symbols=symbols,
        date=date,
        start_date=start_date,
        end_date=end_date
    )
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
