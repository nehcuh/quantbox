"""
配置加载器模块

该模块提供统一的配置加载和管理功能，支持：
- TOML 格式的配置文件加载
- 配置项的动态获取和缓存
- 配置验证和默认值处理
- 多配置文件的合并和管理

主要配置文件：
- exchanges.toml: 交易所基础信息和数据源映射
- instruments.toml: 交易品种详细信息
- trading_hours.toml: 交易时间配置
- fees_margin.toml: 手续费和保证金配置
"""

import os
import toml
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_DIR = Path(__file__).parent
EXCHANGES_CONFIG = CONFIG_DIR / "exchanges.toml"
INSTRUMENTS_CONFIG = CONFIG_DIR / "instruments.toml"
TRADING_HOURS_CONFIG = CONFIG_DIR / "trading_hours.toml"
FEES_MARGIN_CONFIG = CONFIG_DIR / "fees_margin.toml"


class ConfigLoader:
    """配置加载器类"""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化配置加载器

        Args:
            config_dir: 配置文件目录，默认为当前模块所在目录
        """
        self.config_dir = config_dir or CONFIG_DIR
        self._cache = {}

        # 配置文件映射
        self.config_files = {
            'exchanges': self.config_dir / "exchanges.toml",
            'instruments': self.config_dir / "instruments.toml",
            'trading_hours': self.config_dir / "trading_hours.toml",
            'fees_margin': self.config_dir / "fees_margin.toml"
        }

    def load_config(self, config_name: str, force_reload: bool = False) -> Dict[str, Any]:
        """
        加载指定的配置文件

        Args:
            config_name: 配置名称 ('exchanges', 'instruments', 'trading_hours', 'fees_margin')
            force_reload: 是否强制重新加载

        Returns:
            Dict[str, Any]: 配置数据

        Raises:
            FileNotFoundError: 配置文件不存在
            toml.TomlDecodeError: TOML 格式错误
        """
        if config_name not in self.config_files:
            raise ValueError(f"未知的配置名称: {config_name}")

        cache_key = f"{config_name}_config"

        # 检查缓存
        if not force_reload and cache_key in self._cache:
            return self._cache[cache_key]

        config_file = self.config_files[config_name]

        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_file}")

        try:
            config_data = toml.load(config_file)
            self._cache[cache_key] = config_data
            logger.debug(f"成功加载配置文件: {config_file}")
            return config_data
        except toml.TomlDecodeError as e:
            logger.error(f"TOML 格式错误 {config_file}: {e}")
            raise
        except Exception as e:
            logger.error(f"加载配置文件失败 {config_file}: {e}")
            raise

    def get_exchange_info(self, exchange_code: str) -> Optional[Dict[str, Any]]:
        """
        获取交易所信息

        Args:
            exchange_code: 交易所代码 (如 'SHFE', 'DCE')

        Returns:
            Optional[Dict[str, Any]]: 交易所信息，不存在返回 None
        """
        try:
            config = self.load_config('exchanges')
            exchanges = config.get('exchanges', {})
            return exchanges.get(exchange_code)
        except Exception as e:
            logger.error(f"获取交易所信息失败 {exchange_code}: {e}")
            return None

    def get_instrument_info(self, exchange_code: str, instrument_code: str) -> Optional[Dict[str, Any]]:
        """
        获取交易品种信息

        Args:
            exchange_code: 交易所代码
            instrument_code: 品种代码

        Returns:
            Optional[Dict[str, Any]]: 品种信息，不存在返回 None
        """
        try:
            config = self.load_config('instruments')
            instrument_key = f"{exchange_code}.{instrument_code}"
            instruments = config.get('instruments', {})
            return instruments.get(instrument_key)
        except Exception as e:
            logger.error(f"获取品种信息失败 {exchange_code}.{instrument_code}: {e}")
            return None

    def get_trading_hours(self, exchange_code: str, instrument_code: Optional[str] = None) -> Dict[str, Any]:
        """
        获取交易时间配置

        Args:
            exchange_code: 交易所代码
            instrument_code: 品种代码，可选

        Returns:
            Dict[str, Any]: 交易时间配置
        """
        try:
            config = self.load_config('trading_hours')

            # 优先查找品种特定配置
            if instrument_code:
                instrument_key = f"{exchange_code}.{instrument_code}"
                instrument_hours = config.get(instrument_key)
                if instrument_hours:
                    return instrument_hours

            # 查找交易所默认配置
            exchange_hours = config.get(exchange_code)
            if exchange_hours:
                return exchange_hours

            # 返回全局默认配置
            return config.get('default', {})

        except Exception as e:
            logger.error(f"获取交易时间失败 {exchange_code}.{instrument_code}: {e}")
            return {}

    def get_fee_config(self, exchange_code: str, instrument_code: str) -> Dict[str, Any]:
        """
        获取手续费配置

        Args:
            exchange_code: 交易所代码
            instrument_code: 品种代码

        Returns:
            Dict[str, Any]: 手续费配置
        """
        try:
            config = self.load_config('fees_margin')
            fee_key = f"{exchange_code}.{instrument_code}"
            fees = config.get('fees', {})
            fee_config = fees.get(fee_key)

            if fee_config:
                return fee_config

            # 返回默认手续费配置
            return fees.get('default', {})

        except Exception as e:
            logger.error(f"获取手续费配置失败 {exchange_code}.{instrument_code}: {e}")
            return {}

    def get_margin_config(self, exchange_code: str, instrument_code: str) -> Dict[str, Any]:
        """
        获取保证金配置

        Args:
            exchange_code: 交易所代码
            instrument_code: 品种代码

        Returns:
            Dict[str, Any]: 保证金配置
        """
        try:
            config = self.load_config('fees_margin')
            margin_key = f"{exchange_code}.{instrument_code}"
            margins = config.get('margin', {})
            margin_config = margins.get(margin_key)

            if margin_config:
                return margin_config

            # 返回默认保证金配置
            return margins.get('default', {})

        except Exception as e:
            logger.error(f"获取保证金配置失败 {exchange_code}.{instrument_code}: {e}")
            return {}

    def get_data_source_mapping(self, data_source: str) -> Dict[str, str]:
        """
        获取数据源交易所映射

        Args:
            data_source: 数据源名称 ('goldminer', 'tushare', 'joinquant')

        Returns:
            Dict[str, str]: 交易所代码映射
        """
        try:
            config = self.load_config('exchanges')
            data_sources = config.get('data_sources', {})
            return data_sources.get(data_source, {})
        except Exception as e:
            logger.error(f"获取数据源映射失败 {data_source}: {e}")
            return {}

    def list_exchanges(self, market_type: Optional[str] = None) -> List[str]:
        """
        列出所有交易所

        Args:
            market_type: 市场类型过滤 ('futures', 'stock')

        Returns:
            List[str]: 交易所代码列表
        """
        try:
            config = self.load_config('exchanges')
            exchanges_config = config.get('exchanges', {})

            if market_type:
                return [
                    code for code, info in exchanges_config.items()
                    if info.get('market_type') == market_type
                ]

            return list(exchanges_config.keys())
        except Exception as e:
            logger.error(f"列出交易所失败: {e}")
            return []

    def list_instruments(self, exchange_code: str) -> List[str]:
        """
        列出指定交易所的所有品种

        Args:
            exchange_code: 交易所代码

        Returns:
            List[str]: 品种代码列表
        """
        try:
            config = self.load_config('instruments')
            instruments = []

            for key, info in config.items():
                if key == 'instruments' and isinstance(info, dict):
                    for instrument_key in info.keys():
                        if '.' in instrument_key:
                            exch, instr = instrument_key.split('.', 1)
                            if exch == exchange_code:
                                instruments.append(instr)

            return instruments
        except Exception as e:
            logger.error(f"列出品种失败 {exchange_code}: {e}")
            return []

    def validate_instrument(self, exchange_code: str, instrument_code: str) -> bool:
        """
        验证品种是否存在

        Args:
            exchange_code: 交易所代码
            instrument_code: 品种代码

        Returns:
            bool: 是否有效
        """
        info = self.get_instrument_info(exchange_code, instrument_code)
        return info is not None

    def clear_cache(self):
        """清空配置缓存"""
        self._cache.clear()
        logger.debug("配置缓存已清空")

    def reload_all_configs(self):
        """重新加载所有配置文件"""
        self.clear_cache()
        for config_name in self.config_files.keys():
            self.load_config(config_name)
        logger.info("所有配置文件已重新加载")

    def get_mongodb_client(self):
        """获取 MongoDB 客户端连接"""
        import pymongo
        import os

        # 从环境变量或配置获取 MongoDB URI
        mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')

        try:
            config = self.load_config('exchanges')
            if 'mongodb' in config:
                mongodb_uri = config['mongodb'].get('uri', mongodb_uri)
        except:
            pass

        return pymongo.MongoClient(mongodb_uri)

    def get_mongodb_uri(self):
        """获取 MongoDB URI"""
        import os

        # 从环境变量或配置获取 MongoDB URI
        mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')

        try:
            config = self.load_config('exchanges')
            if 'mongodb' in config:
                mongodb_uri = config['mongodb'].get('uri', mongodb_uri)
        except:
            pass

        return mongodb_uri

    def get_tushare_token(self):
        """获取 Tushare token"""
        try:
            config = self.load_config('exchanges')
            if 'tushare' in config:
                return config['tushare'].get('token')
        except Exception as e:
            logger.error(f"获取 Tushare token 失败: {e}")
            return None

    def get_tushare_pro(self):
        """获取 Tushare Pro 接口"""
        import tushare as ts
        token = self.get_tushare_token()
        if token:
            return ts.pro_api(token)
        return None

    def get_gm_token(self):
        """获取掘金 token"""
        try:
            config = self.load_config('exchanges')
            if 'goldminer' in config:
                return config['goldminer'].get('token')
        except Exception as e:
            logger.error(f"获取掘金 token 失败: {e}")
            return None


# 全局配置加载器实例
_config_loader = None


def get_config_loader() -> ConfigLoader:
    """获取全局配置加载器实例"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def reload_configs():
    """重新加载所有配置"""
    loader = get_config_loader()
    loader.reload_all_configs()


