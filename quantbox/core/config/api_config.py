from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class ApiConfig:
    """API配置"""
    tushare_token: str = ""
    wind_token: str = ""
    tqsdk_account: str = ""
    tqsdk_password: str = ""
    goldminer_token: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "tushare_token": self.tushare_token,
            "wind_token": self.wind_token,
            "tqsdk_account": self.tqsdk_account,
            "tqsdk_password": self.tqsdk_password,
            "goldminer_token": self.goldminer_token
        }
