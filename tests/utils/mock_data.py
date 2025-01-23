"""Mock data for testing"""

import pandas as pd
from datetime import datetime, timedelta


class MockData:
    """Mock data generator for testing"""
    
    @staticmethod
    def generate_calendar_data(exchange="SSE", days=30):
        """Generate mock calendar data
        
        Args:
            exchange (str): Exchange name
            days (int): Number of days to generate
            
        Returns:
            pd.DataFrame: Mock calendar data
        """
        today = datetime.now()
        dates = []
        pretrade_dates = []
        
        current_date = today - timedelta(days=days)
        prev_date = current_date - timedelta(days=1)
        
        for _ in range(days):
            # Skip weekends
            while current_date.weekday() > 4:  # 5 is Saturday, 6 is Sunday
                current_date += timedelta(days=1)
            while prev_date.weekday() > 4:
                prev_date += timedelta(days=1)
                
            dates.append(current_date)
            pretrade_dates.append(prev_date)
            
            prev_date = current_date
            current_date += timedelta(days=1)
        
        df = pd.DataFrame({
            "exchange": [exchange] * len(dates),
            "trade_date": [d.strftime("%Y%m%d") for d in dates],
            "pretrade_date": [d.strftime("%Y%m%d") for d in pretrade_dates],
            "is_open": [1] * len(dates)
        })
        
        return df
    
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