# 便捷函数
def get_exchange_info(exchange_code: str) -> Optional[Dict[str, Any]]:
    """获取交易所信息"""
    return get_config_loader().get_exchange_info(exchange_code)


def get_instrument_info(exchange_code: str, instrument_code: str) -> Optional[Dict[str, Any]]:
    """获取品种信息"""
    return get_config_loader().get_instrument_info(exchange_code, instrument_code)


def get_trading_hours(exchange_code: str, instrument_code: Optional[str] = None) -> Dict[str, Any]:
    """获取交易时间"""
    return get_config_loader().get_trading_hours(exchange_code, instrument_code)


def get_fee_config(exchange_code: str, instrument_code: str) -> Dict[str, Any]:
    """获取手续费配置"""
    return get_config_loader().get_fee_config(exchange_code, instrument_code)


def get_margin_config(exchange_code: str, instrument_code: str) -> Dict[str, Any]:
    """获取保证金配置"""
    return get_config_loader().get_margin_config(exchange_code, instrument_code)


def get_data_source_mapping(data_source: str) -> Dict[str, str]:
    """获取数据源映射"""
    return get_config_loader().get_data_source_mapping(data_source)


def list_futures_exchanges() -> List[str]:
    """列出期货交易所"""
    return get_config_loader().list_exchanges('futures')


def list_stock_exchanges() -> List[str]:
    """列出股票交易所"""
    return get_config_loader().list_exchanges('stock')


def list_instruments(exchange_code: str) -> List[str]:
    """列出交易所品种"""
    return get_config_loader().list_instruments(exchange_code)


def get_trading_hours(exchange_code: str, instrument_code: Optional[str] = None) -> Dict[str, Any]:
    """获取交易时间"""
    return get_config_loader().get_trading_hours(exchange_code, instrument_code)


def get_fee_config(exchange_code: str, instrument_code: str) -> Dict[str, Any]:
    """获取手续费配置"""
    return get_config_loader().get_fee_config(exchange_code, instrument_code)


def get_margin_config(exchange_code: str, instrument_code: str) -> Dict[str, Any]:
    """获取保证金配置"""
    return get_config_loader().get_margin_config(exchange_code, instrument_code)


def validate_instrument(exchange_code: str, instrument_code: str) -> bool:
    """验证品种"""
    return get_config_loader().validate_instrument(exchange_code, instrument_code)