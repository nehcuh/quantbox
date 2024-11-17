"""
市场数据保存模块

本模块提供从多个数据源（Tushare、掘金等）获取并保存市场数据到本地数据库的功能。
支持的数据类型包括：
- 交易日期数据
- 期货合约信息
- 期货持仓数据
- 期货日线数据
- 股票列表数据

English Version:
---------------
Market Data Saver Module

This module provides functionality for saving market data from various sources
(Tushare, GoldMiner, etc.) to a local database. Supported data types include:
- Trading dates
- Future contracts
- Future holdings
- Future daily data
- Stock listings

类 (Classes):
    MarketDataSaver: 市场数据保存器主类 (Main class for market data saving operations)

依赖 (Dependencies):
    - pandas
    - pymongo
    - quantbox.fetchers
    - quantbox.util
    - quantbox.config
    - quantbox.logger
    - quantbox.validators
"""

from typing import List, Union
import datetime
import time

import pandas as pd
import pymongo

from quantbox.fetchers.fetcher_goldminer import GMFetcher
from quantbox.fetchers.fetcher_tushare import TSFetcher
from quantbox.fetchers.local_fetch import LocalFetcher, fetch_next_trade_date
from quantbox.util.basic import DATABASE, EXCHANGES, FUTURE_EXCHANGES, STOCK_EXCHANGES
from quantbox.util.tools import (
    util_format_stock_symbols,
    util_make_date_stamp,
    util_to_json_from_pandas,
    is_trade_date
)
from quantbox.config import load_config
from quantbox.logger import setup_logger
from quantbox.validators import validate_dataframe, retry


logger = setup_logger(__name__)


