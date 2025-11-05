# Quantbox 迁移指南（旧版 → 新版）

本文帮助你从旧版 API/结构迁移到新版三层架构（Application/Services/Adapters）。

## 0. 总览

- 新版核心：`MarketDataService`, `DataSaverService`，统一通过服务层访问
- 适配器解耦：`LocalAdapter`(MongoDB), `TSAdapter`(Tushare)，后续可扩展 `GMAdapter`
- 统一数据规范：日期/int，交易所代码/合约代码统一
- CLI/GUI 与 Python API 一致化

## 1. 破坏性变更摘要

1) 命名空间
- 旧：零散函数，如 `ts_get_trade_cal`, `ts_get_future_daily`
- 新：通过 `quantbox.services.MarketDataService`

2) 日期类型
- 旧：可能混用 `datetime/date/str`
- 新：方法参数接受 `YYYY-MM-DD` 或 `YYYYMMDD`，内部统一为 `int`

3) 交易所/代码规范
- 旧：`SSE/SH`、`SZSE/SZ` 等混用；合约编码格式不统一
- 新：交易所统一为 `SHFE, DCE, CZCE, INE, SHSE, SZSE`；合约统一 `RB2405.SHF`

4) 返回类型
- 旧：可能为 `list[dict]` 或 `DataFrame` 不一致
- 新：统一返回 `pandas.DataFrame`

5) 保存逻辑
- 旧：直接写库或脚本式批处理
- 新：`DataSaverService` 统一批处理、索引与去重，返回 `SaveResult`

6) 配置
- 旧：散落在代码/脚本
- 新：环境变量/配置文件与构造参数优先级明确

## 2. 快速映射表

| 旧 API/用法 | 新 API/用法 |
| --- | --- |
| `ts_get_trade_cal(exchange, start, end)` | `MarketDataService().get_trade_calendar([exchange], start, end)` |
| `ts_get_fut_contracts(exchange, symbol)` | `MarketDataService().get_future_contracts([exchange], [symbol])` |
| `ts_get_fut_daily(ts_codes, start, end)` | `MarketDataService().get_future_daily(contracts=ts_codes, start_date=start, end_date=end)` |
| 直接写 Mongo 批量 upsert | `DataSaverService().save_future_daily(...)` |
| 混用 `SSE/SH`, `SZ/SZSE` | `normalize_exchange` 后统一为 `SHSE, SZSE` |
| `RB2405` / `RB2405.SHF` 混用 | 统一使用 `RB2405.SHF` |

## 3. 逐步迁移步骤

1) 清理依赖与安装
- `pip install -r requirements.txt && pip install -e .`

2) 规范化数据参数
- 使用 `quantbox.util.date_utils` 将日期转为 `int`
- 使用 `quantbox.util.exchange_utils.normalize_exchange`
- 统一合约编码为 `RB2405.SHF`

3) 替换数据查询入口
- 将所有旧的 Tushare 直连函数替换为 `MarketDataService` 对应方法

4) 替换数据保存入口
- 将脚本式 Mongo 写入替换为 `DataSaverService.save_*`

5) 配置迁移
- 设置 `TUSHARE_TOKEN` 环境变量或 `~/.quantbox/config.yml`
- 配置 Mongo：`MONGO_HOST/PORT/DB/USER/PASSWORD`

6) 测试与验证
- 基于返回 DataFrame 列定义（见 API_REFERENCE.md 第 3 节）构造断言
- 对比旧/新结果抽样核验

## 4. 代码示例（前后对比）

旧
```python
# 直接调用 Tushare 函数
cal = ts_get_trade_cal("SHFE", "2024-01-01", "2024-12-31")  # 返回 list[dict]
```
新
```python
from quantbox.services import MarketDataService
svc = MarketDataService()
cal = svc.get_trade_calendar(["SHFE"], "2024-01-01", "2024-12-31")  # 返回 DataFrame
```

旧
```python
# 直接拼接合约并查询
k = ts_get_fut_daily(["RB2405.SHF"], "20240101", "20240131")
```
新
```python
k = MarketDataService().get_future_daily(
    contracts=["RB2405.SHF"], start_date=20240101, end_date=20240131
)
```

