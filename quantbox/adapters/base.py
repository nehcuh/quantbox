"""
数据适配器基础接口定义

本模块定义了数据适配器的统一接口，所有具体的数据适配器都应该实现这些接口。
"""

from abc import ABC, abstractmethod
from typing import Optional, Union, List
import datetime
import pandas as pd

from quantbox.util.date_utils import DateLike


class IDataAdapter(ABC):
    """
    数据适配器接口

    所有数据适配器（LocalAdapter, TSAdapter, GMAdapter等）都应实现此接口，
    确保接口的一致性和可替换性。
    """

    @abstractmethod
    def get_trade_calendar(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        获取交易日历

        Args:
            exchanges: 交易所代码（标准格式）或列表，None 表示所有交易所
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame包含以下列：
            - date: 日期（int，YYYYMMDD格式）
            - exchange: 交易所代码（标准格式）
            - is_open: 是否交易日（bool）

        Raises:
            ValueError: 参数无效
            ConnectionError: 连接失败
        """
        pass

    @abstractmethod
    def get_future_contracts(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        symbols: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        获取期货合约信息

        Args:
            exchanges: 交易所代码或列表
            symbols: 合约代码或列表（标准格式：EXCHANGE.symbol）
            spec_names: 品种名称或列表（如 rb, m, SR等）
            date: 查询日期，None 表示最新

        Returns:
            DataFrame包含合约信息，包括：
            - symbol: 合约代码（标准格式）
            - exchange: 交易所
            - name: 合约名称
            - spec_name: 品种名称
            - list_date: 上市日期
            - delist_date: 摘牌日期
            等字段

        Raises:
            ValueError: 参数无效
        """
        pass

    @abstractmethod
    def get_future_daily(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """
        获取期货日线数据

        Args:
            symbols: 合约代码或列表（标准格式）
            exchanges: 交易所代码或列表
            start_date: 开始日期
            end_date: 结束日期
            date: 单日查询（与 start_date/end_date 互斥）

        Returns:
            DataFrame包含日线数据：
            - date: 日期（int）
            - symbol: 合约代码（标准格式）
            - exchange: 交易所
            - open: 开盘价
            - high: 最高价
            - low: 最低价
            - close: 收盘价
            - volume: 成交量
            - amount: 成交额
            - oi: 持仓量
            等字段

        Raises:
            ValueError: 参数无效
        """
        pass

    @abstractmethod
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
        获取期货持仓数据

        Args:
            symbols: 合约代码或列表
            exchanges: 交易所代码或列表
            spec_names: 品种名称或列表
            start_date: 开始日期
            end_date: 结束日期
            date: 单日查询

        Returns:
            DataFrame包含持仓数据：
            - date: 日期
            - symbol: 合约代码
            - exchange: 交易所
            - broker: 席位名称
            - vol: 持仓量
            - vol_chg: 持仓变化
            - rank: 排名
            等字段

        Raises:
            ValueError: 参数无效
        """
        pass

    @abstractmethod
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
        获取股票列表

        Args:
            symbols: 股票代码或列表（标准格式）
            names: 股票名称或列表
            exchanges: 交易所代码或列表（如 SSE, SZSE, BSE）
            markets: 市场板块或列表（如 主板, 创业板, 科创板, CDR, 北交所）
            list_status: 上市状态（'L' 上市, 'D' 退市, 'P' 暂停上市）
            is_hs: 沪港通状态（'N' 否, 'H' 沪股通, 'S' 深股通）

        Returns:
            DataFrame包含股票信息：
            - symbol: 股票代码（标准格式）
            - name: 股票名称
            - exchange: 交易所
            - list_date: 上市日期
            - delist_date: 退市日期（可选）
            - industry: 所属行业
            - area: 地区
            等字段

        Raises:
            ValueError: 参数无效
        """
        pass

    @abstractmethod
    def check_availability(self) -> bool:
        """
        检查数据源是否可用

        Returns:
            bool: 是否可用
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """适配器名称"""
        pass


class BaseDataAdapter(IDataAdapter):
    """
    数据适配器基类

    提供通用的功能实现，减少子类重复代码。
    """

    def __init__(self, name: str):
        """
        初始化基础适配器

        Args:
            name: 适配器名称
        """
        self._name = name

    @property
    def name(self) -> str:
        """适配器名称"""
        return self._name

    def _validate_date_range(
        self,
        start_date: Optional[DateLike],
        end_date: Optional[DateLike],
        date: Optional[DateLike],
    ) -> None:
        """
        验证日期范围参数

        Args:
            start_date: 开始日期
            end_date: 结束日期
            date: 单日查询

        Raises:
            ValueError: 参数冲突或无效
        """
        if date is not None and (start_date is not None or end_date is not None):
            raise ValueError(
                "参数 'date' 与 'start_date'/'end_date' 互斥，请只使用其中一种方式"
            )

    def _validate_symbol_params(
        self,
        symbols: Optional[Union[str, List[str]]],
        exchanges: Optional[Union[str, List[str]]],
        spec_names: Optional[Union[str, List[str]]],
    ) -> None:
        """
        验证合约相关参数

        Args:
            symbols: 合约代码
            exchanges: 交易所代码
            spec_names: 品种名称

        Raises:
            ValueError: 所有参数都为空时抛出
        """
        if symbols is None and exchanges is None and spec_names is None:
            raise ValueError(
                "必须至少指定 'symbols'、'exchanges' 或 'spec_names' 中的一个"
            )

    # 抽象方法需要在子类中实现
    def get_trade_calendar(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        raise NotImplementedError(f"{self.name} 未实现 get_trade_calendar 方法")

    def get_future_contracts(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        symbols: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        raise NotImplementedError(f"{self.name} 未实现 get_future_contracts 方法")

    def get_future_daily(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        raise NotImplementedError(f"{self.name} 未实现 get_future_daily 方法")

    def get_future_holdings(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        raise NotImplementedError(f"{self.name} 未实现 get_future_holdings 方法")

    def get_stock_list(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        names: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        markets: Optional[Union[str, List[str]]] = None,
        list_status: Union[str, List[str], None] = "L",
        is_hs: Optional[str] = None,
    ) -> pd.DataFrame:
        raise NotImplementedError(f"{self.name} 未实现 get_stock_list 方法")

    def check_availability(self) -> bool:
        """默认返回 True，子类可以重写"""
        return True
