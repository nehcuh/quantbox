"""
独立的日期工具测试脚本
不依赖数据库，只测试纯函数
"""
import datetime
import sys
import os

# 添加项目路径到 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接导入函数，避免 __init__.py 中的数据库依赖
import importlib.util
spec = importlib.util.spec_from_file_location(
    "date_utils", 
    os.path.join(os.path.dirname(__file__), "quantbox/util/date_utils.py")
)
date_utils = importlib.util.module_from_spec(spec)

# Mock DATABASE 对象以避免导入错误
class MockDB:
    pass

sys.modules['quantbox.util.basic'] = type(sys)('quantbox.util.basic')
sys.modules['quantbox.util.basic'].DATABASE = MockDB()

spec.loader.exec_module(date_utils)

# 现在可以安全地导入函数了
date_to_int = date_utils.date_to_int
int_to_date_str = date_utils.int_to_date_str
date_to_str = date_utils.date_to_str
util_make_date_stamp = date_utils.util_make_date_stamp


def test_date_to_int():
    """测试 date_to_int 函数"""
    print("Testing date_to_int...")
    
    # 测试不同类型的输入
    assert date_to_int(20240126) == 20240126, "Integer input failed"
    assert date_to_int("2024-01-26") == 20240126, "String with hyphen failed"
    assert date_to_int("20240126") == 20240126, "String without hyphen failed"
    assert date_to_int(datetime.date(2024, 1, 26)) == 20240126, "date object failed"
    assert date_to_int(datetime.datetime(2024, 1, 26, 10, 30)) == 20240126, "datetime object failed"
    
    # 测试 None 输入
    today_int = int(datetime.date.today().strftime('%Y%m%d'))
    assert date_to_int(None) == today_int, "None input failed"
    
    # 测试闰年
    assert date_to_int("2024-02-29") == 20240229, "Leap year failed"
    
    # 测试年份边界
    assert date_to_int("2023-12-31") == 20231231, "End of year failed"
    assert date_to_int("2024-01-01") == 20240101, "Start of year failed"
    
    print("✓ date_to_int tests passed (9 tests)")


def test_int_to_date_str():
    """测试 int_to_date_str 函数"""
    print("Testing int_to_date_str...")
    
    assert int_to_date_str(20240126) == "2024-01-26", "Basic conversion failed"
    assert int_to_date_str(20231231) == "2023-12-31", "End of year failed"
    assert int_to_date_str(20240101) == "2024-01-01", "Start of year failed"
    assert int_to_date_str(20240229) == "2024-02-29", "Leap year failed"
    
    print("✓ int_to_date_str tests passed (4 tests)")


def test_date_to_str():
    """测试 date_to_str 函数"""
    print("Testing date_to_str...")
    
    assert date_to_str("2024-01-26") == "2024-01-26", "String input failed"
    assert date_to_str(20240126) == "2024-01-26", "Integer input failed"
    assert date_to_str(datetime.date(2024, 1, 26)) == "2024-01-26", "date object failed"
    
    # 测试自定义格式
    assert date_to_str("2024-01-26", "%Y/%m/%d") == "2024/01/26", "Custom format failed"
    assert date_to_str(20240126, "%d-%m-%Y") == "26-01-2024", "Custom format 2 failed"
    assert date_to_str("2024-01-26", "%Y%m%d") == "20240126", "No separator format failed"
    
    print("✓ date_to_str tests passed (6 tests)")


def test_util_make_date_stamp():
    """测试 util_make_date_stamp 函数"""
    print("Testing util_make_date_stamp...")
    
    # 测试返回类型
    timestamp = util_make_date_stamp("2024-01-26")
    assert isinstance(timestamp, float), "Return type should be float"
    assert timestamp > 0, "Timestamp should be positive"
    
    # 测试整数和字符串输入的一致性
    timestamp1 = util_make_date_stamp(20240126)
    timestamp2 = util_make_date_stamp("2024-01-26")
    assert timestamp1 == timestamp2, "Integer and string should produce same timestamp"
    
    # 测试 date 对象
    timestamp3 = util_make_date_stamp(datetime.date(2024, 1, 26))
    assert timestamp3 == timestamp1, "date object should produce same timestamp"
    
    print("✓ util_make_date_stamp tests passed (5 tests)")


def test_error_handling():
    """测试错误处理"""
    print("Testing error handling...")
    
    # 测试无效的整数长度
    try:
        date_to_int(2024)
        assert False, "Should raise ValueError for invalid integer length"
    except ValueError as e:
        assert "Integer date must be 8 digits" in str(e)
    
    try:
        date_to_int(202401265)
        assert False, "Should raise ValueError for invalid integer length"
    except ValueError as e:
        assert "Integer date must be 8 digits" in str(e)
    
    # 测试无效的日期值
    try:
        date_to_int(20241332)  # 无效月份
        assert False, "Should raise ValueError for invalid date"
    except ValueError:
        pass
    
    try:
        date_to_int("2023-02-29")  # 非闰年
        assert False, "Should raise ValueError for invalid leap year date"
    except ValueError:
        pass
    
    # 测试无效的日期格式
    try:
        date_to_int("2024/01/26")  # 不支持的格式
        assert False, "Should raise ValueError for unsupported format"
    except ValueError:
        pass
    
    # 测试 int_to_date_str 的错误处理
    try:
        int_to_date_str(2024)
        assert False, "Should raise ValueError for invalid integer length"
    except ValueError as e:
        assert "Date integer must be 8 digits" in str(e)
    
    try:
        int_to_date_str(20240230)  # 无效日期
        assert False, "Should raise ValueError for invalid date"
    except ValueError:
        pass
    
    print("✓ Error handling tests passed (7 tests)")


def test_edge_cases():
    """测试边界情况"""
    print("Testing edge cases...")
    
    # 测试特殊年份
    assert date_to_int("2000-02-29") == 20000229, "Year 2000 leap year failed"
    assert date_to_int("2100-02-28") == 21000228, "Year 2100 (not leap) failed"
    
    # 测试年初年末
    assert date_to_int("1999-12-31") == 19991231, "1999 end failed"
    assert date_to_int("2000-01-01") == 20000101, "2000 start failed"
    
    # 测试不同月份的最后一天
    assert date_to_int("2024-01-31") == 20240131, "Jan 31 failed"
    assert date_to_int("2024-04-30") == 20240430, "Apr 30 failed"
    assert date_to_int("2024-02-29") == 20240229, "Feb 29 (leap) failed"
    
    print("✓ Edge cases tests passed (7 tests)")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Running Standalone Date Utils Tests")
    print("=" * 60)
    
    try:
        test_date_to_int()
        test_int_to_date_str()
        test_date_to_str()
        test_util_make_date_stamp()
        test_error_handling()
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed! (38 tests total)")
        print("=" * 60)
        print("\n✨ Date utils module is working correctly!")
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
