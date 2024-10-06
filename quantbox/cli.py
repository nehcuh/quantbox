import click
from quantbox.savers.save_tushare import TSSaver

@click.group()
def cli():
    """
    Quantbox CLI 工具
    """
    pass

@click.command()
def save_all():
    """
    保存所有数据，包括交易日期、期货合约、期货持仓数据
    """
    saver = TSSaver()
    saver.save_trade_dates()
    saver.save_future_contracts()
    saver.save_future_holdings()
    saver.save_future_daily()

@click.command()
def save_trade_dates():
    """
    保存交易日期数据
    """
    saver = TSSaver()
    saver.save_trade_dates()

@click.command()
def save_future_contracts():
    """
    保存期货合约数据
    """
    saver = TSSaver()
    saver.save_future_contracts()

@click.command()
def save_future_holdings():
    """
    保存期货持仓数据
    """
    saver = TSSaver()
    saver.save_future_holdings()

@click.command()
def save_future_daily():
    """
    保存期货持仓数据
    """
    saver = TSSaver()
    saver.save_future_daily()

@click.command()
def save_stock_list():
    """
    保存期货持仓数据
    """
    saver = TSSaver()
    saver.save_stock_list()

cli.add_command(save_all)
cli.add_command(save_trade_dates)
cli.add_command(save_future_contracts)
cli.add_command(save_future_holdings)
cli.add_command(save_stock_list)
cli.add_command(save_future_daily)

if __name__ == "__main__":
    cli()
