# Quantbox 快速入门指南

本文档帮助你在 5 分钟内快速上手 Quantbox，了解基本功能和使用方法。

## 安装

### 前提条件
- Python 3.8+
- MongoDB 4.0+ (可选，用于本地数据存储)
- Tushare Pro 账号 (用于数据获取)

### 安装步骤

```bash
# 克隆项目
git clone https://github.com/yourusername/quantbox.git
cd quantbox

# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .
```

## 配置

### 配置（自动初始化）

Quantbox 会在首次使用时自动初始化配置，您只需要：

1. **首次运行** - 系统会自动创建配置文件并显示说明
2. **设置 Token** - 编辑生成的配置文件，填入您的 API tokens

#### 自动配置示例

```python
# 首次运行会自动初始化配置
from quantbox.fetchers import TSFetcher
fetcher = TSFetcher()  # 自动创建配置文件
```

#### 手动配置（可选）

如需重新初始化配置：

```bash
quantbox-config
```

#### 配置 Token

1. **获取 Tushare Pro token**：
   - 访问 https://tushare.pro/register
   - 登录后获取 token
   - 编辑 `~/.quantbox/settings/config.toml`
   - 将 token 填入 `[TSPRO]` 部分

2. **配置文件格式**：
```toml
[TSPRO]
token = "your_tushare_token_here"

[GM]
token = ""

[MONGODB]
uri = "mongodb://localhost:27017"
```

如果不配置 MongoDB，系统将只使用远程数据源 (Tushare)。

## 5 分钟教程

### 1. 获取交易日历

```python
from quantbox.services import MarketDataService

# 初始化服务
service = MarketDataService()

# 获取交易日历
calendar = service.get_trade_calendar(
    exchanges=["SHFE"],          # 上期所
    start_date="2024-01-01",
    end_date="2024-12-31"
)

print(calendar.head())
```

输出：
```
   cal_date exchange is_open  pretrade_date
0  20240101     SHFE       0       20231229
1  20240102     SHFE       1       20231229
2  20240103     SHFE       1       20240102
3  20240104     SHFE       1       20240103
4  20240105     SHFE       1       20240104
```

### 2. 查询期货合约

```python
# 获取螺纹钢期货合约列表
contracts = service.get_future_contracts(
    exchanges=["SHFE"],
    symbols=["RB"]
)

print(contracts[["ts_code", "name", "list_date", "delist_date"]])
```

输出：
```
    ts_code   name  list_date  delist_date
0  RB2401.SHF  螺纹钢2401  20230516    20240115
1  RB2402.SHF  螺纹钢2402  20230616    20240215
2  RB2403.SHF  螺纹钢2403  20230717    20240315
...
```

### 3. 获取日线行情

```python
# 获取特定合约的日线数据
daily = service.get_future_daily(
    contracts=["RB2405.SHF"],
    start_date="2024-01-01",
    end_date="2024-01-31"
)

print(daily[["trade_date", "ts_code", "open", "high", "low", "close", "vol"]])
```

输出：
```
   trade_date       ts_code   open   high    low  close     vol
0    20240102  RB2405.SHF  3650.0  3680.0  3630.0  3670.0  125000
1    20240103  RB2405.SHF  3670.0  3700.0  3650.0  3690.0  138000
2    20240104  RB2405.SHF  3690.0  3710.0  3670.0  3680.0  142000
...
```

### 4. 查询持仓数据

```python
# 获取主力合约持仓排名
holdings = service.get_future_holdings(
    contracts=["RB2405.SHF"],
    start_date="2024-01-15",
    end_date="2024-01-15"
)

print(holdings[["trade_date", "broker", "vol", "vol_chg", "long_hld", "short_hld"]])
```

输出：
```
   trade_date       broker     vol  vol_chg  long_hld  short_hld
0    20240115   永安期货  35000    1200     18000      17000
1    20240115   中信期货  32000     800     16500      15500
2    20240115   国泰君安  28000    -500     14000      14000
...
```

## 数据保存

### 保存到本地 MongoDB

```python
from quantbox.services import DataSaverService

# 初始化保存服务
saver = DataSaverService()

# 保存交易日历
result = saver.save_trade_calendar(
    exchanges=["SHFE", "DCE", "CZCE", "INE"],
    start_date="2020-01-01",
    end_date="2024-12-31"
)

print(f"插入: {result.inserted_count} 条")
print(f"更新: {result.modified_count} 条")
```

### 保存合约列表

```python
# 保存所有期货合约
result = saver.save_future_contracts(
    exchanges=["SHFE", "DCE", "CZCE", "INE"]
)

print(f"总共保存 {result.inserted_count + result.modified_count} 个合约")
```

### 保存日线数据

```python
# 保存特定合约的日线数据
result = saver.save_future_daily(
    contracts=["RB2405.SHF", "HC2405.SHF"],
    start_date="2024-01-01",
    end_date="2024-12-31"
)

print(f"保存了 {result.inserted_count} 条日线数据")
```

## 使用 CLI

### 查询数据

```bash
# 查询交易日历
quantbox query calendar --exchange SHFE --start 2024-01-01 --end 2024-01-31

# 查询合约列表
quantbox query contracts --exchange SHFE --symbol RB

# 查询日线数据
quantbox query daily --contract RB2405.SHF --start 2024-01-01 --end 2024-01-31

# 查询持仓数据
quantbox query holdings --contract RB2405.SHF --date 2024-01-15
```

### 保存数据

