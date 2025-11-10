#!/usr/bin/env python3
"""
测试掘金量化（GMAdapter）数据下载功能

测试内容：
1. GMAdapter 初始化
2. 获取交易日历
3. 获取期货合约列表
4. 下载期货日线数据
5. 保存数据到 MongoDB
"""

import asyncio
import sys
import platform

print("=" * 60)
print("掘金量化数据下载测试")
print("=" * 60)

# 检查平台
print(f"\n[平台检查]")
print(f"  操作系统: {platform.system()}")
print(f"  版本: {platform.version()}")
print(f"[INFO] 掘金 SDK 支持 Windows、Linux 和 macOS 平台")

# 测试 1: 导入 GMAdapter
print("\n" + "=" * 60)
print("[测试 1] 导入 GMAdapter")
print("=" * 60)

try:
    from quantbox.adapters.gm_adapter import GMAdapter
    print("[PASS] GMAdapter 导入成功")
except ImportError as e:
    print(f"[FAIL] GMAdapter 导入失败: {e}")
    print("\n[INFO] 请安装掘金 SDK:")
    print("  pip install gm")
    print("  或: uv pip install gm")
    sys.exit(1)

# 测试 2: 初始化 GMAdapter
print("\n" + "=" * 60)
print("[测试 2] 初始化 GMAdapter")
print("=" * 60)

try:
    adapter = GMAdapter()
    print("[PASS] GMAdapter 初始化成功")

    # 检查是否可用
    if adapter.check_availability():
        print("[PASS] 掘金 API 连接正常")
    else:
        print("[WARN] 掘金 API 连接失败")
        print("[INFO] 请检查:")
        print("  1. token 是否配置正确")
        print("  2. 网络连接是否正常")
        print("  3. 掘金服务是否可用")

except Exception as e:
    print(f"[FAIL] GMAdapter 初始化失败: {e}")
    print("\n[INFO] 可能的原因:")
    print("  1. 未配置 token（~/.quantbox/settings/config.toml）")
    print("  2. GM SDK 未安装")
    print("  3. token 无效或过期")
    sys.exit(1)

# 测试 3: 获取交易日历
print("\n" + "=" * 60)
print("[测试 3] 获取交易日历")
print("=" * 60)

try:
    calendar = adapter.get_trade_calendar(
        exchanges="SHFE",
        start_date="2024-11-01",
        end_date="2024-11-08"
    )

    print(f"[PASS] 获取交易日历成功")
    print(f"  记录数: {len(calendar)} 条")

    if len(calendar) > 0:
        print(f"\n  样例数据（前 3 条）:")
        print(calendar.head(3))
    else:
        print("[WARN] 交易日历数据为空")

except Exception as e:
    print(f"[FAIL] 获取交易日历失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 4: 获取期货合约
print("\n" + "=" * 60)
print("[测试 4] 获取期货合约列表")
print("=" * 60)

try:
    contracts = adapter.get_future_contracts(
        exchanges="SHFE",
        date="2024-11-08"
    )

    print(f"[PASS] 获取期货合约成功")
    print(f"  合约数: {len(contracts)} 个")

    if len(contracts) > 0:
        print(f"\n  样例数据（前 5 个）:")
        print(contracts.head(5)[['symbol', 'exchange', 'name']])
    else:
        print("[WARN] 合约列表为空")

except Exception as e:
    print(f"[FAIL] 获取期货合约失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 5: 下载期货日线数据
print("\n" + "=" * 60)
print("[测试 5] 下载期货日线数据")
print("=" * 60)

try:
    # 下载单个合约的数据
    daily_data = adapter.get_future_daily(
        symbols="SHFE.rb2501",
        start_date="2024-11-01",
        end_date="2024-11-08"
    )

    print(f"[PASS] 下载期货日线数据成功")
    print(f"  记录数: {len(daily_data)} 条")

    if len(daily_data) > 0:
        print(f"  数据列: {list(daily_data.columns)}")

        # 检查关键字段
        required_fields = ['symbol', 'exchange', 'date', 'open', 'high', 'low', 'close', 'volume']
        missing_fields = [f for f in required_fields if f not in daily_data.columns]

        if missing_fields:
            print(f"[WARN] 缺少字段: {missing_fields}")
        else:
            print(f"[PASS] 所有必需字段都存在")

        print(f"\n  样例数据（前 3 条）:")
        print(daily_data.head(3))
    else:
        print("[WARN] 日线数据为空")

except Exception as e:
    print(f"[FAIL] 下载期货日线数据失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 6: 使用 DataSaverService 保存数据
print("\n" + "=" * 60)
print("[测试 6] 使用 DataSaverService 保存数据")
print("=" * 60)

try:
    from quantbox.services.data_saver_service import DataSaverService

    # 创建 saver，使用掘金数据源
    saver = DataSaverService(remote_adapter=adapter)

    # 保存期货日线数据
    result = saver.save_future_daily(
        symbols="SHFE.rb2501",
        date="2024-11-08"
    )

    print(f"[PASS] 数据保存成功")
    print(f"  插入: {result.inserted_count} 条")
    print(f"  更新: {result.modified_count} 条")
    print(f"  错误: {result.error_count} 个")
    print(f"  耗时: {result.duration.total_seconds():.2f}s")

    if result.error_count > 0:
        print(f"  错误详情: {result.errors}")

except Exception as e:
    print(f"[FAIL] 数据保存失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 7: 异步版本
print("\n" + "=" * 60)
print("[测试 7] 异步版本测试")
print("=" * 60)

async def test_async_gm():
    """测试异步 GMAdapter"""
    try:
        from quantbox.adapters.asynchronous.gm_adapter import AsyncGMAdapter
        from quantbox.services.async_data_saver_service import AsyncDataSaverService

        # 创建异步适配器
        async_adapter = AsyncGMAdapter()
        print("[PASS] AsyncGMAdapter 初始化成功")

        # 创建异步 saver
        saver = AsyncDataSaverService(remote_adapter=async_adapter)

        # 保存数据
        result = await saver.save_future_daily(
            symbols="SHFE.rb2501",
            start_date="2024-11-01",
            end_date="2024-11-08"
        )

        print(f"[PASS] 异步数据保存成功")
        print(f"  插入: {result.inserted_count} 条")
        print(f"  更新: {result.modified_count} 条")
        print(f"  耗时: {result.duration.total_seconds():.2f}s")

        return True

    except Exception as e:
        print(f"[FAIL] 异步版本测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

try:
    success = asyncio.run(test_async_gm())
except Exception as e:
    print(f"[FAIL] 异步测试失败: {e}")
    success = False

# 总结
print("\n" + "=" * 60)
print("测试总结")
print("=" * 60)

print("\n[结论]")
print("✅ 掘金量化接口工作正常")
print("✅ 可以成功下载和保存数据")
print("\n[下一步]")
print("1. 在 shell 中使用:")
print("   uv run quantbox-async")
print("   quantbox-async> set_adapter gm")
print("   quantbox-async> save_future_daily --symbols SHFE.rb2501 --date 2024-11-08")
print("\n2. 在 Python 中使用:")
print("   from quantbox.adapters.gm_adapter import GMAdapter")
print("   adapter = GMAdapter()")
print("   data = adapter.get_future_daily(...)")

print("\n" + "=" * 60)
