# Quantbox

Quantbox 是一个用于金融数据获取、存储和分析的框架，支持多种数据源（如掘金量化、Tushare等）和多种金融市场数据。该项目旨在为金融分析师、研究员和开发者提供一个方便、灵活和可扩展的工具包。

## 功能特性

- **多数据源支持**：
  - Tushare (ts)：提供A股、期货等市场数据
  - 掘金量化 (gm)：提供实时和历史行情数据
  - 支持自定义数据源扩展
- **数据存储**：支持将获取的数据存储到本地 MongoDB 数据库
- **数据查询**：提供便捷的接口查询存储在本地数据库中的数据
- **命令行工具**：提供 CLI 命令行工具，方便用户执行数据获取和存储操作
- **灵活配置**：支持通过配置文件管理多个数据源的认证信息
- **图形界面支持**：提供 PyQt5 实现的图形界面，方便用户交互
- **统一的交易所代码**：
  - 支持多种交易所代码格式（如 SSE/SHSE）
  - 自动代码转换和标准化
  - 完善的错误处理机制

## 项目结构

```
quantbox/
├── fetchers/           # 数据获取模块
│   ├── base.py            # 基础数据获取器接口
│   ├── config.py          # 获取器配置
│   ├── local_fetcher.py   # 本地数据库查询器
│   ├── remote_fetcher.py  # 远程数据获取基类
│   ├── fetcher_goldminer.py  # 掘金数据获取器
│   ├── fetcher_tushare.py    # Tushare数据获取器
│   ├── monitoring.py      # 性能监控
│   └── validation.py      # 数据验证
├── savers/            # 数据保存模块
│   └── data_saver.py      # 市场数据保存器
├── gui/              # 图形界面模块
│   └── main_window.py     # 主窗口实现
├── util/              # 工具模块
│   ├── basic.py          # 基础工具函数
│   ├── tools.py          # 通用工具函数
│   ├── date_utils.py     # 日期处理工具
│   └── exchange_utils.py  # 交易所代码工具
├── cli.py            # 命令行接口
├── config.py         # 配置管理
├── logger.py         # 日志管理
├── shell.py          # 交互式命令行
└── validators.py     # 数据验证器
```

## 安装

### 环境要求
- Python >= 3.12
- MongoDB >= 4.0
- 依赖包：
  - pymongo >= 4.0
  - pandas >= 2.0
  - tushare
  - toml
  - configparser
  - click

### 安装步骤

1. 安装项目依赖：
```bash
pip install -r requirements.txt
```

2. 安装本项目：
```bash
pip install -e .
```

### 安装 MongoDB

你可以选择以下两种方式安装 MongoDB：

#### 1. 使用 Docker（推荐）

这是最简单的安装方式，只需要按照以下步骤操作：

1. **安装 Docker**
   
   如果你还没有安装 Docker，请先从 [Docker 官网](https://www.docker.com/get-started) 下载并安装。

2. **创建数据卷**
   ```bash
   docker volume create qbmg
   ```

3. **启动 MongoDB 容器**
   ```bash
   cd docker/qb-base
   docker-compose -f database.yaml up -d
   ```

   这将启动一个 MongoDB 容器，具有以下特性：
   - 容器名称：qbmongo
   - 端口映射：27018:27017（外部访问端口为 27018）
   - 数据持久化：使用 qbmg 数据卷
   - 时区设置：Asia/Shanghai
   - 自动重启：容器会在系统重启后自动启动

4. **验证安装**
   ```bash
   docker ps
   ```
   你应该能看到名为 "qbmongo" 的容器正在运行。

#### 2. 手动安装

如果你不想使用 Docker，也可以直接从 [MongoDB 官网](https://www.mongodb.com/try/download/community) 下载并安装 MongoDB。

安装完成后，需要：
1. 启动 MongoDB 服务
2. 确保服务在默认端口（27017）运行
3. 创建一个名为 "quantbox" 的数据库

## 配置

1. **创建配置文件**

   在用户主目录下创建 `.quantbox/config.toml` 文件：
   ```toml
   [tushare]
   token = "your_tushare_token"

   [goldminer]
   token = "your_goldminer_token"
   ```

2. **MongoDB 配置**

   默认连接本地 MongoDB（localhost:27017）。如需修改，在配置文件中添加：
   ```toml
   [mongodb]
   host = "localhost"
   port = 27017
   ```

3. **验证配置**
   
   运行以下命令验证配置是否正确：
   ```bash
   quantbox
   > save_trade_dates
   ```

## 使用示例

### 1. 获取交易日历
```python
from quantbox.fetchers import LocalFetcher
from quantbox.util.exchange_utils import normalize_exchange

# 创建 fetcher 实例
fetcher = LocalFetcher()

# 支持多种交易所代码格式
trade_dates = fetcher.fetch_trade_dates(exchanges="SSE")  # 使用 SSE
trade_dates = fetcher.fetch_trade_dates(exchanges="SHSE")  # 使用 SHSE

# 标准化交易所代码
exchange = normalize_exchange("SSE")  # 返回 "SHSE"
trade_dates = fetcher.fetch_trade_dates(exchanges=exchange)
```

### 2. 获取期货合约信息
```python
from quantbox.fetchers import TSFetcher
from quantbox.util.exchange_utils import validate_exchanges

fetcher = TSFetcher()

# 验证交易所代码
exchanges = validate_exchanges(["SSE", "SZSE"])  # 返回 ["SHSE", "SZSE"]
contracts = fetcher.fetch_future_contracts(exchanges=exchanges)
print(contracts)
```

### 3. 保存市场数据
```python
from quantbox.savers import MarketDataSaver

saver = MarketDataSaver()
saver.save_trade_dates()  # 保存交易日历
saver.save_future_contracts()  # 保存期货合约信息
```

### 4. 使用图形界面

项目提供了图形界面支持，可以通过以下方式启动：

```python
from quantbox.gui import MainWindow
from PyQt5.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec_())
```

## 开发指南

### 交易所代码处理

项目提供了统一的交易所代码处理功能：

```python
from quantbox.util.exchange_utils import (
    normalize_exchange,
    denormalize_exchange,
    validate_exchanges
)

# 标准化单个交易所代码
code = normalize_exchange("SSE")  # 返回 "SHSE"

# 反标准化交易所代码
original = denormalize_exchange("SHSE")  # 返回 "SSE"

# 验证多个交易所代码
codes = ["SSE", "SZSE", None]  # None 将使用默认值
valid_codes = validate_exchanges(codes)  # 返回 ["SHSE", "SZSE"]

# 在数据获取时使用
fetcher = TSFetcher()
df = fetcher.fetch_get_trade_dates(
    exchanges=["SSE", "SZSE"],  # 自动转换为标准格式
    start_date="2024-01-01",
    end_date="2024-01-31"
)
```

### 使用性能监控

项目提供了性能监控功能，可以帮助开发者追踪和优化数据获取操作的性能：

```python
from quantbox.fetchers.local_fetcher import LocalFetcher
from quantbox.fetchers.monitoring import PerformanceMonitor

# 创建 fetcher 实例并添加监控器
fetcher = LocalFetcher()
monitor = PerformanceMonitor()
fetcher.add_monitor(monitor)

# 执行操作并查看性能数据
data = fetcher.fetch_trade_dates(exchanges="SHSE")
print(monitor.get_stats())
```

## 更多文档

- [交易日期系统设计](docs/trade_dates.md)
- [图形界面使用指南](docs/gui.md)

## 贡献指南

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交你的修改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件