```bash
# 保存交易日历
quantbox save calendar --exchange SHFE DCE CZCE INE --start 2020-01-01 --end 2024-12-31

# 保存所有合约
quantbox save contracts --exchange SHFE DCE CZCE INE

# 保存日线数据
quantbox save daily --contract RB2405.SHF --start 2024-01-01 --end 2024-12-31

# 批量保存主力合约日线
quantbox save daily --symbol RB HC --main --start 2024-01-01 --end 2024-12-31
```

### 图形界面

```bash
# 启动图形界面
quantbox gui
```

## 常见使用场景

### 场景1：首次使用 - 初始化数据库

```python
from quantbox.services import DataSaverService

saver = DataSaverService()

# 1. 保存历史交易日历
print("正在保存交易日历...")
saver.save_trade_calendar(
    exchanges=["SHFE", "DCE", "CZCE", "INE"],
    start_date="2015-01-01",
    end_date="2024-12-31"
)

# 2. 保存所有期货合约
print("正在保存期货合约...")
saver.save_future_contracts(
    exchanges=["SHFE", "DCE", "CZCE", "INE"]
)

# 3. 保存主力合约历史数据
print("正在保存主力合约数据...")
main_contracts = ["RB", "HC", "I", "J", "MA", "CF", "SR", "CU", "AL", "ZN"]
for symbol in main_contracts:
    print(f"  保存 {symbol}...")
    saver.save_future_daily(
        symbols=[symbol],
        exchanges=["SHFE", "DCE", "CZCE"],
        is_main=True,
        start_date="2015-01-01",
        end_date="2024-12-31"
    )

print("数据库初始化完成！")
```

### 场景2：每日数据更新

```python
from datetime import datetime, timedelta
from quantbox.services import DataSaverService

saver = DataSaverService()

# 获取昨天日期
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

# 更新交易日历
saver.save_trade_calendar(
    exchanges=["SHFE", "DCE", "CZCE", "INE"],
    start_date=yesterday,
    end_date=yesterday
)

# 更新主力合约日线
main_contracts = ["RB", "HC", "I", "J", "MA", "CF", "SR"]
saver.save_future_daily(
    symbols=main_contracts,
    is_main=True,
    start_date=yesterday,
    end_date=yesterday
)

print(f"已更新 {yesterday} 的数据")
```

### 场景3：查询并分析数据

```python
from quantbox.services import MarketDataService
import pandas as pd

service = MarketDataService()

# 获取螺纹钢主力合约过去一年数据
data = service.get_future_daily(
    symbols=["RB"],
    exchanges=["SHFE"],
    is_main=True,
    start_date="2023-01-01",
    end_date="2024-01-01"
)

# 计算简单移动平均线
data['ma5'] = data['close'].rolling(window=5).mean()
data['ma20'] = data['close'].rolling(window=20).mean()

# 计算收益率
data['returns'] = data['close'].pct_change()

# 统计分析
print(f"平均收盘价: {data['close'].mean():.2f}")
print(f"标准差: {data['close'].std():.2f}")
print(f"最大回撤: {(data['close'] / data['close'].cummax() - 1).min():.2%}")
```

### 场景4：离线使用

```python
from quantbox.services import MarketDataService

# 只使用本地数据，不调用远程API
service = MarketDataService(prefer_local=True)

try:
    # 如果本地有数据，直接返回
    data = service.get_trade_calendar(
        exchanges=["SHFE"],
        start_date="2024-01-01",
        end_date="2024-01-31"
    )
    print("成功从本地获取数据")
except Exception as e:
    print(f"本地数据不可用: {e}")
```

## 数据源选择

Quantbox 支持智能数据源选择：

```python
service = MarketDataService()

# 自动选择：本地优先，本地不可用则使用远程
data = service.get_trade_calendar()

# 强制使用远程 (Tushare)
data = service.get_trade_calendar(use_local=False)

# 强制使用本地 (MongoDB)
data = service.get_trade_calendar(use_local=True)

# 偏好设置
service = MarketDataService(prefer_local=True)   # 本地优先（默认）
service = MarketDataService(prefer_local=False)  # 远程优先
```

## 性能建议

1. **本地优先**：日常查询使用本地数据，速度快且免费
2. **批量操作**：一次获取大量数据比多次小查询高效
3. **合理范围**：避免一次查询过大日期范围
4. **定期更新**：建立定时任务每日更新数据

## 常见问题

### MongoDB 连接失败

```python
# 检查 MongoDB 是否运行
import pymongo
client = pymongo.MongoClient("mongodb://localhost:27017/")
print(client.server_info())  # 应该输出版本信息
```

### Tushare 请求超限

```python
# 使用本地数据避免频繁调用API
service = MarketDataService(prefer_local=True)

# 或者增加请求间隔
import time
for symbol in symbols:
    data = service.get_future_daily(symbols=[symbol])
    time.sleep(0.5)  # 等待0.5秒
```

### 数据格式不一致

```python
# 使用 util 模块标准化数据
from quantbox.util import date_to_int, normalize_exchange

# 日期标准化
date_int = date_to_int("2024-01-01")  # → 20240101

# 交易所代码标准化
exchange = normalize_exchange("SSE")  # → SHSE
```

## 下一步

- 查看 [API 参考文档](API_REFERENCE.md) 了解完整接口
- 阅读 [架构文档](ARCHITECTURE.md) 理解系统设计
- 查看 [迁移指南](MIGRATION_GUIDE.md) 了解版本变更
- 浏览 [示例代码](../examples/) 学习高级用法

## 获取帮助

- **文档**: https://quantbox.readthedocs.io
- **Issue**: https://github.com/yourusername/quantbox/issues
- **讨论**: https://github.com/yourusername/quantbox/discussions

开始你的量化之旅吧！ 🚀