旧
```python
# 手写 Mongo 批处理
bulk_upsert_daily(data)
```
新
```python
from quantbox.services import DataSaverService
res = DataSaverService().save_future_daily(
    contracts=["RB2405.SHF"], start_date=20240101, end_date=20241231
)
print(res.inserted_count, res.modified_count)
```

## 5. 常见坑与修复

- 日期类型：确保统一为 `YYYYMMDD` int；如传入 str，服务层会自动转换
- 交易所代码：`SSE` → `SHSE`，`SZ` → `SZSE`
- 合约编码：必须形如 `RB2405.SHF`，否则适配器可能返回空
- 主力合约：使用 `is_main=True` 与 `symbols=["RB"]` 组合查询
- 字段选择：如需减少内存，可传 `fields=["trade_date", "ts_code", "close"]`

## 6. 弃用与时间线

- 旧直连函数将触发 `DeprecationWarning`，并于下一主要版本移除
- 新增/变更详情以 `CHANGELOG.md` 为准

## 7. 回滚计划

- 保持分支：在迁移期保留旧分支，可随时回滚
- 兼容层：可临时在项目内包装旧函数调用新服务，降低改动面

## 8. 支持

- 参考：[API_REFERENCE.md](API_REFERENCE.md) 与 [QUICK_START.md](QUICK_START.md)
- 提 Issue：GitHub 仓库 Issues

---

## 9. 最新更新 (2025-11-05)

### ⚠️ 重要：废弃警告

**TSFetcher 已正式标记为废弃！**

从 2025-11-05 开始，使用 `quantbox.fetchers.fetcher_tushare.TSFetcher` 会收到 DeprecationWarning：

```python
# ❌ 将触发警告
from quantbox.fetchers.fetcher_tushare import TSFetcher
# DeprecationWarning: quantbox.fetchers.fetcher_tushare.TSFetcher 已废弃，
# 请使用 quantbox.adapters.ts_adapter.TSAdapter 替代。
# 本模块将在未来版本中移除。
```

**请尽快迁移！**

### 🆕 GMAdapter 已添加

新增掘金量化数据源支持框架：

```python
from quantbox.adapters import GMAdapter

# 初始化（需要掘金量化 token）
gm_adapter = GMAdapter(token="your_gm_token")

# 接口框架已就绪，核心实现需要掘金 API 访问
# 查看 quantbox/adapters/gm_adapter.py 中的 TODO 注释
```

GMAdapter 实现了完整的接口签名，可以在 `MarketDataService` 中使用：

```python
from quantbox.services import MarketDataService
from quantbox.adapters import GMAdapter

# 使用掘金作为远程数据源
service = MarketDataService(
    remote_adapter=GMAdapter(token="your_token")
)
```

### ✅ 服务层测试覆盖

新架构现已拥有完善的测试覆盖：

| 模块 | 测试数量 | 覆盖率 |
|------|----------|--------|
| **MarketDataService** | 20 个测试 | **100%** |
| **DataSaverService** | 17 个测试 | **85%** |
| 工具层 (utils/) | 126 个测试 | 85%+ |
| **总计** | **178+ 个测试** | 30%+ |

运行测试：
```bash
# 运行所有测试
uv run pytest tests/ -v

# 运行服务层测试
uv run pytest tests/test_market_data_service.py tests/test_data_saver_service.py -v

# 生成覆盖率报告
uv run pytest --cov=quantbox --cov-report=html
```

### 📊 新旧 API 详细对照

#### TSFetcher → TSAdapter

```python
# ========== 旧代码 ==========
from quantbox.fetchers.fetcher_tushare import TSFetcher

fetcher = TSFetcher()

# 获取交易日历
df = fetcher.fetch_get_trade_dates(
    exchanges=['SSE'],  # 使用旧交易所代码
    start_date=20250101,
    end_date=20250131
)

# 获取期货合约
df = fetcher.fetch_get_future_contracts(
    exchange='SHFE',
    spec_name='rb'  # 单数
)

# 获取日线数据
df = fetcher.fetch_get_future_daily(
    symbol='SHFE.rb2501',  # 单数
    start_date=20250101,
    end_date=20250131
)

# ========== 新代码 ==========
from quantbox.adapters import TSAdapter

adapter = TSAdapter()

# 获取交易日历
df = adapter.get_trade_calendar(
    exchanges=['SHSE'],  # 使用标准交易所代码
    start_date=20250101,
    end_date=20250131
)

# 获取期货合约
df = adapter.get_future_contracts(
    exchanges='SHFE',
    spec_names='rb'  # 复数（参数名变化）
)

# 获取日线数据
df = adapter.get_future_daily(
    symbols='SHFE.rb2501',  # 复数（参数名变化）
    start_date=20250101,
    end_date=20250131
)
```

