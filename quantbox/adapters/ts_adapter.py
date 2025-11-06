"""
TSAdapter - Tushare 数据适配器

从 Tushare API 获取市场数据
"""

from typing import Optional, Union, List
import datetime
import pandas as pd
from tqdm import tqdm

from quantbox.adapters.base import BaseDataAdapter
from quantbox.util.date_utils import DateLike, date_to_int
from quantbox.util.exchange_utils import denormalize_exchange, validate_exchanges
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
                ts_exchange = denormalize_exchange(exchange, "tushare")
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
                ts_exchange = denormalize_exchange(exchange, "tushare")

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
                        ts_exchange = denormalize_exchange(contract.exchange, "tushare")
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
                        ts_exchange = denormalize_exchange(exchange, "tushare")
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
                        ts_exchange = denormalize_exchange(exchange, "tushare")
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

            # 处理返回数据
            # 提取 symbol 和 exchange
            data["symbol"] = data["ts_code"].str.split(".").str[0]
            data["ts_exchange"] = data["ts_code"].str.split(".").str[1]

            # 转换交易所代码 SHF → SHFE, ZCE → CZCE
            exchange_map = {"SHF": "SHFE", "ZCE": "CZCE"}
            data["ts_exchange"] = data["ts_exchange"].replace(exchange_map)
            data["exchange"] = data["ts_exchange"]

            # 对于非郑商所和中金所，转为小写
            for exchange in data["exchange"].unique():
                if exchange not in ["CZCE", "CFFEX"]:
                    data.loc[data["exchange"] == exchange, "symbol"] = (
                        data.loc[data["exchange"] == exchange, "symbol"].str.lower()
                    )

            # 处理日期
            data["date"] = data["trade_date"].astype(int)

            # 重命名字段
            data = data.rename(columns={
                "vol": "volume",
                "oi": "oi"
            })

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
                    ts_exchange = denormalize_exchange(exchange, "tushare")

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
                    ts_exchange = denormalize_exchange(exchange, "tushare")
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
                        ts_exchange = denormalize_exchange(exchange, "tushare")

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

            # 标准化数据
            # 转换 ts_code 为 symbol (去掉 .SH/.SZ 后缀)
            df["symbol"] = df["ts_code"].str.split(".").str[0]

            # 转换交易所代码
            exchange_map = {"SH": "SSE", "SZ": "SZSE", "BJ": "BSE"}
            df["exchange"] = df["ts_code"].str.split(".").str[1].map(exchange_map)

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
