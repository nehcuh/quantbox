"""
市场数据保存模块

本模块提供从多个数据源（Tushare、掘金等）获取并保存市场数据到本地数据库的功能。
支持的数据类型包括：
- 交易日期数据
- 期货合约信息
- 期货持仓数据
- 期货日线数据
- 股票列表数据

类 (Classes):
    MarketDataSaver: 市场数据保存器主类 (Main class for market data saving operations)

依赖 (Dependencies):
    - pandas
    - pymongo
    - quantbox.adapters
    - quantbox.util
    - quantbox.config
    - quantbox.logger
"""

from typing import List, Union, Optional
import datetime
import time
import platform
import pandas as pd
import pymongo
from bson import ObjectId

from quantbox.adapters.ts_adapter import TSAdapter
from quantbox.adapters.local_adapter import LocalAdapter
from quantbox.util.exchange_utils import ALL_EXCHANGES, STOCK_EXCHANGES, FUTURES_EXCHANGES
from quantbox.config.config_loader import get_config_loader
from quantbox.util.date_utils import util_make_date_stamp, date_to_int
from quantbox.util.tools import (
    util_format_stock_symbols,
    util_to_json_from_pandas
)
from quantbox.logger import setup_logger
from quantbox.validators import retry


logger = setup_logger(__name__)


class SaveResult:
    """保存操作的结果类。

    用于跟踪数据保存操作的结果，包括成功和失败的统计信息。

    Attributes:
        success (bool): 操作是否成功
        inserted_count (int): 新增数据条数
        modified_count (int): 修改数据条数
        error_count (int): 错误数据条数
        errors (List[Dict]): 错误详情列表
        start_time (datetime): 操作开始时间
        end_time (datetime): 操作结束时间
        metadata (Dict): 其他元数据
    """

    def __init__(self):
        self.success = True
        self.inserted_count = 0
        self.modified_count = 0
        self.error_count = 0
        self.errors = []
        self.start_time = datetime.datetime.now()
        self.end_time = None
        self.metadata = {}

    def add_error(self, error_type, error_msg, data=None):
        """添加错误信息。

        Args:
            error_type (str): 错误类型
            error_msg (str): 错误信息
            data (Any, optional): 相关数据
        """
        self.success = False
        self.error_count += 1
        self.errors.append({
            "type": error_type,
            "message": error_msg,
            "data": data,
            "timestamp": datetime.datetime.now()
        })

    def complete(self):
        """完成操作，记录结束时间。"""
        self.end_time = datetime.datetime.now()

    @property
    def duration(self):
        """获取操作持续时间。

        Returns:
            datetime.timedelta: 操作持续时间
        """
        if self.end_time:
            return self.end_time - self.start_time
        return datetime.datetime.now() - self.start_time

    def to_dict(self):
        """转换为字典格式。

        Returns:
            Dict: 结果字典
        """
        return {
            "success": self.success,
            "inserted_count": self.inserted_count,
            "modified_count": self.modified_count,
            "error_count": self.error_count,
            "errors": self.errors,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": str(self.duration),
            "metadata": self.metadata
        }


