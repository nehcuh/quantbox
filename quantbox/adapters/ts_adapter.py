"""
TSAdapter - Tushare 数据适配器

从 Tushare API 获取市场数据
"""

from typing import Optional, Union, List
import datetime
import pandas as pd
from tqdm import tqdm

from quantbox.adapters.base import BaseDataAdapter
from quantbox.adapters.formatters import process_tushare_futures_data, process_tushare_stock_data
from quantbox.util.date_utils import DateLike, date_to_int
from quantbox.util.exchange_utils import get_exchange_for_data_source, validate_exchanges
from quantbox.util.contract_utils import normalize_contracts, format_contracts, ContractFormat
from quantbox.config.config_loader import get_config_loader


class TSAdapter(BaseDataAdapter):
    """
    Tushare 数据适配器

    从 Tushare API 获取市场数据。
    """

    def __init__(self, token=None):
        """
        初始化 TSAdapter

        Args:
            token: Tushare API token，默认使用全局 TSPRO
        """
        super().__init__("TSAdapter")
        self.pro = token or get_config_loader().get_tushare_pro()
        if self.pro is None:
            raise ValueError("Tushare API token 未配置")

    def check_availability(self) -> bool:
        """检查 Tushare API 是否可用"""
        try:
            self.pro.trade_cal(exchange='SSE', start_date='20250101', end_date='20250101')
            return True
        except Exception:
            return False

    def get_trade_calendar(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """从 Tushare 获取交易日历"""
        try:
            if exchanges is None:
                exchanges = validate_exchanges(None, "all")
            elif isinstance(exchanges, str):
                exchanges = [exchanges]

            start_str = str(date_to_int(start_date)) if start_date else None
            end_str = str(date_to_int(end_date)) if end_date else None

            all_data = []
            for exchange in exchanges:
                ts_exchange = get_exchange_for_data_source(exchange, "tushare", "api")
                df = self.pro.trade_cal(exchange=ts_exchange, start_date=start_str, end_date=end_str, is_open='1')

                if not df.empty:
                    df['exchange'] = exchange
                    df['date'] = df['cal_date'].astype(int)
                    df['is_open'] = True
                    all_data.append(df[['date', 'exchange', 'is_open']])

            if not all_data:
                return pd.DataFrame(columns=['date', 'exchange', 'is_open'])

            return pd.concat(all_data, ignore_index=True)
        except Exception as e:
            raise Exception(f"获取交易日历失败: {str(e)}")

    def get_future_contracts(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        symbols: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """从 Tushare 获取期货合约信息"""
        try:
            # 验证和标准化交易所参数
            if exchanges is None:
                exchanges = validate_exchanges(None, "futures")
            elif isinstance(exchanges, str):
                exchanges = [exchanges]
            else:
                exchanges = validate_exchanges(exchanges, "futures")

            # 标准化品种名称
            if spec_names and isinstance(spec_names, str):
                spec_names = [s.strip() for s in spec_names.split(",")]

            # 标准化日期
            cursor_date = None
            if date:
                date_int = date_to_int(date)
                cursor_date = f"{date_int//10000:04d}-{(date_int//100)%100:02d}-{date_int%100:02d}"

            all_data = []
            for exchange in exchanges:
                # 转换为 Tushare 交易所代码
                ts_exchange = get_exchange_for_data_source(exchange, "tushare", "api")

                # 获取合约信息（fut_type="1" 表示普通合约，不包括主力和连续）
                data = self.pro.fut_basic(exchange=ts_exchange, fut_type="1")

                if data.empty:
                    continue

                # 处理日期字段
                for date_col in ["list_date", "delist_date"]:
                    data[date_col] = pd.to_datetime(data[date_col]).dt.strftime("%Y-%m-%d")

                # 提取中文名称
                data["spec_name"] = data["name"].str.extract(r'(.+?)(?=\d{3,})')

                # 处理合约代码
                data["symbol"] = data["ts_code"].str.split(".").str[0]
                data["exchange"] = exchange

                # Tushare 中 symbol 都默认使用大写，对于非郑商所和中金所需要转小写
                if exchange not in ["CZCE", "CFFEX"]:
                    data["symbol"] = data["symbol"].str.lower()

                # 按品种名称过滤
                if spec_names:
                    data = data[data["spec_name"].isin(spec_names)]

                # 按日期过滤（合约在该日期有效）
                if cursor_date:
                    data = data[
                        (data["list_date"] <= cursor_date) &
                        (data["delist_date"] > cursor_date)
                    ]

                # 按 symbols 过滤
                if symbols:
                    symbol_list = [symbols] if isinstance(symbols, str) else symbols
                    # 标准化 symbols 为小写（如果不是郑商所和中金所）
                    if exchange not in ["CZCE", "CFFEX"]:
                        symbol_list = [s.lower() for s in symbol_list]
                    data = data[data["symbol"].isin(symbol_list)]

                if not data.empty:
                    # 选择关键字段
                    data = data[[
                        "symbol", "exchange", "spec_name", "name",
                        "list_date", "delist_date"
                    ]]
                    all_data.append(data)

            if not all_data:
                return pd.DataFrame(columns=[
                    "symbol", "exchange", "spec_name", "name",
                    "list_date", "delist_date"
                ])

            return pd.concat(all_data, ignore_index=True)

        except Exception as e:
            raise Exception(f"获取期货合约信息失败: {str(e)}")

    def get_future_daily(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
        show_progress: bool = False,
    ) -> pd.DataFrame:
        """从 Tushare 获取期货日线数据

        Args:
            symbols: 合约代码或列表
            exchanges: 交易所代码或列表
            start_date: 起始日期
            end_date: 结束日期
            date: 单日查询日期
            show_progress: 是否显示进度条，默认 False
        """
        try:
            # 标准化合约代码
            if symbols:
                if isinstance(symbols, str):
                    symbols = [symbols]
                # 将合约代码转换为 Tushare 格式 (symbol.EXCHANGE)
                ts_symbols = []
                for symbol in symbols:
                    contracts = normalize_contracts(symbol)
                    if contracts:
                        contract = contracts[0]
                        # 转换 SHFE → SHF, CZCE → ZCE
                        ts_exchange = get_exchange_for_data_source(contract.exchange, "tushare", "api")
                        if ts_exchange == "SHF":
                            ts_exchange = "SHF"
                        elif ts_exchange == "ZCE":
                            ts_exchange = "ZCE"
                        ts_symbols.append(f"{contract.symbol.upper()}.{ts_exchange}")

            # 处理日期参数
            if date:
                # 单日查询
                trade_date_str = str(date_to_int(date))

                if symbols:
                    # 按合约代码查询
                    data = self.pro.fut_daily(
                        ts_code=",".join(ts_symbols),
                        trade_date=trade_date_str
                    )
                else:
                    # 按交易所查询
                    if exchanges is None:
                        exchanges = validate_exchanges(None, "futures")
                    elif isinstance(exchanges, str):
                        exchanges = [exchanges]

                    all_data = []
                    exchanges_iter = tqdm(exchanges, desc="获取期货日线", disable=not show_progress)
                    for exchange in exchanges_iter:
                        ts_exchange = get_exchange_for_data_source(exchange, "tushare", "api")
                        df = self.pro.fut_daily(
                            trade_date=trade_date_str,
                            exchange=ts_exchange
                        )
                        if not df.empty:
                            all_data.append(df)

                    data = pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

            else:
                # 日期范围查询
                if start_date is None:
                    raise ValueError("必须指定 date 或 start_date")

                start_str = str(date_to_int(start_date))
                end_str = str(date_to_int(end_date)) if end_date else str(date_to_int(datetime.datetime.today()))

                if symbols:
                    # 按合约代码查询
                    data = self.pro.fut_daily(
                        ts_code=",".join(ts_symbols),
                        start_date=start_str,
                        end_date=end_str
                    )
                else:
                    # 按交易所查询
                    if exchanges is None:
                        exchanges = validate_exchanges(None, "futures")
                    elif isinstance(exchanges, str):
                        exchanges = [exchanges]

                    all_data = []
                    exchanges_iter = tqdm(exchanges, desc="获取期货日线", disable=not show_progress)
                    for exchange in exchanges_iter:
                        ts_exchange = get_exchange_for_data_source(exchange, "tushare", "api")
                        if show_progress:
                            exchanges_iter.set_postfix({"交易所": exchange})
                        df = self.pro.fut_daily(
                            exchange=ts_exchange,
                            start_date=start_str,
                            end_date=end_str
                        )
                        if not df.empty:
                            all_data.append(df)

                    data = pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

            if data.empty:
                return pd.DataFrame(columns=[
                    "symbol", "exchange", "date", "open", "high", "low", "close",
                    "volume", "amount", "oi"
                ])

            # 使用公共格式转换函数处理数据
            data = process_tushare_futures_data(
                data,
                parse_ts_code=True,
                normalize_case=True,
                standardize_columns=True
            )

            # 保留 oi 字段名（不使用 open_interest）
            if "open_interest" in data.columns:
                data = data.rename(columns={"open_interest": "oi"})

            # 选择关键字段
            result_columns = [
                "symbol", "exchange", "date", "open", "high", "low", "close",
                "volume", "amount"
            ]
            if "oi" in data.columns:
                result_columns.append("oi")

            data = data[result_columns]

            return data

        except Exception as e:
            raise Exception(f"获取期货日线数据失败: {str(e)}")

    def get_future_minute(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
        freq: str = "1min",
        show_progress: bool = False,
    ) -> pd.DataFrame:
        """从 Tushare 获取期货分钟线数据

        Args:
            symbols: 合约代码或列表（标准格式，如 "SHFE.rb2501"）
            exchanges: 交易所代码或列表（标准格式，如 "SHFE"）
            start_date: 起始日期
            end_date: 结束日期
            date: 单日查询日期（与 start_date/end_date 互斥）
            freq: 分钟频率，支持 "1min", "5min", "15min", "30min", "60min"，默认 "1min"
            show_progress: 是否显示进度条，默认 False

        Returns:
            DataFrame 包含以下列：
            - symbol: 合约代码（标准格式，如 "SHFE.rb2501"）
            - exchange: 交易所代码（标准格式，如 "SHFE"）
            - datetime: 时间戳（int，格式：YYYYMMDDHHmm）
            - date: 日期（int，格式：YYYYMMDD）
            - time: 时间（str，格式：HH:MM:SS）
            - open: 开盘价
            - high: 最高价
            - low: 最低价
            - close: 收盘价
            - volume: 成交量
            - amount: 成交额
            - oi: 持仓量（如果有）

        注意:
            - 分钟数据量很大，建议指定具体合约或较短的日期范围
            - 建议使用 5min 或更长周期以减少数据量
            - Tushare 分钟数据接口有调用限制，频繁调用可能受限
        """
        try:
            # 验证频率参数
            valid_freqs = ["1min", "5min", "15min", "30min", "60min"]
            if freq not in valid_freqs:
                raise ValueError(f"不支持的频率: {freq}，必须是 {valid_freqs} 之一")

            # 验证日期参数
            self._validate_date_range(start_date, end_date, date)

            # 验证必须指定合约或交易所
            if not symbols and not exchanges:
                raise ValueError("必须指定 symbols 或 exchanges 参数")

            # 标准化合约代码
            ts_symbols = []
            if symbols:
                if isinstance(symbols, str):
                    symbols = [symbols]

                for symbol in symbols:
                    from quantbox.util.contract_utils import parse_contract
                    contract = parse_contract(symbol)
                    if contract:
                        # 转换为 Tushare 格式
                        ts_exchange = get_exchange_for_data_source(contract.exchange, "tushare", "api")
                        ts_symbols.append(f"{contract.symbol.upper()}.{ts_exchange}")

            # 处理日期参数
            if date:
                # 单日查询
                trade_date_str = str(date_to_int(date))
                start_str = trade_date_str
                end_str = trade_date_str
            else:
                # 日期范围查询
                if start_date is None:
                    raise ValueError("必须指定 date 或 start_date")

                start_str = str(date_to_int(start_date))
                end_str = str(date_to_int(end_date)) if end_date else str(date_to_int(datetime.datetime.today()))

            # 获取数据
            all_data = []

            if ts_symbols:
                # 按合约查询（逐个合约查询以避免超限）
                symbols_iter = tqdm(ts_symbols, desc=f"获取期货{freq}数据", disable=not show_progress)
                for ts_symbol in symbols_iter:
                    if show_progress:
                        symbols_iter.set_postfix({"合约": ts_symbol})

                    try:
                        df = self.pro.fut_min(
                            ts_code=ts_symbol,
                            start_date=start_str,
                            end_date=end_str,
                            freq=freq
                        )
                        if not df.empty:
                            all_data.append(df)
                    except Exception as e:
                        if show_progress:
                            tqdm.write(f"获取 {ts_symbol} 数据失败: {str(e)}")
                        continue

            else:
                # 按交易所查询
                if exchanges is None:
                    exchanges = validate_exchanges(None, "futures")
                elif isinstance(exchanges, str):
                    exchanges = [exchanges]

                exchanges_iter = tqdm(exchanges, desc=f"获取期货{freq}数据", disable=not show_progress)
                for exchange in exchanges_iter:
                    if show_progress:
                        exchanges_iter.set_postfix({"交易所": exchange})

                    ts_exchange = get_exchange_for_data_source(exchange, "tushare", "api")
                    try:
                        df = self.pro.fut_min(
                            exchange=ts_exchange,
                            start_date=start_str,
                            end_date=end_str,
                            freq=freq
                        )
                        if not df.empty:
                            all_data.append(df)
                    except Exception as e:
                        if show_progress:
                            tqdm.write(f"获取交易所 {exchange} 数据失败: {str(e)}")
                        continue

            if not all_data:
                return pd.DataFrame(columns=[
                    "symbol", "exchange", "datetime", "date", "time",
                    "open", "high", "low", "close", "volume", "amount", "oi"
                ])

            # 合并所有数据
            data = pd.concat(all_data, ignore_index=True)

            # 使用公共格式转换函数处理数据
            data = process_tushare_futures_data(
                data,
                parse_ts_code=True,
                normalize_case=True,
                standardize_columns=True
            )

            # 处理时间字段
            # Tushare 返回的 trade_time 格式为 "YYYY-MM-DD HH:MM:SS"
            if "trade_time" in data.columns:
                data["datetime"] = pd.to_datetime(data["trade_time"]).dt.strftime("%Y%m%d%H%M").astype(int)
                data["time"] = pd.to_datetime(data["trade_time"]).dt.strftime("%H:%M:%S")

            # 保留 oi 字段名（不使用 open_interest）
            if "open_interest" in data.columns:
                data = data.rename(columns={"open_interest": "oi"})

            # 选择关键字段
            result_columns = [
                "symbol", "exchange", "datetime", "date", "time",
                "open", "high", "low", "close", "volume", "amount"
            ]
            if "oi" in data.columns:
                result_columns.append("oi")

            # 只保留存在的列
            result_columns = [col for col in result_columns if col in data.columns]
            data = data[result_columns]

            # 按时间排序
            if "datetime" in data.columns:
                data = data.sort_values(["symbol", "datetime"]).reset_index(drop=True)

            return data

        except Exception as e:
            raise Exception(f"获取期货分钟数据失败: {str(e)}")

    def get_future_holdings(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
        show_progress: bool = False,
    ) -> pd.DataFrame:
        """从 Tushare 获取期货持仓数据

        Args:
            symbols: 合约代码或列表
            exchanges: 交易所代码或列表
            spec_names: 品种名称或列表
            start_date: 起始日期
            end_date: 结束日期
            date: 单日查询日期
            show_progress: 是否显示进度条，默认 False
        """
        try:
            # 验证和标准化交易所参数
            if exchanges is None:
                exchanges = validate_exchanges(None, "futures")
            elif isinstance(exchanges, str):
                exchanges = [exchanges]
            else:
                exchanges = validate_exchanges(exchanges, "futures")

            # 标准化合约代码
            if symbols:
                if isinstance(symbols, str):
                    symbols = [symbols]
                # 将合约代码标准化（提取符号部分）
                normalized_symbols = []
                for symbol in symbols:
                    contracts = normalize_contracts(symbol)
                    if contracts:
                        normalized_symbols.append(contracts[0].symbol.upper())
                symbols = normalized_symbols

            all_data = []

            # 单日查询
            if date:
                trade_date_str = str(date_to_int(date))

                for exchange in exchanges:
                    ts_exchange = get_exchange_for_data_source(exchange, "tushare", "api")

                    if symbols:
                        # 按合约代码查询
                        for symbol in symbols:
                            try:
                                df = self.pro.fut_holding(
                                    trade_date=trade_date_str,
                                    symbol=symbol,
                                    exchange=ts_exchange
                                )
                                if not df.empty:
                                    df["exchange"] = exchange
                                    all_data.append(df)
                            except Exception:
                                continue
                    else:
                        # 查询整个交易所（Tushare 可能不支持，需要逐个合约查询）
                        try:
                            df = self.pro.fut_holding(
                                trade_date=trade_date_str,
                                exchange=ts_exchange
                            )
                            if not df.empty:
                                df["exchange"] = exchange
                                all_data.append(df)
                        except Exception:
                            continue

            # 日期范围查询
            else:
                if start_date is None:
                    raise ValueError("必须指定 date 或 start_date")

                start_str = str(date_to_int(start_date))
                end_str = str(date_to_int(end_date)) if end_date else str(date_to_int(datetime.datetime.today()))

                # 获取日期范围内的交易日
                trade_dates = []
                for exchange in exchanges:
                    ts_exchange = get_exchange_for_data_source(exchange, "tushare", "api")
                    cal_df = self.pro.trade_cal(
                        exchange=ts_exchange,
                        start_date=start_str,
                        end_date=end_str,
                        is_open='1'
                    )
                    if not cal_df.empty:
                        trade_dates.extend(cal_df['cal_date'].tolist())

                trade_dates = sorted(set(trade_dates))

                # 逐日查询
                dates_iter = tqdm(trade_dates, desc="获取期货持仓", disable=not show_progress)
                for trade_date in dates_iter:
                    if show_progress:
                        dates_iter.set_postfix({"日期": str(trade_date)})
                    for exchange in exchanges:
                        ts_exchange = get_exchange_for_data_source(exchange, "tushare", "api")

                        if symbols:
                            for symbol in symbols:
                                try:
                                    df = self.pro.fut_holding(
                                        trade_date=str(trade_date),
                                        symbol=symbol,
                                        exchange=ts_exchange
                                    )
                                    if not df.empty:
                                        df["exchange"] = exchange
                                        all_data.append(df)
                                except Exception:
                                    continue
                        else:
                            try:
                                df = self.pro.fut_holding(
                                    trade_date=str(trade_date),
                                    exchange=ts_exchange
                                )
                                if not df.empty:
                                    df["exchange"] = exchange
                                    all_data.append(df)
                            except Exception:
                                continue

            if not all_data:
                return pd.DataFrame(columns=[
                    "symbol", "exchange", "date", "broker", "vol",
                    "vol_chg", "long_hld", "long_chg", "short_hld", "short_chg"
                ])

            # 合并数据
            result = pd.concat(all_data, ignore_index=True)

            # 处理日期
            result["date"] = result["trade_date"].astype(int)

            # 对于非郑商所和中金所，转为小写
            for exchange in result["exchange"].unique():
                if exchange not in ["CZCE", "CFFEX"]:
                    result.loc[result["exchange"] == exchange, "symbol"] = (
                        result.loc[result["exchange"] == exchange, "symbol"].str.lower()
                    )

            # 选择关键字段
            key_columns = [
                "symbol", "exchange", "date", "broker", "vol",
                "vol_chg", "long_hld", "long_chg", "short_hld", "short_chg"
            ]
            available_columns = [col for col in key_columns if col in result.columns]
            result = result[available_columns]

            return result

        except Exception as e:
            raise Exception(f"获取期货持仓数据失败: {str(e)}")

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
        从 Tushare API 获取股票列表

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
            # 构建参数
            params = {}

            # 处理上市状态
            if list_status is not None:
                if isinstance(list_status, list):
                    params["list_status"] = ",".join(list_status)
                else:
                    params["list_status"] = list_status

            # 处理沪港通状态
            if is_hs is not None:
                params["is_hs"] = is_hs

            # 获取基础股票列表
            df = self.pro.stock_basic(**params)

            if df.empty:
                return pd.DataFrame(columns=["symbol", "name", "exchange", "list_date", "delist_date", "industry", "area"])

            # 使用公共格式转换函数处理股票数据
            df = process_tushare_stock_data(
                df,
                parse_ts_code=True,
                standardize_columns=False  # 保持原字段名
            )

            # 转换日期格式
            df["list_date"] = df["list_date"].astype(int)
            if "delist_date" in df.columns:
                df["delist_date"] = df["delist_date"].fillna(0).astype(int)
                df.loc[df["delist_date"] == 0, "delist_date"] = None

            # 应用过滤条件
            filtered_df = df.copy()

            # 按股票代码过滤
            if symbols is not None:
                if isinstance(symbols, str):
                    symbols = [symbols]
                filtered_df = filtered_df[filtered_df["symbol"].isin(symbols)]

            # 按股票名称过滤
            if names is not None:
                if isinstance(names, str):
                    names = [names]
                filtered_df = filtered_df[filtered_df["name"].isin(names)]

            # 按交易所过滤
            if exchanges is not None:
                if isinstance(exchanges, str):
                    exchanges = [exchanges]
                # 验证并标准化交易所
                from quantbox.util.exchange_utils import validate_exchanges
                exchanges = validate_exchanges(exchanges)
                filtered_df = filtered_df[filtered_df["exchange"].isin(exchanges)]

            # 按市场板块过滤
            if markets is not None:
                if isinstance(markets, str):
                    markets = [markets]
                filtered_df = filtered_df[filtered_df["market"].isin(markets)]

            # 选择关键字段
            key_columns = [
                "symbol", "name", "exchange", "list_date", "delist_date",
                "industry", "area", "market"
            ]
            available_columns = [col for col in key_columns if col in filtered_df.columns]
            result = filtered_df[available_columns].copy()

            return result

        except Exception as e:
            raise Exception(f"获取股票列表失败: {str(e)}")
