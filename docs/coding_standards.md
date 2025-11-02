# Quantbox 编码规范

## 1. 日期和时间格式规范

### 1.1 日期格式标准

**统一使用以下日期格式：**

| 用途 | 格式 | 示例 | 说明 |
|------|------|------|------|
| 数据库存储（主要） | `YYYY-MM-DD` 字符串 | `"2024-01-15"` | 便于阅读和排序 |
| 时间戳字段 | Unix 时间戳（float） | `1705276800.0` | 用于高效查询 |
| 整数日期（辅助） | `YYYYMMDD` 整数 | `20240115` | 用于快速比较 |
| API 传参 | 兼容多种格式 | 见下方 | 自动转换为标准格式 |

### 1.2 日期参数接收规则

**所有接受日期参数的函数应支持以下格式：**

```python
# 支持的输入格式
date_inputs = [
    "2024-01-15",           # 字符串（带连字符）
    "20240115",             # 字符串（无连字符）
    20240115,               # 整数
    datetime.date(2024, 1, 15),  # date 对象
    datetime.datetime(2024, 1, 15, 10, 30),  # datetime 对象
]
```

### 1.3 日期工具函数

**统一使用 `quantbox.util.date_utils` 模块中的函数：**

```python
from quantbox.util.date_utils import (
    date_to_int,           # 转为整数格式
    int_to_date_str,       # 整数转为字符串
    util_make_date_stamp,  # 转为时间戳
)
```

## 2. 交易所代码规范

### 2.1 交易所代码标准

**统一使用以下交易所代码（MongoDB 存储格式）：**

| 交易所 | 标准代码 | 说明 |
|--------|----------|------|
| 上海证券交易所 | `SHSE` | 注意不是 SSE |
| 深圳证券交易所 | `SZSE` | |
| 上海期货交易所 | `SHFE` | |
| 大连商品交易所 | `DCE` | |
| 中国金融期货交易所 | `CFFEX` | |
| 郑州商品交易所 | `CZCE` | |
| 上海国际能源交易中心 | `INE` | |

### 2.2 交易所代码转换

**使用 `quantbox.util.exchange_utils` 进行代码转换：**

```python
from quantbox.util.exchange_utils import (
    normalize_exchange,    # 标准化单个交易所代码
    validate_exchanges,    # 验证并标准化交易所列表
)

# 示例
normalize_exchange("SSE")  # 返回 "SHSE"
validate_exchanges(["SSE", "SZSE"])  # 返回 ["SHSE", "SZSE"]
```

### 2.3 外部 API 映射

不同数据源使用不同的交易所代码，需要进行映射：

| 标准代码 | TuShare | 掘金量化 |
|---------|---------|----------|
| SHSE | SSE | SHSE |
| SZSE | SZSE | SZSE |
| SHFE | SHF (注意) | SHFE |
| CZCE | ZCE (注意) | CZCE |
| CFFEX | CFFEX | CFFEX |
| DCE | DCE | DCE |
| INE | INE | INE |
| GFEX | GFEX | GFEX |

**掘金量化合约代码大小写规则：**

| 交易所 | 合约代码大小写 | 示例 | 说明 |
|--------|----------------|------|------|
| SHFE | 小写 | SHFE.rb2501 | 上期所期货合约使用小写 |
| DCE | 小写 | DCE.m2501 | 大商所期货合约使用小写 |
| INE | 小写 | INE.sc2409 | 上期能源期货合约使用小写 |
| GFEX | 小写 | GFEX.lc2405 | 广期所期货合约使用小写 |
| CFFEX | 大写 | CFFEX.IF2412 | 中金所期货合约使用大写 |
| CZCE | 大写+3位月 | CZCE.SR501 | 郑商所：大写+3位月份数字 |

## 3. 合约代码规范

### 3.1 期货合约代码格式

**数据库存储格式：**