class DataIntegrityChecker:
    """数据完整性检查器。

    用于检查数据的完整性和一致性。

    Attributes:
        client: MongoDB 客户端
        config: 配置信息
    """

    def __init__(self, client, config):
        self.client = client
        self.config = config

    def check_trade_dates(self, exchange, start_date=None, end_date=None):
        """检查交易日期数据的完整性。

        Args:
            exchange (str): 交易所代码
            start_date (str, optional): 开始日期
            end_date (str, optional): 结束日期

        Returns:
            SaveResult: 检查结果
        """
        result = SaveResult()
        collections = self.client.trade_date

        try:
            # 1. 基本数据查询
            pipeline = [
                {"$match": {"exchange": exchange}},
                {"$sort": {"trade_date": 1}},
                {
                    "$group": {
                        "_id": None,
                        "dates": {"$push": "$trade_date"},
                        "count": {"$sum": 1},
                        "min_date": {"$min": "$trade_date"},
                        "max_date": {"$max": "$trade_date"}
                    }
                }
            ]
            if start_date:
                pipeline[0]["$match"]["trade_date"] = {"$gte": start_date}
            if end_date:
                pipeline[0]["$match"]["trade_date"]["$lte"] = end_date

            data = list(collections.aggregate(pipeline))
            if not data:
                result.add_error("NO_DATA", f"交易所 {exchange} 没有数据")
                return result

            # 2. 检查数据基本统计
            stats = data[0]
            result.metadata.update({
                "total_count": stats["count"],
                "date_range": {
                    "start": stats["min_date"],
                    "end": stats["max_date"]
                }
            })

            # 3. 检查异常交易日模式
            dates_df = pd.DataFrame({"trade_date": pd.to_datetime(stats["dates"])})
            dates_df["year"] = dates_df["trade_date"].dt.year
            dates_df["month"] = dates_df["trade_date"].dt.month
            dates_df["day"] = dates_df["trade_date"].dt.day
            dates_df["weekday"] = dates_df["trade_date"].dt.weekday

            # 3.1 检查是否存在周末交易（国内市场不应该有周末交易）
            weekend_trades = dates_df[dates_df["weekday"].isin([5, 6])]
            if not weekend_trades.empty:
                result.add_error(
                    "WEEKEND_TRADES",
                    f"发现周末交易日记录",
                    weekend_trades["trade_date"].dt.strftime("%Y-%m-%d").tolist()
                )

            # 3.2 检查每月交易日数量是否异常（过少可能表示数据缺失）
            monthly_counts = dates_df.groupby(["year", "month"]).size()
            # 国内市场每月通常至少有 15 个交易日（考虑春节等长假）
            suspicious_months = monthly_counts[monthly_counts < 15]
            if not suspicious_months.empty:
                for (year, month), count in suspicious_months.items():
                    result.add_error(
                        "LOW_TRADING_DAYS",
                        f"{year}年{month}月交易日数量异常偏少: {count}天",
                        {"year": year, "month": month, "count": int(count)}
                    )

            # 4. 检查字段完整性
            invalid_docs = collections.find({
                "exchange": exchange,
                "$or": [
                    {"trade_date": {"$exists": False}},
                    {"pretrade_date": {"$exists": False}},
                    {"datestamp": {"$exists": False}}
                ]
            })
            for doc in invalid_docs:
                result.add_error(
                    "MISSING_FIELD",
                    f"数据字段不完整: {doc['_id']}",
                    doc
                )

            # 5. 检查 pretrade_date 的有效性
            invalid_pretrade = collections.find({
                "exchange": exchange,
                "$expr": {"$gt": ["$pretrade_date", "$trade_date"]}
            })
            for doc in invalid_pretrade:
                result.add_error(
                    "INVALID_PRETRADE_DATE",
                    f"前一交易日晚于交易日: {doc['trade_date']}",
                    {
                        "trade_date": doc["trade_date"],
                        "pretrade_date": doc["pretrade_date"]
                    }
                )

            result.complete()
            return result

        except Exception as e:
            result.add_error("CHECK_ERROR", str(e))
            result.complete()
            return result

    def check_future_contracts(self, exchange):
        """检查期货合约数据的完整性。

        Args:
            exchange (str): 交易所代码

        Returns:
            SaveResult: 检查结果
        """
        result = SaveResult()
        collections = self.client.future_contracts

        try:
            # 1. 检查必要字段
            invalid_docs = collections.find({
                "exchange": exchange,
                "$or": [
                    {"symbol": {"$exists": False}},
                    {"name": {"$exists": False}},
                    {"list_date": {"$exists": False}},
                    {"delist_date": {"$exists": False}},
                    {"datestamp": {"$exists": False}}
                ]
            })
            for doc in invalid_docs:
                result.add_error(
                    "MISSING_FIELD",
                    f"数据字段不完整: {doc['_id']}",
                    doc
                )

            # 2. 检查日期有效性
            invalid_dates = collections.find({
                "exchange": exchange,
                "$expr": {"$gt": ["$list_date", "$delist_date"]}
            })
            for doc in invalid_dates:
                result.add_error(
                    "INVALID_DATE",
                    f"上市日期晚于退市日期: {doc['symbol']}",
                    doc
                )

            # 3. 统计信息
            stats = collections.aggregate([
                {"$match": {"exchange": exchange}},
                {
                    "$group": {
                        "_id": None,
                        "total_count": {"$sum": 1},
                        "active_count": {
                            "$sum": {
                                "$cond": [
                                    {
                                        "$and": [
                                            {"$lte": ["$list_date", datetime.datetime.now().strftime("%Y-%m-%d")]},
                                            {"$gte": ["$delist_date", datetime.datetime.now().strftime("%Y-%m-%d")]}
                                        ]
                                    },
                                    1,
                                    0
                                ]
                            }
                        }
                    }
                }
            ])
            stats_data = list(stats)
            if stats_data:
                result.metadata["total_count"] = stats_data[0]["total_count"]
                result.metadata["active_count"] = stats_data[0]["active_count"]

            result.complete()
            return result

        except Exception as e:
            result.add_error("CHECK_ERROR", str(e))
            result.complete()
            return result