#### 推荐：使用 MarketDataService

```python
from quantbox.services import MarketDataService

# 初始化服务（自动配置本地和远程适配器）
service = MarketDataService(prefer_local=True)

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

### 🔧 主要参数变化

| 类别 | 旧参数名 | 新参数名 | 说明 |
|------|----------|----------|------|
| 方法名 | `fetch_get_*` | `get_*` | 移除 fetch 前缀 |
| 交易所 | `exchanges=['SSE']` | `exchanges=['SHSE']` | 使用标准代码 |
| 合约 | `symbol='rb2501'` | `symbols='SHFE.rb2501'` | 参数名复数化 |
| 品种 | `spec_name='rb'` | `spec_names='rb'` | 参数名复数化 |

### 📦 SaveResult 结果对象

`DataSaverService` 现在返回详细的保存结果：

```python
from quantbox.services import DataSaverService

saver = DataSaverService()
result = saver.save_trade_calendar(
    exchanges='SHSE',
    start_date=20250101,
    end_date=20250131
)

# 检查结果
if result.success:
    print(f"✅ 成功!")
    print(f"   插入: {result.inserted_count} 条")
    print(f"   更新: {result.modified_count} 条")
    print(f"   耗时: {result.duration}")
else:
    print(f"❌ 失败: {result.error_count} 个错误")
    for error in result.errors:
        print(f"   - {error['type']}: {error['message']}")

# 转换为字典
result_dict = result.to_dict()
```

### 🚀 迁移检查清单

- [ ] 将所有 `from quantbox.fetchers.fetcher_tushare import TSFetcher` 替换为 `from quantbox.adapters import TSAdapter`
- [ ] 更新方法调用：`fetch_get_*()` → `get_*()`
- [ ] 更新参数名：`symbol` → `symbols`, `spec_name` → `spec_names`
- [ ] 更新交易所代码：`SSE` → `SHSE`, `SZ` → `SZSE`
- [ ] 使用 `SaveResult` 对象检查保存结果
- [ ] 运行测试验证无回归：`uv run pytest tests/ -v`
- [ ] 考虑使用 `MarketDataService` 获得自动数据源选择

### 📅 时间线

| 日期 | 事件 |
|------|------|
| 2025-10-30 | 新架构发布 |
| 2025-11-05 | TSFetcher 标记废弃 ✅ |
| 2026-01-01 | TSFetcher 计划移除 ⏳ |

**尽快迁移以避免未来版本中的兼容性问题！**

### 🔧 CLI 和 Shell 已更新为新架构 (2025-11-05)

**quantbox-shell 和 CLI 命令现已使用新的 DataSaverService！**

#### 变化说明

从 2025-11-05 开始，所有 CLI 和 Shell 命令已迁移到新架构：

**Shell (交互式命令行)**：
```bash
# 启动 Shell
python -m quantbox.shell

