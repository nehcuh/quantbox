"""Mock data generator for testing"""

import pandas as pd
from datetime import datetime, timedelta


class MockData:
    """Mock data generator for testing"""
    
    def __init__(self):
        """Initialize mock data"""
        self._trade_dates = {
            "SSE": [
                "2023-12-25", "2023-12-26", "2023-12-27", "2023-12-28", "2023-12-29",
                "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
                "2024-01-08", "2024-01-09", "2024-01-10", "2024-01-11", "2024-01-12",
                "2024-01-15", "2024-01-16", "2024-01-17", "2024-01-18", "2024-01-19"
            ],
            "SZSE": [
                "2023-12-25", "2023-12-26", "2023-12-27", "2023-12-28", "2023-12-29",
                "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
                "2024-01-08", "2024-01-09", "2024-01-10", "2024-01-11", "2024-01-12",
                "2024-01-15", "2024-01-16", "2024-01-17", "2024-01-18", "2024-01-19"
            ],
            "CFFEX": [
                "2023-12-25", "2023-12-26", "2023-12-27", "2023-12-28", "2023-12-29",
                "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
                "2024-01-08", "2024-01-09", "2024-01-10", "2024-01-11", "2024-01-12",
                "2024-01-15", "2024-01-16", "2024-01-17", "2024-01-18", "2024-01-19"
            ]
        }
    
    def generate_calendar_data(self, exchange: str) -> pd.DataFrame:
        """Generate calendar data for testing"""
        # 生成日期范围
        start_date = datetime(2023, 12, 25)  # 从 12 月 25 日开始
        end_date = datetime(2024, 1, 19)   # 到 1 月 19 日结束
        date_range = []
        current_date = start_date
        while current_date <= end_date:
            date_range.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)
        
        # 生成日历数据
        data = []
        for date in date_range:
            data.append({
                "exchange": exchange,
                "trade_date": date,
                "is_open": 1 if date in self._trade_dates[exchange] else 0,
                "pretrade_date": self._get_previous_trade_date(exchange, date),
                "datestamp": int(datetime.strptime(date, "%Y-%m-%d").timestamp() * 1_000_000_000)
            })
        
        return pd.DataFrame(data)
    
    def _get_previous_trade_date(self, exchange: str, date: str) -> str:
        """Get previous trade date"""
        trade_dates = self._trade_dates[exchange]
        try:
            idx = trade_dates.index(date)
            if idx > 0:
                return trade_dates[idx - 1]
        except ValueError:
            # 如果当前日期不是交易日，找到前一个交易日
            dt = datetime.strptime(date, "%Y-%m-%d")
            while dt.strftime("%Y-%m-%d") not in trade_dates:
                dt -= timedelta(days=1)
                if dt < datetime(2023, 12, 25):
                    return ""
            return dt.strftime("%Y-%m-%d")
        return ""
    
    @staticmethod
    def generate_stock_basic_data(count=10):
        """Generate mock stock basic data
        
        Args:
            count (int): Number of stocks to generate
            
        Returns:
            pd.DataFrame: Mock stock basic data
        """
        symbols = [f"00{i:04d}" for i in range(count)]
        names = [f"Stock{i}" for i in range(count)]
        areas = ["深圳", "上海", "北京"] * ((count + 2) // 3)
        industries = ["科技", "金融", "医药", "能源"] * ((count + 3) // 4)
        
        df = pd.DataFrame({
            "ts_code": [f"{s}.SZ" if i % 2 == 0 else f"{s}.SH" for i, s in enumerate(symbols)],
            "symbol": symbols,
            "name": names,
            "area": areas[:count],
            "industry": industries[:count],
            "list_date": ["20100101"] * count,
            "market": ["主板"] * count,
        })
        
        return df