```python
# 格式：品种代码 + 年月（统一4位数字）
examples = [
    "m2501",     # 豆粕 2025年1月
    "rb2505",    # 螺纹钢 2025年5月
    "IF2412",    # 沪深300期指（大写，中金所特殊）
    "SR2501",    # 白糖 2025年1月（郑商所，数据库统一4位）
]
```

**规则：**
- 数据库统一存储：品种代码 + 4位数字（YYMM）
- 大小写规则：
  - DCE、SHFE、INE、GFEX：品种代码小写
  - CFFEX、CZCE：品种代码大写

**掘金量化API格式：**
```python
# 不同交易所的大小写规则
goldminer_formats = [
    "SHFE.rb2501",    # 上期所：小写
    "DCE.m2501",      # 大商所：小写  
    "CFFEX.IF2412",   # 中金所：大写
    "CZCE.SR501",     # 郑商所：大写 + 3位月份数字
    "INE.sc2409",     # 上期能源：小写
    "GFEX.lc2405",    # 广期所：小写
]
```

**郑商所特殊规则：**
- 数据库存储：SR2501（4位年月）
- 掘金格式：CZCE.SR501（3位年月，去掉年份的第一位）

### 3.2 股票代码格式

**格式：交易所.代码**

```python
examples = [
    "SHSE.600000",  # 浦发银行
    "SZSE.000001",  # 平安银行
]
```

## 4. 数据库字段规范

### 4.1 交易日历（trade_date collection）

```python
{
    "exchange": "SHSE",              # 交易所代码（标准格式）
    "trade_date": "2024-01-15",      # 交易日期（主字段）
    "pretrade_date": "2024-01-12",   # 前一交易日
    "datestamp": 1705276800.0,       # Unix 时间戳
    "date_int": 20240115             # 整数日期（索引字段）
}
```

### 4.2 期货合约（future_contracts collection）

```python
{
    "exchange": "DCE",                      # 交易所代码
    "symbol": "m2501",                      # 合约代码
    "name": "豆粕2501",                     # 合约名称
    "chinese_name": "豆粕",                 # 品种中文名
    "list_date": "2024-01-01",             # 上市日期
    "delist_date": "2025-01-15",           # 退市日期
    "list_datestamp": 1704067200.0,        # 上市时间戳
    "delist_datestamp": 1736870400.0,      # 退市时间戳
}
```

### 4.3 期货日线（future_daily collection）

```python
{
    "symbol": "m2501",                 # 合约代码
    "exchange": "DCE",                 # 交易所代码
    "trade_date": "2024-01-15",        # 交易日期
    "open": 3500.0,                    # 开盘价
    "high": 3550.0,                    # 最高价
    "low": 3480.0,                     # 最低价
    "close": 3520.0,                   # 收盘价
    "settle": 3515.0,                  # 结算价
    "vol": 125000,                     # 成交量
    "amount": 43750000.0,              # 成交额
    "oi": 85000,                       # 持仓量
    "datestamp": 1705276800.0          # 时间戳
}
```

### 4.4 期货持仓（future_holdings collection）

```python
{
    "trade_date": "2024-01-15",        # 交易日期
    "symbol": "m2501",                 # 合约代码
    "exchange": "DCE",                 # 交易所代码
    "broker": "中信期货",               # 席位名称
    "vol": 15000,                      # 持仓量
    "vol_chg": 1200,                   # 持仓变化
    "long_hld": 8000,                  # 多头持仓
    "long_chg": 600,                   # 多头变化
    "short_hld": 7000,                 # 空头持仓
    "short_chg": 600,                  # 空头变化
    "datestamp": 1705276800.0          # 时间戳
}
```

## 5. 命名规范

### 5.1 变量命名

```python
# 日期相关
trade_date          # 交易日期
start_date          # 起始日期
end_date            # 结束日期
cursor_date         # 参考日期

# 交易所相关
exchange            # 单个交易所
exchanges           # 交易所列表

# 合约相关
symbol              # 单个合约代码
symbols             # 合约代码列表
spec_name           # 品种名称
spec_names          # 品种名称列表
```

