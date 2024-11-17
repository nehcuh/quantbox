# Quantbox

Quantbox 是一个用于金融数据获取、存储和分析的框架，支持多种数据源（如掘金量化、Tushare等）和多种金融市场数据。该项目旨在为金融分析师、研究员和开发者提供一个方便、灵活和可扩展的工具包。

## 功能特性

- **多数据源支持**：
  - Tushare (ts)
  - 掘金量化 (gm)
  - 支持自定义数据源扩展
- **数据存储**：支持将获取的数据存储到本地 MongoDB 数据库
- **数据查询**：提供便捷的接口查询存储在本地数据库中的数据
- **命令行工具**：提供 CLI 命令行工具，方便用户执行数据获取和存储操作
- **灵活配置**：支持通过配置文件管理多个数据源的认证信息

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

## 配置

在使用之前，你需要配置 `config.toml` 文件，放置在 `~/.quantbox/settings/` 目录下，配置示例如下：

```toml
[TSPRO]
token = "your tushare token"

[GM]
token = "your gm token"

[MONGODB]
uri = "mongodb://localhost:27017"
```

## 使用

### 数据库安装
推荐直接使用 Docker 进行部署：

1. **创建数据卷**
    ```bash
    docker volume create qbmg
    ```
2. **利用 docker-compose 工具配置镜像**
    ```bash
    cd quantbox/docker/qb-base
    docker-compose -f database.yaml up -d
    ```

### 命令行工具

Quantbox 提供了一个便捷的命令行工具，帮助你快速获取和存储数据。

1. **保存所有数据**
    ```bash
    quantbox-save save-all --engine ts  # 使用 Tushare 数据源
    quantbox-save save-all --engine gm  # 使用掘金量化数据源
    ```

2. **保存期货持仓数据**
    ```bash
    quantbox-save save-future-holdings --engine ts  # 使用 Tushare 数据源
    quantbox-save save-future-holdings --engine gm  # 使用掘金量化数据源
    ```

3. **保存期货合约数据**
    ```bash
    quantbox-save save-future-contracts --engine ts
    ```

4. **保存交易日期数据**
    ```bash
    quantbox-save save-trade-dates --engine ts
    ```

5. **保存股票列表**
    ```bash
    quantbox-save save-stock-list --engine ts
    ```

6. **保存期货日线行情**
    ```bash
    quantbox-save save-future-daily --engine ts
    ```

### Python API 使用示例

```python
from quantbox.fetchers import TSFetcher, GMFetcher
from quantbox.savers import DataSaver

# 使用 Tushare 数据源
ts_fetcher = TSFetcher()
saver = DataSaver(fetcher=ts_fetcher)
saver.save_future_holdings()

# 使用掘金量化数据源
gm_fetcher = GMFetcher()
saver = DataSaver(fetcher=gm_fetcher)
saver.save_future_holdings()
```

## 开发

### 添加新的数据源
1. 在 `quantbox/fetchers` 目录下创建新的 fetcher 类
2. 继承 `BaseFetcher` 类并实现必要的方法
3. 在 `DataSaver` 中添加对新数据源的支持

### 运行测试
```bash
pytest tests/
```

## 贡献指南

1. Fork 本项目
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建一个 Pull Request

## 代码规范

- 使用 Python 类型注解
- 遵循 PEP 8 编码规范
- 为新功能编写测试用例
- 保持代码文档的更新

## 版本历史

- 0.1.0
  - 支持多数据源（Tushare、掘金量化）
  - 改进配置管理
  - 优化数据获取接口
  - 添加完整的命令行工具支持
