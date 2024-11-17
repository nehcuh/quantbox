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

## 项目结构

```
quantbox/
├── fetchers/           # 数据获取模块
│   ├── base_fetcher.py     # 基础数据获取器接口
│   ├── local_fetcher.py    # 本地数据库查询器
│   ├── remote_fetch_gm.py  # 掘金数据获取器
│   └── remote_fetch_tushare.py  # Tushare数据获取器
├── savers/            # 数据保存模块
│   └── data_saver.py      # 市场数据保存器
├── util/              # 工具模块
│   ├── basic.py          # 基础工具函数
│   └── tools.py          # 通用工具函数
└── cli.py            # 命令行接口
```

## 安装

### 环境要求
- Python >= 3.7
- MongoDB

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

在使用之前，你需要配置 `config.toml` 文件，放置在 `~/.quantbox/settings/` 目录下：

1. **创建配置目录**
   ```bash
   mkdir -p ~/.quantbox/settings
   ```

2. **复制配置模板**
   ```bash
   cp templates/config.toml ~/.quantbox/settings/
   ```

3. **编辑配置文件**
   
   编辑 `~/.quantbox/settings/config.toml` 文件，填入你的配置信息：

   ```toml
   [TSPRO]
   token = "your tushare token"  # 从 https://tushare.pro 获取

   [GMAPI]
   token = "your gm token"  # 从 https://www.myquant.cn 获取

   [MONGODB]
   uri = "mongodb://localhost:27017"  # 如果使用默认的手动安装 MongoDB
   # uri = "mongodb://localhost:27018"  # 如果使用 Docker 安装的 MongoDB
   ```

   配置项说明：
   - **TSPRO.token**: Tushare API 的访问令牌，可以从 [Tushare Pro](https://tushare.pro) 官网注册获取
   - **GMAPI.token**: 掘金量化 API 的访问令牌，可以从[掘金量化](https://www.myquant.cn)官网注册获取
   - **MONGODB.uri**: MongoDB 数据库的连接 URI
     * 如果是手动安装的 MongoDB，通常使用 "mongodb://localhost:27017"
     * 如果是使用 Docker 安装的 MongoDB，需要使用 "mongodb://localhost:27018"，因为我们将容器的 27017 端口映射到了主机的 27018 端口

4. **验证配置**
   
   运行以下命令验证配置是否正确：
   ```bash
   python cli.py save-trade-dates
   ```
   如果配置正确，将会开始下载交易日期数据。

## 使用示例

### 1. 获取交易日历
```python
from quantbox import LocalFetcher

fetcher = LocalFetcher()
trade_dates = fetcher.fetch_trade_dates(exchanges="SSE")
print(trade_dates)
```

### 2. 获取期货合约信息
```python
from quantbox import TSFetcher

fetcher = TSFetcher()
contracts = fetcher.fetch_future_contracts(symbol="IF")
print(contracts)
```

### 3. 保存市场数据
```python
from quantbox.savers import MarketDataSaver

saver = MarketDataSaver()
saver.save_trade_dates()  # 保存交易日历
saver.save_future_contracts()  # 保存期货合约信息
```

## 开发指南

### 添加新的数据源

1. 在 `fetchers` 目录下创建新的数据获取器类，继承 `BaseFetcher`
2. 实现必要的方法（如 `fetch_trade_dates`、`fetch_future_contracts` 等）
3. 在 `data_saver.py` 中添加对新数据源的支持

### 代码风格

- 遵循 PEP 8 编码规范
- 使用类型注解
- 提供详细的文档字符串

## 贡献指南

欢迎提交 Pull Request 或 Issue！

## 许可证

MIT License
