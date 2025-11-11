"""
LocalAdapter - MongoDB 数据适配器

从本地 MongoDB 数据库读取市场数据
"""

from typing import Optional, Union, List
import datetime
import pandas as pd
import pymongo

from quantbox.adapters.base import BaseDataAdapter
from quantbox.util.date_utils import DateLike, date_to_int, util_make_date_stamp
from quantbox.util.exchange_utils import normalize_exchange, validate_exchanges
from quantbox.util.contract_utils import normalize_contracts, parse_contract
from quantbox.config.config_loader import get_config_loader


class LocalAdapter(BaseDataAdapter):
    """
    本地数据库适配器

    从 MongoDB 读取市场数据，包括交易日历、期货合约、日线数据、持仓数据等。
    """

    def __init__(self, database=None):
        """
        初始化 LocalAdapter

        Args:
            database: MongoDB 数据库连接，默认使用全局 DATABASE
        """
        super().__init__("LocalAdapter")
        self.database = database or get_config_loader().get_mongodb_client().quantbox

    def check_availability(self) -> bool:
        """
        检查数据库连接是否可用

        Returns:
            bool: 数据库是否可用
        """
        try:
            # 尝试执行一个简单的查询
            self.database.trade_date.find_one()
            return True
        except Exception:
            return False

    def get_trade_calendar(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        从 MongoDB 获取交易日历

        Args:
            exchanges: 交易所代码（标准格式）或列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame 包含以下列：
            - date: 日期（int，YYYYMMDD格式）
            - exchange: 交易所代码（标准格式）
        """
        try:
            # 构建查询条件
            query = {}

            # 处理交易所过滤
            if exchanges is not None:
                if isinstance(exchanges, str):
                    exchanges = [exchanges]
                # 标准化交易所代码
                exchanges = validate_exchanges(exchanges)
                query["exchange"] = {"$in": exchanges}

            # 处理日期范围（优先使用 datestamp 字段进行快速查询）
            if start_date is not None or end_date is not None:
                date_query = {}
                if start_date is not None:
                    start_stamp = util_make_date_stamp(start_date)
                    date_query["$gte"] = start_stamp
                if end_date is not None:
                    end_stamp = util_make_date_stamp(end_date)
                    date_query["$lte"] = end_stamp
                if date_query:
                    query["datestamp"] = date_query

            # 执行查询
            cursor = self.database.trade_date.find(
                query,
                {"_id": 0, "date": 1, "exchange": 1},
                sort=[("exchange", pymongo.ASCENDING), ("datestamp", pymongo.ASCENDING)]
            )

            df = pd.DataFrame(list(cursor))

            if df.empty:
                # 返回空 DataFrame 但包含正确的列
                return pd.DataFrame(columns=["date", "exchange"])

            # 数据已经是标准格式，直接返回
            result = df[["date", "exchange"]].copy()

            return result

        except Exception as e:
            raise Exception(f"获取交易日历失败: {str(e)}")

    def get_future_contracts(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        symbols: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        从 MongoDB 获取期货合约信息

        Args:
            exchanges: 交易所代码或列表
            symbols: 合约代码或列表（标准格式）
            spec_names: 品种名称或列表（如 rb, m, SR等）
            date: 查询日期，None 表示所有合约

        Returns:
            DataFrame 包含合约信息
        """
        try:
            # 验证至少有一个参数
            self._validate_symbol_params(symbols, exchanges, spec_names)

            # 构建查询条件
            query = {}

            # 处理合约代码
            if symbols is not None:
                if isinstance(symbols, str):
                    symbols = [symbols]
                # 标准化合约代码
                symbols = normalize_contracts(symbols)
                query["symbol"] = {"$in": symbols}

            # 处理交易所
            if exchanges is not None:
                if isinstance(exchanges, str):
                    exchanges = [exchanges]
                exchanges = validate_exchanges(exchanges)
                query["exchange"] = {"$in": exchanges}

            # 处理品种名称
            if spec_names is not None:
                if isinstance(spec_names, str):
                    spec_names = [spec_names]
                # 品种名称在数据库中可能存储为 chinese_name 或 fut_code
                query["$or"] = [
                    {"chinese_name": {"$in": spec_names}},
                    {"fut_code": {"$in": [s.upper() for s in spec_names]}}
                ]

            # 处理日期过滤（查询在指定日期上市且未退市的合约）
            if date is not None:
                datestamp = util_make_date_stamp(date)
                query["list_datestamp"] = {"$lte": datestamp}
                query["delist_datestamp"] = {"$gte": datestamp}

            # 执行查询
            cursor = self.database.future_contracts.find(
                query,
                {"_id": 0},
                sort=[("exchange", pymongo.ASCENDING), ("symbol", pymongo.ASCENDING)]
            )

            df = pd.DataFrame(list(cursor))

            if df.empty:
                # 返回空 DataFrame 但包含基本列
                return pd.DataFrame(columns=["symbol", "exchange", "name", "spec_name", "list_date", "delist_date"])

            # 转换日期格式
            if "list_date" in df.columns:
                df["list_date"] = df["list_date"].apply(lambda x: int(x.replace("-", "")) if isinstance(x, str) else x)
            if "delist_date" in df.columns:
                df["delist_date"] = df["delist_date"].apply(lambda x: int(x.replace("-", "")) if isinstance(x, str) else x)

            # 确保包含 spec_name 列
            if "fut_code" in df.columns and "spec_name" not in df.columns:
                df["spec_name"] = df["fut_code"]

            return df

        except Exception as e:
            raise Exception(f"获取期货合约信息失败: {str(e)}")

    def get_future_daily(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        从 MongoDB 获取期货日线数据

        Args:
            symbols: 合约代码或列表
            exchanges: 交易所代码或列表
            start_date: 开始日期
            end_date: 结束日期
            date: 单日查询

        Returns:
            DataFrame 包含日线数据
        """
        try:
            # 验证参数
            self._validate_date_range(start_date, end_date, date)
            self._validate_symbol_params(symbols, exchanges, None)

            # 构建查询条件
            query = {}

            # 处理合约代码
            if symbols is not None:
                if isinstance(symbols, str):
                    symbols = [symbols]

                # 智能解析合约代码，支持多种格式：
                # 1. 完整格式: "DCE.a2501" -> symbol="a2501", exchange="DCE"
                # 2. 简单格式: "a2501" -> symbol="a2501" (不设置 exchange 过滤)
                parsed_symbols = []
                parsed_exchanges = []

                for sym in symbols:
                    # 尝试解析为完整格式
                    if '.' in sym:
                        try:
                            contract_info = parse_contract(sym)
                            parsed_symbols.append(contract_info.symbol)
                            parsed_exchanges.append(contract_info.exchange)
                        except Exception:
                            # 解析失败，直接使用原始值
                            parsed_symbols.append(sym)
                    else:
                        # 简单格式，直接使用
                        parsed_symbols.append(sym)

                query["symbol"] = {"$in": parsed_symbols}

                # 如果从 symbols 中解析出了 exchange，且用户没有显式指定 exchanges
                # 则使用解析出的 exchange 进行过滤
                if parsed_exchanges and exchanges is None:
                    query["exchange"] = {"$in": list(set(parsed_exchanges))}

            # 处理交易所
            if exchanges is not None:
                if isinstance(exchanges, str):
                    exchanges = [exchanges]
                exchanges = validate_exchanges(exchanges)
                query["exchange"] = {"$in": exchanges}

            # 处理日期范围
            if date is not None:
                # 单日查询
                datestamp = util_make_date_stamp(date)
                query["datestamp"] = datestamp
            else:
                # 日期范围查询
                date_query = {}
                if start_date is not None:
                    start_stamp = util_make_date_stamp(start_date)
                    date_query["$gte"] = start_stamp
                if end_date is not None:
                    end_stamp = util_make_date_stamp(end_date)
                    date_query["$lte"] = end_stamp
                if date_query:
                    query["datestamp"] = date_query

            # 执行查询
            cursor = self.database.future_daily.find(
                query,
                {"_id": 0},
                sort=[("symbol", pymongo.ASCENDING), ("datestamp", pymongo.ASCENDING)]
            )

            df = pd.DataFrame(list(cursor))

            if df.empty:
                # 返回空 DataFrame 但包含基本列
                return pd.DataFrame(columns=["date", "symbol", "exchange", "open", "high", "low", "close", "volume", "amount", "oi"])

            # 转换日期格式（确保 date 字段是整数格式）
            if "date" in df.columns and df["date"].dtype in [int, 'int64', 'int32']:
                # date 字段已经是正确的整数格式，无需转换
                pass
            elif "trade_date" in df.columns:
                # 从 trade_date 字符串转换
                df["date"] = df["trade_date"].apply(lambda x: int(x.replace("-", "")) if isinstance(x, str) else x)
            elif "datestamp" in df.columns and "date" not in df.columns:
                # 从 datestamp 提取日期（仅当没有 date 字段时）
                df["date"] = df["datestamp"].apply(
                    lambda x: int(x.strftime("%Y%m%d")) if isinstance(x, datetime.datetime)
                    else int(datetime.datetime.fromtimestamp(x).strftime("%Y%m%d"))
                )

            # 确保字段存在（某些数据源可能缺少某些字段）
            required_fields = ["date", "symbol", "exchange", "open", "high", "low", "close", "volume"]
            for field in required_fields:
                if field not in df.columns:
                    df[field] = None

            return df

        except Exception as e:
            raise Exception(f"获取期货日线数据失败: {str(e)}")

    def get_future_holdings(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        从 MongoDB 获取期货持仓数据

        Args:
            symbols: 合约代码或列表
            exchanges: 交易所代码或列表
            spec_names: 品种名称或列表
            start_date: 开始日期
            end_date: 结束日期
            date: 单日查询

        Returns:
            DataFrame 包含持仓数据
        """
        try:
            # 验证参数
            self._validate_date_range(start_date, end_date, date)
            self._validate_symbol_params(symbols, exchanges, spec_names)

            # 构建查询条件
            query = {}

            # 处理合约代码（同样支持灵活格式）
            if symbols is not None:
                if isinstance(symbols, str):
                    symbols = [symbols]

                # 智能解析合约代码，支持多种格式
                parsed_symbols = []
                parsed_exchanges = []

                for sym in symbols:
                    # 尝试解析为完整格式
                    if '.' in sym:
                        try:
                            contract_info = parse_contract(sym)
                            parsed_symbols.append(contract_info.symbol)
                            parsed_exchanges.append(contract_info.exchange)
                        except Exception:
                            # 解析失败，直接使用原始值
                            parsed_symbols.append(sym)
                    else:
                        # 简单格式，直接使用
                        parsed_symbols.append(sym)

                query["symbol"] = {"$in": parsed_symbols}

                # 如果从 symbols 中解析出了 exchange，且用户没有显式指定 exchanges
                # 则使用解析出的 exchange 进行过滤
                if parsed_exchanges and exchanges is None:
                    query["exchange"] = {"$in": list(set(parsed_exchanges))}

            # 处理交易所
            if exchanges is not None:
                if isinstance(exchanges, str):
                    exchanges = [exchanges]
                exchanges = validate_exchanges(exchanges)
                query["exchange"] = {"$in": exchanges}

            # 处理品种名称（需要先查询合约信息）
            if spec_names is not None:
                if isinstance(spec_names, str):
                    spec_names = [spec_names]
                # 从合约表查询对应的合约代码
                contracts_query = {"$or": [
                    {"chinese_name": {"$in": spec_names}},
                    {"fut_code": {"$in": [s.upper() for s in spec_names]}}
                ]}
                contract_symbols = list(self.database.future_contracts.find(
                    contracts_query,
                    {"symbol": 1, "_id": 0}
                ))
                if contract_symbols:
                    query["symbol"] = {"$in": [c["symbol"] for c in contract_symbols]}

            # 处理日期范围
            if date is not None:
                datestamp = util_make_date_stamp(date)
                query["datestamp"] = datestamp
            else:
                date_query = {}
                if start_date is not None:
                    start_stamp = util_make_date_stamp(start_date)
                    date_query["$gte"] = start_stamp
                if end_date is not None:
                    end_stamp = util_make_date_stamp(end_date)
                    date_query["$lte"] = end_stamp
                if date_query:
                    query["datestamp"] = date_query

            # 执行查询
            cursor = self.database.future_holdings.find(
                query,
                {"_id": 0},
                sort=[("datestamp", pymongo.ASCENDING), ("symbol", pymongo.ASCENDING), ("rank", pymongo.ASCENDING)]
            )

            df = pd.DataFrame(list(cursor))

            if df.empty:
                return pd.DataFrame(columns=["date", "symbol", "exchange", "broker", "vol", "vol_chg", "rank"])

            # 转换日期格式（确保 date 字段是整数格式）
            if "date" in df.columns and df["date"].dtype in [int, 'int64', 'int32']:
                # date 字段已经是正确的整数格式，无需转换
                pass
            elif "trade_date" in df.columns:
                df["date"] = df["trade_date"].apply(lambda x: int(x.replace("-", "")) if isinstance(x, str) else x)
            elif "datestamp" in df.columns and "date" not in df.columns:
                # 从 datestamp 提取日期（仅当没有 date 字段时）
                df["date"] = df["datestamp"].apply(
                    lambda x: int(x.strftime("%Y%m%d")) if isinstance(x, datetime.datetime)
                    else int(datetime.datetime.fromtimestamp(x).strftime("%Y%m%d"))
                )

            return df

        except Exception as e:
            raise Exception(f"获取期货持仓数据失败: {str(e)}")

    def get_next_trade_date(
        self,
        exchange: str,
        cursor_date: Optional[DateLike] = None,
        n: int = 1,
        include: bool = False
    ) -> Optional[dict]:
        """
        获取指定日期之后的交易日

        Args:
            exchange: 交易所代码
            cursor_date: 指定日期，默认为当前日期
            n: 往后回溯的天数，默认为 1
            include: 是否包含当天，默认为 False

        Returns:
            交易日信息字典，包含 trade_date 字段
        """
        try:
            from quantbox.util.date_utils import date_to_int, util_make_date_stamp
            import datetime

            if cursor_date is None:
                cursor_date = datetime.datetime.today()

            # 标准化交易所代码
            exchange = validate_exchanges([exchange])[0]

            # 构建查询条件
            query = {"exchange": exchange}

            # 处理日期条件
            cursor_datestamp = util_make_date_stamp(cursor_date)
            if include:
                query["datestamp"] = {"$gte": cursor_datestamp}
            else:
                query["datestamp"] = {"$gt": cursor_datestamp}

            # 执行查询
            cursor = self.database.trade_date.find(
                query,
                {"_id": 0, "trade_date": 1, "exchange": 1, "datestamp": 1},
                sort=[("datestamp", pymongo.ASCENDING)],
                limit=n
            )

            results = list(cursor)
            if not results:
                return None

            # 返回最后一个结果（第n个交易日）
            result = results[-1]
            return result

        except Exception as e:
            raise Exception(f"获取下一个交易日失败: {str(e)}")

    def get_stock_list(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        names: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        markets: Optional[Union[str, List[str]]] = None,
        list_status: Union[str, List[str], None] = "L",
        is_hs: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        从 MongoDB 获取股票列表

        Args:
            symbols: 股票代码或列表（标准格式）
            names: 股票名称或列表
            exchanges: 交易所代码或列表（如 SSE, SZSE, BSE）
            markets: 市场板块或列表（如 主板, 创业板, 科创板, CDR, 北交所）
            list_status: 上市状态（'L' 上市, 'D' 退市, 'P' 暂停上市）
            is_hs: 沪港通状态（'N' 否, 'H' 沪股通, 'S' 深股通）

        Returns:
            DataFrame包含股票信息
        """
        try:
            # 构建查询条件
            query = {}

            # 处理股票代码
            if symbols is not None:
                if isinstance(symbols, str):
                    symbols = [symbols]
                query["symbol"] = {"$in": symbols}

            # 处理股票名称
            if names is not None:
                if isinstance(names, str):
                    names = [names]
                query["name"] = {"$in": names}

            # 处理交易所
            if exchanges is not None:
                if isinstance(exchanges, str):
                    exchanges = [exchanges]
                exchanges = validate_exchanges(exchanges)
                query["exchange"] = {"$in": exchanges}

            # 处理市场板块
            if markets is not None:
                if isinstance(markets, str):
                    markets = [markets]
                query["market"] = {"$in": markets}

            # 处理上市状态
            if list_status is not None:
                if isinstance(list_status, str):
                    list_status = [list_status]
                query["list_status"] = {"$in": list_status}

            # 处理沪港通状态
            if is_hs is not None:
                query["is_hs"] = is_hs

            # 执行查询
            cursor = self.database.stock_list.find(
                query,
                {"_id": 0},
                sort=[("exchange", pymongo.ASCENDING), ("symbol", pymongo.ASCENDING)]
            )

            df = pd.DataFrame(list(cursor))

            if df.empty:
                # 返回空 DataFrame 但包含基本列
                return pd.DataFrame(columns=["symbol", "name", "exchange", "list_date", "delist_date", "industry", "area"])

            # 转换日期格式
            if "list_date" in df.columns:
                df["list_date"] = df["list_date"].apply(lambda x: int(x.replace("-", "")) if isinstance(x, str) else x)
            if "delist_date" in df.columns:
                df["delist_date"] = df["delist_date"].apply(lambda x: int(x.replace("-", "")) if isinstance(x, str) else x)

            return df

        except Exception as e:
            raise Exception(f"获取股票列表失败: {str(e)}")