### 5.2 函数命名

**数据获取函数：**
```python
fetch_trade_dates()         # 获取交易日历
fetch_future_contracts()    # 获取期货合约
fetch_future_daily()        # 获取期货日线
fetch_future_holdings()     # 获取期货持仓
```

**数据保存函数：**
```python
save_trade_dates()          # 保存交易日历
save_future_contracts()     # 保存期货合约
save_future_daily()         # 保存期货日线
save_future_holdings()      # 保存期货持仓
```

## 6. 函数参数规范

### 6.1 日期参数

```python
def fetch_data(
    start_date: Union[str, int, datetime.date, None] = None,
    end_date: Union[str, int, datetime.date, None] = None,
    cursor_date: Union[str, int, datetime.date, None] = None,
) -> pd.DataFrame:
    """
    Args:
        start_date: 起始日期，支持多种格式（YYYY-MM-DD, YYYYMMDD, 整数, date对象）
        end_date: 结束日期，格式同 start_date
        cursor_date: 参考日期，用于单日查询
    """
    pass
```

### 6.2 交易所参数

```python
def fetch_data(
    exchanges: Union[str, List[str], None] = None,
) -> pd.DataFrame:
    """
    Args:
        exchanges: 交易所代码，可以是：
            - None: 使用默认交易所列表
            - 字符串: 单个交易所，如 "SHSE" 或 "SSE"（自动转换）
            - 列表: 多个交易所，如 ["SHSE", "SZSE"]
    """
    pass
```

### 6.3 合约参数

```python
def fetch_data(
    symbols: Union[str, List[str], None] = None,
    spec_names: Union[str, List[str], None] = None,
) -> pd.DataFrame:
    """
    Args:
        symbols: 合约代码，支持单个或列表
        spec_names: 品种名称，支持单个或列表
    """
    pass
```

## 7. 错误处理规范

### 7.1 参数验证

```python
def fetch_data(date: str) -> pd.DataFrame:
    # 1. 验证必需参数
    if date is None:
        raise ValueError("date parameter is required")
    
    # 2. 验证参数格式
    try:
        normalized_date = date_to_int(date)
    except ValueError as e:
        raise ValueError(f"Invalid date format: {date}") from e
    
    # 3. 验证参数值
    if normalized_date > date_to_int(datetime.date.today()):
        raise ValueError(f"Date {date} is in the future")
```

### 7.2 异常传播

```python
def high_level_function():
    try:
        data = fetch_data()
    except ValueError as e:
        # 添加上下文信息后重新抛出
        raise ValueError(f"Failed to fetch data: {str(e)}") from e
    except Exception as e:
        # 未预期的错误，记录日志后抛出
        logger.error(f"Unexpected error: {str(e)}")
        raise
```

## 8. 日志规范

### 8.1 日志级别

```python
import logging

# DEBUG: 详细的调试信息
logger.debug(f"Query params: {query}")

# INFO: 正常的业务流程信息
logger.info(f"Fetching data for {exchange} from {start_date} to {end_date}")

# WARNING: 警告信息，不影响主流程
logger.warning(f"No data found for {symbol} on {date}")

# ERROR: 错误信息，但程序可以继续
logger.error(f"Failed to save data: {str(e)}")

# CRITICAL: 严重错误，程序可能无法继续
logger.critical(f"Database connection lost")
```

## 9. 类型注解规范

### 9.1 基本类型

```python
from typing import List, Dict, Union, Optional
import datetime
import pandas as pd

def fetch_data(
    symbols: List[str],                                    # 列表
    exchange: str,                                         # 字符串
    date: Union[str, int, datetime.date],                 # 联合类型
    config: Optional[Dict[str, str]] = None,              # 可选参数
) -> pd.DataFrame:                                        # 返回类型
    pass
```

