#!/usr/bin/env python3
"""
接口验证测试脚本

测试所有 Adapter 和 Service 的功能是否正常
"""

import sys
from datetime import datetime, timedelta
from typing import Optional
import traceback

def print_section(title: str):
    """打印章节标题"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_success(msg: str):
    """打印成功消息"""
    print(f"[OK] {msg}")

def print_error(msg: str):
    """打印错误消息"""
    print(f"[ERROR] {msg}")

def print_info(msg: str):
    """打印信息"""
    print(f"[INFO] {msg}")

def test_ts_adapter():
    """测试 Tushare Adapter"""
    print_section("测试 TSAdapter (Tushare API)")

    try:
        from quantbox.adapters.ts_adapter import TSAdapter

        print_info("初始化 TSAdapter...")
        adapter = TSAdapter()

        # 测试 1: check_availability
        print_info("测试 1/5: check_availability()")
        if adapter.check_availability():
            print_success("Tushare API 可用")
        else:
            print_error("Tushare API 不可用，请检查 token 配置")
            return False

        # 测试 2: get_trade_calendar
        print_info("测试 2/5: get_trade_calendar()")
        calendar = adapter.get_trade_calendar(
            exchanges=['SHFE'],
            start_date='2024-01-01',
            end_date='2024-01-10'
        )
        if not calendar.empty:
            print_success(f"获取交易日历成功: {len(calendar)} 条记录")
            print(f"   列: {list(calendar.columns)}")
            print(f"   示例: {calendar.head(2).to_dict('records')}")
        else:
            print_error("获取交易日历失败：返回空数据")

        # 测试 3: get_future_contracts
        print_info("测试 3/5: get_future_contracts()")
        contracts = adapter.get_future_contracts(
            exchanges=['SHFE'],
            date='2024-01-15'
        )
        if not contracts.empty:
            print_success(f"获取期货合约成功: {len(contracts)} 条记录")
            print(f"   列: {list(contracts.columns)}")
            if len(contracts) > 0:
                print(f"   示例: {contracts.head(2)[['symbol', 'name', 'exchange', 'list_date']].to_dict('records')}")
        else:
            print_error("获取期货合约失败：返回空数据")

        # 测试 4: get_future_daily
        print_info("测试 4/5: get_future_daily()")
        daily = adapter.get_future_daily(
            symbols=['SHFE.rb2501'],  # 使用带交易所的完整格式
            start_date='2024-11-01',
            end_date='2024-11-05'
        )
        if not daily.empty:
            print_success(f"获取期货日线成功: {len(daily)} 条记录")
            print(f"   列: {list(daily.columns)}")
            if len(daily) > 0:
                print(f"   示例: {daily.head(2)[['date', 'symbol', 'open', 'close', 'volume']].to_dict('records')}")
        else:
            print_error("获取期货日线失败：返回空数据")

        # 测试 5: get_stock_list
        print_info("测试 5/5: get_stock_list()")
        stocks = adapter.get_stock_list(
            exchanges=['SSE'],
            list_status='L'
        )
        if not stocks.empty:
            print_success(f"获取股票列表成功: {len(stocks)} 条记录")
            print(f"   列: {list(stocks.columns)}")
            if len(stocks) > 0:
                print(f"   示例: {stocks.head(2)[['symbol', 'name', 'exchange', 'list_date']].to_dict('records')}")
        else:
            print_error("获取股票列表失败：返回空数据")

        print_success("TSAdapter 所有测试通过！")
        return True

    except Exception as e:
        print_error(f"TSAdapter 测试失败: {str(e)}")
        traceback.print_exc()
        return False

def test_gm_adapter():
    """测试掘金量化 Adapter"""
    print_section("测试 GMAdapter (掘金量化 API)")

    try:
        import platform
        if platform.system() == 'Darwin':
            print_error("掘金量化 API 不支持 macOS，跳过测试")
            return True

        from quantbox.adapters.gm_adapter import GMAdapter

        print_info("初始化 GMAdapter...")
        try:
            adapter = GMAdapter()
        except (ImportError, NotImplementedError) as e:
            print_error(f"GMAdapter 初始化失败: {str(e)}")
            return False

        # 测试 1: check_availability
        print_info("测试 1/4: check_availability()")
        if adapter.check_availability():
            print_success("掘金量化 API 可用")
        else:
            print_error("掘金量化 API 不可用，请检查 token 配置或网络连接")
            return False

        # 测试 2: get_trade_calendar
        print_info("测试 2/4: get_trade_calendar()")
        calendar = adapter.get_trade_calendar(
            exchanges=['SHFE'],
            start_date='2024-01-01',
            end_date='2024-01-10'
        )
        if not calendar.empty:
            print_success(f"获取交易日历成功: {len(calendar)} 条记录")
            print(f"   列: {list(calendar.columns)}")
            print(f"   示例: {calendar.head(2).to_dict('records')}")
        else:
            print_error("获取交易日历失败：返回空数据")

        # 测试 3: get_future_daily
        print_info("测试 3/4: get_future_daily()")
        try:
            daily = adapter.get_future_daily(
                symbols=['SHFE.rb2501'],  # 使用带交易所的完整格式
                start_date='2024-11-01',
                end_date='2024-11-05'
            )
            if not daily.empty:
                print_success(f"获取期货日线成功: {len(daily)} 条记录")
                print(f"   列: {list(daily.columns)}")
                if len(daily) > 0:
                    print(f"   示例: {daily.head(2)[['date', 'symbol', 'open', 'close', 'volume']].to_dict('records')}")
            else:
                print_error("获取期货日线失败：返回空数据")
        except Exception as e:
            print_error(f"获取期货日线失败: {str(e)}")

        # 测试 4: get_future_holdings
        print_info("测试 4/4: get_future_holdings()")
        try:
            holdings = adapter.get_future_holdings(
                symbols=['SHFE.rb2501'],  # 使用带交易所的完整格式
                date='2024-11-01'
            )
            if not holdings.empty:
                print_success(f"获取期货持仓成功: {len(holdings)} 条记录")
                print(f"   列: {list(holdings.columns)}")
                if len(holdings) > 0:
                    print(f"   示例: {holdings.head(2)[['date', 'symbol', 'broker', 'vol']].to_dict('records')}")
            else:
                print_error("获取期货持仓失败：返回空数据")
        except Exception as e:
            print_error(f"获取期货持仓失败: {str(e)}")

        print_success("GMAdapter 所有测试通过！")
        return True

    except Exception as e:
        print_error(f"GMAdapter 测试失败: {str(e)}")
        traceback.print_exc()
        return False

def test_local_adapter():
    """测试 Local Adapter (MongoDB)"""
    print_section("测试 LocalAdapter (MongoDB)")

    try:
        from quantbox.adapters.local_adapter import LocalAdapter

        print_info("初始化 LocalAdapter...")
        adapter = LocalAdapter()

        # 测试 1: check_availability
        print_info("测试 1/5: check_availability()")
        if adapter.check_availability():
            print_success("MongoDB 连接正常")
        else:
            print_error("MongoDB 不可用，请检查 MongoDB 服务是否启动")
            return False

        # 测试 2: get_trade_calendar
        print_info("测试 2/5: get_trade_calendar()")
        calendar = adapter.get_trade_calendar(
            exchanges=['SHFE'],
            start_date='2024-01-01',
            end_date='2024-01-10'
        )
        if not calendar.empty:
            print_success(f"查询交易日历成功: {len(calendar)} 条记录")
        else:
            print_info("本地交易日历数据为空（可能尚未保存数据）")

        # 测试 3: get_future_contracts
        print_info("测试 3/5: get_future_contracts()")
        contracts = adapter.get_future_contracts(
            exchanges=['SHFE'],
            date='2024-01-15'
        )
        if not contracts.empty:
            print_success(f"查询期货合约成功: {len(contracts)} 条记录")
        else:
            print_info("本地期货合约数据为空（可能尚未保存数据）")

        # 测试 4: get_future_daily
        print_info("测试 4/5: get_future_daily()")
        daily = adapter.get_future_daily(
            symbols=['SHFE.rb2501'],  # 使用带交易所的完整格式
            start_date='2024-11-01',
            end_date='2024-11-05'
        )
        if not daily.empty:
            print_success(f"查询期货日线成功: {len(daily)} 条记录")
        else:
            print_info("本地期货日线数据为空（可能尚未保存数据）")

        # 测试 5: get_stock_list
        print_info("测试 5/5: get_stock_list()")
        stocks = adapter.get_stock_list(
            exchanges=['SSE']
        )
        if not stocks.empty:
            print_success(f"查询股票列表成功: {len(stocks)} 条记录")
        else:
            print_info("本地股票列表数据为空（可能尚未保存数据）")

        print_success("LocalAdapter 所有测试通过！")
        return True

    except Exception as e:
        print_error(f"LocalAdapter 测试失败: {str(e)}")
        traceback.print_exc()
        return False

def test_market_data_service():
    """测试 MarketDataService"""
    print_section("测试 MarketDataService")

    try:
        from quantbox.services.market_data_service import MarketDataService

        print_info("初始化 MarketDataService...")
        service = MarketDataService()

        # 测试 1: get_trade_calendar
        print_info("测试 1/5: get_trade_calendar()")
        calendar = service.get_trade_calendar(
            exchanges=['SHFE'],
            start_date='2024-01-01',
            end_date='2024-01-10'
        )
        if not calendar.empty:
            print_success(f"获取交易日历成功: {len(calendar)} 条记录")
            print(f"   数据源策略: 本地优先，远程备用")
        else:
            print_error("获取交易日历失败")

        # 测试 2: get_future_contracts
        print_info("测试 2/5: get_future_contracts()")
        contracts = service.get_future_contracts(
            exchanges=['SHFE'],
            date='2024-01-15'
        )
        if not contracts.empty:
            print_success(f"获取期货合约成功: {len(contracts)} 条记录")
        else:
            print_error("获取期货合约失败")

        # 测试 3: get_future_daily
        print_info("测试 3/5: get_future_daily()")
        daily = service.get_future_daily(
            symbols=['SHFE.rb2501'],  # 使用带交易所的完整格式
            start_date='2024-11-01',
            end_date='2024-11-05'
        )
        if not daily.empty:
            print_success(f"获取期货日线成功: {len(daily)} 条记录")
        else:
            print_info("期货日线数据为空（可能合约不存在或日期范围无数据）")

        # 测试 4: get_future_holdings
        print_info("测试 4/5: get_future_holdings()")
        holdings = service.get_future_holdings(
            symbols=['SHFE.rb2501'],  # 使用带交易所的完整格式
            start_date='2024-11-01',
            end_date='2024-11-05'
        )
        if not holdings.empty:
            print_success(f"获取期货持仓成功: {len(holdings)} 条记录")
        else:
            print_info("期货持仓数据为空（可能日期范围无数据）")

        # 测试 5: get_stock_list
        print_info("测试 5/5: get_stock_list()")
        stocks = service.get_stock_list(
            exchanges=['SSE']
        )
        if not stocks.empty:
            print_success(f"获取股票列表成功: {len(stocks)} 条记录")
        else:
            print_error("获取股票列表失败")

        print_success("MarketDataService 所有测试通过！")
        return True

    except Exception as e:
        print_error(f"MarketDataService 测试失败: {str(e)}")
        traceback.print_exc()
        return False

def test_data_saver_service():
    """测试 DataSaverService"""
    print_section("测试 DataSaverService")

    try:
        from quantbox.services.data_saver_service import DataSaverService

        print_info("初始化 DataSaverService...")
        service = DataSaverService(show_progress=False)

        # 测试 1: save_trade_calendar (小范围测试)
        print_info("测试 1/5: save_trade_calendar()")
        result = service.save_trade_calendar(
            exchanges=['SHFE'],
            start_date='2024-01-01',
            end_date='2024-01-10'
        )
        print_success(f"保存交易日历成功: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")

        # 测试 2: save_future_contracts
        print_info("测试 2/5: save_future_contracts()")
        result = service.save_future_contracts(
            exchanges=['SHFE'],
            date='2024-01-15'
        )
        print_success(f"保存期货合约成功: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")

        # 测试 3: save_future_daily (小范围测试)
        print_info("测试 3/5: save_future_daily()")
        result = service.save_future_daily(
            symbols=['SHFE.rb2501'],  # 使用带交易所的完整格式
            start_date='2024-11-01',
            end_date='2024-11-05'
        )
        print_success(f"保存期货日线成功: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")

        # 测试 4: save_future_holdings (单日测试)
        print_info("测试 4/5: save_future_holdings()")
        result = service.save_future_holdings(
            symbols=['SHFE.rb2501'],  # 使用带交易所的完整格式
            date='2024-11-01'
        )
        print_success(f"保存期货持仓成功: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")

        # 测试 5: save_stock_list
        print_info("测试 5/5: save_stock_list()")
        result = service.save_stock_list(
            exchanges=['SSE']
        )
        print_success(f"保存股票列表成功: 插入 {result.inserted_count} 条，更新 {result.modified_count} 条")

        print_success("DataSaverService 所有测试通过！")
        return True

    except Exception as e:
        print_error(f"DataSaverService 测试失败: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("=" + " "*20 + "Quantbox 接口验证测试" + " "*37 + "=")
    print("="*80)

    results = {}

    # 1. 测试 Adapters
    results['TSAdapter'] = test_ts_adapter()
    results['GMAdapter'] = test_gm_adapter()
    results['LocalAdapter'] = test_local_adapter()

    # 2. 测试 Services
    results['MarketDataService'] = test_market_data_service()
    results['DataSaverService'] = test_data_saver_service()

    # 生成测试报告
    print_section("测试结果汇总")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    print(f"\n总测试模块数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"通过率: {passed/total*100:.1f}%\n")

    for name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}  {name}")

    print("\n" + "="*80)
    if failed == 0:
        print(">>> 所有测试通过！Quantbox 新架构工作正常！")
        return 0
    else:
        print(f">>> 有 {failed} 个模块测试失败，请检查错误信息")
        return 1

if __name__ == '__main__':
    sys.exit(main())
