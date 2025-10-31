"""
MarketDataService - 统一的市场数据查询服务

提供统一的市场数据查询接口，自动选择合适的数据源（本地优先）
"""

from typing import Optional, Union, List
import datetime
import pandas as pd

from quantbox.adapters.base import BaseDataAdapter
from quantbox.adapters.local_adapter import LocalAdapter
from quantbox.adapters.ts_adapter import TSAdapter
from quantbox.util.date_utils import DateLike


class MarketDataService:
    """
    市场数据服务
    
    统一的数据查询接口，支持：
    - 自动选择数据源（本地优先，远程备用）
    - 交易日历查询
    - 期货合约信息查询
    - 期货日线数据查询
    - 期货持仓数据查询
    """
    
    def __init__(
        self,
        local_adapter: Optional[BaseDataAdapter] = None,
        remote_adapter: Optional[BaseDataAdapter] = None,
        prefer_local: bool = True
    ):
        """
        初始化市场数据服务
        
        Args:
            local_adapter: 本地数据适配器，默认使用 LocalAdapter
            remote_adapter: 远程数据适配器，默认使用 TSAdapter
            prefer_local: 是否优先使用本地数据源，默认为 True
        """
        self.local_adapter = local_adapter or LocalAdapter()
        self.remote_adapter = remote_adapter or TSAdapter()
        self.prefer_local = prefer_local
    
    def _get_adapter(self, use_local: Optional[bool] = None) -> BaseDataAdapter:
        """
        获取适配器
        
        Args:
            use_local: 是否使用本地适配器，None 表示根据 prefer_local 自动选择
        
        Returns:
            适配器实例
        """
        if use_local is None:
            use_local = self.prefer_local
        
        if use_local:
            # 检查本地适配器是否可用
            if self.local_adapter and self.local_adapter.check_availability():
                return self.local_adapter
            # 本地不可用，回退到远程
            return self.remote_adapter
        else:
            return self.remote_adapter
    
    def get_trade_calendar(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        use_local: Optional[bool] = None
    ) -> pd.DataFrame:
        """
        获取交易日历
        
        Args:
            exchanges: 交易所代码或列表，None 表示所有交易所
            start_date: 起始日期
            end_date: 结束日期
            use_local: 是否使用本地数据源，None 表示自动选择
        
        Returns:
            交易日历 DataFrame，包含字段：
            - date: 日期（整数格式 YYYYMMDD）
            - exchange: 交易所代码
            - is_open: 是否开市
        """
        adapter = self._get_adapter(use_local)
        return adapter.get_trade_calendar(
            exchanges=exchanges,
            start_date=start_date,
            end_date=end_date
        )
    
    def get_future_contracts(
        self,
        exchanges: Optional[Union[str, List[str]]] = None,
        symbols: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        date: Optional[DateLike] = None,
        use_local: Optional[bool] = None
    ) -> pd.DataFrame:
        """
        获取期货合约信息
        
        Args:
            exchanges: 交易所代码或列表
            symbols: 合约代码或列表
            spec_names: 品种名称或列表
            date: 查询日期（合约在该日期有效）
            use_local: 是否使用本地数据源，None 表示自动选择
        
        Returns:
            期货合约信息 DataFrame，包含字段：
            - symbol: 合约代码
            - exchange: 交易所代码
            - spec_name: 品种名称
            - name: 合约名称
            - list_date: 上市日期
            - delist_date: 退市日期
        """
        adapter = self._get_adapter(use_local)
        return adapter.get_future_contracts(
            exchanges=exchanges,
            symbols=symbols,
            spec_names=spec_names,
            date=date
        )
    
    def get_future_daily(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
        use_local: Optional[bool] = None
    ) -> pd.DataFrame:
        """
        获取期货日线数据
        
        Args:
            symbols: 合约代码或列表
            exchanges: 交易所代码或列表
            start_date: 起始日期（范围查询）
            end_date: 结束日期（范围查询）
            date: 单日查询日期
            use_local: 是否使用本地数据源，None 表示自动选择
        
        Returns:
            期货日线数据 DataFrame，包含字段：
            - symbol: 合约代码
            - exchange: 交易所代码
            - date: 日期（整数格式 YYYYMMDD）
            - open: 开盘价
            - high: 最高价
            - low: 最低价
            - close: 收盘价
            - volume: 成交量
            - amount: 成交金额
            - oi: 持仓量（可选）
        """
        adapter = self._get_adapter(use_local)
        return adapter.get_future_daily(
            symbols=symbols,
            exchanges=exchanges,
            start_date=start_date,
            end_date=end_date,
            date=date
        )
    
    def get_future_holdings(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
        use_local: Optional[bool] = None
    ) -> pd.DataFrame:
        """
        获取期货持仓数据
        
        Args:
            symbols: 合约代码或列表
            exchanges: 交易所代码或列表
            spec_names: 品种名称或列表
            start_date: 起始日期（范围查询）
            end_date: 结束日期（范围查询）
            date: 单日查询日期
            use_local: 是否使用本地数据源，None 表示自动选择
        
        Returns:
            期货持仓数据 DataFrame，包含字段：
            - symbol: 合约代码
            - exchange: 交易所代码
            - date: 日期（整数格式 YYYYMMDD）
            - broker: 会员名称
            - vol: 成交量
            - vol_chg: 成交量变化
            - long_hld: 多头持仓
            - long_chg: 多头持仓变化
            - short_hld: 空头持仓
            - short_chg: 空头持仓变化
        """
        adapter = self._get_adapter(use_local)
        return adapter.get_future_holdings(
            symbols=symbols,
            exchanges=exchanges,
            spec_names=spec_names,
            start_date=start_date,
            end_date=end_date,
            date=date
        )
