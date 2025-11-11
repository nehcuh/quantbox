"""
DataSaverService - 统一的数据保存服务

提供统一的数据保存接口，从远程数据源获取数据并保存到本地
"""

from typing import Optional, Union, List
import datetime
import pandas as pd
import pymongo

from quantbox.adapters.base import BaseDataAdapter
from quantbox.adapters.local_adapter import LocalAdapter
from quantbox.adapters.ts_adapter import TSAdapter
from quantbox.util.date_utils import DateLike, date_to_int, util_make_date_stamp
from quantbox.util.exchange_utils import FUTURES_EXCHANGES, STOCK_EXCHANGES, ALL_EXCHANGES
from quantbox.config.config_loader import get_config_loader


class SaveResult:
    """
    保存操作结果类

    用于跟踪数据保存操作的统计信息
    """

    def __init__(self):
        self.success = True
        self.inserted_count = 0
        self.modified_count = 0
        self.error_count = 0
        self.errors = []
        self.start_time = datetime.datetime.now()
        self.end_time = None

    def add_error(self, error_type: str, error_msg: str, data=None):
        """添加错误信息"""
        self.success = False
        self.error_count += 1
        self.errors.append({
            "type": error_type,
            "message": error_msg,
            "data": data,
            "timestamp": datetime.datetime.now()
        })

    def complete(self):
        """完成操作，记录结束时间"""
        self.end_time = datetime.datetime.now()

    @property
    def duration(self):
        """获取操作持续时间"""
        if self.end_time:
            return self.end_time - self.start_time
        return datetime.datetime.now() - self.start_time

    def to_dict(self):
        """转换为字典格式"""
        return {
            "success": self.success,
            "inserted_count": self.inserted_count,
            "modified_count": self.modified_count,
            "error_count": self.error_count,
            "errors": self.errors,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": str(self.duration)
        }