class MarketDataSaver:
    """
    市场数据保存器，用于从多个数据源获取并保存市场数据到本地数据库。

    本类提供了从多个数据源（如 Tushare）获取数据并保存到本地 MongoDB 数据库的方法。
    包含数据验证、错误恢复和完整的日志记录功能。

    属性：
        ts_adapter: Tushare 数据适配器实例
        local_adapter: 本地数据适配器实例
        client: MongoDB 数据库客户端
        config: 配置设置
        exchanges: 支持的所有交易所列表
        future_exchanges: 支持的期货交易所列表
        stock_exchanges: 支持的股票交易所列表

    使用注意：
        使用本类前请确保：
        1. 数据库连接已正确配置
        2. 数据源凭证已设置
        3. 必要的配置已加载

    """

    def __init__(self):
        """
        初始化市场数据保存器实例。

        设置数据适配器、数据库客户端和配置。
        """
        self.ts_adapter = TSAdapter()
        self.local_adapter = LocalAdapter()
        self.client = get_config_loader().get_mongodb_client().quantbox
        self.config = get_config_loader()._load_user_config()
        self.exchanges = ALL_EXCHANGES.copy()
        self.future_exchanges = FUTURES_EXCHANGES.copy()
        self.stock_exchanges = STOCK_EXCHANGES.copy()
        self.integrity_checker = DataIntegrityChecker(self.client, self.config)

    def _create_trade_dates_index(self, collections):
        """创建交易日期集合的索引。

        Args:
            collections: MongoDB 集合对象

        Raises:
            Exception: 创建索引失败时抛出
        """
        try:
            # 创建复合唯一索引，确保每个交易所的每个交易日只有一条记录
            collections.create_index(
                [
                    ("exchange", pymongo.ASCENDING),
                    ("trade_date", pymongo.ASCENDING)
                ],
                unique=True,
                background=True
            )
            # 创建用于查询的辅助索引
            collections.create_index(
                [("datestamp", pymongo.DESCENDING)],
                background=True
            )
            logger.debug("成功创建/更新交易日期索引")
        except pymongo.errors.DuplicateKeyError:
            logger.debug("索引已存在")
        except Exception as e:
            logger.error(f"创建交易日期索引失败: {str(e)}")
            raise

    def _get_latest_trade_date(self, collections, exchange):
        """获取指定交易所的最新交易日期。

        Args:
            collections: MongoDB 集合对象
            exchange: 交易所代码

        Returns:
            str: 最新交易日期，如果没有数据则返回 None
        """
        try:
            count = collections.count_documents({"exchange": exchange})
            if count > 0:
                first_doc = collections.find_one(
                    {"exchange": exchange},
                    sort=[("datestamp", pymongo.DESCENDING)]
                )
                latest_date = first_doc["trade_date"]
                logger.info(f"交易所 {exchange} 最新数据日期: {latest_date}")
                return latest_date
            logger.info(f"交易所 {exchange} 无历史数据")
            return None
        except Exception as e:
            logger.error(f"获取交易所 {exchange} 最新交易日期失败: {str(e)}")
            raise

    def _save_trade_dates_for_exchange(self, collections, exchange, start_date):
        """保存指定交易所的交易日期数据。

        Args:
            collections: MongoDB 集合对象
            exchange: 交易所代码
            start_date: 起始日期

        Returns:
            int: 新增的数据条数
        """
        try:
            # 检查是否需要更新
            if pd.Timestamp(start_date) >= pd.Timestamp.today():
                logger.info(f"交易所 {exchange} 数据已是最新，无需更新")
                return 0

            # 获取新数据
            df = self.ts_adapter.get_trade_calendar(
                exchanges=exchange,
                start_date=start_date
            )

            if df is None or df.empty:
                logger.warning(f"交易所 {exchange} 没有新的交易日期数据")
                return 0

            # 数据验证
            if not self._validate_trade_dates_data(df):
                logger.error(f"交易所 {exchange} 数据验证失败")
                return 0

            # 转换为 JSON 并保存
            data = util_to_json_from_pandas(df)
            if not data:
                logger.warning(f"交易所 {exchange} 数据转换为 JSON 后为空")
                return 0

            # 使用 bulk_write 进行批量插入，支持去重
            operations = [
                pymongo.UpdateOne(
                    {
                        "exchange": doc["exchange"],
                        "trade_date": doc["trade_date"]
                    },
                    {"$set": doc},
                    upsert=True
                ) for doc in data
            ]

            result = collections.bulk_write(operations)
            inserted_count = result.upserted_count
            modified_count = result.modified_count
            logger.info(f"交易所 {exchange} 新增 {inserted_count} 条数据，更新 {modified_count} 条数据")
            return inserted_count

        except Exception as e:
            logger.error(f"保存交易所 {exchange} 数据时出错: {str(e)}")
            raise

    def _validate_trade_dates_data(self, df):
        """验证交易日期数据的有效性。

        Args:
            df: 待验证的数据框

        Returns:
            bool: 数据是否有效
        """
        try:
            # 检查必要字段
            required_columns = {"exchange", "trade_date", "pretrade_date", "datestamp"}
            if not all(col in df.columns for col in required_columns):
                logger.error(f"数据缺少必要字段: {required_columns - set(df.columns)}")
                return False

            # 检查数据类型
            if not pd.api.types.is_string_dtype(df["trade_date"]):
                logger.error("trade_date 字段类型错误")
                return False

            if not pd.api.types.is_string_dtype(df["exchange"]):
                logger.error("exchange 字段类型错误")
                return False

            # 检查日期格式
            try:
                pd.to_datetime(df["trade_date"])
            except Exception:
                logger.error("trade_date 日期格式错误")
                return False

            return True
        except Exception as e:
            logger.error(f"数据验证过程出错: {str(e)}")
            return False

    @retry(max_attempts=3, delay=60)
    def save_trade_dates(self, start_date: Optional[str] = None):
        """
        保存交易日期数据到本地数据库。

        从 Tushare 获取交易日期数据并保存到本地 MongoDB 数据库的 'trade_date' 集合中。
        支持增量更新和数据去重。包含完整的数据验证、日志记录和错误恢复机制。

        Args:
            start_date: 开始日期，默认为 None。
                       如果为 None，则使用配置文件中指定的默认起始日期。

        Returns:
            SaveResult: 保存操作的结果

        Raises:
            Exception: 当数据保存过程中发生错误时抛出
        """
        result = SaveResult()
        logger.info("开始保存交易日期数据 (数据源: Tushare)")
        collections = self.client.trade_date

        try:
            # 创建检查点
            checkpoint_id = self._create_save_checkpoint(collections, "save_trade_dates")

            # 创建索引
            self._create_trade_dates_index(collections)

            if start_date is None:
                start_date = self.config['saver'].get('default_start_date', '1990-12-19')

            total_inserted = 0
            for exchange in self.exchanges:
                try:
                    # 获取最新日期
                    latest_date = self._get_latest_trade_date(collections, exchange)
                    current_start_date = latest_date if latest_date else start_date

                    # 保存数据
                    inserted_count = self._save_trade_dates_for_exchange(
                        collections,
                        exchange,
                        current_start_date
                    )
                    total_inserted += inserted_count

                    # 数据完整性检查
                    check_result = self.integrity_checker.check_trade_dates(
                        exchange,
                        start_date=current_start_date
                    )
                    if not check_result.success:
                        for error in check_result.errors:
                            result.add_error(
                                f"INTEGRITY_CHECK_{error['type']}",
                                f"交易所 {exchange}: {error['message']}",
                                error['data']
                            )

                except Exception as e:
                    error_msg = f"处理交易所 {exchange} 数据时出错: {str(e)}"
                    logger.error(error_msg)
                    result.add_error("EXCHANGE_ERROR", error_msg)

            # 更新结果
            result.inserted_count = total_inserted
            result.complete()

            # 更新检查点状态
            self._update_save_checkpoint(
                checkpoint_id,
                "completed" if result.success else "failed",
                result
            )

            # 保存操作日志
            self._save_operation_log("save_trade_dates", result)

            logger.info(
                f"交易日期数据保存完成，总共新增 {total_inserted} 条数据，"
                f"错误 {result.error_count} 条"
            )
            return result

        except Exception as e:
            error_msg = f"保存交易日期数据时出错: {str(e)}"
            logger.error(error_msg)
            result.add_error("FATAL_ERROR", error_msg)
            result.complete()

            # 更新检查点状态
            if 'checkpoint_id' in locals():
                self._update_save_checkpoint(checkpoint_id, "failed", result)

            # 保存操作日志
            self._save_operation_log("save_trade_dates", result)

            raise

    def _create_future_contracts_index(self, collections):
        """创建期货合约集合的索引。

        Args:
            collections: MongoDB 集合对象

        Raises:
            Exception: 创建索引失败时抛出
        """
        try:
            # 创建复合唯一索引
            collections.create_index(
                [
                    ("exchange", pymongo.ASCENDING),
                    ("symbol", pymongo.ASCENDING)
                ],
                unique=True,
                background=True
            )
            # 创建用于查询的辅助索引
            collections.create_index(
                [("datestamp", pymongo.DESCENDING)],
                background=True
            )
            logger.debug("成功创建/更新期货合约索引")
        except pymongo.errors.DuplicateKeyError:
            logger.debug("索引已存在")
        except Exception as e:
            logger.error(f"创建期货合约索引失败: {str(e)}")
            raise

    def _validate_future_contracts_data(self, df):
        """验证期货合约数据的有效性。

        Args:
            df: 待验证的数据框

        Returns:
            bool: 数据是否有效
        """
        try:
            # 检查必要字段
            required_columns = {
                "exchange", "symbol", "name", "list_date",
                "delist_date", "datestamp"
            }
            if not all(col in df.columns for col in required_columns):
                logger.error(f"数据缺少必要字段: {required_columns - set(df.columns)}")
                return False

            # 检查数据类型
            if not pd.api.types.is_string_dtype(df["symbol"]):
                logger.error("symbol 字段类型错误")
                return False

            if not pd.api.types.is_string_dtype(df["exchange"]):
                logger.error("exchange 字段类型错误")
                return False

            # 检查日期格式
            try:
                pd.to_datetime(df["list_date"])
                pd.to_datetime(df["delist_date"])
            except Exception:
                logger.error("上市或退市日期格式错误")
                return False

            return True
        except Exception as e:
            logger.error(f"数据验证过程出错: {str(e)}")
            return False

    def _get_existing_contracts(self, collections, exchange, batch_size):
        """获取已存在的合约信息。

        Args:
            collections: MongoDB 集合对象
            exchange: 交易所代码
            batch_size: 批量处理大小

        Returns:
            set: 已存在的合约代码集合
        """
        try:
            cursor = collections.find(
                {"exchange": exchange},
                {"_id": 0, "symbol": 1},
                batch_size=batch_size
            )
            return {doc["symbol"] for doc in cursor}
        except Exception as e:
            logger.error(f"获取交易所 {exchange} 已存在合约信息失败: {str(e)}")
            raise

    def _save_future_contracts_for_exchange(
        self,
        collections,
        exchange,
        batch_size,
        existing_symbols=None
    ):
        """保存指定交易所的期货合约数据。

        Args:
            collections: MongoDB 集合对象
            exchange: 交易所代码
            batch_size: 批量处理大小
            existing_symbols: 已存在的合约代码集合，如果为 None 则查询数据库

        Returns:
            int: 新增的数据条数
        """
        try:
            # 获取所有合约信息
            total_contracts = self.ts_adapter.get_future_contracts(
                exchanges=exchange
            )
            if total_contracts is None or total_contracts.empty:
                logger.warning(f"交易所 {exchange} 未获取到合约信息")
                return 0

            # 数据验证
            if not self._validate_future_contracts_data(total_contracts):
                logger.error(f"交易所 {exchange} 合约数据验证失败")
                return 0

            symbols = total_contracts.symbol.tolist()
            logger.info(f"交易所 {exchange} 共有 {len(symbols)} 个合约")

            # 获取已存在的合约
            if existing_symbols is None:
                existing_symbols = self._get_existing_contracts(
                    collections, exchange, batch_size
                )

            # 找出新增的合约
            new_symbols = set(symbols) - existing_symbols
            if not new_symbols:
                logger.info(f"交易所 {exchange} 没有新的合约信息需要添加")
                return 0

            # 只处理新的合约信息
            new_contracts = total_contracts.loc[
                total_contracts["symbol"].isin(list(new_symbols))
            ]
            data = util_to_json_from_pandas(new_contracts)

            # 使用 bulk_write 进行批量插入，支持去重
            operations = [
                pymongo.UpdateOne(
                    {
                        "exchange": doc["exchange"],
                        "symbol": doc["symbol"]
                    },
                    {"$set": doc},
                    upsert=True
                ) for doc in data
            ]

            # 分批处理
            total_ops = len(operations)
            inserted_count = 0
            modified_count = 0
            for i in range(0, total_ops, batch_size):
                batch_ops = operations[i:i + batch_size]
                result = collections.bulk_write(batch_ops)
                inserted_count += result.upserted_count
                modified_count += result.modified_count

            logger.info(
                f"交易所 {exchange} 新增 {inserted_count} 个合约信息，"
                f"更新 {modified_count} 个合约信息"
            )
            return inserted_count

        except Exception as e:
            logger.error(f"保存交易所 {exchange} 合约数据时出错: {str(e)}")
            raise

    @retry(max_attempts=3, delay=60)
    def save_future_contracts(self, batch_size: Optional[int] = None):
        """
        保存期货合约信息到本地数据库。

        从 Tushare 获取期货合约信息并保存到本地 MongoDB 数据库的 'future_contracts' 集合中。
        支持增量更新和数据去重。包含完整的数据验证、日志记录和错误恢复机制。

        Args:
            batch_size: 批量插入数据的大小，默认为 None。
                       如果为 None，则使用配置文件中指定的默认批量大小。

        Returns:
            SaveResult: 保存操作的结果

        Raises:
            Exception: 当数据保存过程中发生错误时抛出
        """
        result = SaveResult()
        logger.info("开始保存期货合约信息")
        collections = self.client.future_contracts

        try:
            # 创建检查点
            checkpoint_id = self._create_save_checkpoint(collections, "save_future_contracts")

            # 创建索引
            self._create_future_contracts_index(collections)

            # 设置批量处理大小
            if batch_size is None:
                batch_size = self.config['saver'].get('batch_size', 10000)

            total_inserted = 0
            for exchange in self.future_exchanges:
                try:
                    # 保存数据
                    inserted_count = self._save_future_contracts_for_exchange(
                        collections,
                        exchange,
                        batch_size
                    )
                    total_inserted += inserted_count

                    # 数据完整性检查
                    check_result = self.integrity_checker.check_future_contracts(exchange)
                    if not check_result.success:
                        for error in check_result.errors:
                            result.add_error(
                                f"INTEGRITY_CHECK_{error['type']}",
                                f"交易所 {exchange}: {error['message']}",
                                error['data']
                            )

                    # 添加统计信息
                    if check_result.metadata:
                        result.metadata[f"{exchange}_stats"] = check_result.metadata

                except Exception as e:
                    error_msg = f"处理交易所 {exchange} 数据时出错: {str(e)}"
                    logger.error(error_msg)
                    result.add_error("EXCHANGE_ERROR", error_msg)

            # 更新结果
            result.inserted_count = total_inserted
            result.complete()

            # 更新检查点状态
            self._update_save_checkpoint(
                checkpoint_id,
                "completed" if result.success else "failed",
                result
            )

            # 保存操作日志
            self._save_operation_log("save_future_contracts", result)

            logger.info(
                f"期货合约信息保存完成，总共新增 {total_inserted} 个合约，"
                f"错误 {result.error_count} 条"
            )
            return result

        except Exception as e:
            error_msg = f"保存期货合约信息时出错: {str(e)}"
            logger.error(error_msg)
            result.add_error("FATAL_ERROR", error_msg)
            result.complete()

            # 更新检查点状态
            if 'checkpoint_id' in locals():
                self._update_save_checkpoint(checkpoint_id, "failed", result)

            # 保存操作日志
            self._save_operation_log("save_future_contracts", result)

            raise

    @retry(max_attempts=3, delay=60)
    def save_future_holdings(
        self,
        exchanges: Union[str, List[str], None] = None,
        start_date: Union[str, datetime.date, None] = None,
        end_date: Union[str, datetime.date, None] = None,
        offset: int = None,
        max_workers: int = None
    ):
        """
        保存期货持仓数据到本地数据库。

        从指定的数据源获取期货持仓数据并保存到本地 MongoDB 数据库的 'future_holdings' 集合中。

        参数：
            exchanges: 交易所列表，默认为 None。
                       如果为 None，则使用所有支持的期货交易所。
            start_date: 开始日期，默认为 None。
                       如果为 None，则使用配置文件中指定的默认起始日期。
            end_date: 结束日期，默认为 None。
                      如果为 None，则使用当前日期。
            offset: 偏移天数，默认为 None。
                   如果为 None，则使用配置文件中指定的默认偏移天数。
            max_workers: 最大工作线程数，默认为 None。
                        如果为 None，则使用配置文件中指定的默认最大工作线程数。

        注意：
            - 会自动创建必要的数据库索引
            - 包含错误重试机制
            - 保存完整的操作日志
        """
        logger.info("开始保存期货持仓数据")
        collections = self.client.future_holdings

        try:
            # 创建索引
            collections.create_index(
                [
                    ("trade_date", pymongo.ASCENDING),
                    ("broker", pymongo.ASCENDING),
                    ("symbol", pymongo.ASCENDING)
                ],
                unique=True,
                background=True
            )
            collections.create_index(
                [
                    ("exchange", pymongo.ASCENDING),
                    ("symbol", pymongo.ASCENDING),
                    ("datestamp", pymongo.DESCENDING),
                ],
                background=True
            )
            logger.debug("成功创建/更新索引")
        except Exception as e:
            logger.error(f"创建索引失败: {str(e)}")
            raise

        # 处理配置参数
        if offset is None:
            offset = self.config['saver'].get('offset', 365)
        if max_workers is None:
            max_workers = self.config['saver'].get('max_workers', 4)
        trading_end_hour = self.config['saver'].get('trading_end_hour', 16)

        # 处理交易所参数
        if exchanges is None:
            exchanges = self.future_exchanges
        elif isinstance(exchanges, str):
            exchanges = [exchanges]

        # 处理日期参数
        if start_date is None:
            start_date = self.config['saver'].get('default_start_date', '1990-12-19')
        if end_date is None:
            end_date = datetime.date.today().strftime("%Y-%m-%d")

        logger.info(f"处理日期范围: {start_date} 到 {end_date}")

        total_inserted = 0
        for exchange in exchanges:
            try:
                # 获取交易日列表
                trade_dates = self.local_adapter.get_trade_calendar(
                    exchanges=exchange,
                    start_date=start_date,
                    end_date=end_date
                )

                if trade_dates is None or trade_dates.empty:
                    logger.warning(f"交易所 {exchange} 在指定日期范围内没有交易日")
                    continue

                # 提交所有任务
                for trade_date in trade_dates.trade_date.tolist():
                    try:
                        count = collections.count_documents({
                            "datestamp": util_make_date_stamp(trade_date),
                            "exchange": exchange,
                        })

                        if count == 0:
                            logger.info(f"获取交易所 {exchange} 在交易日 {trade_date} 的持仓排名")

                            # 根据不同引擎调用不同的数据获取方法
                            if engine == 'ts':
                                results = self.ts_adapter.get_future_holdings(
                                    exchanges=exchange, date=trade_date
                                )
                            else:
                                raise ValueError(f"不支持的数据引擎: {engine}，请使用 'ts'")

                            if results is not None and not results.empty:
                                # 检查重复记录
                                duplicates = results.duplicated(subset=['trade_date', 'broker', 'symbol'], keep='last')
                                if duplicates.any():
                                    logger.warning(f"发现 {duplicates.sum()} 条重复记录，将保留最新的记录")
                                    results = results[~duplicates]

                                # 使用 upsert 操作保存数据
                                for _, row in results.iterrows():
                                    data = util_to_json_from_pandas(pd.DataFrame([row]))
                                    collections.update_one(
                                        {
                                            "trade_date": row['trade_date'],
                                            "broker": row['broker'],
                                            "symbol": row['symbol']
                                        },
                                        {"$set": data[0]},
                                        upsert=True
                                    )

                                inserted_count = len(results)
                                logger.info(f"交易所 {exchange} 在交易日 {trade_date} 新增/更新 {inserted_count} 条持仓数据")
                                total_inserted += inserted_count
                            else:
                                logger.warning(f"交易所 {exchange} 在交易日 {trade_date} 未获取到持仓数据")
                    except pymongo.errors.DuplicateKeyError as e:
                        logger.warning(f"处理重复数据: {str(e)}")
                    except Exception as e:
                        logger.error(f"处理交易所 {exchange} 在交易日 {trade_date} 的数据时出错: {str(e)}")
                        continue

            except Exception as e:
                logger.error(f"处理交易所 {exchange} 数据时出错: {str(e)}")
                continue

        logger.info(f"期货持仓数据保存完成，总共新增 {total_inserted} 条数据")

    @retry(max_attempts=3, delay=60)
    def save_stock_list(
        self,
        symbols: Union[str, List[str], None] = None,
        names: Union[str, List[str], None] = None,
        exchanges: Union[str, List[str], None] = None,
        markets: Union[str, List[str], None] = None,
        list_status: Union[str, List[str], None] = "L",
        is_hs: Union[str, None] = None,
        force_refresh: bool = False,
    ):
        """
        保存股票列表数据到本地数据库。

        从 Tushare 获取股票列表数据并保存到本地 MongoDB 数据库的 'stock_list' 集合中。

        参数：
            symbols: 股票代码或列表（标准格式）
            names: 股票名称或列表
            exchanges: 交易所代码或列表（如 SSE, SZSE, BSE）
            markets: 市场板块或列表（如 主板, 创业板, 科创板, CDR, 北交所）
            list_status: 上市状态（'L' 上市, 'D' 退市, 'P' 暂停上市）
            is_hs: 沪港通状态（'N' 否, 'H' 沪股通, 'S' 深股通）
            force_refresh: 是否强制刷新所有数据，默认为 False（增量更新）

        注意：
            - 会自动创建必要的数据库索引
            - 包含错误重试机制
            - 保存完整的操作日志
            - 默认采用增量更新策略，只获取缺失的数据
        """
        logger.info("开始保存股票列表数据")
        collections = self.client.stock_list

        try:
            # 创建索引
            collections.create_index(
                [("symbol", pymongo.ASCENDING), ("list_datestamp", pymongo.ASCENDING)],
                unique=True,
                background=True
            )
            logger.debug("成功创建/更新索引")
        except Exception as e:
            logger.error(f"创建索引失败: {str(e)}")
            raise

        try:
            # 如果强制刷新，先清空现有数据
            if force_refresh:
                logger.info("强制刷新模式，清空现有股票列表数据")
                collections.delete_many({})
                existing_symbols = set()
            else:
                # 获取现有的股票代码集合
                existing_symbols = set(collections.distinct("symbol"))
                logger.info(f"现有股票列表包含 {len(existing_symbols)} 条记录")

            # 获取股票列表数据
            logger.info("从数据源获取股票列表数据")
            data = self.ts_adapter.get_stock_list(
                symbols=symbols,
                names=names,
                exchanges=exchanges,
                markets=markets,
                list_status=list_status,
                is_hs=is_hs
            )

            if data is None or data.empty:
                logger.warning("未获取到股票列表数据")
                return

            # 数据预处理
            logger.debug("开始处理股票列表数据")
            # 标准化股票代码
            data.symbol = util_format_stock_symbols(data.symbol, "standard")

            # 移除不需要的列
            if "ts_code" in data.columns:
                data = data.drop(columns=["ts_code"])

            # 添加上市日期时间戳
            data["list_datestamp"] = (
                data["list_date"].map(str).apply(lambda x: util_make_date_stamp(x))
            )

            # 如果不是强制刷新，过滤掉已存在的数据
            if not force_refresh and len(existing_symbols) > 0:
                original_count = len(data)
                data = data[~data["symbol"].isin(existing_symbols)]
                filtered_count = len(data)
                logger.info(f"过滤后保留 {filtered_count}/{original_count} 条新记录")

            if data.empty:
                logger.info("没有新的股票数据需要保存")
                return

            # 保存新数据
            result = collections.insert_many(util_to_json_from_pandas(data))
            inserted_count = len(result.inserted_ids)
            logger.info(f"股票列表数据保存完成，新增 {inserted_count} 条记录")

            # 验证数据完整性（仅针对本次插入的数据）
            if inserted_count != len(data):
                raise ValueError(
                    f"数据完整性检查失败：期望保存 {len(data)} 条记录，"
                    f"实际保存 {inserted_count} 条记录"
                )

        except Exception as e:
            logger.error(f"保存股票列表数据时出错: {str(e)}")
            raise

    @retry(max_attempts=3, delay=60)
    def save_future_daily(
        self,
        exchanges: Union[str, List[str], None] = None,
        start_date: Union[str, datetime.date, None] = None,
        end_date: Union[str, datetime.date, None] = None,
        offset: int = 365,
    ):
        """
        保存期货日线数据到本地数据库。

        从 Tushare 获取期货日线数据并保存到本地 MongoDB 数据库的 'future_daily' 集合中。

        参数：
            exchanges: 交易所列表，默认为 None。
                       如果为 None，则使用所有支持的期货交易所。
            start_date: 开始日期，默认为 None。
                       如果为 None，则使用配置文件中指定的默认起始日期。
            end_date: 结束日期，默认为 None。
                      如果为 None，则使用当前日期。
            offset: 偏移天数，默认为 365。

        注意：
            - 会自动创建必要的数据库索引
            - 包含错误重试机制
            - 保存完整的操作日志
        """
        logger.info("开始保存期货日线数据")
        collections = self.client.future_daily

        try:
            # 创建索引
            collections.create_index(
                [("symbol", pymongo.ASCENDING), ("datestamp", pymongo.DESCENDING)],
                unique=True,
                background=True
            )
            logger.debug("成功创建/更新索引")
        except Exception as e:
            logger.error(f"创建索引失败: {str(e)}")
            raise

        # 处理交易所参数
        if exchanges is None:
            exchanges = self.future_exchanges
        elif isinstance(exchanges, str):
            exchanges = [exchanges]

        # 处理日期参数
        if start_date is None:
            start_date = self.config['saver'].get('default_start_date', '1990-12-19')
        if end_date is None:
            end_date = datetime.date.today().strftime("%Y-%m-%d")

        logger.info(f"处理日期范围: {start_date} 到 {end_date}")

        total_inserted = 0
        for exchange in exchanges:
            try:
                # 获取该交易所的所有合约
                logger.info(f"获取交易所 {exchange} 的合约列表")
                contracts = self.local_adapter.get_future_contracts(exchanges=exchange)

                if contracts is None or contracts.empty:
                    logger.warning(f"交易所 {exchange} 未获取到合约信息")
                    continue

                for _, contract_info in contracts.iterrows():
                    try:
                        symbol = contract_info["symbol"]
                        list_date = contract_info["list_date"]
                        delist_date = contract_info["delist_date"]

                        # 检查是否已存在数据
                        latest_doc = collections.find_one(
                            {"symbol": symbol},
                            sort=[("datestamp", pymongo.DESCENDING)]
                        )

                        if latest_doc:
                            latest_date = latest_doc["trade_date"]
                            next_date = self.local_adapter.get_next_trade_date(
                                exchange=exchange,
                                cursor_date=latest_date,
                                n=1,
                                include=False
                            )

                            if next_date is None:
                                logger.debug(f"合约 {symbol} 数据已是最新")
                                continue

                            start = next_date['trade_date']
                            logger.info(f"更新合约 {symbol} 从 {start} 到 {delist_date} 的日线数据")

                            # 如果已经到了退市日期，跳过
                            if pd.Timestamp(start) >= pd.Timestamp(delist_date):
                                logger.debug(f"合约 {symbol} 已到退市日期")
                                continue
                        else:
                            start = list_date
                            logger.info(f"获取合约 {symbol} 从 {start} 到 {delist_date} 的日线数据")

                        # 获取日线数据
                        data = self.ts_adapter.get_future_daily(
                            symbols=symbol,
                            start_date=start,
                            end_date=delist_date
                        )

                        if data is None or data.empty:
                            logger.warning(f"合约 {symbol} 在 {start} 到 {delist_date} 期间无数据")
                            continue

                        # 标准化日线数据
                        data = self.standardize_future_daily_data(data, source='ts')

                        # 添加日期时间戳
                        data["datestamp"] = data["trade_date"].map(str).apply(
                            lambda x: util_make_date_stamp(x)
                        )

                        # 保存数据
                        result = collections.insert_many(util_to_json_from_pandas(data))
                        inserted_count = len(result.inserted_ids)
                        total_inserted += inserted_count
                        logger.info(f"合约 {symbol} 新增 {inserted_count} 条日线数据")

                    except Exception as e:
                        logger.error(f"处理合约 {symbol} 数据时出错: {str(e)}")
                        continue

            except Exception as e:
                logger.error(f"处理交易所 {exchange} 数据时出错: {str(e)}")
                continue

        logger.info(f"期货日线数据保存完成，总共新增 {total_inserted} 条数据")

    def standardize_future_daily_data(self, df: pd.DataFrame, source: str = 'gm') -> pd.DataFrame:
        """
        Standardize futures daily data format from different sources.

        Args:
            df: DataFrame containing futures daily data
            source: Data source ('gm' or 'tushare')

        Returns:
            Standardized DataFrame with columns:
            - symbol: Contract symbol with exchange prefix in uppercase (e.g., SHFE.RB2011)
            - trade_date: Trading date in YYYY-MM-DD format
            - open: Opening price
            - high: Highest price
            - low: Lowest price
            - close: Closing price
            - volume: Trading volume
            - amount: Trading amount
            - datestamp: Date timestamp
        """
        result = df.copy()

        if source.lower() == 'tushare':
            # Rename volume column
            # if 'vol' in result.columns:
            #     result = result.rename(columns={'vol': 'volume'})

            # Convert ts_code to symbol with exchange prefix in uppercase
            if 'ts_code' in result.columns:
                result['symbol'] = result['ts_code'].apply(
                    lambda x: (x.split('.')[1] + '.' + x.split('.')[0]).upper()
                )
                result = result.drop('ts_code', axis=1)
                logger.debug("Converted Tushare ts_code to uppercase symbol format")

            # Format trade_date
            if 'trade_date' in result.columns and not isinstance(result['trade_date'].iloc[0], str):
                result['trade_date'] = pd.to_datetime(result['trade_date'].astype(str)).dt.strftime('%Y-%m-%d')

        elif source.lower() == 'gm':
            # Convert GoldMiner symbol to uppercase
            if 'symbol' in result.columns:
                result['symbol'] = result['symbol'].str.upper()
                logger.debug("Converted GoldMiner symbol to uppercase format")

            # Add datestamp if not present
            if 'datestamp' not in result.columns and 'trade_date' in result.columns:
                result['datestamp'] = result['trade_date'].apply(lambda x: pd.Timestamp(x).timestamp())

        # Ensure consistent column order
        desired_columns = ['symbol', 'exchange', 'trade_date', 'pre_close', 'pre_settle', 'open', 'high', 'low', 'close', 'settle', 'change1', 'change2', 'vol', 'amount', 'oi', 'oi_chg']
        available_columns = [col for col in desired_columns if col in result.columns]
        result = result[available_columns]

        return result


    def _save_operation_log(self, operation, result):
        """保存操作日志。

        Args:
            operation (str): 操作名称
            result (SaveResult): 操作结果
        """
        try:
            log_data = {
                "operation": operation,
                "timestamp": datetime.datetime.now(),
                **result.to_dict()
            }
            self.client.operation_logs.insert_one(log_data)
        except Exception as e:
            logger.error(f"保存操作日志失败: {str(e)}")

    def _create_save_checkpoint(self, collections, operation):
        """创建保存检查点。

        Args:
            collections: MongoDB 集合对象
            operation (str): 操作名称

        Returns:
            str: 检查点 ID
        """
        try:
            checkpoint = {
                "operation": operation,
                "timestamp": datetime.datetime.now(),
                "status": "started"
            }
            result = self.client.save_checkpoints.insert_one(checkpoint)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"创建检查点失败: {str(e)}")
            raise

    def _update_save_checkpoint(self, checkpoint_id, status, result=None):
        """更新保存检查点。

        Args:
            checkpoint_id (str): 检查点 ID
            status (str): 状态
            result (SaveResult, optional): 操作结果
        """
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.datetime.now()
            }
            if result:
                update_data["result"] = result.to_dict()

            self.client.save_checkpoints.update_one(
                {"_id": ObjectId(checkpoint_id)},
                {"$set": update_data}
            )
        except Exception as e:
            logger.error(f"更新检查点失败: {str(e)}")


if __name__ == "__main__":
    saver = MarketDataSaver()
    # saver.save_trade_dates()
    saver.save_future_contracts()
    # saver.save_future_holdings(exchanges=["DCE"])
    # saver.save_future_holdings(engine="gm")
    # saver.save_stock_list()
    # saver.save_future_daily()
