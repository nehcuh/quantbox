# Quantbox 快速入门指南

本文档帮助你在 5 分钟内快速上手 Quantbox，从安装到使用。

## 📦 安装

### 前提条件

- **Python 3.12+**
- **MongoDB 4.0+**（用于本地数据存储）
- **Tushare Pro 账号**（用于数据获取）

### 快速安装

```bash
# 从 PyPI 安装（推荐）
pip install quantbox

# 或安装掘金支持（仅 Windows/Linux）
pip install quantbox[goldminer]
```

### MongoDB 快速启动

```bash
# 使用 Docker（推荐）
docker run -d --name quantbox-mongo -p 27017:27017 mongo:latest

# 或本地安装
# macOS: brew install mongodb-community && brew services start mongodb-community
# Ubuntu: sudo apt install mongodb && sudo systemctl start mongodb
```

## ⚙️ 配置

### 1. 获取 Tushare Token

1. 访问 [Tushare Pro](https://tushare.pro/register) 注册账号
2. 登录后进入 [个人中心](https://tushare.pro/user/token) 获取 token
3. 免费用户有积分限制，建议充值获取更多积分

### 2. 初始化配置

```bash
# 运行配置工具
quantbox-config
```

这将自动创建配置文件：`~/.quantbox/settings/config.toml`

### 3. 编辑配置文件

```bash
# macOS/Linux
vi ~/.quantbox/settings/config.toml

# Windows
notepad %USERPROFILE%\.quantbox\settings\config.toml
```

填入你的 token：

```toml
[TSPRO]
token = "your_tushare_token_here"  # 替换为实际 token

[GM]
token = ""  # 可选，如果使用掘金

[MONGODB]
uri = "mongodb://localhost:27017"
```

### 4. 验证配置

```python
from quantbox.services import MarketDataService

service = MarketDataService()
print("✅ Quantbox 配置成功！")
```

## 🚀 5 分钟教程

### 1. 获取交易日历

```python
from quantbox.services import MarketDataService

# 初始化服务
service = MarketDataService()

# 获取交易日历
calendar = service.get_trade_calendar(
    exchanges="SHFE",           # 上期所
    start_date="2024-01-01",
    end_date="2024-01-05"
)

print(calendar)
```

**输出示例**：
```
        date exchange  datestamp
0   20240102     SHFE  1704124800
1   20240103     SHFE  1704211200
2   20240104     SHFE  1704297600
3   20240105     SHFE  1704384000
```

### 2. 查询期货合约

```python
# 获取某日所有上市合约
contracts = service.get_future_contracts(
    exchanges="SHFE",
    date="2024-01-15"
)

print(contracts[['symbol', 'name', 'list_date', 'delist_date']].head())
```

**输出示例**：
```
    symbol      name  list_date  delist_date
0  SHFE.ag2402  沪银2402   20211124     20240215
1  SHFE.ag2403  沪银2403   20211224     20240315
2  SHFE.ag2404  沪银2404   20220124     20240415
```

### 3. 获取日线数据

```python
# 获取单个合约的日线数据
daily = service.get_future_daily(
    symbols="SHFE.ag2402",      # 支持完整格式
    start_date="2024-01-01",
    end_date="2024-01-31"
)

print(daily[['trade_date', 'open', 'high', 'low', 'close', 'volume']].head())
```

**输出示例**：
```
   trade_date    open    high     low   close   volume
0    20240102  5345.0  5389.0  5312.0  5378.0   123456
1    20240103  5380.0  5420.0  5365.0  5410.0   145678
2    20240104  5412.0  5445.0  5398.0  5425.0   134567
```

### 4. 获取持仓数据

```python
# 获取某日的持仓排名数据
holdings = service.get_future_holdings(
    exchanges="SHFE",
    date="2024-01-15"
)

print(holdings[['symbol', 'broker', 'vol', 'vol_chg']].head(10))
```

**输出示例**：
```
       symbol        broker      vol  vol_chg
0  SHFE.ag2402      永安期货    12345     1234
1  SHFE.ag2402      中信期货    11234      987
2  SHFE.ag2402      国泰君安    10123      654
```

## 💾 保存数据到本地

使用 `DataSaverService` 将数据保存到 MongoDB：

```python
from quantbox.services import DataSaverService

# 初始化保存服务
saver = DataSaverService()

# 保存交易日历
result = saver.save_trade_calendar(
    exchanges=["SHFE", "DCE", "CZCE"],
    start_date="2024-01-01",
    end_date="2024-12-31"
)
print(f"保存成功：插入 {result.inserted_count} 条，更新 {result.modified_count} 条")

# 保存期货合约
result = saver.save_future_contracts(
    exchanges="SHFE",
    date="2024-01-15"
)

# 保存日线数据
result = saver.save_future_daily(
    exchanges="SHFE",
    start_date="2024-01-01",
    end_date="2024-01-31"
)
```

## ⚡ 异步版本（高性能）

Quantbox 提供完整的异步 API，性能提升 10-20 倍：

```python
import asyncio
from quantbox.services import AsyncMarketDataService

async def main():
    service = AsyncMarketDataService()

    # 异步获取数据
    calendar = await service.get_trade_calendar(
        exchanges="SHFE",
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    print(f"获取 {len(calendar)} 条数据")

# 运行异步代码
asyncio.run(main())
```

详细异步使用指南请参阅 [ASYNC_GUIDE.md](ASYNC_GUIDE.md)

## 🎯 智能数据源选择

Quantbox 会自动优先使用本地数据，节省 API 调用：

```python
# 默认：本地优先
service = MarketDataService()
data = service.get_trade_calendar()  # 先查本地，没有再查远程

# 强制使用远程数据源
data = service.get_trade_calendar(use_local=False)

# 仅使用本地数据源
data = service.get_trade_calendar(use_local=True)
```

## 📝 数据格式说明

### 合约代码格式

Quantbox 支持多种合约代码格式：

```python
# 完整格式（推荐）
symbols = "SHFE.ag2402"

# 简单格式（会自动补全交易所）
symbols = "ag2402"  # 需要指定 default_exchange

# 多个合约
symbols = ["SHFE.ag2402", "SHFE.au2402"]
symbols = "SHFE.ag2402,SHFE.au2402"  # 逗号分隔
```

### 日期格式

支持多种日期格式：

```python
# 字符串格式（推荐）
start_date = "2024-01-01"
start_date = "20240101"

# 整数格式
start_date = 20240101

# datetime 对象
from datetime import datetime
start_date = datetime(2024, 1, 1)
```

## 🔧 命令行工具

Quantbox 提供便捷的命令行工具：

```bash
# 配置管理
quantbox-config                    # 初始化配置
quantbox-config --force            # 强制重新初始化

# 交互式 Shell（同步）
quantbox
quantbox> get_trade_calendar --exchanges SHFE --start-date 2024-01-01

# 交互式 Shell（异步，高性能）
quantbox-async
quantbox-async> save_all --start-date 2024-01-01

# 数据保存
quantbox-save --help               # 查看帮助
quantbox-save-async --help         # 异步版本
```

## 📚 下一步

- **完整 API 文档**：[API_REFERENCE.md](API_REFERENCE.md)
- **异步使用指南**：[ASYNC_GUIDE.md](ASYNC_GUIDE.md)
- **架构设计**：[ARCHITECTURE.md](ARCHITECTURE.md)
- **迁移指南**：[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

## ❓ 常见问题

### Q: 首次使用如何获取数据？

A: 首次使用需要从远程数据源获取，建议先保存到本地：

```python
from quantbox.services import DataSaverService

saver = DataSaverService()

# 保存最近一年的交易日历
saver.save_trade_calendar(
    exchanges=["SHFE", "DCE", "CZCE"],
    start_date="2023-01-01",
    end_date="2024-12-31"
)
```

### Q: Tushare 积分不足怎么办？

A:
- 免费用户每天有积分限制
- 建议充值获取更多积分
- 或减少请求频率，使用本地数据

### Q: MongoDB 连接失败？

A: 检查：
- MongoDB 是否运行：`docker ps` 或 `brew services list`
- 端口是否正确：默认 27017
- 配置文件中的 uri 是否正确

### Q: macOS 可以使用掘金吗？

A: 掘金 SDK 不支持 macOS，请使用 Tushare 作为数据源。

## 💡 提示

- 使用异步版本可获得 10-20 倍性能提升
- 定期保存数据到本地可减少 API 调用
- 使用 `show_progress=True` 查看数据下载进度
- 查看日志了解数据来源（本地/远程）

---

**开始你的量化之旅！** 🚀
