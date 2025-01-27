# 数据管理

本文档详细介绍了 QuantBox 的数据管理功能，包括数据获取、存储和访问。

## 数据来源

QuantBox 目前支持以下数据源：

1. **Tushare**
   - 股票数据
   - 期货数据
   - 基础数据（交易日历等）

2. **掘金量化**（开发中）
   - 实时行情
   - 历史数据

## 数据类型

### 1. 交易日历

交易日历数据包含各个交易所的交易日期信息，支持：
- 股票交易所（上交所、深交所）
- 期货交易所（上期所、大商所、郑商所、中金所、能源所）

### 2. 期货合约

期货合约数据包含以下字段：
- `symbol`: 合约代码
- `name`: 合约名称
- `exchange`: 交易所代码
- `list_date`: 上市日期
- `delist_date`: 退市日期
- `list_datestamp`: 上市时间戳
- `delist_datestamp`: 退市时间戳
- `chinese_name`: 品种中文名
- `all_contracts`: 同品种所有合约列表

#### 数据获取

1. **命令行工具**

```bash
# 保存所有交易所的期货合约数据
python scripts/save_future_contracts.py

# 保存指定交易所的期货合约数据
python scripts/save_future_contracts.py -e DCE

# 保存指定交易所和品种的期货合约数据
python scripts/save_future_contracts.py -e DCE -s 豆粕

# 保存指定日期的期货合约数据
python scripts/save_future_contracts.py -d 20240127
```

2. **交互式命令行**

```bash
# 启动交互式命令行
python -m quantbox.cli.shell

# 在交互式命令行中使用以下命令
quantbox> save future_contracts              # 保存所有交易所数据
quantbox> save future_contracts -e DCE       # 保存大商所数据
quantbox> save future_contracts -s 豆粕      # 保存豆粕品种数据
quantbox> save future_contracts -d 20240127  # 保存指定日期数据
```

#### 数据库结构

期货合约数据存储在 MongoDB 数据库中，使用以下索引优化查询性能：

1. **复合唯一索引**
   ```javascript
   {
     "exchange": 1,
     "symbol": 1,
     "list_date": 1
   }
   ```
   此索引确保合约记录的唯一性，并优化按交易所、合约代码和上市日期的查询。

2. **时间戳索引**
   ```javascript
   {
     "list_datestamp": -1
   }
   {
     "delist_datestamp": -1
   }
   ```
   这些索引优化按上市时间和退市时间的查询，支持高效的时间范围查询。

### 3. 期货行情（开发中）

期货行情数据将支持：
- 日线数据
- 分钟数据
- 实时行情

## 数据访问

### Python API

```python
from quantbox.data.database import MongoDBManager
from quantbox.core.config import ConfigLoader

# 初始化数据库管理器
db = MongoDBManager(ConfigLoader.get_database_config())

# 获取期货合约数据
collection = db.future_contracts
contracts = collection.find({
    "exchange": "DCE",
    "chinese_name": "豆粕"
})

# 处理数据
for contract in contracts:
    print(f"合约代码: {contract['symbol']}")
    print(f"上市日期: {contract['list_date']}")
    print(f"退市日期: {contract.get('delist_date', '未退市')}")
```

## 数据更新策略

1. **增量更新**
   - 系统会自动处理数据重复问题
   - 使用 upsert 操作确保数据一致性

2. **定时更新**
   - 建议每日收盘后更新一次数据
   - 可以通过 cron 等工具实现自动更新

## 错误处理

数据管理模块实现了完整的错误处理机制：

1. **数据验证**
   - 检查必要字段
   - 验证字段类型和格式
   - 确保数据完整性

2. **异常处理**
   - 网络错误重试
   - 数据库操作异常处理
   - 详细的错误日志
