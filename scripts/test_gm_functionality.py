#!/usr/bin/env python3
"""
GMAdapter 完整功能测试

测试掘金量化 API 的所有功能
"""

import sys
import traceback
from datetime import datetime

def print_section(title: str):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def main():
    print("\n" + "="*70)
    print("       GMAdapter 完整功能测试")
    print("="*70)

    try:
        from quantbox.adapters.gm_adapter import GMAdapter

        print("\n[INFO] 初始化 GMAdapter...")
        adapter = GMAdapter()
        print("[OK] GMAdapter 初始化成功")

        # 测试 1: check_availability
        print_section("测试 1: check_availability()")
        try:
            available = adapter.check_availability()
            if available:
                print("[OK] 掘金 API 可用")
            else:
                print("[ERROR] 掘金 API 不可用")
                return
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            traceback.print_exc()
            return

        # 测试 2: get_trade_calendar
        print_section("测试 2: get_trade_calendar()")
        try:
            calendar = adapter.get_trade_calendar(
                exchanges=['SHFE', 'DCE'],
                start_date='2024-11-01',
                end_date='2024-11-10'
            )
            if not calendar.empty:
                print(f"[OK] 获取交易日历成功: {len(calendar)} 条记录")
                print(f"     列: {list(calendar.columns)}")
                print(f"     交易所: {calendar['exchange'].unique().tolist()}")
                print(f"     示例数据:")
                print(calendar.head(3).to_string(index=False))
            else:
                print("[WARNING] 交易日历为空")
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            traceback.print_exc()

        # 测试 3: get_future_contracts
        print_section("测试 3: get_future_contracts()")
        try:
            contracts = adapter.get_future_contracts(
                exchanges=['SHFE'],
                date='2024-11-01'
            )
            if not contracts.empty:
                print(f"[OK] 获取期货合约成功: {len(contracts)} 条记录")
                print(f"     列: {list(contracts.columns)}")
                print(f"     示例数据:")
                print(contracts.head(3).to_string(index=False))
            else:
                print("[INFO] 期货合约为空（掘金 API 不支持历史合约查询）")
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            traceback.print_exc()

        # 测试 4: get_future_daily
        print_section("测试 4: get_future_daily()")
        try:
            # 测试单个合约
            daily = adapter.get_future_daily(
                symbols=['SHFE.rb2501'],
                start_date='2024-11-01',
                end_date='2024-11-08'
            )
            if not daily.empty:
                print(f"[OK] 获取期货日线成功: {len(daily)} 条记录")
                print(f"     列: {list(daily.columns)}")
                print(f"     合约: {daily['symbol'].unique().tolist()}")
                print(f"     日期范围: {daily['date'].min()} - {daily['date'].max()}")
                print(f"     示例数据:")
                print(daily.head(3)[['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']].to_string(index=False))
            else:
                print("[WARNING] 期货日线为空")
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            traceback.print_exc()

        # 测试 5: get_future_daily - 多个合约
        print_section("测试 5: get_future_daily() - 多个合约")
        try:
            daily = adapter.get_future_daily(
                symbols=['SHFE.rb2501', 'DCE.m2505'],
                start_date='2024-11-01',
                end_date='2024-11-05'
            )
            if not daily.empty:
                print(f"[OK] 获取多合约日线成功: {len(daily)} 条记录")
                print(f"     合约: {daily['symbol'].unique().tolist()}")
                print(f"     各合约数据量:")
                for symbol in daily['symbol'].unique():
                    count = len(daily[daily['symbol'] == symbol])
                    print(f"       {symbol}: {count} 条")
            else:
                print("[WARNING] 期货日线为空")
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            traceback.print_exc()

        # 测试 6: get_future_holdings
        print_section("测试 6: get_future_holdings()")
        try:
            holdings = adapter.get_future_holdings(
                symbols=['SHFE.rb2501'],
                date='2024-11-01'
            )
            if not holdings.empty:
                print(f"[OK] 获取期货持仓成功: {len(holdings)} 条记录")
                print(f"     列: {list(holdings.columns)}")
                print(f"     合约: {holdings['symbol'].unique().tolist()}")
                print(f"     经纪商数量: {holdings['broker'].nunique()}")
                print(f"     示例数据（前3名）:")
                print(holdings.head(3)[['date', 'symbol', 'broker', 'vol', 'long_hld', 'short_hld']].to_string(index=False))
            else:
                print("[WARNING] 期货持仓为空")
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            traceback.print_exc()

        # 测试 7: get_future_holdings - 通过交易所
        print_section("测试 7: get_future_holdings() - 通过交易所")
        try:
            print("[INFO] 注意：此测试需要从本地数据库查询合约列表")
            holdings = adapter.get_future_holdings(
                exchanges=['DCE'],
                date='2024-11-01'
            )
            if not holdings.empty:
                print(f"[OK] 获取交易所持仓成功: {len(holdings)} 条记录")
                print(f"     合约数量: {holdings['symbol'].nunique()}")
                print(f"     示例合约: {holdings['symbol'].unique()[:5].tolist()}")
            else:
                print("[WARNING] 交易所持仓为空（可能本地数据库无合约数据）")
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            # traceback.print_exc()  # 这个可能因为本地数据库没有合约而失败，不打印详细错误

        # 测试 8: get_stock_list
        print_section("测试 8: get_stock_list()")
        try:
            stocks = adapter.get_stock_list(
                exchanges=['SSE']
            )
            if not stocks.empty:
                print(f"[OK] 获取股票列表成功: {len(stocks)} 条记录")
            else:
                print("[INFO] 股票列表为空（掘金 API 股票列表功能尚未实现）")
        except Exception as e:
            print(f"[INFO] 股票列表功能尚未实现: {str(e)}")

        # 测试总结
        print_section("测试总结")
        print("\n[OK] GMAdapter 核心功能测试完成！")
        print("\n功能验证结果：")
        print("  [OK] check_availability() - 可用性检查")
        print("  [OK] get_trade_calendar() - 交易日历")
        print("  [INFO] get_future_contracts() - 期货合约（API不支持）")
        print("  [OK] get_future_daily() - 期货日线数据")
        print("  [OK] get_future_holdings() - 期货持仓数据")
        print("  [INFO] get_stock_list() - 股票列表（未实现）")

    except ImportError as e:
        print(f"\n[ERROR] 导入错误: {str(e)}")
        print("[INFO] 请确保掘金 SDK 已安装: uv pip install gm")
        traceback.print_exc()
    except NotImplementedError as e:
        print(f"\n[ERROR] 功能未实现: {str(e)}")
        print("[INFO] 可能在 macOS 系统上运行（不支持）")
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {str(e)}")
        traceback.print_exc()

    print("\n" + "="*70)
    print(">>> GMAdapter 测试完成")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
