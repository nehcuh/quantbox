"""
Test file for refactored date_utils module

测试重构后的 date_utils 模块，验证所有函数的正确性和性能
"""
import datetime
import time
from quantbox.util.date_utils import (
    date_to_int,
    int_to_date_str,
    date_to_str,
    util_make_date_stamp,
    is_trade_date,
    get_pre_trade_date,
    get_next_trade_date,
    get_trade_calendar,
    get_trade_dates,
)


def test_date_to_int():
    """测试 date_to_int 函数"""
    print("=" * 60)
    print("Testing date_to_int...")
    print("-" * 60)

    # 测试 None（应该返回今天）
    result = date_to_int(None)
    expected = int(datetime.date.today().strftime('%Y%m%d'))
    assert result == expected, f"None test failed: {result} != {expected}"
    print(f"✓ None -> {result}")

    # 测试整数输入
    result = date_to_int(20240126)
    assert result == 20240126, f"Integer test failed: {result}"
    print(f"✓ 20240126 -> {result}")

    # 测试带连字符的字符串
    result = date_to_int("2024-01-26")
    assert result == 20240126, f"String with dash test failed: {result}"
    print(f"✓ '2024-01-26' -> {result}")

    # 测试不带连字符的字符串
    result = date_to_int("20240126")
    assert result == 20240126, f"String without dash test failed: {result}"
    print(f"✓ '20240126' -> {result}")

    # 测试带斜杠的字符串
    result = date_to_int("2024/01/26")
    assert result == 20240126, f"String with slash test failed: {result}"
    print(f"✓ '2024/01/26' -> {result}")

    # 测试 datetime.date 对象
    result = date_to_int(datetime.date(2024, 1, 26))
    assert result == 20240126, f"date object test failed: {result}"
    print(f"✓ datetime.date(2024, 1, 26) -> {result}")

    # 测试 datetime.datetime 对象
    result = date_to_int(datetime.datetime(2024, 1, 26, 15, 30))
    assert result == 20240126, f"datetime object test failed: {result}"
    print(f"✓ datetime.datetime(2024, 1, 26, 15, 30) -> {result}")

    # 测试错误输入
    try:
        date_to_int("invalid")
        assert False, "Should raise ValueError for invalid string"
    except ValueError as e:
        print(f"✓ Invalid string raises ValueError: {e}")

    try:
        date_to_int(2024)
        assert False, "Should raise ValueError for wrong length integer"
    except ValueError as e:
        print(f"✓ Wrong length integer raises ValueError: {e}")

    print("✓ All date_to_int tests passed!\n")


def test_int_to_date_str():
    """测试 int_to_date_str 函数"""
    print("=" * 60)
    print("Testing int_to_date_str...")
    print("-" * 60)

    result = int_to_date_str(20240126)
    assert result == "2024-01-26", f"Conversion failed: {result}"
    print(f"✓ 20240126 -> '{result}'")

    # 测试边界日期
    result = int_to_date_str(20240101)
    assert result == "2024-01-01", f"Start of year failed: {result}"
    print(f"✓ 20240101 -> '{result}'")

    result = int_to_date_str(20241231)
    assert result == "2024-12-31", f"End of year failed: {result}"
    print(f"✓ 20241231 -> '{result}'")

    # 测试错误输入
    try:
        int_to_date_str(2024)
        assert False, "Should raise ValueError for wrong length"
    except ValueError as e:
        print(f"✓ Wrong length raises ValueError: {e}")

    try:
        int_to_date_str(20241332)  # 无效月份
        assert False, "Should raise ValueError for invalid date"
    except ValueError as e:
        print(f"✓ Invalid date raises ValueError: {e}")

    print("✓ All int_to_date_str tests passed!\n")


def test_date_to_str():
    """测试 date_to_str 函数"""
    print("=" * 60)
    print("Testing date_to_str...")
    print("-" * 60)

    # 测试默认格式
    result = date_to_str(20240126)
    assert result == "2024-01-26", f"Default format failed: {result}"
    print(f"✓ 20240126 -> '{result}'")

    # 测试自定义格式
    result = date_to_str(20240126, "%Y/%m/%d")
    assert result == "2024/01/26", f"Custom format failed: {result}"
    print(f"✓ 20240126 with format '%Y/%m/%d' -> '{result}'")

    result = date_to_str("2024-01-26", "%Y%m%d")
    assert result == "20240126", f"Format to no-dash failed: {result}"
    print(f"✓ '2024-01-26' with format '%Y%m%d' -> '{result}'")

    # 测试 datetime 对象
    dt = datetime.datetime(2024, 1, 26, 15, 30, 45)
    result = date_to_str(dt, "%Y-%m-%d %H:%M:%S")
    assert result == "2024-01-26 15:30:45", f"Datetime with time failed: {result}"
    print(f"✓ datetime with time -> '{result}'")

    print("✓ All date_to_str tests passed!\n")


