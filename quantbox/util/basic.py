from typing import Dict, Optional, List, Tuple
import os
import pymongo
import toml
import configparser
import json
import tushare as ts

class Config:
    def __init__(self, config_file: Optional[str] = None):
        """
        explanation:
            获取本地配置文件

        params:
            config_file ->
                含义: 配置存放文件, 默认从 `~/.quantbox/settings/config.toml` 中读取配置
                类型: str
                参数支持:  ~/.quantbox/settings/config.toml
        """
        default_config = os.path.join(os.path.expanduser("~"), ".quantbox", "settings", "config.toml")
        self.config_file = config_file or default_config
        self.config = {}

        if self.config_file.endswith(".ini"):
            self._load_ini_config()
        elif self.config_file.endswith(".toml"):
            self._load_toml_config()
        elif self.config_file.endswith(".json"):
            self._load_json_config()

        self.exchanges = ["SHSE", "SZSE", "SHFE", "DCE", "CFFEX", "CZCE", "INE"]
        self.stock_exchanges = ["SHSE", "SZSE"]
        self.future_exchanges = ["SHFE", "DCE", "CFFEX", "CZCE", "INE"]
        self.default_start = "1990-12-19"
        
        # 初始化MongoDB客户端
        self._init_mongodb()

    def _init_mongodb(self):
        """初始化MongoDB客户端连接"""
        if 'MONGODB' not in self.config:
            # 使用默认设置
            uri = 'mongodb://localhost:27017'
        else:
            # 从配置文件读取uri
            uri = self.config['MONGODB'].get('uri', 'mongodb://localhost:27017')
            
        self._client = pymongo.MongoClient(uri)

    @property
    def ts_token(self):
        """
        explanation:
            获取 tushare token
        """
        if 'TSPRO' not in self.config:
            raise ValueError(f"[ERROR]\t 配置文件中没有 TSPRO 配置")
        token = self.config["TSPRO"].get("token", None)
        if token is None:
            raise ValueError(f"[ERROR]\t TSPRO 配置中没有获取到 tushare token")
        return token

    @property
    def gm_token(self):
        """
        explanation:
            获取掘金量化 token 
        """
        if 'GM' not in self.config:
            raise ValueError(f"[ERROR]\t 配置文件中没有 GM 配置")
        token = self.config["GM"].get("token", None)
        if token is None:
            raise ValueError(f"[ERROR]\t GM 配置中没有获取到 gm token")
        return token

    @property
    def ts_pro(self):
        """
        explanation:
            获取 tushare pro 接口
        """
        return ts.pro_api(self.ts_token)

    @property
    def mongo_uri(self):
        """
        explanation:
            获取数据库链接
        """
        if "MONGODB" not in self.config:
            mongo_uri = "mongodb://localhost:27018"
        else:
            mongo_uri = self.config["MONGODB"].get("uri", None)
            if mongo_uri is None or len(mongo_uri) == 0:
                mongo_uri = "mongodb://localhost:27018"
        return mongo_uri

    @property
    def client(self):
        """
        explanation:
            获取 MONGODB 配置
        """
        return self._client

    def _load_ini_config(self):
        """
        explanation:
            内部方法，加载 .ini 格式配置文件
        """
        parser = configparser.ConfigParser()
        parser.read(self.config_file)
        for section in parser.sections():
            self.config[section] = {}
            for key, value in parser.items(section):
                self.config[section][key] = value

    def _load_json_config(self):
        """
        explanation:
            内部方法，加载 .json 格式配置文件
        """
        with open(self.config_file, "r", encoding="utf8") as f:
            self.config = json.load(f)

    def _load_toml_config(self):
        """
        explanation:
            内部方法，加载 .toml 格式配置文件
        """
        self.config = toml.load(self.config_file)

QUANTCONFIG = Config()
DATABASE = QUANTCONFIG.client.quantbox
TSPRO = QUANTCONFIG.ts_pro
EXCHANGES = QUANTCONFIG.exchanges
STOCK_EXCHANGES = QUANTCONFIG.stock_exchanges
FUTURE_EXCHANGES = QUANTCONFIG.future_exchanges
DEFAULT_START = QUANTCONFIG.default_start
