from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class LogConfig:
    """日志配置"""
    level: str = "INFO"
    file: str = "~/.settings/quantbox/logs/quantbox.log"
    console: bool = True
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    max_size: int = 10  # MB
    backup_count: int = 5
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "level": self.level,
            "file": self.file,
            "console": self.console,
            "format": self.format,
            "max_size": self.max_size,
            "backup_count": self.backup_count
        }
