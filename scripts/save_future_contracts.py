"""保存期货合约数据到数据库的命令行工具。"""

import sys
import logging
from datetime import datetime
import click

from quantbox.data.fetcher import TushareFetcher
from quantbox.data.database import MongoDBManager
from quantbox.core.config import ConfigLoader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.command()
@click.option(
    '--exchange',
    '-e',
    type=click.Choice(['SHFE', 'DCE', 'CZCE', 'CFFEX', 'INE']),
    help='交易所代码，不指定则处理所有交易所'
)
@click.option(
    '--spec-name',
    '-s',
    help='期货品种名称，如"豆粕"，不指定则处理所有品种'
)
@click.option(
    '--cursor-date',
    '-d',
    type=str,
    help='参考日期，格式为YYYYMMDD或YYYY-MM-DD，不指定则使用当前日期'
)
def main(exchange: str, spec_name: str, cursor_date: str):
    """从 Tushare 获取期货合约数据并保存到数据库。

    示例：
        # 保存所有交易所的期货合约数据
        python save_future_contracts.py

        # 保存大商所的期货合约数据
        python save_future_contracts.py -e DCE

        # 保存大商所豆粕期货合约数据
        python save_future_contracts.py -e DCE -s 豆粕

        # 保存指定日期的期货合约数据
        python save_future_contracts.py -d 20240127
    """
    try:
        # 初始化数据获取器和数据库管理器
        fetcher = TushareFetcher()
        db = MongoDBManager(ConfigLoader.get_database_config())

        # 处理日期参数
        if cursor_date:
            try:
                # 尝试将日期字符串转换为标准格式
                cursor_date = datetime.strptime(
                    cursor_date.replace('-', ''),
                    '%Y%m%d'
                ).strftime('%Y%m%d')
            except ValueError as e:
                logger.error(f"日期格式错误: {e}")
                sys.exit(1)

        # 确定要处理的交易所列表
        exchanges = [exchange] if exchange else ['SHFE', 'DCE', 'CZCE', 'CFFEX', 'INE']

        total_inserted = 0
        total_updated = 0

        # 处理每个交易所
        for exch in exchanges:
            try:
                logger.info(f"正在处理交易所 {exch} 的期货合约数据...")

                # 获取期货合约数据
                data = fetcher.fetch_get_future_contracts(
                    exchange=exch,
                    spec_name=spec_name,
                    cursor_date=cursor_date
                )

                if data is None or data.empty:
                    logger.warning(f"未获取到交易所 {exch} 的期货合约数据")
                    continue

                # 保存数据到数据库
                inserted, updated = db.save_future_contracts(data, exch)
                total_inserted += inserted
                total_updated += updated

                logger.info(
                    f"交易所 {exch} 处理完成: "
                    f"新增 {inserted} 条，更新 {updated} 条"
                )

            except Exception as e:
                logger.error(f"处理交易所 {exch} 时出错: {e}")
                continue

        logger.info(
            f"所有数据处理完成: "
            f"总共新增 {total_inserted} 条，更新 {total_updated} 条"
        )

    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        sys.exit(1)

    finally:
        # 关闭数据库连接
        if 'db' in locals():
            db.close()


if __name__ == '__main__':
    main()