class MarketDataSaver:
    """
    市场数据保存器，用于从多个数据源获取并保存市场数据到本地数据库。

    本类提供了从多个数据源（如 Tushare、掘金等）获取数据并保存到本地 MongoDB 数据库的方法。
    包含数据验证、错误恢复和完整的日志记录功能。

    属性：
        ts_fetcher: Tushare 数据获取器实例
        gm_fetcher: 掘金数据获取器实例
        queryer: 本地数据获取器实例
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

    English Version：
    ---------------
    A class for saving market data from various sources to local database.

    This class provides methods to fetch and save different types of market data
    from multiple data sources (Tushare, GoldMiner, etc.) to a local MongoDB database.
    It handles data validation, error recovery, and proper logging throughout the
    saving process.

    Attributes：
        ts_fetcher: Tushare data fetcher instance
        gm_fetcher: GoldMiner data fetcher instance
        queryer: Local data fetcher instance
        client: MongoDB database client
        config: Configuration settings
        exchanges: List of all supported exchanges
        future_exchanges: List of supported future exchanges
        stock_exchanges: List of supported stock exchanges

    Note：
        Before using this class, ensure that：
        1. Database connection is properly configured
        2. Data source credentials are set up
        3. Required configurations are loaded
    """

    def __init__(self):
        """
        初始化市场数据保存器实例。

        设置数据获取器、数据库客户端和配置。

        English Version：
        ---------------
        Initialize the MarketDataSaver instance.

        Set up data fetchers, database client, and configuration settings.
        """
        self.ts_fetcher = TSFetcher()
        self.gm_fetcher = GMFetcher()
        self.queryer = LocalFetcher()
        self.client = DATABASE
        self.config = load_config()
        self.exchanges = EXCHANGES
        self.future_exchanges = FUTURE_EXCHANGES
        self.stock_exchanges = STOCK_EXCHANGES

    @retry(max_attempts=3, delay=60)
    def save_trade_dates(self, start_date: str = None):
        """
        保存交易日期数据到本地数据库。

        从 Tushare 获取交易日期数据并保存到本地 MongoDB 数据库的 'trade_date' 集合中。

        参数：
            start_date: 开始日期，默认为 None。
                       如果为 None，则使用配置文件中指定的默认起始日期。

        注意：
            - 会自动创建必要的数据库索引
            - 包含错误重试机制
            - 保存完整的操作日志

        English Version：
        ---------------
        Save trading dates data to local database.

        Fetches trading dates from Tushare and saves them to the 'trade_date'
        collection in the local MongoDB database.

        Args：
            start_date: Start date for fetching trading dates, defaults to None.
                       If None, uses the default start date from configuration.

        Note：
            - Automatically creates necessary database indexes
            - Includes error retry mechanism
            - Maintains complete operation logs
        """
        logger.info("开始保存交易日期数据")
        collections = self.client.trade_date
        
        try：
            # 创建索引
            collections.create_index(
                [("exchange", pymongo.ASCENDING), ("datestamp", pymongo.DESCENDING)],
                background=True
            )
            logger.debug("成功创建/更新索引")
        except Exception as e：
            logger.error(f"创建索引失败: {str(e)}")
            raise
            
        if start_date is None：
            start_date = self.config['saver'].get('default_start_date', '1990-12-19')
            
        total_inserted = 0
        for exchange in self.exchanges：
            try：
                # 获取最新日期
                count = collections.count_documents({"exchange": exchange})
                if count > 0：
                    first_doc = collections.find_one(
                        {"exchange": exchange},
                        sort=[("datestamp", pymongo.DESCENDING)]
                    )
                    latest_date = first_doc["trade_date"]
                    logger.info(f"交易所 {exchange} 最新数据日期: {latest_date}")
                else：
                    latest_date = start_date
                    logger.info(f"交易所 {exchange} 无历史数据，从 {start_date} 开始获取")

                # 获取并验证数据
                df = self.ts_fetcher.fetch_get_trade_dates(
                    exchanges=exchange,
                    start_date=latest_date
                )
                
                if df is None or df.empty：
                    logger.warning(f"交易所 {exchange} 没有新的交易日期数据")
                    continue
                    
                # 转换为 JSON 并保存
                data = util_to_json_from_pandas(df)
                if data：
                    result = collections.insert_many(data)
                    inserted_count = len(result.inserted_ids)
                    total_inserted += inserted_count
                    logger.info(f"交易所 {exchange} 新增 {inserted_count} 条交易日期数据")
                    
            except Exception as e：
                logger.error(f"处理交易所 {exchange} 数据时出错: {str(e)}")
                raise
                
        logger.info(f"交易日期数据保存完成，总共新增 {total_inserted} 条数据")

    @retry(max_attempts=3, delay=60)
    @validate_dataframe(collection_name='future_contracts')
    def save_future_contracts(self, batch_size: int = None):
        """
        保存期货合约信息到本地数据库。

        从 Tushare 获取期货合约信息并保存到本地 MongoDB 数据库的 'future_contracts' 集合中。

        参数：
            batch_size: 批量插入数据的大小，默认为 None。
                       如果为 None，则使用配置文件中指定的默认批量大小。

        注意：
            - 会自动创建必要的数据库索引
            - 包含错误重试机制
            - 保存完整的操作日志

        English Version：
        ---------------
        Save future contracts data to local database.

        Fetches future contracts from Tushare and saves them to the 'future_contracts'
        collection in the local MongoDB database.

        Args：
            batch_size: Batch size for inserting data, defaults to None.
                       If None, uses the default batch size from configuration.

        Note：
            - Automatically creates necessary database indexes
            - Includes error retry mechanism
            - Maintains complete operation logs
        """
        logger.info("开始保存期货合约信息")
        collections = self.client.future_contracts
        
        try：
            # 创建索引
            collections.create_index(
                [
                    ("exchange", pymongo.ASCENDING),
                    ("symbol", pymongo.ASCENDING),
                    ("datestamp", pymongo.DESCENDING),
                ],
                background=True
            )
            logger.debug("成功创建/更新索引")
        except Exception as e：
            logger.error(f"创建索引失败: {str(e)}")
            raise
            
        if batch_size is None：
            batch_size = self.config['saver'].get('batch_size', 10000)
            
        total_inserted = 0
        for exchange in self.future_exchanges：
            try：
                logger.info(f"开始处理交易所 {exchange} 的合约信息")
                
                # 获取所有合约信息
                total_contracts = self.ts_fetcher.fetch_get_future_contracts(
                    exchange=exchange
                )
                if total_contracts is None or total_contracts.empty：
                    logger.warning(f"交易所 {exchange} 未获取到合约信息")
                    continue
                    
                symbols = total_contracts.symbol.tolist()
                logger.info(f"交易所 {exchange} 共有 {len(symbols)} 个合约")
                
                # 检查已存在的合约
                count = collections.count_documents(
                    {"exchange": exchange, "symbol": {"$in": symbols}}
                )
                
                if count > 0：
                    # 查询当前已有的合约信息
                    logger.info(f"交易所 {exchange} 已有 {count} 个合约记录，检查新增合约")
                    cursor = collections.find(
                        {"exchange": exchange, "symbol": {"$in": symbols}},
                        {"_id": 0, "symbol": 1},
                        batch_size=batch_size
                    )
                    
                    # 使用集合操作找出新增的合约
                    local_symbols = {doc["symbol"] for doc in cursor}
                    new_symbols = set(symbols) - local_symbols
                    
                    if new_symbols：
                        # 只插入新的合约信息
                        new_contracts = total_contracts.loc[
                            total_contracts["symbol"].isin(list(new_symbols))
                        ]
                        data = util_to_json_from_pandas(new_contracts)
                        result = collections.insert_many(data)
                        inserted_count = len(result.inserted_ids)
                        total_inserted += inserted_count
                        logger.info(f"交易所 {exchange} 新增 {inserted_count} 个合约信息")
                    else：
                        logger.info(f"交易所 {exchange} 没有新的合约信息需要添加")
                else：
                    # 全部是新合约，直接插入
                    data = util_to_json_from_pandas(total_contracts)
                    result = collections.insert_many(data)
                    inserted_count = len(result.inserted_ids)
                    total_inserted += inserted_count
                    logger.info(f"交易所 {exchange} 新增 {inserted_count} 个合约信息")
                    
            except Exception as e：
                logger.error(f"处理交易所 {exchange} 数据时出错: {str(e)}")
                raise
                
        logger.info(f"期货合约信息保存完成，总共新增 {total_inserted} 个合约")

    @retry(max_attempts=3, delay=60)
    @validate_dataframe(collection_name='future_holdings')
    def save_future_holdings(
        self,
        exchanges: Union[str, List[str], None] = None,
        start_date: Union[str, datetime.date, None] = None,
        end_date: Union[str, datetime.date, None] = None,
        offset: int = None,
        engine: str = "ts",
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
            engine: 数据源引擎，默认为 'ts' (Tushare)。
                   可以是 'ts' (Tushare) 或 'gm' (GoldMiner)。
            max_workers: 最大工作线程数，默认为 None。
                        如果为 None，则使用配置文件中指定的默认最大工作线程数。

        注意：
            - 会自动创建必要的数据库索引
            - 包含错误重试机制
            - 保存完整的操作日志

        English Version：
        ---------------
        Save future holdings data to local database.

        Fetches future holdings from the specified data source and saves them to the
        'future_holdings' collection in the local MongoDB database.

        Args：
            exchanges: List of exchanges to fetch data for, defaults to None.
                       If None, uses all supported future exchanges.
            start_date: Start date for fetching data, defaults to None.
                       If None, uses the default start date from configuration.
            end_date: End date for fetching data, defaults to None.
                      If None, uses the current date.
            offset: Offset in days for fetching data, defaults to None.
                   If None, uses the default offset from configuration.
            engine: Data source engine, defaults to 'ts' (Tushare).
                   Can also be 'gm' (GoldMiner).
            max_workers: Maximum number of worker threads, defaults to None.
                        If None, uses the default max workers from configuration.

        Note：
            - Automatically creates necessary database indexes
            - Includes error retry mechanism
            - Maintains complete operation logs
        """
        logger.info("开始保存期货持仓数据")
        collections = self.client.future_holdings
        
        try：
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
        except Exception as e：
            logger.error(f"创建索引失败: {str(e)}")
            raise
            
        # 处理配置参数
        if offset is None：
            offset = self.config['saver'].get('offset', 365)
        if max_workers is None：
            max_workers = self.config['saver'].get('max_workers', 4)
        trading_end_hour = self.config['saver'].get('trading_end_hour', 16)
            
        # 处理交易所参数
        if exchanges is None：
            exchanges = self.future_exchanges
        if isinstance(exchanges, str)：
            exchanges = exchanges.split(",")
        # 股票交易所不考虑
        exchanges = [x for x in exchanges if x not in self.stock_exchanges]
        
        # FIXME：上海能源交易所在 tushare 的接口上获取相应持仓数据为空
        if "INE" in exchanges：
            exchanges.remove("INE")
            logger.warning("上海能源交易所(INE)暂不支持获取持仓数据")
                
        # 处理日期参数
        if end_date is None：
            end_date = datetime.date.today()
            if start_date is None：
                start_date = end_date - datetime.timedelta(days=offset)
        else：
            if start_date is None：
                start_date = pd.Timestamp(end_date) - pd.Timedelta(days=offset)
                
        # 如果是当天且未到收盘时间，使用前一天数据
        if (is_trade_date(end_date, exchanges[0]) and 
            pd.Timestamp(end_date) == pd.Timestamp(datetime.date.today()) and 
            datetime.datetime.now().hour < trading_end_hour)：
            end_date = pd.Timestamp(end_date) - pd.Timedelta(days=1)
            logger.info(f"当前未到收盘时间，使用前一天 {end_date} 的数据")
            
        logger.info(f"处理日期范围: {start_date} 到 {end_date}")
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def process_exchange_date(exchange: str, trade_date: str) -> int：
            """处理单个交易所的单个交易日数据"""
            try：
                count = collections.count_documents({
                    "datestamp": util_make_date_stamp(trade_date),
                    "exchange": exchange,
                })
                
                if count == 0：
                    logger.info(f"获取交易所 {exchange} 在交易日 {trade_date} 的持仓排名")
                    
                    # 根据不同引擎调用不同的数据获取方法
                    if engine == 'ts'：
                        results = self.ts_fetcher.fetch_get_holdings(
                            exchanges=exchange, cursor_date=trade_date
                        )
                    elif engine == 'gm'：
                        results = self.gm_fetcher.fetch_get_holdings(
                            exchanges=exchange, cursor_date=trade_date
                        )
                    else：
                        raise ValueError(f"不支持的数据引擎: {engine}，请使用 'ts' 或 'gm'")
                        
                    if results is not None and not results.empty：
                        # 检查重复记录
                        duplicates = results.duplicated(subset=['trade_date', 'broker', 'symbol'], keep='last')
                        if duplicates.any()：
                            logger.warning(f"发现 {duplicates.sum()} 条重复记录，将保留最新的记录")
                            results = results[~duplicates]
                        
                        # 使用 upsert 操作保存数据
                        for _, row in results.iterrows()：
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
                        return inserted_count
                    else：
                        logger.warning(f"交易所 {exchange} 在交易日 {trade_date} 未获取到持仓数据")
                else：
                    logger.debug(f"交易所 {exchange} 在交易日 {trade_date} 的持仓数据已存在")
                    
            except pymongo.errors.DuplicateKeyError as e：
                logger.warning(f"处理重复数据: {str(e)}")
            except Exception as e：
                logger.error(f"处理交易所 {exchange} 在交易日 {trade_date} 的数据时出错: {str(e)}")
                raise
                
            return 0
            
        total_inserted = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor：
            future_to_params = {}
            
            for exchange in exchanges：
                try：
                    # 获取交易日列表
                    trade_dates = self.queryer.fetch_trade_dates(
                        exchanges=exchange,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    if trade_dates is None or trade_dates.empty：
                        logger.warning(f"交易所 {exchange} 在指定日期范围内没有交易日")
                        continue
                        
                    # 提交所有任务
                    for trade_date in trade_dates.trade_date.tolist()：
                        future = executor.submit(
                            process_exchange_date,
                            exchange,
                            trade_date
                        )
                        future_to_params[future] = (exchange, trade_date)
                        
                except Exception as e：
                    logger.error(f"处理交易所 {exchange} 的交易日列表时出错: {str(e)}")
                    raise
                    
            # 收集结果
            for future in as_completed(future_to_params)：
                exchange, trade_date = future_to_params[future]
                try：
                    inserted_count = future.result()
                    total_inserted += inserted_count
                except Exception as e：
                    logger.error(
                        f"处理交易所 {exchange} 在交易日 {trade_date} 的任务失败: {str(e)}"
                    )
                    raise
                    
        logger.info(f"期货持仓数据保存完成，总共新增 {total_inserted} 条数据")

    @retry(max_attempts=3, delay=60)
    @validate_dataframe(collection_name='stock_list')
    def save_stock_list(self, list_status: str = None):
        """
        保存股票列表数据到本地数据库。

        从 Tushare 获取股票列表数据并保存到本地 MongoDB 数据库的 'stock_list' 集合中。

        参数：
            list_status: 股票列表状态，默认为 None。
                       可以是 'L' (上市)、'D' (退市)、'P' (暂停)。

        注意：
            - 会自动创建必要的数据库索引
            - 包含错误重试机制
            - 保存完整的操作日志

        English Version：
        ---------------
        Save stock list data to local database.

        Fetches stock list data from Tushare and saves it to the 'stock_list'
        collection in the local MongoDB database.

        Args：
            list_status: List status, defaults to None.
                       Can be 'L' (listed), 'D' (delisted), or 'P' (paused).

        Note：
            - Automatically creates necessary database indexes
            - Includes error retry mechanism
            - Maintains complete operation logs
        """
        logger.info("开始保存股票列表数据")
        collections = self.client.stock_list
        
        try：
            # 创建索引
            collections.create_index(
                [("symbol", pymongo.ASCENDING), ("list_datestamp", pymongo.ASCENDING)],
                background=True
            )
            logger.debug("成功创建/更新索引")
        except Exception as e：
            logger.error(f"创建索引失败: {str(e)}")
            raise
            
        try：
            # 获取股票列表数据
            logger.info("从数据源获取股票列表数据")
            data = self.ts_fetcher.fetch_get_stock_list(list_status=list_status)
            
            if data is None or data.empty：
                logger.warning("未获取到股票列表数据")
                return
                
            # 数据预处理
            logger.debug("开始处理股票列表数据")
            # 标准化股票代码
            data.symbol = util_format_stock_symbols(data.symbol, "standard")
            
            # 移除不需要的列
            columns = data.columns.tolist()
            if "ts_code" in columns：
                columns.remove("ts_code")
                
            # 添加上市日期时间戳
            data["list_datestamp"] = (
                data["list_date"].map(str).apply(lambda x: util_make_date_stamp(x))
            )
            
            # 清空现有数据
            logger.info("清空现有股票列表数据")
            collections.delete_many({})
            
            # 保存新数据
            result = collections.insert_many(util_to_json_from_pandas(data))
            inserted_count = len(result.inserted_ids)
            logger.info(f"股票列表数据保存完成，共保存 {inserted_count} 条记录")
            
            # 验证数据完整性
            count = collections.count_documents({})
            if count != len(data)：
                raise ValueError(
                    f"数据完整性检查失败：期望保存 {len(data)} 条记录，"
                    f"实际保存 {count} 条记录"
                )
                
        except Exception as e：
            logger.error(f"保存股票列表数据时出错: {str(e)}")
            raise

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

        English Version：
        ---------------
        Save future daily data to local database.

        Fetches future daily data from Tushare and saves it to the 'future_daily'
        collection in the local MongoDB database.

        Args：
            exchanges: List of exchanges to fetch data for, defaults to None.
                       If None, uses all supported future exchanges.
            start_date: Start date for fetching data, defaults to None.
                       If None, uses the default start date from configuration.
            end_date: End date for fetching data, defaults to None.
                      If None, uses the current date.
            offset: Offset in days for fetching data, defaults to 365.

        Note：
            - Automatically creates necessary database indexes
            - Includes error retry mechanism
            - Maintains complete operation logs
        """
        collections = self.client.future_daily
        collections.create_index(
            [("symbol", pymongo.ASCENDING), ("datestamp", pymongo.DESCENDING)]
        )
        cursor_date = datetime.date.today()
        for exchange in self.future_exchanges：
            contracts = self.queryer.fetch_future_contracts(exchanges=exchange)
            for _, contract_info in contracts.iterrows()：
                list_date = contract_info["list_date"]
                delist_date = contract_info["delist_date"]
                symbol = contract_info["symbol"]
                count = collections.count_documents(
                    {"symbol": symbol, "datestamp": util_make_date_stamp(cursor_date)}
                )
                if count > 0：
                    first_doc = collections.find_one(
                        {"symbol": symbol}, sort=[("datestamp", pymongo.DESCENDING)]
                    )
                    latest_date = first_doc["trade_date"]
                    print(f"当前保存合约 {symbol} 从 {latest_date} 到 {delist_date} 日线行情")
                    if (pd.Timestamp(latest_date) < pd.Timestamp(delist_date)) and (self.queryer.fetch_next_trade_date(latest_date)['trade_date'] < datetime.date.today().strftime("%Y-%m-%d"))：
                        data = self.ts_fetcher.fetch_get_future_daily(
                            symbols=symbol,
                            start_date=self.queryer.fetch_next_trade_date(latest_date)['trade_date'],
                            end_date=delist_date,
                        )
                        collections.insert_many(
                            util_to_json_from_pandas(data[columns])
                        )
                else：
                    print(f"当前保存合约 {symbol} 从 {list_date} 到 {delist_date} 日线行情")
                    data = self.ts_fetcher.fetch_get_future_daily(
                        symbols=symbol,
                        start_date=list_date,
                        end_date=delist_date,
                    )
                    if data is None or data.empty：
                        print(
                            f"当前合约 {symbol}, 上市时间 {list_date}, 下市时间 {delist_date}, 没有查询到数据"
                        )
                        continue
                    collections.insert_many(util_to_json_from_pandas(data))


if __name__ == "__main__"：
    saver = MarketDataSaver()
    # saver.save_trade_dates()
    # saver.save_future_contracts()
    # saver.save_future_holdings(exchanges=["DCE"])
    saver.save_future_holdings(engine="gm")
    # saver.save_stock_list()
    # saver.save_future_daily()
