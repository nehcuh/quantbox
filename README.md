# Quantbox

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Test Files](https://img.shields.io/badge/test_files-12-success.svg)](https://github.com/curiousbull/quantbox)
[![Test Cases](https://img.shields.io/badge/test_cases-187+-success.svg)](https://github.com/curiousbull/quantbox)
[![Services Coverage](https://img.shields.io/badge/services-100%25%20%7C%2085%25-brightgreen.svg)](https://github.com/curiousbull/quantbox)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![PyPI Version](https://img.shields.io/pypi/v/quantbox.svg)](https://pypi.org/project/quantbox/)

**Quantbox** 是一个现代化的 Python 金融数据获取和管理框架，采用清晰的三层架构设计，支持多种数据源（Tushare、掘金量化等），为量化研究和交易提供统一、高效的数据接口。

> ⚠️ **重要更新 (2025-11-11)**：
> - ✨ 优化交易日历数据结构（移除冗余 `is_open` 字段，新增 `datestamp` 索引）
> - 🎯 增强合约查询接口（支持简单格式和完整格式，智能解析）
> - 📈 查询性能提升 6.4%，存储空间减少 12%
> - 详见 [迁移指南](docs/MIGRATION_GUIDE.md)

## ✨ 核心特性

- 🏗️ **三层架构设计**：工具层 → 适配器层 → 服务层，职责清晰，易于扩展
- ⚡ **异步高性能**：完整异步实现，性能提升 10-20 倍，支持 Python 3.14 nogil
- 🔌 **多数据源支持**：统一接口访问 Tushare、掘金量化 (GMAdapter)、本地 MongoDB
- 🚀 **智能数据源选择**：自动优先使用本地数据，降低 API 调用成本
- ⚡ **缓存预热系统**：启动时预热 1491 个缓存条目，运行时性能提升 95%+
- 💾 **高效数据存储**：批量 upsert 操作，自动去重和索引优化
- 🎯 **灵活合约格式**：支持简单格式 `"a2501"` 和完整格式 `"DCE.a2501"`，智能解析
- 📈 **优化数据结构**：交易日历使用 `datestamp` 索引，查询性能提升 6.4%
- 📊 **完整类型注解**：全面的类型提示，更好的 IDE 支持
- ✅ **高测试覆盖率**：12个测试文件，187+ 测试用例，服务层 100%/85% 覆盖
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
git clone https://github.com/curiousbull/quantbox.git
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

**使用 pip（从 PyPI 安装）**：

```bash
# 基础安装
pip install quantbox

# 安装掘金量化支持（Windows/Linux）
pip install quantbox[goldminer]

# 安装所有可选依赖
pip install quantbox[all]

# 开发安装（从源码）
git clone https://github.com/curiousbull/quantbox.git
cd quantbox
pip install -e .
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

# 获取期货日线数据（支持多种合约格式）
daily = service.get_future_daily(
    symbols="DCE.a2501",      # 完整格式：交易所.合约
    start_date="2024-01-01",
    end_date="2024-01-31"
)
# 也支持简单格式：symbols="a2501"
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

### ⚡ 异步高性能版本（性能提升 10-20 倍）

quantbox 提供完整的异步实现，适用于大规模数据下载和并发查询场景。

#### 异步查询数据

```python
import asyncio
from quantbox.services import AsyncMarketDataService

async def main():
    # 创建异步服务实例
    service = AsyncMarketDataService()

    # 异步获取期货持仓（性能提升 12-17 倍）
    holdings = await service.get_future_holdings(
        exchanges=["SHFE", "DCE"],
        start_date="2024-01-01",
        end_date="2024-01-10",
        show_progress=True
    )
    print(f"获取 {len(holdings)} 条持仓数据")

asyncio.run(main())
```

#### 异步保存数据

```python
import asyncio
from quantbox.services import AsyncDataSaverService

async def main():
    # 创建异步保存服务
    saver = AsyncDataSaverService(show_progress=True)

    # 并发保存所有数据（性能提升 14 倍）
    results = await saver.save_all(
        start_date="2024-01-01",
        end_date="2024-01-10"
    )

    # 打印结果
    for key, result in results.items():
        print(f"{key}: 插入 {result.inserted_count}，更新 {result.modified_count}")

asyncio.run(main())
```

#### 使用异步 Shell

```bash
# 启动异步交互式 Shell
quantbox-async

# 在 Shell 中执行命令
quantbox-async> save_all --start-date 2024-01-01 --end-date 2024-01-10
quantbox-async> save_future_holdings --exchanges SHFE,DCE --date 2024-01-05
```

#### 使用异步 CLI

```bash
# 并发保存所有数据
quantbox-save-async save-all --start-date 2024-01-01

# 保存期货持仓（核心性能优化）
quantbox-save-async save-holdings --exchanges SHFE,DCE \
                                    --start-date 2024-01-01 \
                                    --end-date 2024-01-10

# 运行性能基准测试
quantbox-save-async benchmark --exchanges SHFE,DCE
```

#### 性能对比

| 操作 | 同步版本 | 异步版本 | 提升倍数 |
|---|---|---|---|
| 期货持仓下载（10 天） | 250s | 15-20s | **12-17x** |
| 完整数据保存 (save_all) | 355s | 25s | **14x** |
| 并发查询多交易所 | 45s | 8s | **5.6x** |

**Python 3.14 nogil 额外提升**：在 nogil 模式下可再提升 50-60%

详细文档：
- [异步使用指南](docs/ASYNC_GUIDE.md)
- [异步实现报告](docs/ASYNC_IMPLEMENTATION_REPORT.md)
- [nogil 测试指南](docs/NOGIL_TESTING_GUIDE.md)

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
│   ├── ts_adapter.py     # Tushare 适配器
│   ├── gm_adapter.py     # 掘金量化适配器
│   ├── formatters.py     # 公共格式转换工具
│   └── asynchronous/     # 异步适配器
├── services/             # 服务层
│   ├── market_data_service.py        # 数据查询服务
│   ├── data_saver_service.py         # 数据保存服务
│   ├── async_market_data_service.py  # 异步查询服务
│   └── async_data_saver_service.py   # 异步保存服务
├── config/               # 配置管理
│   ├── config_loader.py  # 配置加载器
│   ├── exchanges.toml    # 交易所配置
│   ├── instruments.toml  # 合约配置
│   ├── fees_margin.toml  # 手续费和保证金配置
│   └── templates/        # 配置模板
├── util/                 # 工具层
│   ├── date_utils.py     # 日期处理工具
│   ├── exchange_utils.py # 交易所代码工具
│   ├── contract_utils.py # 合约代码工具
│   ├── tools.py          # 通用工具函数
│   └── cache_warmup.py   # 缓存预热系统
├── gui/                  # 图形界面（可选）
├── cli.py                # 命令行工具（同步）
├── cli_async.py          # 命令行工具（异步）
├── shell.py              # 交互式 Shell（同步）
└── shell_async.py        # 交互式 Shell（异步）
```

## 🔄 API 变更

### v2.0 新 API（推荐）

```python
# ✅ 新版本 - 简洁清晰
from quantbox.services import MarketDataService

service = MarketDataService()
data = service.get_trade_calendar(exchanges="SHSE")
```

### v1.x 旧 API（已移除）

```python
# ❌ 旧版本 - 已在 v0.2.0 中完全移除
# from quantbox.fetchers import TSFetcher
# from quantbox.savers import MarketDataSaver

# 这些模块已不存在，请使用新的服务层 API
```

**注意**：旧的 `fetchers/` 和 `savers/` 模块已在 v0.2.0 中完全移除。

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

### v0.2.0 (2025-11-12)

- 🎉 **重大重构**：全新的三层架构设计
- ✨ **新增**：MarketDataService 和 DataSaverService（同步+异步）
- ⚡ **异步支持**：完整异步实现，性能提升 10-20 倍
- 🗑️ **移除**：删除旧的 fetchers/ 和 savers/ 模块
- 🔧 **改进**：统一的数据接口和错误处理
- 📚 **文档**：全面更新的使用文档
- ✅ **测试**：187+ 测试用例，服务层覆盖率 100%/85%
- 🚀 **工具**：迁移到 uv 项目管理
- 🧹 **清理**：项目结构优化，移除临时文件和开发文件

完整更新日志请查看 [docs/refactor_progress.md](docs/refactor_progress.md)

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Tushare](https://tushare.pro/) - 金融数据接口
- [掘金量化](https://www.myquant.cn/) - 量化交易平台
- [uv](https://github.com/astral-sh/uv) - 现代化 Python 包管理器

## 📮 联系方式

- 问题反馈：[GitHub Issues](https://github.com/curiousbull/quantbox/issues)
- 功能建议：[GitHub Discussions](https://github.com/curiousbull/quantbox/discussions)

---

**Made with ❤️ by the Quantbox Team**
