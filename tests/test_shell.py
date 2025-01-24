"""Test quantbox shell"""

import pytest
from unittest.mock import patch, MagicMock
from quantbox.cli.shell import QuantboxShell


@patch('quantbox.cli.shell.TushareFetcher')
def test_save_trade_dates(mock_fetcher):
    """Test save trade_dates command"""
    # 设置 mock
    mock_instance = mock_fetcher.return_value
    
    shell = QuantboxShell()
    
    # 测试不带参数
    shell.process_command("save trade_dates")
    assert mock_instance.fetch_calendar.call_count == 8  # 所有交易所
    mock_instance.fetch_calendar.reset_mock()
    
    # 测试带交易所参数
    shell.process_command("save trade_dates -e SSE")
    mock_instance.fetch_calendar.assert_called_once_with(
        exchange="SSE",
        start_date=None,
        end_date=None
    )
    mock_instance.fetch_calendar.reset_mock()
    
    # 测试带交易所类型参数
    shell.process_command("save trade_dates -t STOCK")
    assert mock_instance.fetch_calendar.call_count == 2  # SSE 和 SZSE
    mock_instance.fetch_calendar.reset_mock()
    
    # 测试带日期参数
    shell.process_command("save trade_dates -s 20240101 -d 20240124")  # 使用 -d 而不是 -e
    assert mock_instance.fetch_calendar.call_count == 8  # 所有交易所
    for call_args in mock_instance.fetch_calendar.call_args_list:
        assert call_args[1]['start_date'] == '20240101'
        assert call_args[1]['end_date'] == '20240124'


def test_help_command():
    """Test help command"""
    shell = QuantboxShell()
    
    with patch('builtins.print') as mock_print:
        shell.process_command("help")
        mock_print.assert_called()


def test_exit_command():
    """Test exit command"""
    shell = QuantboxShell()
    
    with pytest.raises(SystemExit):
        shell.process_command("exit")