## 10. 文档字符串规范

### 10.1 函数文档

```python
def fetch_trade_dates(
    exchanges: Union[str, List[str], None] = None,
    start_date: Union[str, int, datetime.date, None] = None,
    end_date: Union[str, int, datetime.date, None] = None,
) -> pd.DataFrame:
    """获取交易日历数据
    
    从数据库或远程数据源获取指定交易所的交易日历。
    
    Args:
        exchanges: 交易所代码，支持单个或列表。默认为所有交易所。
            示例: "SHSE", ["SHSE", "SZSE"]
        start_date: 起始日期，支持多种格式。默认为配置的起始日期。
            示例: "2024-01-01", 20240101, datetime.date(2024, 1, 1)
        end_date: 结束日期，格式同 start_date。默认为当前日期。
    
    Returns:
        pd.DataFrame: 交易日历数据，包含以下字段：
            - exchange: 交易所代码
            - trade_date: 交易日期（YYYY-MM-DD）
            - pretrade_date: 前一交易日
            - datestamp: Unix 时间戳
            - date_int: 整数格式日期（YYYYMMDD）
    
    Raises:
        ValueError: 日期格式无效或日期范围无效
        ConnectionError: 数据库连接失败
    
    Examples:
        >>> fetcher = LocalFetcher()
        >>> df = fetcher.fetch_trade_dates(
        ...     exchanges="SHSE",
        ...     start_date="2024-01-01",
        ...     end_date="2024-01-31"
        ... )
        >>> print(df.head())
    """
    pass
```

## 11. 测试规范

### 11.1 测试文件命名

```
tests/
  test_fetchers.py           # fetchers 模块测试
  test_savers.py             # savers 模块测试
  test_date_utils.py         # 日期工具测试
  test_exchange_utils.py     # 交易所工具测试
```

### 11.2 测试用例结构

```python
import pytest

class TestFetchTradeDates:
    """交易日历获取功能测试"""
    
    def test_fetch_single_exchange(self):
        """测试单个交易所查询"""
        pass
    
    def test_fetch_multiple_exchanges(self):
        """测试多个交易所查询"""
        pass
    
    def test_fetch_with_date_range(self):
        """测试日期范围查询"""
        pass
    
    def test_invalid_exchange_code(self):
        """测试无效的交易所代码"""
        with pytest.raises(ValueError):
            pass
```

## 12. 性能优化规范

### 12.1 数据库查询优化

```python
# 1. 使用索引
collection.create_index([("exchange", 1), ("datestamp", 1)])

# 2. 限制返回字段
collection.find(query, {"_id": 0, "trade_date": 1, "exchange": 1})

# 3. 使用批量操作
operations = [UpdateOne(...) for doc in docs]
collection.bulk_write(operations)

# 4. 使用 hint 指定索引
collection.find(query).hint([("exchange", 1), ("datestamp", 1)])
```

### 12.2 缓存策略

```python
from functools import lru_cache

@lru_cache(maxsize=1024)
def get_trade_date(date: int, exchange: str) -> Dict:
    """使用 LRU 缓存频繁查询的数据"""
    pass
```

## 13. 版本兼容性

### 13.1 Python 版本

- 最低支持：Python 3.7
- 推荐使用：Python 3.9+

### 13.2 依赖包版本

```toml
[project]
dependencies = [
    "pandas>=2.0.0",
    "pymongo>=4.0.0",
    "tushare>=1.2.0",
]
```

## 14. 编码风格

遵循 PEP 8 规范：
- 使用 4 个空格缩进
- 每行最多 100 个字符
- 函数之间空两行
- 类之间空两行
- import 语句按标准库、第三方库、本地模块分组

```python
# 标准库
import os
import sys
from typing import List

# 第三方库
import pandas as pd
import pymongo

# 本地模块
from quantbox.util import date_utils
from quantbox.fetchers import LocalFetcher
```
