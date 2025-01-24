"""Command line interface for trade dates operations"""

import click
from datetime import datetime
from typing import Optional

from ..data.fetcher import TushareFetcher
from ..core.config import ExchangeType


@click.command()
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
            click.echo(f"Successfully saved trade dates for exchange: {exchange}")
        else:
            # 根据exchange_type保存数据
            if exchange_type == ExchangeType.STOCK:
                exchanges = ["SSE", "SZSE"]
            elif exchange_type == ExchangeType.FUTURES:
                exchanges = ["SHFE", "DCE", "CZCE", "CFFEX", "INE", "GFEX"]
            else:
                # 默认保存所有交易所
                exchanges = ["SSE", "SZSE", "SHFE", "DCE", "CZCE", "CFFEX", "INE", "GFEX"]
            
            for ex in exchanges:
                fetcher.fetch_calendar(
                    exchange=ex,
                    start_date=start_date,
                    end_date=end_date
                )
                click.echo(f"Successfully saved trade dates for exchange: {ex}")
        
    except Exception as e:
        click.echo(f"Error saving trade dates: {str(e)}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    save_trade_dates()
