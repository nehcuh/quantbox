# QuantBox 技术设计文档

## 1. 编码规则

### 1.1 证券代码规范

#### 1.1.1 A股代码规范

A股代码由以下部分组成：
1. 交易所代码
2. 证券代码

示例：
- SSE.600000：上交所浦发银行
- SZSE.000001：深交所平安银行

#### 1.1.2 交易所代码

| 交易所名称 | 交易所代码 | 官网地址 |
|------------|------------|----------|
| 上海证券交易所 | SSE | http://www.sse.com.cn |
| 深圳证券交易所 | SZSE | http://www.szse.cn |
| 北京证券交易所 | BSE | http://www.bse.cn |

### 1.2 期货代码规范

期货代码规范请参考 [期货编码规则](futures.md)

### 1.3 日期和时间处理

#### 日期格式
- 数据库存储格式：
  - `trade_date`: int，格式为 YYYYMMDD，例如 20240123
  - `pretrade_date`: int，格式为 YYYYMMDD
  - `datestamp`: int，纳秒级时间戳

- API 接口格式：
  - 输入：支持 str("2024-01-23")、datetime、date、int(20240123)
  - 输出：根据具体接口需求，统一使用 date_utils 模块进行转换

## 2. 接口命名规范

### 2.1 数据获取接口
- `fetch_get_*`: 从远程数据源获取数据
- `fetch_*`: 从本地数据库获取数据
- `batch_*`: 批量操作接口

示例：
```python
def fetch_get_calendar(self, exchange: str) -> pd.DataFrame:
    """从远程数据源获取交易日历"""
    pass

def fetch_calendar(self, exchange: str) -> pd.DataFrame:
    """从本地数据库获取交易日历"""
    pass

def batch_check_trade_dates(self, dates: List[Union[str, int, datetime]]) -> Dict[str, bool]:
    """批量检查日期是否为交易日"""
    pass
```

## 3. 数据库设计

### 3.1 交易日历表 (trade_dates)

```mongodb
{
    "exchange": "SSE",           # 交易所代码
    "trade_date": 20240123,      # 交易日期
    "pretrade_date": 20240122,   # 前一交易日
    "datestamp": 1705852800000000000,  # 纳秒级时间戳
}
```

索引设计：
- 主键：`(exchange, trade_date)`
- 二级索引：
  - `idx_exchange`: (exchange)
  - `idx_trade_date`: (trade_date)

## 4. 代码组织

```
quantbox/
│
├── config/                      # 配置文件目录
│   ├── __init__.py
│   ├── database_config.py      # 数据库配置
│   └── api_config.py           # API密钥等配置
│
├── data/                       # 数据相关目录
│   ├── __init__.py
│   ├── fetcher/               # 数据获取模块
│   │   ├── __init__.py
│   │   ├── base_fetcher.py    # 基础数据获取类
│   │   ├── tushare_fetcher.py # Tushare数据源
│   │   ├── tqsdk_fetcher.py   # 天勤量化数据源
│   │   ├── goldminer_fetcher.py # 掘金量化数据源
│   │   ├── wind_fetcher.py # Wind数据源
│   │   └── local_fetcher.py   # 本地数据获取
│   │
│   ├── cleaner/               # 数据清洗模块
│   │   ├── __init__.py
│   │   └── data_cleaner.py
│   │
│   └── processor/             # 数据加工模块
│       ├── __init__.py
│       └── data_processor.py
│
├── analysis/                   # 数据分析模块
│   ├── __init__.py
│   ├── technical/             # 技术分析
│   │   ├── __init__.py
│   │   └── indicators.py
│   └── fundamental/           # 基本面分析
│       ├── __init__.py
│       └── metrics.py
│
├── strategy/                  # 策略模块
│   ├── __init__.py
│   ├── base_strategy.py      # 基础策略类
│   └── strategies/           # 具体策略实现
│       ├── __init__.py
│       ├── momentum.py
│       └── mean_reversion.py
│
├── backtest/                 # 回测模块
│   ├── __init__.py
│   ├── engine.py            # 回测引擎
│   └── performance.py       # 绩效分析
│
├── optimization/            # 策略优化模块
│   ├── __init__.py
│   └── optimizer.py
│
├── trading/                # 实盘交易模块
│   ├── __init__.py
│   ├── broker/            # 券商接口
│   │   ├── __init__.py
│   │   └── base_broker.py
│   └── execution/         # 订单执行
│       ├── __init__.py
│       └── executor.py
│
├── utils/                 # 工具函数
│   ├── __init__.py
│   ├── logger.py         # 日志工具
│   └── helpers.py        # 辅助函数
│
├── db/                   # 数据库相关
│   ├── __init__.py
│   ├── models.py        # 数据模型
│   └── database.py      # 数据库连接
│
├── cache/               # 缓存相关
│   ├── __init__.py
│   └── cache_manager.py
│
├── tests/              # 测试目录
│   ├── __init__.py
│   └── test_*.py
│
├── notebooks/         # Jupyter notebooks
│   └── research.ipynb
│
├── examples/                       # 示例
│
├── requirements.txt   # 依赖包
├── setup.py          # 安装脚本
└── README.md         # 项目说明
```
