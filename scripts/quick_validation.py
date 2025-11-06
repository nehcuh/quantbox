#!/usr/bin/env python3
"""
快速接口验证测试

测试关键功能是否正常工作
"""

import sys

def print_section(title: str):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def main():
    print("\n" + "="*60)
    print("       Quantbox 快速接口验证")
    print("="*60)

    # 测试 1: TSAdapter - 交易日历
    print_section("1. TSAdapter - 交易日历")
    try:
        from quantbox.adapters.ts_adapter import TSAdapter
        adapter = TSAdapter()

        if adapter.check_availability():
            print("[OK] Tushare API 可用")

            calendar = adapter.get_trade_calendar(
                exchanges=['SHFE'],
                start_date='2024-11-01',
                end_date='2024-11-10'
            )
            print(f"[OK] 交易日历: {len(calendar)} 条记录")
            if not calendar.empty:
                print(f"     示例: {calendar.head(1).to_dict('records')}")
        else:
            print("[ERROR] Tushare API 不可用")
    except Exception as e:
        print(f"[ERROR] {str(e)}")

    # 测试 2: TSAdapter - 期货合约
    print_section("2. TSAdapter - 期货合约")
    try:
        from quantbox.adapters.ts_adapter import TSAdapter
        adapter = TSAdapter()

        contracts = adapter.get_future_contracts(
            exchanges=['SHFE'],
            date='2024-11-15'
        )
        print(f"[OK] 期货合约: {len(contracts)} 条记录")
        if not contracts.empty:
            print(f"     示例: {contracts.head(1)[['symbol', 'name', 'exchange']].to_dict('records')}")
    except Exception as e:
        print(f"[ERROR] {str(e)}")

    # 测试 3: TSAdapter - 股票列表
    print_section("3. TSAdapter - 股票列表")
    try:
        from quantbox.adapters.ts_adapter import TSAdapter
        adapter = TSAdapter()

        stocks = adapter.get_stock_list(
            exchanges=['SSE']
        )
        print(f"[OK] 股票列表: {len(stocks)} 条记录")
        if not stocks.empty:
            print(f"     示例: {stocks.head(1)[['symbol', 'name', 'exchange']].to_dict('records')}")
    except Exception as e:
        print(f"[ERROR] {str(e)}")

    # 测试 4: LocalAdapter (MongoDB)
    print_section("4. LocalAdapter - MongoDB")
    try:
        from quantbox.adapters.local_adapter import LocalAdapter
        adapter = LocalAdapter()

        if adapter.check_availability():
            print("[OK] MongoDB 连接正常")

            # 查询交易日历
            calendar = adapter.get_trade_calendar(
                exchanges=['SHFE'],
                start_date='2024-11-01',
                end_date='2024-11-10'
            )
            if not calendar.empty:
                print(f"[OK] 本地交易日历: {len(calendar)} 条记录")
            else:
                print("[INFO] 本地交易日历为空（需先保存数据）")
        else:
            print("[ERROR] MongoDB 不可用")
    except Exception as e:
        print(f"[ERROR] {str(e)}")

    # 测试 5: MarketDataService
    print_section("5. MarketDataService - 智能数据源")
    try:
        from quantbox.services.market_data_service import MarketDataService
        service = MarketDataService()

        # 测试交易日历（本地优先，远程备用）
        calendar = service.get_trade_calendar(
            exchanges=['SHFE'],
            start_date='2024-11-01',
            end_date='2024-11-10'
        )
        if not calendar.empty:
            print(f"[OK] 交易日历: {len(calendar)} 条记录")
        else:
            print("[ERROR] 获取交易日历失败")

        # 测试股票列表
        stocks = service.get_stock_list(exchanges=['SSE'])
        if not stocks.empty:
            print(f"[OK] 股票列表: {len(stocks)} 条记录")
        else:
            print("[ERROR] 获取股票列表失败")
    except Exception as e:
        print(f"[ERROR] {str(e)}")

    # 测试 6: DataSaverService
    print_section("6. DataSaverService - 数据保存")
    try:
        from quantbox.services.data_saver_service import DataSaverService
        service = DataSaverService(show_progress=False)

        # 保存交易日历（小范围测试）
        result = service.save_trade_calendar(
            exchanges=['SHFE'],
            start_date='2024-11-01',
            end_date='2024-11-10'
        )
        print(f"[OK] 保存交易日历: 插入 {result.inserted_count}, 更新 {result.modified_count}")

        # 保存期货合约
        result = service.save_future_contracts(
            exchanges=['SHFE'],
            date='2024-11-15'
        )
        print(f"[OK] 保存期货合约: 插入 {result.inserted_count}, 更新 {result.modified_count}")

        # 保存股票列表
        result = service.save_stock_list(exchanges=['SSE'])
        print(f"[OK] 保存股票列表: 插入 {result.inserted_count}, 更新 {result.modified_count}")
    except Exception as e:
        print(f"[ERROR] {str(e)}")

    print("\n" + "="*60)
    print(">>> 快速测试完成！")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