class DataSaverService:
    """
    数据保存服务

    统一的数据保存接口，支持：
    - 从远程数据源获取数据
    - 数据验证和清洗
    - 批量保存到本地数据库
    - 增量更新和去重
    """

    def __init__(
        self,
        remote_adapter: Optional[BaseDataAdapter] = None,
        local_adapter: Optional[LocalAdapter] = None,
        database=None,
        show_progress: bool = False
    ):
        """
        初始化数据保存服务

        Args:
            remote_adapter: 远程数据适配器，默认使用 TSAdapter
            local_adapter: 本地数据适配器，默认使用 LocalAdapter
            database: MongoDB 数据库实例，默认使用全局 DATABASE
            show_progress: 是否显示进度条，默认 False
        """
        self.remote_adapter = remote_adapter or TSAdapter()
        self.local_adapter = local_adapter or LocalAdapter()
        self.database = database or get_config_loader().get_mongodb_client().quantbox
        self.show_progress = show_progress

    def _create_index(self, collection, index_keys, unique=False):
        """
        创建索引

        Args:
            collection: MongoDB 集合
            index_keys: 索引键列表
            unique: 是否唯一索引
        """
        try:
            collection.create_index(
                index_keys,
                unique=unique,
                background=True
            )
        except pymongo.errors.DuplicateKeyError:
            pass
        except Exception as e:
            print(f"创建索引失败: {str(e)}")

    def _bulk_upsert(self, collection, data: List[dict], key_fields: List[str]) -> dict:
        """
        批量更新或插入数据

        Args:
            collection: MongoDB 集合
            data: 数据列表
            key_fields: 唯一键字段列表

        Returns:
            结果字典，包含 upserted_count 和 modified_count
        """
        if not data:
            return {"upserted_count": 0, "modified_count": 0}

        operations = []
        for doc in data:
            # 构建查询条件
            query = {field: doc[field] for field in key_fields if field in doc}
            operations.append(
                pymongo.UpdateOne(
                    query,
                    {"$set": doc},
                    upsert=True
                )
            )

        result = collection.bulk_write(operations)
        return {
            "upserted_count": result.upserted_count,
            "modified_count": result.modified_count
        }

    def save_trade_calendar(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None
    ) -> SaveResult:
        """
        保存交易日历数据

        Args:
            exchanges: 交易所代码或列表，默认 None（使用所有交易所）
            start_date: 起始日期，默认 None（使用今年年初）
            end_date: 结束日期，默认 None（使用今天）

        智能默认行为：
            - 如果 exchanges 为 None，使用所有交易所
            - 如果 start_date 为 None，使用今年年初
            - 如果 end_date 为 None，使用今天

        Returns:
            SaveResult: 保存结果
        """
        result = SaveResult()

        try:
            # 智能默认
            if exchanges is None:
                exchanges = ALL_EXCHANGES

            if start_date is None:
                # 默认从今年年初开始
                start_date = datetime.datetime(datetime.datetime.today().year, 1, 1).strftime("%Y%m%d")

            if end_date is None:
                # 默认到今天
                end_date = datetime.datetime.today().strftime("%Y%m%d")

            # 从远程获取数据
            df = self.remote_adapter.get_trade_calendar(
                exchanges=exchanges,
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                result.add_error("NO_DATA", "未获取到交易日历数据")
                result.complete()
                return result

            # 优化数据结构：去掉 is_open，增加 datestamp
            # 我们只保存交易日，因此 is_open 肯定为 True，没必要存储
            if "is_open" in df.columns:
                df = df.drop(columns=["is_open"])

            # 增加 datestamp 字段用于快速日期比较
            if "datestamp" not in df.columns:
                df["datestamp"] = df["date"].apply(util_make_date_stamp)

            # 转换为字典列表
            data = df.to_dict('records')

            # 创建索引
            collection = self.database.trade_date
            # 唯一索引：交易所 + 日期
            self._create_index(
                collection,
                [("exchange", pymongo.ASCENDING), ("date", pymongo.ASCENDING)],
                unique=True
            )
            # datestamp 索引：用于快速日期范围查询
            self._create_index(
                collection,
                [("exchange", pymongo.ASCENDING), ("datestamp", pymongo.ASCENDING)],
                unique=False
            )

            # 批量保存
            save_result = self._bulk_upsert(
                collection,
                data,
                ["exchange", "date"]
            )

            result.inserted_count = save_result["upserted_count"]
            result.modified_count = save_result["modified_count"]
            result.complete()

        except Exception as e:
            result.add_error("SAVE_ERROR", f"保存交易日历失败: {str(e)}")
            result.complete()

        return result

    def save_future_contracts(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        symbols: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        date: Optional[DateLike] = None
    ) -> SaveResult:
        """
        保存期货合约信息

        Args:
            exchanges: 交易所代码或列表，默认 None（使用所有期货交易所）
            symbols: 合约代码或列表
            spec_names: 品种名称或列表
            date: 查询日期

        智能默认行为：
            - 如果所有参数都为 None，使用所有期货交易所

        Returns:
            SaveResult: 保存结果
        """
        result = SaveResult()

        try:
            # 智能默认：如果没有指定任何参数，使用所有期货交易所
            if all(x is None for x in [exchanges, symbols, spec_names, date]):
                exchanges = FUTURES_EXCHANGES

            # 从远程获取数据
            df = self.remote_adapter.get_future_contracts(
                exchanges=exchanges,
                symbols=symbols,
                spec_names=spec_names,
                date=date
            )

            if df.empty:
                result.add_error("NO_DATA", "未获取到期货合约数据")
                result.complete()
                return result

            # 转换为字典列表
            data = df.to_dict('records')

            # 创建索引
            collection = self.database.future_contracts
            self._create_index(
                collection,
                [("symbol", pymongo.ASCENDING), ("exchange", pymongo.ASCENDING)],
                unique=True
            )

            # 批量保存
            save_result = self._bulk_upsert(
                collection,
                data,
                ["symbol", "exchange"]
            )

            result.inserted_count = save_result["upserted_count"]
            result.modified_count = save_result["modified_count"]
            result.complete()

        except Exception as e:
            result.add_error("SAVE_ERROR", f"保存期货合约失败: {str(e)}")
            result.complete()

        return result

    def save_future_daily(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None
    ) -> SaveResult:
        """
        保存期货日线数据

        Args:
            symbols: 合约代码或列表，默认 None（获取所有合约）
            exchanges: 交易所代码或列表，默认 None（使用所有期货交易所）
            start_date: 起始日期，默认 None（从 1990-01-01 开始）
            end_date: 结束日期，默认 None（到今天）
            date: 单日查询日期，默认 None

        智能默认行为：
            - 如果所有参数都为 None，默认保存从 1990-01-01 到今天所有期货交易所的历史数据
            - 这样可以一次性获取完整的历史行情数据

        Returns:
            SaveResult: 保存结果
        """
        result = SaveResult()

        try:
            # 智能默认：如果没有指定任何参数，默认保存历史所有数据
            if all(x is None for x in [symbols, exchanges, start_date, end_date, date]):
                start_date = "1990-01-01"  # 从 1990 年开始
                end_date = datetime.datetime.today().strftime("%Y%m%d")
                exchanges = FUTURES_EXCHANGES  # 默认使用所有期货交易所

            # 从远程获取数据
            df = self.remote_adapter.get_future_daily(
                symbols=symbols,
                exchanges=exchanges,
                start_date=start_date,
                end_date=end_date,
                date=date,
                show_progress=self.show_progress
            )

            if df.empty:
                result.add_error("NO_DATA", "未获取到期货日线数据")
                result.complete()
                return result

            # 转换为字典列表
            data = df.to_dict('records')

            # 创建索引
            collection = self.database.future_daily
            self._create_index(
                collection,
                [("symbol", pymongo.ASCENDING), ("exchange", pymongo.ASCENDING), ("date", pymongo.ASCENDING)],
                unique=True
            )
            self._create_index(
                collection,
                [("date", pymongo.DESCENDING)]
            )

            # 批量保存
            save_result = self._bulk_upsert(
                collection,
                data,
                ["symbol", "exchange", "date"]
            )

            result.inserted_count = save_result["upserted_count"]
            result.modified_count = save_result["modified_count"]
            result.complete()

        except Exception as e:
            result.add_error("SAVE_ERROR", f"保存期货日线失败: {str(e)}")
            result.complete()

        return result

    def save_future_minute(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
        freq: str = "1min"
    ) -> SaveResult:
        """
        保存期货分钟线数据

        Args:
            symbols: 合约代码或列表（如 "SHFE.rb2501"）
            exchanges: 交易所代码或列表（如 "SHFE", "DCE"）
            start_date: 起始日期（默认最近一周）
            end_date: 结束日期（默认今天）
            date: 单日查询日期（与 start_date/end_date 互斥）
            freq: 分钟频率，支持 "1min", "5min", "15min", "30min", "60min"（默认 "1min"）

        智能默认行为：
            - 如果没有指定日期，默认保存最近一周的数据（避免数据量过大）
            - 必须指定 symbols 或 exchanges

        注意:
            - 分钟数据量很大，建议使用 5min 或更长周期
            - 建议指定具体合约或较短的日期范围
            - Tushare 分钟数据接口有调用限制

        Returns:
            SaveResult: 保存结果
        """
        result = SaveResult()

        try:
            # 验证必须指定合约或交易所
            if not symbols and not exchanges:
                raise ValueError("必须指定 symbols 或 exchanges 参数")

            # 智能默认：如果没有指定日期，默认保存最近一周的数据
            if all(x is None for x in [start_date, end_date, date]):
                # 默认最近一周（避免数据量过大）
                end_date = datetime.datetime.today()
                start_date = end_date - datetime.timedelta(days=7)
                start_date = start_date.strftime("%Y%m%d")
                end_date = end_date.strftime("%Y%m%d")

            # 从远程获取数据
            df = self.remote_adapter.get_future_minute(
                symbols=symbols,
                exchanges=exchanges,
                start_date=start_date,
                end_date=end_date,
                date=date,
                freq=freq,
                show_progress=self.show_progress
            )

            if df.empty:
                result.add_error("NO_DATA", "未获取到期货分钟数据")
                result.complete()
                return result

            # 转换为字典列表
            data = df.to_dict('records')

            # 创建索引
            collection = self.database.future_minute
            # 唯一索引：合约 + 交易所 + 时间戳
            self._create_index(
                collection,
                [("symbol", pymongo.ASCENDING), ("exchange", pymongo.ASCENDING), ("datetime", pymongo.ASCENDING)],
                unique=True
            )
            # 时间索引
            self._create_index(
                collection,
                [("datetime", pymongo.DESCENDING)]
            )
            # 日期索引（用于按日期查询）
            self._create_index(
                collection,
                [("date", pymongo.DESCENDING)]
            )

            # 批量保存
            save_result = self._bulk_upsert(
                collection,
                data,
                ["symbol", "exchange", "datetime"]
            )

            result.inserted_count = save_result["upserted_count"]
            result.modified_count = save_result["modified_count"]
            result.complete()

        except Exception as e:
            result.add_error("SAVE_ERROR", f"保存期货分钟数据失败: {str(e)}")
            result.complete()

        return result

    def save_future_holdings(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None
    ) -> SaveResult:
        """
        保存期货持仓数据

        Args:
            symbols: 合约代码或列表
            exchanges: 交易所代码或列表，默认 None（使用所有期货交易所）
            spec_names: 品种名称或列表
            start_date: 起始日期，默认 None（从 1990-01-01 开始）
            end_date: 结束日期，默认 None（到今天）
            date: 单日查询日期，默认 None

        智能默认行为：
            - 如果所有参数都为 None，默认保存从 1990-01-01 到今天所有期货交易所的历史持仓数据
            - 这样可以一次性获取完整的持仓历史数据，便于分析趋势

        Returns:
            SaveResult: 保存结果
        """
        result = SaveResult()

        try:
            # 智能默认：如果没有指定任何参数，默认保存历史所有数据
            if all(x is None for x in [symbols, exchanges, spec_names, start_date, end_date, date]):
                start_date = "1990-01-01"  # 从 1990 年开始
                end_date = datetime.datetime.today().strftime("%Y%m%d")
                exchanges = FUTURES_EXCHANGES

            # 从远程获取数据
            df = self.remote_adapter.get_future_holdings(
                symbols=symbols,
                exchanges=exchanges,
                spec_names=spec_names,
                start_date=start_date,
                end_date=end_date,
                date=date,
                show_progress=self.show_progress
            )

            if df.empty:
                result.add_error("NO_DATA", "未获取到期货持仓数据")
                result.complete()
                return result

            # 转换为字典列表
            data = df.to_dict('records')

            # 创建索引
            collection = self.database.future_holdings
            self._create_index(
                collection,
                [("symbol", pymongo.ASCENDING), ("exchange", pymongo.ASCENDING),
                 ("date", pymongo.ASCENDING), ("broker", pymongo.ASCENDING)],
                unique=True
            )
            self._create_index(
                collection,
                [("date", pymongo.DESCENDING)]
            )

            # 批量保存
            save_result = self._bulk_upsert(
                collection,
                data,
                ["symbol", "exchange", "date", "broker"]
            )

            result.inserted_count = save_result["upserted_count"]
            result.modified_count = save_result["modified_count"]
            result.complete()

        except Exception as e:
            result.add_error("SAVE_ERROR", f"保存期货持仓失败: {str(e)}")
            result.complete()

        return result

    def save_stock_list(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        names: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        markets: Optional[Union[str, List[str]]] = None,
        list_status: Union[str, List[str], None] = "L",
        is_hs: Optional[str] = None
    ) -> SaveResult:
        """
        保存股票列表数据

        Args:
            symbols: 股票代码或列表（标准格式）
            names: 股票名称或列表
            exchanges: 交易所代码或列表（如 SSE, SZSE, BSE）
            markets: 市场板块或列表（如 主板, 创业板, 科创板, CDR, 北交所）
            list_status: 上市状态（'L' 上市, 'D' 退市, 'P' 暂停上市）
            is_hs: 沪港通状态（'N' 否, 'H' 沪股通, 'S' 深股通）

        智能默认行为：
            - 如果所有参数都为 None，默认保存所有上市股票（list_status="L"）

        Returns:
            SaveResult: 保存结果
        """
        result = SaveResult()

        try:
            # 智能默认：如果没有指定任何参数，默认保存所有上市股票
            if all(x is None for x in [symbols, names, exchanges, markets, list_status, is_hs]):
                list_status = "L"

            # 从远程获取数据
            df = self.remote_adapter.get_stock_list(
                symbols=symbols,
                names=names,
                exchanges=exchanges,
                markets=markets,
                list_status=list_status,
                is_hs=is_hs
            )

            if df.empty:
                result.add_error("NO_DATA", "未获取到股票列表数据")
                result.complete()
                return result

            # 转换为字典列表
            data = df.to_dict('records')

            # 创建索引
            collection = self.database.stock_list
            self._create_index(
                collection,
                [("symbol", pymongo.ASCENDING), ("exchange", pymongo.ASCENDING)],
                unique=True
            )

            # 批量保存
            save_result = self._bulk_upsert(
                collection,
                data,
                ["symbol", "exchange"]
            )

            result.inserted_count = save_result["upserted_count"]
            result.modified_count = save_result["modified_count"]
            result.complete()

        except Exception as e:
            result.add_error("SAVE_ERROR", f"保存股票列表失败: {str(e)}")
            result.complete()

        return result
