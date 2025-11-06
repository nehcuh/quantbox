# Quantbox

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-178%20passed-success.svg)](https://github.com/your-org/quantbox)
[![Code Coverage](https://img.shields.io/badge/coverage-30%25-yellow.svg)](https://github.com/your-org/quantbox)
[![Services Coverage](https://img.shields.io/badge/services-100%25%20%7C%2085%25-brightgreen.svg)](https://github.com/your-org/quantbox)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Quantbox** 是一个现代化的 Python 金融数据获取和管理框架，采用清晰的三层架构设计，支持多种数据源（Tushare、掘金量化等），为量化研究和交易提供统一、高效的数据接口。

> ⚠️ **重要更新 (2025-11-05)**：旧的 `TSFetcher` API 已标记为废弃，请使用新的 `TSAdapter` 或 `MarketDataService`。详见 [迁移指南](docs/MIGRATION_GUIDE.md)。

## ✨ 核心特性

- 🏗️ **三层架构设计**：工具层 → 适配器层 → 服务层，职责清晰，易于扩展
- 🔌 **多数据源支持**：统一接口访问 Tushare、掘金量化 (GMAdapter)、本地 MongoDB
- 🚀 **智能数据源选择**：自动优先使用本地数据，降低 API 调用成本
- ⚡ **缓存预热系统**：启动时预热 1491 个缓存条目，运行时性能提升 95%+
- 💾 **高效数据存储**：批量 upsert 操作，自动去重和索引优化
- 📊 **完整类型注解**：全面的类型提示，更好的 IDE 支持
- ✅ **高测试覆盖率**：178+ 测试用例，服务层 100%/85% 覆盖
- 🛠️ **现代化工具链**：使用 uv 进行快速依赖管理

## 🏛️ 架构概览

```
┌─────────────────────────────────────────┐
│         Application Layer               │
│      (Your Scripts & Applications)      │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│          Services Layer                 │
│  ┌──────────────┐  ┌─────────────────┐ │
│  │ MarketData   │  │  DataSaver      │ │
│  │   Service    │  │   Service       │ │
│  └──────────────┘  └─────────────────┘ │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│         Adapters Layer                  │
│  ┌──────────┐  ┌──────────┐  ┌───────┐ │
│  │  Local   │  │ TuShare  │  │  GM   │ │
│  │ Adapter  │  │ Adapter  │  │ ...   │ │
│  └──────────┘  └──────────┘  └───────┘ │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│      Utils Layer                        │
│  Date • Exchange • Contract Utilities   │
└─────────────────────────────────────────┘
```

详细架构说明请参阅 [ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 🚀 快速开始

### 安装

**使用 uv（推荐）**：

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆项目
git clone https://github.com/your-org/quantbox.git
cd quantbox

# 安装基础依赖（自动创建虚拟环境）
uv sync

# 【可选】安装掘金量化 SDK（仅支持 Windows/Linux，macOS 不支持）
uv sync --extra goldminer

# 【可选】安装所有可选依赖（包括开发工具、GUI、掘金 SDK）
uv sync --extra all

# 激活虚拟环境（Linux/macOS）
source .venv/bin/activate

# 激活虚拟环境（Windows）
.venv\Scripts\activate
```

**使用 pip**：

```bash
# 基础安装
pip install -e .

# 安装掘金量化支持（Windows/Linux）
pip install -e ".[goldminer]"

# 安装所有可选依赖
pip install -e ".[all]"
```

### 配置

Quantbox 会在首次使用时自动初始化配置文件，无需手动创建。

#### 自动配置

首次运行时，系统会自动：
1. 创建配置目录：`~/.quantbox/settings/`
2. 生成配置文件：`~/.quantbox/settings/config.toml`
3. 显示配置说明和下一步操作

#### 手动配置（可选）

如需重新初始化配置，可运行：

```bash
# 初始化配置
quantbox-config

# 强制覆盖现有配置
quantbox-config --force

# 使用自定义配置目录
quantbox-config --config-dir /path/to/config
```

#### 配置文件格式

```toml
# Tushare Pro API 配置
[TSPRO]
token = "your_tushare_token_here"

# 掘金量化 API 配置
[GM]
token = ""

# MongoDB 数据库配置
[MONGODB]
uri = "mongodb://localhost:27017"
```

### 启动 MongoDB

使用 Docker（推荐）：

```bash
cd docker/qb-base
docker-compose -f database.yaml up -d
```

## 📖 使用示例

### 应用初始化和缓存预热

```python
import quantbox

# 方法1：推荐的标准初始化（自动预热缓存）
stats = quantbox.init(auto_warm=True, warm_verbose=False)
print(f"初始化完成，预热耗时: {stats['total_time']:.3f}s")

# 方法2：手动预热缓存
stats = quantbox.warm_caches(verbose=True)
print(f"预热了 {stats['functions_warmed']} 个函数，{stats['cache_entries']} 个缓存条目")

# 方法3：后台自动预热（不阻塞应用启动）
quantbox.auto_warm_on_import(enable=True)
```

**缓存预热带来的性能提升**：
- 🚀 应用启动后首次操作速度提升 **95%+**
- ⚡ 交易所代码转换从 ~1ms 降低到 ~0.02ms
- 📈 支持数百个常用函数组合的智能缓存

### 查询市场数据

```python
from quantbox.services import MarketDataService

# 创建服务实例
service = MarketDataService()

# 获取交易日历
calendar = service.get_trade_calendar(
    exchanges=["SHSE", "SZSE"],
    start_date="2024-01-01",
    end_date="2024-01-31"
)
print(calendar)

# 获取期货合约信息
contracts = service.get_future_contracts(
    exchanges="SHFE",
    date="2024-01-15"
)
print(contracts)

# 获取期货日线数据
daily = service.get_future_daily(
    symbols="SHFE.rb2501",
    start_date="2024-01-01",
    end_date="2024-01-31"
)
print(daily)

# 获取持仓数据
holdings = service.get_future_holdings(
    exchanges="DCE",
    date="2024-01-15"
)
print(holdings)
```

### 保存数据到本地

```python
from quantbox.services import DataSaverService

# 创建保存服务实例
saver = DataSaverService()

# 保存交易日历
result = saver.save_trade_calendar(
    exchanges=["SHSE", "SZSE"],
    start_date="2024-01-01",
    end_date="2024-12-31"
)
print(f"插入: {result.inserted_count}, 更新: {result.modified_count}")

# 保存期货合约
result = saver.save_future_contracts(
    exchanges="SHFE",
    date="2024-01-15"
)

# 保存日线数据
result = saver.save_future_daily(
    exchanges="DCE",
    start_date="2024-01-01",
    end_date="2024-01-31"
)
```

### 数据源切换

```python
from quantbox.services import MarketDataService

# 默认：本地优先
service = MarketDataService()
data = service.get_trade_calendar()  # 先查本地，没有再查远程

# 强制使用远程数据源
data = service.get_trade_calendar(use_local=False)

# 强制使用本地数据源
data = service.get_trade_calendar(use_local=True)
```

更多示例请参阅 [QUICK_START.md](docs/QUICK_START.md)

## 📚 文档

- **[快速开始指南](docs/QUICK_START.md)** - 5分钟上手教程
- **[缓存预热指南](examples/cache_warmup_example.py)** - 详细的缓存预热使用示例
- **[架构文档](docs/ARCHITECTURE.md)** - 详细的系统架构说明
- **[API 参考](docs/API_REFERENCE.md)** - 完整的 API 文档
- **[迁移指南](docs/MIGRATION_GUIDE.md)** - 从旧版本迁移
- **[编码规范](docs/coding_standards.md)** - 项目编码标准
- **[重构设计](docs/refactor_design.md)** - 重构设计文档

## 🧪 测试

运行所有测试：

```bash
uv run pytest tests/ -v
```

运行核心测试（跳过数据库测试）：

```bash
uv run pytest tests/ -v -m "not db"
```

生成覆盖率报告：

```bash
uv run pytest tests/ --cov=quantbox --cov-report=html
```

## 🗂️ 项目结构

```
quantbox/
├── adapters/              # 数据适配器层
│   ├── base.py           # 适配器基类
│   ├── local_adapter.py  # MongoDB 适配器
│   └── ts_adapter.py     # Tushare 适配器
├── services/             # 服务层
│   ├── market_data_service.py  # 数据查询服务
│   └── data_saver_service.py   # 数据保存服务
├── util/                 # 工具层
│   ├── date_utils.py     # 日期处理工具
│   ├── exchange_utils.py # 交易所代码工具
│   ├── tools.py          # 通用工具函数
│   └── cache_warmup.py   # 缓存预热系统
├── fetchers/             # 遗留数据获取器（待废弃）
├── savers/               # 遗留数据保存器（待废弃）
└── gui/                  # 图形界面
```

## 🔄 API 变更

### v2.0 新 API（推荐）

```python
# ✅ 新版本 - 简洁清晰
from quantbox.services import MarketDataService

service = MarketDataService()
data = service.get_trade_calendar(exchanges="SHSE")
```

### v1.x 旧 API（已废弃）

```python
# ❌ 旧版本 - 将被移除
from quantbox.fetchers import TSFetcher

fetcher = TSFetcher()
data = fetcher.fetch_get_trade_dates(exchanges="SSE")
```

详细迁移指南请参阅 [MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md)

## 🤝 贡献

我们欢迎所有形式的贡献！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交修改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

请确保：

- 所有测试通过
- 新增代码有相应的测试
- 遵循项目编码规范

## 📊 性能

### 缓存预热性能
- **预热耗时**：~77ms（147个函数，1,491个缓存条目）
- **运行时提升**：首次操作速度提升 **95%+**
- **代码转换**：交易所代码转换从 ~1ms → ~0.02ms
- **缓存命中率**：>95%（常用操作组合）

### 数据操作性能
- **查询速度**：本地查询 < 10ms，远程查询 < 500ms
- **批量写入**：10,000 条/秒（使用 bulk_write）
- **内存占用**：< 100MB（正常运行）
- **并发支持**：线程安全的数据访问

## 📝 更新日志

### v2.0.0 (2025-10-31)

- 🎉 **重大重构**：全新的三层架构设计
- ✨ **新增**：MarketDataService 和 DataSaverService
- 🔧 **改进**：统一的数据接口和错误处理
- 📚 **文档**：全面更新的使用文档
- ✅ **测试**：159 个测试，95%+ 覆盖率
- 🚀 **工具**：迁移到 uv 项目管理

完整更新日志请查看 [docs/refactor_progress.md](docs/refactor_progress.md)

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Tushare](https://tushare.pro/) - 金融数据接口
- [掘金量化](https://www.myquant.cn/) - 量化交易平台
- [uv](https://github.com/astral-sh/uv) - 现代化 Python 包管理器

## 📮 联系方式

- 问题反馈：[GitHub Issues](https://github.com/your-org/quantbox/issues)
- 功能建议：[GitHub Discussions](https://github.com/your-org/quantbox/discussions)

---

**Made with ❤️ by the Quantbox Team**
