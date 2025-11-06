#!/usr/bin/env python3
"""
诊断脚本 - 检查 Tushare 和 掘金 的配置
"""

import sys
import traceback

def test_tushare_token():
    """测试 Tushare token 配置"""
    print("\n" + "="*60)
    print("  诊断 Tushare Token")
    print("="*60)

    try:
        from quantbox.config.config_loader import get_config_loader
        config_loader = get_config_loader()

        # 检查配置
        ts_token = config_loader.get_tushare_token()
        if ts_token:
            print(f"[OK] Tushare token 已配置: {ts_token[:10]}***")
        else:
            print("[ERROR] Tushare token 未配置")
            return False

        # 测试直接调用 Tushare API
        print("\n[INFO] 测试直接调用 Tushare API...")
        import tushare as ts
        pro = ts.pro_api(ts_token)

        # 测试1: 获取股票列表
        print("[INFO] 测试1: 获取股票列表...")
        try:
            df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
            if df is not None and not df.empty:
                print(f"[OK] 成功获取股票列表: {len(df)} 条")
                print(f"     示例: {df.head(1)[['ts_code', 'name']].to_dict('records')}")
            else:
                print("[WARNING] 股票列表为空")
        except Exception as e:
            print(f"[ERROR] 获取股票列表失败: {str(e)}")

        # 测试2: 获取交易日历
        print("\n[INFO] 测试2: 获取交易日历...")
        try:
            df = pro.trade_cal(exchange='SSE', start_date='20241101', end_date='20241110')
            if df is not None and not df.empty:
                print(f"[OK] 成功获取交易日历: {len(df)} 条")
                print(f"     示例: {df.head(1)[['exchange', 'cal_date', 'is_open']].to_dict('records')}")
            else:
                print("[WARNING] 交易日历为空")
        except Exception as e:
            print(f"[ERROR] 获取交易日历失败: {str(e)}")

        # 测试3: 获取期货合约
        print("\n[INFO] 测试3: 获取期货合约...")
        try:
            df = pro.fut_basic(exchange='SHFE', fut_type='1', fields='ts_code,symbol,name,list_date,delist_date')
            if df is not None and not df.empty:
                print(f"[OK] 成功获取期货合约: {len(df)} 条")
                print(f"     示例: {df.head(1)[['ts_code', 'name']].to_dict('records')}")
            else:
                print("[WARNING] 期货合约为空")
        except Exception as e:
            print(f"[ERROR] 获取期货合约失败: {str(e)}")

        return True

    except Exception as e:
        print(f"[ERROR] Tushare 诊断失败: {str(e)}")
        traceback.print_exc()
        return False

def test_gm_token():
    """测试掘金 token 配置"""
    print("\n" + "="*60)
    print("  诊断掘金量化 Token")
    print("="*60)

    try:
        import platform
        if platform.system() == 'Darwin':
            print("[INFO] 系统: macOS - 掘金 API 不支持")
            return True

        from quantbox.config.config_loader import get_config_loader
        config_loader = get_config_loader()

        # 检查配置
        gm_token = config_loader.get_gm_token()
        if gm_token:
            print(f"[OK] 掘金 token 已配置: {gm_token[:10]}***")
        else:
            print("[ERROR] 掘金 token 未配置")
            return False

        # 检查 SDK 是否安装
        try:
            from gm.api import set_token, get_trading_dates_by_year
            print("[OK] 掘金 SDK 已安装")
        except ImportError:
            print("[ERROR] 掘金 SDK 未安装")
            print("[INFO] 请运行: pip install gm")
            return False

        # 测试调用
        print("\n[INFO] 测试掘金 API 调用...")
        try:
            set_token(gm_token)
            dates = get_trading_dates_by_year(
                exchange='SHSE',
                start_year=2024,
                end_year=2024
            )
            if dates is not None and not dates.empty:
                print(f"[OK] 成功获取交易日期: {len(dates)} 条")
                print(f"     示例: {dates.head(1).to_dict('records')}")
            else:
                print("[WARNING] 交易日期为空")
        except Exception as e:
            print(f"[ERROR] 调用掘金 API 失败: {str(e)}")

        return True

    except Exception as e:
        print(f"[ERROR] 掘金诊断失败: {str(e)}")
        traceback.print_exc()
        return False

def test_mongodb():
    """测试 MongoDB 连接"""
    print("\n" + "="*60)
    print("  诊断 MongoDB 连接")
    print("="*60)

    try:
        from quantbox.config.config_loader import get_config_loader
        config_loader = get_config_loader()

        # 获取 MongoDB 客户端
        client = config_loader.get_mongodb_client()
        db = client.quantbox

        # 测试连接
        print("[INFO] 测试连接...")
        db.command('ping')
        print("[OK] MongoDB 连接正常")

        # 检查现有数据
        print("\n[INFO] 检查现有集合...")
        collections = db.list_collection_names()
        if collections:
            print(f"[OK] 找到 {len(collections)} 个集合:")
            for coll_name in collections:
                count = db[coll_name].count_documents({})
                print(f"     - {coll_name}: {count} 条记录")
        else:
            print("[INFO] 数据库为空（尚未保存任何数据）")

        return True

    except Exception as e:
        print(f"[ERROR] MongoDB 诊断失败: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("\n" + "="*60)
    print("       Quantbox 配置诊断工具")
    print("="*60)

    # 诊断各组件
    ts_ok = test_tushare_token()
    gm_ok = test_gm_token()
    mongo_ok = test_mongodb()

    # 总结
    print("\n" + "="*60)
    print("  诊断结果总结")
    print("="*60)
    print(f"  Tushare:  {'[OK]' if ts_ok else '[FAIL]'}")
    print(f"  掘金:     {'[OK]' if gm_ok else '[FAIL]'}")
    print(f"  MongoDB:  {'[OK]' if mongo_ok else '[FAIL]'}")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
