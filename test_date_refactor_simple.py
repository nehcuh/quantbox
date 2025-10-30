"""
简单的日期工具测试脚本
不依赖 pytest，直接运行测试
"""
import datetime
import sys
from quantbox.util.date_utils import (
    date_to_int,
    int_to_date_str,
    date_to_str,
    util_make_date_stamp,
)


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
    
    print("✓ date_to_int tests passed")


def test_int_to_date_str():
    """测试 int_to_date_str 函数"""
    print("Testing int_to_date_str...")
    
    assert int_to_date_str(20240126) == "2024-01-26", "Basic conversion failed"
    assert int_to_date_str(20231231) == "2023-12-31", "End of year failed"
    assert int_to_date_str(20240101) == "2024-01-01", "Start of year failed"
    
    print("✓ int_to_date_str tests passed")


def test_date_to_str():
    """测试 date_to_str 函数"""
    print("Testing date_to_str...")
    
    assert date_to_str("2024-01-26") == "2024-01-26", "String input failed"
    assert date_to_str(20240126) == "2024-01-26", "Integer input failed"
    assert date_to_str(datetime.date(2024, 1, 26)) == "2024-01-26", "date object failed"
    
    # 测试自定义格式
    assert date_to_str("2024-01-26", "%Y/%m/%d") == "2024/01/26", "Custom format failed"
    assert date_to_str(20240126, "%d-%m-%Y") == "26-01-2024", "Custom format 2 failed"
    
    print("✓ date_to_str tests passed")


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
    
    print("✓ util_make_date_stamp tests passed")


def test_error_handling():
    """测试错误处理"""
    print("Testing error handling...")
    
    # 测试无效的整数长度
    try:
        date_to_int(2024)
        assert False, "Should raise ValueError for invalid integer length"
    except ValueError:
        pass
    
    # 测试无效的日期值
    try:
        date_to_int(20241332)  # 无效月份
        assert False, "Should raise ValueError for invalid date"
    except ValueError:
        pass
    
    # 测试无效的日期格式
    try:
        date_to_int("2024/01/26")  # 不支持的格式
        assert False, "Should raise ValueError for unsupported format"
    except ValueError:
        pass
    
    print("✓ Error handling tests passed")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Running Date Utils Tests")
    print("=" * 60)
    
    try:
        test_date_to_int()
        test_int_to_date_str()
        test_date_to_str()
        test_util_make_date_stamp()
        test_error_handling()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
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
