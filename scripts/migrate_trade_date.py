#!/usr/bin/env python
"""
交易日历数据迁移脚本

将 trade_date 集合中的旧数据结构迁移到新结构：
- 移除 is_open 字段（冗余，我们只保存交易日）
- 添加 datestamp 字段（用于快速日期比较）

旧结构:
{
    "date": 20240105,      # int
    "exchange": "SHSE",    # str
    "is_open": True        # bool - 冗余
}

新结构:
{
    "date": 20240105,       # int - YYYYMMDD 格式
    "exchange": "SHFE",     # str
    "datestamp": 1704384000 # timestamp - 用于快速比较
}

使用方法:
    python scripts/migrate_trade_date.py [--dry-run]

选项:
    --dry-run: 只显示将要更新的文档数量，不实际修改数据
"""

import sys
import argparse
from pymongo import UpdateOne
from quantbox.config.config_loader import get_config_loader
from quantbox.util.date_utils import util_make_date_stamp


def migrate_trade_date(dry_run=False):
    """
    迁移 trade_date 集合数据结构

    Args:
        dry_run: 如果为 True，只统计不实际修改
    """
    print("=" * 80)
    print("交易日历数据迁移脚本")
    print("=" * 80)
    print()

    # 连接数据库
    print("连接 MongoDB...")
    config = get_config_loader()
    client = config.get_mongodb_client()
    db = client.quantbox
    collection = db.trade_date

    # 统计需要迁移的文档
    print("统计需要迁移的文档...")

    # 查找有 is_open 字段的文档（旧结构）
    docs_with_is_open = collection.count_documents({"is_open": {"$exists": True}})

    # 查找没有 datestamp 字段的文档
    docs_without_datestamp = collection.count_documents({"datestamp": {"$exists": False}})

    print(f"包含 is_open 字段的文档数: {docs_with_is_open}")
    print(f"缺少 datestamp 字段的文档数: {docs_without_datestamp}")
    print()

    if docs_with_is_open == 0 and docs_without_datestamp == 0:
        print("✅ 所有文档已经是新格式，无需迁移")
        return

    if dry_run:
        print("🔍 Dry-run 模式：将要进行的操作")
        if docs_with_is_open > 0:
            print(f"   - 移除 {docs_with_is_open} 个文档的 is_open 字段")
        if docs_without_datestamp > 0:
            print(f"   - 为 {docs_without_datestamp} 个文档添加 datestamp 字段")
        print()
        print("请运行不带 --dry-run 参数的命令来执行实际迁移")
        return

    # 执行实际迁移
    print("开始迁移...")
    print()

    # 第一步：移除 is_open 字段
    if docs_with_is_open > 0:
        print(f"步骤 1/2: 移除 is_open 字段 ({docs_with_is_open} 个文档)...")
        result = collection.update_many(
            {"is_open": {"$exists": True}},
            {"$unset": {"is_open": ""}}
        )
        print(f"   ✅ 已更新 {result.modified_count} 个文档")
        print()
    else:
        print("步骤 1/2: 跳过（所有文档已移除 is_open 字段）")
        print()

    # 第二步：添加 datestamp 字段
    if docs_without_datestamp > 0:
        print(f"步骤 2/2: 添加 datestamp 字段 ({docs_without_datestamp} 个文档)...")

        # 批量获取需要更新的文档
        docs = collection.find(
            {"datestamp": {"$exists": False}},
            {"_id": 1, "date": 1}
        )

        # 构建批量更新操作
        operations = []
        count = 0

        for doc in docs:
            try:
                # 计算 datestamp
                date_int = doc["date"]
                datestamp = util_make_date_stamp(date_int)

                operations.append(
                    UpdateOne(
                        {"_id": doc["_id"]},
                        {"$set": {"datestamp": datestamp}}
                    )
                )
                count += 1

                # 每 1000 个文档执行一次批量操作
                if len(operations) >= 1000:
                    collection.bulk_write(operations)
                    print(f"   已处理 {count} 个文档...")
                    operations = []

            except Exception as e:
                print(f"   ⚠️  处理文档 {doc['_id']} 时出错: {str(e)}")

        # 执行剩余操作
        if operations:
            collection.bulk_write(operations)

        print(f"   ✅ 已更新 {count} 个文档")
        print()
    else:
        print("步骤 2/2: 跳过（所有文档已有 datestamp 字段）")
        print()

    # 验证迁移结果
    print("验证迁移结果...")
    docs_with_is_open = collection.count_documents({"is_open": {"$exists": True}})
    docs_without_datestamp = collection.count_documents({"datestamp": {"$exists": False}})

    if docs_with_is_open == 0 and docs_without_datestamp == 0:
        print("✅ 迁移成功！所有文档已更新为新格式")
    else:
        print("⚠️  迁移后仍有部分文档需要处理:")
        if docs_with_is_open > 0:
            print(f"   - {docs_with_is_open} 个文档仍有 is_open 字段")
        if docs_without_datestamp > 0:
            print(f"   - {docs_without_datestamp} 个文档缺少 datestamp 字段")

    print()
    print("=" * 80)
    print("迁移完成")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="迁移 trade_date 集合数据结构",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 预览迁移操作（不实际修改数据）
  python scripts/migrate_trade_date.py --dry-run

  # 执行实际迁移
  python scripts/migrate_trade_date.py
        """
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只显示将要更新的文档数量，不实际修改数据"
    )

    args = parser.parse_args()

    try:
        migrate_trade_date(dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
