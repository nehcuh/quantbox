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
