"""
TSAdapter - Tushare 数据适配器

从 Tushare API 获取市场数据
"""

from typing import Optional, Union, List
import datetime
import pandas as pd

from quantbox.adapters.base import BaseDataAdapter
from quantbox.util.date_utils import DateLike, date_to_int
from quantbox.util.exchange_utils_new import denormalize_exchange, validate_exchanges
from quantbox.util.contract_utils_new import normalize_contracts, format_contracts, ContractFormat
from quantbox.util.basic import TSPRO


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
        self.pro = token or TSPRO
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
        raise NotImplementedError("TSAdapter 的 get_future_contracts 方法尚未实现")
    
    def get_future_daily(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """从 Tushare 获取期货日线数据"""
        raise NotImplementedError("TSAdapter 的 get_future_daily 方法尚未实现")
    
    def get_future_holdings(
        self,
        symbols: Optional[Union[str, List[str]]] = None,
        exchanges: Optional[Union[str, List[str]]] = None,
        spec_names: Optional[Union[str, List[str]]] = None,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
        date: Optional[DateLike] = None,
    ) -> pd.DataFrame:
        """从 Tushare 获取期货持仓数据"""
        raise NotImplementedError("TSAdapter 的 get_future_holdings 方法尚未实现")