# 或者使用命令
quantbox> save_future_daily
quantbox> save_trade_dates
quantbox> save_all
```

**CLI (命令行工具)**：
```bash
# 使用 CLI 命令
quantbox-cli save-future-daily
quantbox-cli save-trade-dates
quantbox-cli save-all
```

#### 主要变化

| 变化点 | 旧架构 | 新架构 |
|--------|--------|--------|
| **数据保存类** | `MarketDataSaver` | `DataSaverService` |
| **Engine 参数** | 支持 `--engine ts/gm` | 已移除，默认使用 Tushare |
| **返回结果** | 无详细反馈 | 显示插入/更新条数 |
| **save_stock_list** | 正常支持 | 临时使用旧架构（新架构待实现）|

#### 不再支持的功能

- ❌ **Engine 参数**: `save_future_daily --engine gm` 不再支持
- ⚠️ **GMAdapter**: 新架构默认使用 Tushare，GM 支持需单独配置

#### 兼容性说明

**命令名称保持不变**：
- `save_future_daily` ✅
- `save_trade_dates` ✅ (内部调用 save_trade_calendar)
- `save_future_contracts` ✅
- `save_future_holdings` ✅
- `save_stock_list` ✅ (临时使用旧架构)
- `save_all` ✅

**用户无需修改使用方式**，但会看到更详细的输出：

```bash
# 新架构输出示例
quantbox> save_future_daily
期货日线数据保存完成: 插入 1250 条，更新 48 条
```

#### 注意事项

1. **stock_list 命令**：由于新架构暂未实现 `save_stock_list`，该命令临时使用旧的 `MarketDataSaver`
2. **数据源**：所有命令默认使用 Tushare 数据源
3. **性能提升**：新架构使用批量 upsert，性能更好

### 🎯 智能默认行为与参数支持 (2025-11-05 更新)

#### 智能默认行为

从 2025-11-05 开始，所有保存命令在**无参数调用时都有智能默认行为**：

| 命令 | 无参数默认行为 |
|------|---------------|
| `save_trade_dates` | 保存今年所有交易所的交易日历（1月1日至今天）|
| `save_future_contracts` | 保存所有期货交易所的合约信息 |
| `save_future_daily` | 保存今天所有期货交易所的日线数据 |
| `save_future_holdings` | 保存今天所有期货交易所的持仓数据 |

**示例**：
```bash
# Shell 中无参数调用
quantbox> save_future_daily
# ↑ 自动保存今天所有期货交易所（SHFE, DCE, CZCE, CFFEX, INE, GFEX）的数据
期货日线数据保存完成: 插入 1250 条，更新 48 条
```

#### 参数支持

所有命令现在支持丰富的参数选项：

**Shell 命令参数格式**：
```bash
# 保存指定交易所
save_future_daily --exchanges SHFE,DCE

# 保存指定合约
save_future_daily --symbols SHFE.rb2501,DCE.m2505

# 保存指定日期
save_future_daily --date 2025-01-15

# 保存日期范围
save_future_daily --start-date 2025-01-01 --end-date 2025-01-31

# 组合使用
save_future_daily --exchanges SHFE --start-date 2025-01-01 --end-date 2025-01-31
```

**CLI 命令参数格式**：
```bash
# 保存指定交易所
quantbox-cli save-future-daily --exchanges SHFE,DCE

# 保存指定合约
quantbox-cli save-future-daily --symbols SHFE.rb2501,DCE.m2505

# 保存指定日期
quantbox-cli save-future-daily --date 2025-01-15

# 保存日期范围
quantbox-cli save-future-daily --start-date 2025-01-01 --end-date 2025-01-31
```

#### 完整参数列表

**save_trade_dates**：
- `--exchanges`: 交易所代码，多个用逗号分隔
- `--start-date`: 起始日期（默认：今年1月1日）
- `--end-date`: 结束日期（默认：今天）

**save_future_contracts**：
- `--exchanges`: 交易所代码（默认：所有期货交易所）
- `--symbols`: 合约代码
- `--spec-names`: 品种名称（如：rb,cu,al）
- `--date`: 查询日期

**save_future_daily**：
- `--exchanges`: 交易所代码（默认：所有期货交易所）
- `--symbols`: 合约代码
- `--date`: 单日查询（默认：今天）
- `--start-date`: 起始日期
- `--end-date`: 结束日期

**save_future_holdings**：
- `--exchanges`: 交易所代码（默认：所有期货交易所）
- `--symbols`: 合约代码
- `--spec-names`: 品种名称
- `--date`: 单日查询（默认：今天）
- `--start-date`: 起始日期
- `--end-date`: 结束日期

#### 使用技巧

1. **快速保存今天数据**：无参数调用即可
   ```bash
   save_future_daily
   ```

2. **保存特定交易所**：使用 `--exchanges`
   ```bash
   save_future_daily --exchanges SHFE,DCE
   ```

3. **保存特定合约**：使用 `--symbols`
   ```bash
   save_future_daily --symbols SHFE.rb2501,SHFE.rb2505
   ```

4. **历史数据回填**：使用日期范围
   ```bash
   save_future_daily --start-date 2024-01-01 --end-date 2024-12-31
   ```
