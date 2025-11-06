# Quantbox 迁移指南

本指南帮助你从旧版 API 迁移到新版三层架构（Services/Adapters/Utils）。

## 概览

**新版核心特性**：
- 统一的服务层：`MarketDataService`, `DataSaverService`
- 解耦的适配器：`LocalAdapter`(MongoDB), `TSAdapter`(Tushare), `GMAdapter`(掘金量化)
- 标准化的数据接口：日期统一为 int，交易所/合约代码统一
- 完善的测试覆盖：178+ 测试用例，服务层 100%/85% 覆盖

## 主要变更

| 变更点 | 旧版本 | 新版本 |
|--------|--------|--------|
| **命名空间** | `TSFetcher`, `GMFetcher` | `TSAdapter`, `GMAdapter` |
| **方法名** | `fetch_get_*()` | `get_*()` |
| **日期格式** | 混用 `datetime/str/int` | 统一为 `int` (YYYYMMDD) |
| **交易所代码** | `SSE`, `SZ` 混用 | `SHSE`, `SZSE` 标准化 |
| **合约编码** | `RB2405` 或 `RB2405.SHF` | 统一为 `SHFE.rb2501` |
| **参数名** | `symbol`, `spec_name` (单数) | `symbols`, `spec_names` (复数) |
| **返回类型** | 可能为 `list[dict]` | 统一返回 `pd.DataFrame` |
| **保存结果** | 无详细反馈 | 返回 `SaveResult` 对象 |

## 快速映射表

### 数据查询

```python
# ========== 旧版本 ==========
from quantbox.fetchers.fetcher_tushare import TSFetcher

fetcher = TSFetcher()

# 交易日历
df = fetcher.fetch_get_trade_dates(
    exchanges=['SSE'],
    start_date=20250101,
    end_date=20250131
)

# 期货合约
df = fetcher.fetch_get_future_contracts(
    exchange='SHFE',
    spec_name='rb'
)

# 日线数据
df = fetcher.fetch_get_future_daily(
    symbol='SHFE.rb2501',
    start_date=20250101,
    end_date=20250131
)

# ========== 新版本（方式1：使用 Adapter）==========
from quantbox.adapters import TSAdapter

adapter = TSAdapter()

# 交易日历
df = adapter.get_trade_calendar(
    exchanges=['SHSE'],  # 标准交易所代码
    start_date=20250101,
    end_date=20250131
)

# 期货合约
df = adapter.get_future_contracts(
    exchanges='SHFE',
    spec_names='rb'  # 参数名复数化
)

# 日线数据
df = adapter.get_future_daily(
    symbols='SHFE.rb2501',  # 参数名复数化
    start_date=20250101,
    end_date=20250131
)

# ========== 新版本（方式2：使用 Service，推荐）==========
from quantbox.services import MarketDataService

service = MarketDataService()

# 自动选择数据源（本地优先，远程备用）
df = service.get_trade_calendar(
    exchanges='SHSE',
    start_date=20250101,
    end_date=20250131
)

# 显式指定数据源
df_local = service.get_future_contracts(use_local=True)
df_remote = service.get_future_contracts(use_local=False)
```

### 数据保存

```python
# ========== 旧版本 ==========
# 手写 MongoDB 批处理或使用旧的 MarketDataSaver

# ========== 新版本 ==========
from quantbox.services import DataSaverService

saver = DataSaverService()

# 保存数据并获取详细结果
result = saver.save_future_daily(
    exchanges='SHFE',
    start_date=20250101,
    end_date=20250131
)

# 检查结果
if result.success:
    print(f"插入: {result.inserted_count} 条")
    print(f"更新: {result.modified_count} 条")
    print(f"耗时: {result.duration:.2f}s")
else:
    print(f"错误: {result.error_count} 个")
    for error in result.errors:
        print(f"  - {error['message']}")
```

## 掘金量化支持

从 v2.0 开始，GMAdapter 已完整实现：

```python
from quantbox.adapters import GMAdapter
from quantbox.services import MarketDataService

# 方式1：直接使用 GMAdapter
gm = GMAdapter(token="your_gm_token")
df = gm.get_trade_calendar(
    exchanges=['SHFE'],
    start_date=20250101,
    end_date=20250131
)

# 方式2：在 Service 中使用（推荐）
service = MarketDataService(
    remote_adapter=GMAdapter(token="your_token")
)
df = service.get_future_daily(symbols='SHFE.rb2501', use_local=False)
```

**注意**：掘金 SDK 仅支持 Windows/Linux，不支持 macOS。

## CLI 和 Shell 更新

所有命令行工具已迁移到新架构，用法保持不变：

```bash
# Shell 交互式命令
quantbox
quantbox> save_future_daily
quantbox> save_trade_calendar
quantbox> save_all

# CLI 命令
quantbox-cli save-future-daily
quantbox-cli save-trade-calendar
```

**智能默认行为**（无参数调用）：
- `save_trade_calendar`: 保存今年所有交易所的交易日历
- `save_future_daily`: 保存从 1990-01-01 到今天的所有历史日线数据
- `save_future_holdings`: 保存从 1990-01-01 到今天的所有历史持仓数据

**参数支持**：
```bash
# 指定交易所
save_future_daily --exchanges SHFE,DCE

# 指定日期范围
save_future_daily --start-date 2025-01-01 --end-date 2025-01-31

# 指定单日
save_future_daily --date 2025-01-15

# 组合使用
save_future_daily --exchanges SHFE --date 2025-01-15
```

## 迁移检查清单

- [ ] 替换导入：`TSFetcher` → `TSAdapter` 或 `MarketDataService`
- [ ] 更新方法名：`fetch_get_*()` → `get_*()`
- [ ] 更新参数名：`symbol` → `symbols`, `spec_name` → `spec_names`
- [ ] 更新交易所代码：`SSE` → `SHSE`, `SZ` → `SZSE`
- [ ] 更新合约格式：统一为 `SHFE.rb2501`
- [ ] 使用 `SaveResult` 检查保存结果
- [ ] 运行测试验证：`uv run pytest tests/ -v`

## 常见问题

**Q: 旧代码还能用吗？**
A: 旧的 `TSFetcher` 已标记为废弃，会触发 `DeprecationWarning`，计划在 2026-01-01 移除。

**Q: 如何选择 Adapter 还是 Service？**
A: 推荐使用 `MarketDataService`，它提供自动数据源选择（本地优先）和统一接口。直接使用 Adapter 适合需要明确控制数据源的场景。

**Q: 掘金 API 在 macOS 上如何使用？**
A: 掘金 SDK 不支持 macOS，建议使用 Tushare 或在 Windows/Linux 环境中运行。

**Q: 如何处理日期格式？**
A: 服务层会自动转换日期格式，你可以传入 `"2025-01-01"`, `"20250101"` 或 `20250101`，都会被正确处理。

## 时间线

| 日期 | 事件 |
|------|------|
| 2025-10-30 | v2.0 发布，新架构上线 |
| 2025-11-05 | TSFetcher 标记废弃，GMAdapter 完成 |
| 2026-01-01 | TSFetcher 计划移除 |

## 参考文档

- [快速开始](QUICK_START.md)
- [API 参考](API_REFERENCE.md)
- [架构文档](ARCHITECTURE.md)
- [重构进度](refactor_progress.md)

---

**需要帮助？** 在 [GitHub Issues](https://github.com/your-org/quantbox/issues) 提问
