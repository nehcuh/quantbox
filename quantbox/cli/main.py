"""Command line interface for quantbox"""

import click
from typing import Optional

from .trade_dates import save_trade_dates as _save_trade_dates


@click.group()
def cli():
    """Quantbox command line interface"""
    pass


@cli.group()
def save():
    """Save data to database"""
    pass


@save.command(name="trade_dates")
@click.option(
    "--exchange",
    "-e",
    type=str,
    help="Exchange code (e.g., SSE, SZSE). If not provided, will save for all exchanges.",
)
@click.option(
    "--exchange-type",
    "-t",
    type=click.Choice(["STOCK", "FUTURES"], case_sensitive=False),
    help="Exchange type. Used when exchange is not specified.",
)
@click.option(
    "--start-date",
    "-s",
    type=str,
    help="Start date in YYYYMMDD format. If not provided, will use 19890101.",
)
@click.option(
    "--end-date",
    "-d",
    type=str,
    help="End date in YYYYMMDD format. If not provided, will use current year's end.",
)
def save_trade_dates(
    exchange: Optional[str] = None,
    exchange_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Save trade dates to database.
    
    If neither exchange nor exchange-type is provided, will save for all exchanges.
    If start-date is not provided, will use 19890101.
    If end-date is not provided, will use current year's end.
    """
    _save_trade_dates(exchange, exchange_type, start_date, end_date)


if __name__ == "__main__":
    cli()
