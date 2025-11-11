# Scripts 目录

本目录包含各种实用脚本和诊断工具。

## 工具脚本

### 配置与诊断

- **`diagnose_config.py`** - 配置诊断工具
  - 检查 Tushare token 配置
  - 检查掘金量化 token 配置
  - 检查 MongoDB 连接
  - 验证各组件是否正常工作

### 测试与验证

- **`test_all_adapters.py`** - 综合适配器测试
  - 测试所有数据适配器（LocalAdapter, TSAdapter, GMAdapter）
  - 测试所有服务层（MarketDataService, DataSaverService）
  - 验证数据查询功能和数据一致性
  - 提供完整的测试报告和统计

- **`test_gm_functionality.py`** - 掘金量化功能测试
  - 完整测试 GMAdapter 所有功能
  - 验证掘金 API 集成

### 性能测试

- **`benchmark_trade_dates.py`** - 交易日期性能基准测试
  - 测试交易日期查询性能
  - 对比不同实现的效率

### 数据管理

- **`save_data.py`** - 数据保存脚本
  - 批量保存市场数据
  - 数据初始化工具

- **`check_trade_dates.py`** - 交易日期检查
  - 验证交易日历数据完整性
  - 检查日期数据准确性

- **`migrate_trade_date.py`** - 交易日历数据迁移脚本
  - 将旧的 trade_date 数据结构迁移到优化后的新结构
  - 移除冗余的 is_open 字段
  - 添加 datestamp 字段以提升查询性能
  - 支持 dry-run 模式预览迁移操作

### GUI 启动

- **`run_gui.py`** - 启动图形界面
  - 快速启动 Quantbox GUI

## 使用方法

### 诊断配置

```bash
# 检查所有配置
uv run python scripts/diagnose_config.py
```

### 测试适配器

```bash
# 测试所有适配器和服务
uv run python scripts/test_all_adapters.py

# 测试掘金功能（仅 Windows/Linux）
uv run python scripts/test_gm_functionality.py
```

### 保存数据

```bash
# 保存市场数据
uv run python scripts/save_data.py

# 迁移交易日历数据结构（预览模式）
uv run python scripts/migrate_trade_date.py --dry-run

# 迁移交易日历数据结构（实际执行）
uv run python scripts/migrate_trade_date.py
```

### 性能测试

```bash
# 运行交易日期性能测试
uv run python scripts/benchmark_trade_dates.py
```

## 注意事项

1. **配置要求**：大多数脚本需要正确配置 Tushare token 和/或掘金 token
2. **数据库要求**：某些脚本需要 MongoDB 运行
3. **平台兼容性**：掘金相关脚本仅支持 Windows/Linux，不支持 macOS

## 开发说明

添加新脚本时，请：
1. 使用描述性的文件名
2. 在文件顶部添加清晰的文档字符串
3. 在本 README 中添加说明
4. 确保脚本可以独立运行
