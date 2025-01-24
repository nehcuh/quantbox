# 交易日历保存功能手工测试用例

## 测试环境要求

1. **系统要求**
   - Python 3.8 或以上版本
   - MongoDB 服务已启动
   - 已安装 quantbox 包（开发模式：`pip install -e .`）

2. **配置要求**
   - `~/.quantbox/settings/config.toml` 文件已正确配置
   - 配置文件中包含有效的 Tushare token
   - MongoDB 连接信息正确配置

## 测试用例

### TC-001: 默认行为测试

**目的**：验证不带任何参数时，能否正确保存所有交易所的数据

**步骤**：
1. 命令行工具方式：
   ```bash
   python -m quantbox.cli.trade_dates
   ```
2. 脚本方式：
   ```bash
   python scripts/save_trade_dates.py
   ```

**预期结果**：
- 成功保存以下所有交易所的数据：
  1. SSE（上交所）
  2. SZSE（深交所）
  3. SHFE（上期所）
  4. DCE（大商所）
  5. CZCE（郑商所）
  6. CFFEX（中金所）
  7. INE（能源所）
  8. GFEX（广期所）
- 每个交易所都显示保存成功的提示信息

### TC-002: 单个交易所测试

**目的**：验证指定单个交易所时，是否只保存该交易所的数据

**步骤**：
1. 命令行工具方式：
   ```bash
   python -m quantbox.cli.trade_dates -e SSE
   ```
2. 脚本方式：
   ```bash
   python scripts/save_trade_dates.py -e SSE
   ```

**预期结果**：
- 只保存上交所（SSE）的数据
- 显示一条保存成功的提示信息

### TC-003: 股票交易所测试

**目的**：验证指定股票交易所类型时，是否只保存股票交易所的数据

**步骤**：
1. 命令行工具方式：
   ```bash
   python -m quantbox.cli.trade_dates -t STOCK
   ```
2. 脚本方式：
   ```bash
   python scripts/save_trade_dates.py -t STOCK
   ```

**预期结果**：
- 只保存以下交易所的数据：
  1. SSE（上交所）
  2. SZSE（深交所）
- 显示两条保存成功的提示信息

### TC-004: 期货交易所测试

**目的**：验证指定期货交易所类型时，是否只保存期货交易所的数据

**步骤**：
1. 命令行工具方式：
   ```bash
   python -m quantbox.cli.trade_dates -t FUTURES
   ```
2. 脚本方式：
   ```bash
   python scripts/save_trade_dates.py -t FUTURES
   ```

**预期结果**：
- 只保存以下交易所的数据：
  1. SHFE（上期所）
  2. DCE（大商所）
  3. CZCE（郑商所）
  4. CFFEX（中金所）
  5. INE（能源所）
  6. GFEX（广期所）
- 显示六条保存成功的提示信息

### TC-005: 日期范围测试

**目的**：验证指定日期范围时，是否只保存该范围内的数据

**步骤**：
1. 命令行工具方式：
   ```bash
   python -m quantbox.cli.trade_dates -e SSE -s 20240101 -d 20241231
   ```
2. 脚本方式：
   ```bash
   python scripts/save_trade_dates.py -e SSE -s 20240101 -d 20241231
   ```

**预期结果**：
- 只保存上交所 2024 年的交易日历数据
- 显示一条保存成功的提示信息

### TC-006: 帮助信息测试

**目的**：验证帮助信息是否完整准确

**步骤**：
1. 命令行工具方式：
   ```bash
   python -m quantbox.cli.trade_dates --help
   ```
2. 脚本方式：
   ```bash
   python scripts/save_trade_dates.py --help
   ```

**预期结果**：
- 显示完整的帮助信息，包括：
  1. 所有可用的命令行选项
  2. 每个选项的说明
  3. 默认值说明
  4. 使用示例

## 数据验证

对于每个测试用例，除了检查命令执行成功外，还应该：

1. **检查数据库**
   - 使用 MongoDB 客户端工具查看保存的数据
   - 确认数据的完整性和正确性

2. **检查日期范围**
   - 确认数据的起始日期是否正确（默认从 19890101 开始）
   - 确认数据的结束日期是否正确（默认到当年年底）

3. **检查数据格式**
   - 确认日期格式是否正确（YYYYMMDD）
   - 确认是否包含所有必要字段（交易所、日期、前一交易日、是否开市等）

## 错误处理测试

### TC-007: 无效交易所测试

**目的**：验证输入无效的交易所代码时的错误处理

**步骤**：
```bash
python -m quantbox.cli.trade_dates -e INVALID
```

**预期结果**：
- 显示适当的错误信息
- 程序不会崩溃

### TC-008: 无效日期测试

**目的**：验证输入无效的日期格式时的错误处理

**步骤**：
```bash
python -m quantbox.cli.trade_dates -e SSE -s 2024-01-01
```

**预期结果**：
- 显示适当的错误信息
- 程序不会崩溃

## 注意事项

1. 每次测试前，建议清空相关的数据集，以确保测试结果的准确性
2. 测试时注意观察命令的执行时间，特别是在保存大量数据时
3. 如果遇到错误，记录错误信息和复现步骤
4. 测试完成后，检查数据库空间使用情况
