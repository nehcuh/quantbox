# QuantBox GUI

QuantBox GUI 是一个图形用户界面，用于方便地获取和查看量化交易数据。

## 功能特点

1. 数据获取
   - 支持多个数据源（TuShare、GoldMiner）
   - 支持多种数据类型（持仓、交易日期、合约）
   - 支持日期范围选择
   - 支持交易所选择
   - 自动保存到 MongoDB

2. 数据查看
   - 支持查看所有数据集合
   - 支持 MongoDB 查询语法
   - 表格形式展示数据
   - 自动过滤 MongoDB ID

## 安装要求

- Python 3.7+
- MongoDB
- PyQt6
- pandas
- pymongo

## 安装步骤

1. 确保已安装并启动 MongoDB：
   ```bash
   brew services start mongodb-community
   ```

2. 安装 QuantBox：
   ```bash
   pip install -e .
   ```

## 使用方法

1. 启动 GUI：
   ```bash
   quantbox-gui
   ```

2. 获取数据：
   - 选择数据源（TuShare/GoldMiner）
   - 选择日期范围
   - 选择数据类型（Holdings/Trade Dates/Contracts）
   - 选择交易所
   - 点击 "Fetch Data" 按钮

3. 查看数据：
   - 切换到 "Data View" 标签页
   - 选择要查看的数据集合
   - 输入查询条件（可选）
   - 点击 "Query" 按钮

## 查询示例

1. 查询特定交易所的数据：
   ```json
   {"exchange": "SHFE"}
   ```

2. 查询特定日期范围的数据：
   ```json
   {"trade_date": {"$gte": "2024-01-01", "$lte": "2024-01-31"}}
   ```

3. 查询特定合约的数据：
   ```json
   {"symbol": "cu2402"}
   ```

## 注意事项

1. 确保 MongoDB 服务已启动
2. 数据获取可能需要一定时间，请耐心等待
3. 大量数据的查询可能会较慢，建议使用适当的查询条件
4. 所有错误信息都会以对话框形式显示