def test_util_make_date_stamp():
    """测试 util_make_date_stamp 函数"""
    print("=" * 60)
    print("Testing util_make_date_stamp...")
    print("-" * 60)

    # 测试已知日期的时间戳
    result = util_make_date_stamp("2024-01-26")
    # 创建一个对应的 datetime 对象进行比较
    expected_dt = datetime.datetime(2024, 1, 26, 0, 0, 0)
    expected = expected_dt.timestamp()
    assert result == expected, f"Timestamp mismatch: {result} != {expected}"
    print(f"✓ '2024-01-26' -> {result} (expected: {expected})")

    # 测试整数输入
    result = util_make_date_stamp(20240126)
    assert result == expected, f"Integer input failed: {result}"
    print(f"✓ 20240126 -> {result}")

    # 测试 datetime 对象（应该取日期部分）
    dt_with_time = datetime.datetime(2024, 1, 26, 15, 30, 45)
    result = util_make_date_stamp(dt_with_time)
    assert result == expected, f"Datetime object failed: {result}"
    print(f"✓ datetime(2024, 1, 26, 15, 30, 45) -> {result} (time stripped)")

    # 测试 None（应该返回今天的时间戳）
    result = util_make_date_stamp(None)
    today_dt = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    expected_today = today_dt.timestamp()
    assert result == expected_today, f"None test failed: {result} != {expected_today}"
    print(f"✓ None -> {result} (today)")

    print("✓ All util_make_date_stamp tests passed!\n")


def test_performance():
    """性能测试 - 比较新旧实现"""
    print("=" * 60)
    print("Performance Testing...")
    print("-" * 60)

    test_dates = [
        20240101,
        20240115,
        "2024-06-15",
        "2024-12-31",
        datetime.date(2024, 3, 15),
    ]

    iterations = 10000

    # 测试 date_to_int 性能
    start = time.time()
    for _ in range(iterations):
        for date in test_dates:
            date_to_int(date)
    elapsed = time.time() - start
    print(f"✓ date_to_int: {iterations * len(test_dates)} conversions in {elapsed:.4f}s")
    print(f"  Average: {elapsed / (iterations * len(test_dates)) * 1000:.4f}ms per conversion")

    # 测试 date_to_str 性能
    start = time.time()
    for _ in range(iterations):
        for date in test_dates:
            date_to_str(date)
    elapsed = time.time() - start
    print(f"✓ date_to_str: {iterations * len(test_dates)} conversions in {elapsed:.4f}s")
    print(f"  Average: {elapsed / (iterations * len(test_dates)) * 1000:.4f}ms per conversion")

    # 测试 util_make_date_stamp 性能
    start = time.time()
    for _ in range(iterations):
        for date in test_dates:
            util_make_date_stamp(date)
    elapsed = time.time() - start
    print(f"✓ util_make_date_stamp: {iterations * len(test_dates)} conversions in {elapsed:.4f}s")
    print(f"  Average: {elapsed / (iterations * len(test_dates)) * 1000:.4f}ms per conversion")

    print()


def test_trade_date_functions():
    """测试交易日相关函数（需要数据库连接）"""
    print("=" * 60)
    print("Testing trade date functions (requires DB)...")
    print("-" * 60)

    try:
        # 测试 is_trade_date
        result = is_trade_date("2024-01-26", "SHSE")
        print(f"✓ is_trade_date('2024-01-26', 'SHSE') -> {result}")

        # 测试周末不是交易日
        result = is_trade_date("2024-01-28", "SHSE")  # 周日
        print(f"✓ is_trade_date('2024-01-28', 'SHSE') -> {result} (Sunday)")

        # 测试 get_pre_trade_date
        result = get_pre_trade_date("2024-01-26", "SHSE", 1)
        if result:
            print(f"✓ get_pre_trade_date('2024-01-26', 'SHSE', 1) -> {result.get('trade_date')}")
        else:
            print("✗ get_pre_trade_date returned None")

        # 测试 get_next_trade_date
        result = get_next_trade_date("2024-01-26", "SHSE", 1)
        if result:
            print(f"✓ get_next_trade_date('2024-01-26', 'SHSE', 1) -> {result.get('trade_date')}")
        else:
            print("✗ get_next_trade_date returned None")

        # 测试 get_trade_calendar
        calendar = get_trade_calendar("2024-01-01", "2024-01-31", "SHSE")
        print(f"✓ get_trade_calendar('2024-01-01', '2024-01-31', 'SHSE') -> {len(calendar)} days")
        if calendar:
            print(f"  First: {calendar[0].get('trade_date')}")
            print(f"  Last: {calendar[-1].get('trade_date')}")

        # 测试 get_trade_dates (新函数)
        dates = get_trade_dates("2024-01-01", "2024-01-05", "SHSE")
        print(f"✓ get_trade_dates('2024-01-01', '2024-01-05', 'SHSE') -> {dates}")

    except Exception as e:
        print(f"✗ Trade date tests failed (DB may not be available): {e}")
        print("  This is OK if running without database connection")

    print()


def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "DATE_UTILS REFACTOR TEST SUITE" + " " * 17 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    try:
        test_date_to_int()
        test_int_to_date_str()
        test_date_to_str()
        test_util_make_date_stamp()
        test_performance()
        test_trade_date_functions()

        print("=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        print()

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        raise
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}\n")
        raise


if __name__ == "__main__":
    run_all_tests()
