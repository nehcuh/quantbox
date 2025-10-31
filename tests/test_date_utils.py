"""
日期工具模块单元测试
"""
import pytest
import datetime
from quantbox.util.date_utils import (
    date_to_int,
    int_to_date_str,
    date_to_str,
    util_make_date_stamp,
    DateLike
)


class TestDateToInt:
    """测试 date_to_int 函数"""
    
    def test_none_input(self):
        """测试 None 输入，应返回今天的日期"""
        result = date_to_int(None)
        expected = int(datetime.date.today().strftime('%Y%m%d'))
        assert result == expected
    
    def test_integer_input(self):
        """测试整数输入"""
        assert date_to_int(20240126) == 20240126
        assert date_to_int(20231231) == 20231231
    
    def test_string_with_hyphen(self):
        """测试带连字符的字符串输入"""
        assert date_to_int("2024-01-26") == 20240126
        assert date_to_int("2023-12-31") == 20231231
    
    def test_string_without_hyphen(self):
        """测试不带连字符的字符串输入"""
        assert date_to_int("20240126") == 20240126
        assert date_to_int("20231231") == 20231231
    
    def test_date_object(self):
        """测试 datetime.date 对象输入"""
        date_obj = datetime.date(2024, 1, 26)
        assert date_to_int(date_obj) == 20240126
    
    def test_datetime_object(self):
        """测试 datetime.datetime 对象输入"""
        dt_obj = datetime.datetime(2024, 1, 26, 10, 30, 45)
        assert date_to_int(dt_obj) == 20240126
    
    def test_invalid_integer_length(self):
        """测试无效的整数长度"""
        with pytest.raises(ValueError, match="Integer date must be 8 digits"):
            date_to_int(2024)
        with pytest.raises(ValueError, match="Integer date must be 8 digits"):
            date_to_int(202401265)
    
    def test_invalid_date_value(self):
        """测试无效的日期值"""
        with pytest.raises(ValueError):
            date_to_int(20241332)  # 无效月份
        with pytest.raises(ValueError):
            date_to_int("2024-13-01")  # 无效月份
    
    def test_invalid_date_format(self):
        """测试无效的日期格式"""
        with pytest.raises(ValueError):
            date_to_int("2024/01/26")  # 不支持的格式
        with pytest.raises(ValueError):
            date_to_int("26-01-2024")  # 错误的顺序


class TestIntToDateStr:
    """测试 int_to_date_str 函数"""
    
    def test_valid_input(self):
        """测试有效输入"""
        assert int_to_date_str(20240126) == "2024-01-26"
        assert int_to_date_str(20231231) == "2023-12-31"
    
    def test_invalid_length(self):
        """测试无效的整数长度"""
        with pytest.raises(ValueError, match="Date integer must be 8 digits"):
            int_to_date_str(2024)
        with pytest.raises(ValueError, match="Date integer must be 8 digits"):
            int_to_date_str(202401265)
    
    def test_invalid_date_value(self):
        """测试无效的日期值"""
        with pytest.raises(ValueError):
            int_to_date_str(20241332)  # 无效月份
        with pytest.raises(ValueError):
            int_to_date_str(20240230)  # 无效日期


class TestDateToStr:
    """测试 date_to_str 函数"""
    
    def test_default_format(self):
        """测试默认格式"""
        assert date_to_str("2024-01-26") == "2024-01-26"
        assert date_to_str(20240126) == "2024-01-26"
        assert date_to_str(datetime.date(2024, 1, 26)) == "2024-01-26"
    
    def test_custom_format(self):
        """测试自定义格式"""
        assert date_to_str("2024-01-26", "%Y/%m/%d") == "2024/01/26"
        assert date_to_str(20240126, "%d-%m-%Y") == "26-01-2024"
    
    def test_none_input(self):
        """测试 None 输入"""
        result = date_to_str(None)
        expected = datetime.date.today().strftime("%Y-%m-%d")
        assert result == expected


class TestUtilMakeDateStamp:
    """测试 util_make_date_stamp 函数"""
    
    def test_valid_input(self):
        """测试有效输入"""
        # 2024-01-26 00:00:00 的时间戳（可能因时区而异）
        timestamp = util_make_date_stamp("2024-01-26")
        assert isinstance(timestamp, float)
        assert timestamp > 0
    
    def test_integer_input(self):
        """测试整数输入"""
        timestamp1 = util_make_date_stamp(20240126)
        timestamp2 = util_make_date_stamp("2024-01-26")
        assert timestamp1 == timestamp2
    
    def test_none_input(self):
        """测试 None 输入"""
        result = util_make_date_stamp(None)
        assert isinstance(result, float)
        assert result > 0


class TestEdgeCases:
    """测试边界情况"""
    
    def test_leap_year(self):
        """测试闰年日期"""
        # 2024 是闰年
        assert date_to_int("2024-02-29") == 20240229
        
        # 2023 不是闰年
        with pytest.raises(ValueError):
            date_to_int("2023-02-29")
    
    def test_year_2000(self):
        """测试 2000 年（特殊的闰年）"""
        assert date_to_int("2000-02-29") == 20000229
    
    def test_end_of_year(self):
        """测试年末日期"""
        assert date_to_int("2023-12-31") == 20231231
        assert date_to_int("2024-12-31") == 20241231
    
    def test_start_of_year(self):
        """测试年初日期"""
        assert date_to_int("2024-01-01") == 20240101
        assert date_to_int("2023-01-01") == 20230101


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
