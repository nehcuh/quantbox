from pymongo import MongoClient
import pandas as pd
from datetime import datetime

# 连接到 MongoDB
client = MongoClient('mongodb://localhost:27018')
db = client['quantbox']

def test_trade_dates():
    """测试交易日期数据"""
    collection = db['trade_date']
    # 获取最新的交易日期
    latest = collection.find_one(sort=[('datestamp', -1)])
    print("\n=== 交易日期测试 ===")
    print(f"总记录数: {collection.count_documents({})}")
    print(f"最新交易日: {latest['datestamp'] if latest else 'N/A'}")
    print(f"数据示例:")
    for doc in collection.find().limit(3):
        print(doc)

def test_future_contracts():
    """测试期货合约数据"""
    collection = db['future_contracts']
    # 获取一条数据来查看结构
    sample = collection.find_one()
    print("\n=== 期货合约测试 ===")
    print(f"总记录数: {collection.count_documents({})}")
    print(f"数据结构示例:")
    if sample:
        print("字段列表:", list(sample.keys()))
        print("数据示例:", sample)
    print(f"\n数据示例:")
    for doc in collection.find().limit(3):
        print(doc)

def test_future_holdings():
    """测试期货持仓数据"""
    collection = db['future_holdings']
    # 获取一条数据来查看结构
    sample = collection.find_one()
    print("\n=== 期货持仓测试 ===")
    print(f"总记录数: {collection.count_documents({})}")
    print(f"数据结构示例:")
    if sample:
        print("字段列表:", list(sample.keys()))
        print("数据示例:", sample)
    print(f"\n数据示例:")
    for doc in collection.find().limit(3):
        print(doc)

if __name__ == '__main__':
    print("开始测试数据库...")
    test_trade_dates()
    test_future_contracts()
    test_future_holdings()
    print("\n测试完成！")
