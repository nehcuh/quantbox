from typing import List, Dict, Union, Optional
from datetime import datetime, date
import pandas as pd
import tushare as ts
from .base_fetcher import BaseFetcher
from ..database import MongoDBManager
from ...core.config import ConfigLoader, ExchangeType
import numpy as np
import re


class TushareFetcher(BaseFetcher):
    """Tushare数据获取类"""
    
    def __init__(self):
        """初始化Tushare接口"""
        config = ConfigLoader.get_api_config()
        if not config.tushare_token:
            raise ValueError("Tushare token not found in config")
        ts.set_token(config.tushare_token)
        self.pro = ts.pro_api()
        self.future_exchanges = ["SHFE", "DCE", "CFFEX", "CZCE", "INE"]
        
        # 初始化MongoDB管理器
        self.db = MongoDBManager(ConfigLoader.get_database_config())
        self.db.ensure_calendar_index()
        
        # 获取所有交易所的交易日历缓存
        self._calendar_cache = {}
        self._cache_key_format = "{exchange}_{start_date}_{end_date}"
    
    def _get_cached_calendar(
        self,
        exchange: Optional[str] = None,
        exchange_type: Optional[ExchangeType] = None,
        start_date: Optional[Union[str, int, date, datetime]] = None,
        end_date: Optional[Union[str, int, date, datetime]] = None
    ) -> pd.DataFrame:
        """获取交易日历，优先从内存缓存获取，其次从本地数据库获取
        
        Args:
            exchange: 交易所代码，如果为None则根据exchange_type获取
            exchange_type: 交易所类型，如果exchange为None则必须指定
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            pd.DataFrame: 交易日历数据
        """
        # 确定要获取的交易所
        if exchange is None and exchange_type is None:
            raise ValueError("Either exchange or exchange_type must be specified")
        
        if exchange is None:
            if exchange_type == ExchangeType.STOCK:
                exchanges = ["SSE", "SZSE"]
            elif exchange_type == ExchangeType.FUTURES:
                exchanges = ["SHFE", "DCE", "CZCE", "CFFEX", "INE", "GFEX"]
            else:
                raise ValueError(f"Unknown exchange type: {exchange_type}")
        else:
            exchanges = [exchange]
        
        # 标准化日期格式，用于缓存key
        start_date_int = int(pd.Timestamp(start_date).strftime('%Y%m%d')) if start_date else 0
        end_date_int = int(pd.Timestamp(end_date).strftime('%Y%m%d')) if end_date else 0
        
        # 从内存缓存获取数据
        dfs = []
        need_db_query = False
        for ex in exchanges:
            cache_key = (ex, start_date_int, end_date_int)  # 使用元组作为key
            if cache_key in self._calendar_cache:
                dfs.append(self._calendar_cache[cache_key])
            else:
                need_db_query = True
                break
        
        # 如果所有数据都在缓存中，直接返回
        if not need_db_query:
            return pd.concat(dfs, ignore_index=True) if len(dfs) > 1 else dfs[0]
        
        # 从本地数据库获取数据
        dfs = []
        need_update = False
        for ex in exchanges:
            df = self.db.get_calendar(ex, start_date, end_date)
            if len(df) == 0 or 'is_open' not in df.columns:
                need_update = True
                break
            # 更新内存缓存
            cache_key = (ex, start_date_int, end_date_int)
            self._calendar_cache[cache_key] = df
            dfs.append(df)
        
        # 如果本地数据库没有数据或者没有is_open字段，则从Tushare获取并保存
        if need_update:
            df = self.fetch_get_calendar(exchange, exchange_type, start_date, end_date)
            self.db.save_calendar(df)
            # 更新内存缓存
            for ex in exchanges:
                cache_key = (ex, start_date_int, end_date_int)
                ex_df = df[df['exchange'] == ex].copy()
                self._calendar_cache[cache_key] = ex_df
            return df
        
        # 合并多个交易所的数据
        df = pd.concat(dfs, ignore_index=True)
        return df
    
    def fetch_get_calendar(
        self,
        exchange: Optional[str] = None,
        exchange_type: Optional[ExchangeType] = None,
        start_date: Optional[Union[str, int, date, datetime]] = None,
        end_date: Optional[Union[str, int, date, datetime]] = None
    ) -> pd.DataFrame:
        """从Tushare获取交易日历
        
        Args:
            exchange: 交易所代码，如果为None则根据exchange_type获取
            exchange_type: 交易所类型，如果exchange为None则必须指定
            start_date: 开始日期，如果为None则使用19890101
            end_date: 结束日期，如果为None则获取从start_date至当年度12月31日的数据
            
        Returns:
            pd.DataFrame: 包含以下列的DataFrame：
                - exchange: str, 交易所代码
                - trade_date: int, 交易日期，格式为YYYYMMDD
                - pretrade_date: int, 前一交易日，格式为YYYYMMDD
                - datestamp: int, 纳秒级时间戳
                - is_open: int, 是否为交易日
        """
        # 根据交易所类型自动选择交易所代码
        if exchange_type is not None:
            exchange = exchange_type.value
        
        # 如果没有指定交易所，则使用默认交易所
        if exchange is None:
            exchange = "SSE"
            
        # 处理日期范围
        current_year = datetime.now().year
        if start_date is None:
            # 如果没有指定开始日期，则使用1989年1月1日
            start_date = "19890101"
        else:
            # 统一日期格式
            if isinstance(start_date, (date, datetime)):
                start_date = start_date.strftime("%Y%m%d")
            elif isinstance(start_date, str):
                start_date = start_date.replace("-", "")
            elif isinstance(start_date, int):
                start_date = str(start_date)
        
        if end_date is None:
            # 如果没有指定结束日期，则使用当前年份的12月31日
            end_date = f"{current_year}1231"
        else:
            # 统一日期格式
            if isinstance(end_date, (date, datetime)):
                end_date = end_date.strftime("%Y%m%d")
            elif isinstance(end_date, str):
                end_date = end_date.replace("-", "")
            elif isinstance(end_date, int):
                end_date = str(end_date)
        
        # 获取交易日历
        df = ts.pro_api().trade_cal(
            exchange=exchange,
            start_date=start_date,
            end_date=end_date,
            fields=["exchange", "cal_date", "pretrade_date", "is_open"]
        )
        
        # 重命名列
        df = df.rename(columns={"cal_date": "trade_date"})
        
        # 转换日期格式
        df["trade_date"] = df["trade_date"].fillna(0).astype(int)
        df["pretrade_date"] = df["pretrade_date"].fillna(0).astype(int)
        
        # 添加时间戳
        df["datestamp"] = pd.to_datetime(df["trade_date"].astype(str)).astype(np.int64)
        
        return df
    
    def fetch_calendar(
        self,
        exchange: str,
        start_date: Optional[Union[str, int, datetime]] = None,
        end_date: Optional[Union[str, int, datetime]] = None
    ) -> pd.DataFrame:
        """获取交易日历
        
        Args:
            exchange: 交易所代码，SSE上交所 SZSE深交所 CFFEX中金所 SHFE上期所 CZCE郑商所 DCE大商所 INE上能源
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            
        Returns:
            pd.DataFrame: 包含以下列的DataFrame：
                - exchange: str, 交易所代码
                - trade_date: int, 交易日期，格式为YYYYMMDD
                - pretrade_date: int, 前一交易日，格式为YYYYMMDD
                - datestamp: int, 纳秒级时间戳
                - is_open: int, 是否为交易日
        """
        # 统一日期格式为YYYYMMDD
        if start_date is not None:
            if isinstance(start_date, str):
                start_date = start_date.replace("-", "")
            elif isinstance(start_date, datetime):
                start_date = start_date.strftime("%Y%m%d")
            start_date = int(start_date)
            
        if end_date is not None:
            if isinstance(end_date, str):
                end_date = end_date.replace("-", "")
            elif isinstance(end_date, datetime):
                end_date = end_date.strftime("%Y%m%d")
            end_date = int(end_date)
        
        # 获取交易日历
        df = self._get_cached_calendar(exchange)
        
        # 过滤日期范围
        if start_date is not None:
            df = df[df['trade_date'] >= start_date]
        if end_date is not None:
            df = df[df['trade_date'] <= end_date]
            
        # 确保返回的DataFrame包含所需的列
        if 'is_open' not in df.columns:
            df['is_open'] = 1  # 假设所有返回的日期都是交易日
            
        return df
    
    def is_trade_date(
        self,
        date: Union[str, int, datetime],
        exchange: str = "SSE"
    ) -> bool:
        """检查日期是否为交易日
        
        Args:
            date: 需要检查的日期
            exchange: 交易所代码，默认为SSE
            
        Returns:
            bool: 是否为交易日
        """
        # 统一日期格式为YYYYMMDD
        if isinstance(date, str):
            date = date.replace("-", "")
        elif isinstance(date, datetime):
            date = date.strftime("%Y%m%d")
        date = int(date)
        
        # 获取交易日历
        df = self._get_cached_calendar(exchange)
        df_date = df[df['trade_date'] == date]
        
        # 检查是否为交易日
        return bool(False if df_date.empty else df_date['is_open'].iloc[0] == 1)
    
    def batch_is_trade_date(
        self,
        dates: List[Union[str, int, datetime]],
        exchange: str = "SSE"
    ) -> Dict[str, bool]:
        """批量检查日期是否为交易日
        
        Args:
            dates: 需要检查的日期列表
            exchange: 交易所代码，默认为SSE
            
        Returns:
            Dict[str, bool]: 日期到是否为交易日的映射，日期格式为YYYYMMDD
        """
        # 统一日期格式为YYYYMMDD
        formatted_dates = []
        date_map = {}  # 用于存储原始日期格式到YYYYMMDD的映射
        
        for d in dates:
            if isinstance(d, str):
                formatted = d.replace("-", "")
            elif isinstance(d, datetime):
                formatted = d.strftime("%Y%m%d")
            else:
                formatted = str(d)
                
            formatted_dates.append(int(formatted))
            date_map[int(formatted)] = int(formatted)
        
        # 获取交易日历
        df = self._get_cached_calendar(exchange)
        
        # 生成结果
        result = {}
        for d in formatted_dates:
            df_date = df[df['trade_date'] == d]
            is_trade = bool(False if df_date.empty else df_date['is_open'].iloc[0] == 1)
            result[d] = is_trade
            
        return result
    
    def get_previous_trade_date(
        self,
        date: Union[str, int, datetime],
        n: int = 1,
        include_input_date: bool = False,
        exchange: str = "SSE",
        start_date: Optional[Union[str, int, date, datetime]] = None,
        end_date: Optional[Union[str, int, date, datetime]] = None
    ) -> int:
        """获取前N个交易日
        
        Args:
            date: 当前日期
            n: 往前数第N个交易日，默认为1
            include_input_date: 如果输入日期是交易日，是否将其纳入统计，默认为False
            exchange: 交易所代码，默认为SSE
            start_date: 开始日期，可选
            end_date: 结束日期，可选
            
        Returns:
            往前数第N个交易日，格式为YYYYMMDD
            如果找不到对应的交易日，返回None
        """
        # 统一日期格式为YYYYMMDD
        if isinstance(date, str):
            date = date.replace("-", "")
        elif isinstance(date, datetime):
            date = date.strftime("%Y%m%d")
        date = int(date)
        
        # 获取交易日历
        df = self._get_cached_calendar(exchange, start_date=start_date, end_date=end_date)
        
        # 获取所有交易日
        trade_dates = df[df["is_open"] == 1]["trade_date"].sort_values().reset_index(drop=True)
        
        # 找到当前日期的位置
        try:
            if include_input_date:
                mask = trade_dates <= date
            else:
                mask = trade_dates < date
                
            if not mask.any():
                return None
                
            current_idx = trade_dates[mask].index[-1]
            if current_idx - n + 1 < 0:  # 如果没有足够的前置交易日
                return None
                
            return int(trade_dates.iloc[current_idx - n + 1])
        except (IndexError, KeyError):
            return None
    
    def get_next_trade_date(
        self,
        date: Union[str, int, datetime],
        n: int = 1,
        include_input_date: bool = False,
        exchange: str = "SSE",
        start_date: Optional[Union[str, int, date, datetime]] = None,
        end_date: Optional[Union[str, int, date, datetime]] = None
    ) -> int:
        """获取后N个交易日
        
        Args:
            date: 当前日期
            n: 往后数第N个交易日，默认为1
            include_input_date: 如果输入日期是交易日，是否将其纳入统计，默认为False
            exchange: 交易所代码，默认为SSE
            start_date: 开始日期，可选
            end_date: 结束日期，可选
            
        Returns:
            往后数第N个交易日，格式为YYYYMMDD
            如果找不到对应的交易日，返回None
        """
        # 统一日期格式为YYYYMMDD
        if isinstance(date, str):
            date = date.replace("-", "")
        elif isinstance(date, datetime):
            date = date.strftime("%Y%m%d")
        date = int(date)
        
        # 获取交易日历
        df = self._get_cached_calendar(exchange, start_date=start_date, end_date=end_date)
        
        # 获取所有交易日
        trade_dates = df[df["is_open"] == 1]["trade_date"].sort_values().reset_index(drop=True)
        
        # 找到当前日期的位置
        try:
            if include_input_date:
                mask = trade_dates >= date
            else:
                mask = trade_dates > date
                
            if not mask.any():
                return None
                
            current_idx = trade_dates[mask].index[0]
            if current_idx + n - 1 >= len(trade_dates):  # 如果没有足够的后续交易日
                return None
                
            return int(trade_dates.iloc[current_idx + n - 1])
        except (IndexError, KeyError):
            return None

    def fetch_get_future_contracts(
        self,
        exchange: str = "DCE",
        spec_name: Union[str, List[str], None] = None,
        cursor_date: Optional[Union[str, int]] = None,
        fields: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Fetch future contract information from TuShare.
        从 Tushare 获取期货合约信息。

        Args:
            exchange: Exchange to fetch data from, defaults to DCE
                    要获取数据的交易所，默认为大商所
                Supported: ['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
                支持: ['SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
            spec_name: Chinese name of contract, defaults to None to fetch all
                     合约中文名称，默认为 None 获取所有品种
                Examples: ["豆粕", "棕榈油", ...]
                示例: ["豆粕", "棕榈油", ...]
            cursor_date: Reference date for filtering contracts, defaults to None to fetch all
                       过滤合约的参考日期，默认为 None 获取所有合约
                Format: int (YYYYMMDD) or str ('YYYY-MM-DD')
                格式：整数 (YYYYMMDD) 或字符串 ('YYYY-MM-DD')
            fields: Custom fields to return, defaults to None to return all fields
                   自定义返回字段，默认为 None 返回所有字段
                Examples: ['symbol', 'name', 'list_date', 'delist_date']
                示例: ['symbol', 'name', 'list_date', 'delist_date']

        Returns:
            DataFrame containing contract information
            包含合约信息的DataFrame

        Raises:
            ValueError: If invalid exchange or date format is provided
                      当提供的交易所或日期格式无效时
            RuntimeError: If API call fails
                        当API调用失败时
        """
        try:
            # 验证交易所
            if exchange not in self.future_exchanges:
                raise ValueError(f"Invalid exchange: {exchange}. Supported exchanges: {self.future_exchanges}")

            # 确保必要字段存在
            required_fields = ["list_date", "delist_date", "name", "ts_code"]
            if fields:
                fields.extend([f for f in required_fields if f not in fields])
                # 获取合约信息，只获取普通合约，不包括主力和连续合约
                data = self.pro.fut_basic(exchange=exchange, fut_type="1", fields=fields)
            else:
                data = self.pro.fut_basic(exchange=exchange, fut_type="1")

            if data.empty:
                # 返回带有正确列的空DataFrame
                return pd.DataFrame(columns=["qbcode", "symbol", "name", "chinese_name", "list_date", "delist_date", 
                                          "list_datestamp", "delist_datestamp", "exchange"])

            # 处理日期，转换为整数格式 YYYYMMDD
            for date_col in ["list_date", "delist_date"]:
                data[f"{date_col}stamp"] = pd.to_datetime(data[date_col].astype(str)).astype(np.int64) // 10**9
                data[date_col] = pd.to_datetime(data[date_col]).dt.strftime("%Y%m%d").astype(int)

            # 提取中文名称（去除空格）
            data["chinese_name"] = data["name"].apply(lambda x: re.match(r'(.+?)(?=\d{3,})', x).group(1).strip())
            
            # 处理合约代码
            data["exchange"] = exchange
            
            # 将 ts_code 格式从 "symbol.exchange" 转换为 "exchange.symbol"
            data["qbcode"] = data["ts_code"].apply(lambda x: x.split(".")[1] + "." + x.split(".")[0])
            
            # 根据交易所处理 symbol
            if exchange == "SHFE":
                # 上期所合约代码小写
                data["symbol"] = data["symbol"].apply(str.lower)
            elif exchange == "CZCE":
                # 郑商所合约代码大写
                data["symbol"] = data["symbol"].apply(str.upper)
            elif exchange == "DCE":
                # 大商所合约代码小写
                data["symbol"] = data["symbol"].apply(str.lower)
            elif exchange == "CFFEX":
                # 中金所合约代码大写
                data["symbol"] = data["symbol"].apply(str.upper)
            elif exchange == "INE":
                # 能源所合约代码小写
                data["symbol"] = data["symbol"].apply(str.lower)
            
            # 按品种名称过滤
            if spec_name:
                if isinstance(spec_name, str):
                    spec_name = [s.strip() for s in spec_name.split(",")]
                data = data[data["chinese_name"].isin(spec_name)]

            # 按日期过滤
            if cursor_date is not None:
                try:
                    # 将 cursor_date 转换为整数格式 YYYYMMDD
                    if isinstance(cursor_date, str):
                        cursor_date = int(pd.Timestamp(cursor_date).strftime("%Y%m%d"))
                    # 确保 list_date 和 delist_date 是整数类型
                    data["list_date"] = data["list_date"].astype(int)
                    data["delist_date"] = data["delist_date"].astype(int)
                    # 过滤合约
                    data = data[data["list_date"].astype(int) <= cursor_date]
                    data = data[data["delist_date"].astype(int) > cursor_date]
                except ValueError as e:
                    raise ValueError(f"Invalid cursor_date format: {cursor_date}. Error: {str(e)}")

            # 整理列顺序
            if "ts_code" in data.columns and fields is None:
                columns = ["qbcode"] + [col for col in data.columns if col not in ["qbcode", "ts_code"]]
            else:
                columns = ["qbcode"] + [col for col in data.columns if col != "qbcode"]
            data = data[columns]

            return data

        except Exception as e:
            raise RuntimeError(f"Failed to fetch future contracts: {str(e)}")
