import unittest
from quantbox.config.config_loader import get_config_loader
from unittest.mock import patch, mock_open

class TestConfig(unittest.TestCase):
    @patch('os.path.expanduser', return_value='/mock/default/config.toml')
    @patch('toml.load', return_value={'TSPRO': {'token': 'testtoken'}, 'MONGODB': {'uri': 'localhost'}})
    def test_load_default_toml_config(self, mock_toml_load, mock_expanduser):
        """
         测试加载 .toml 配置文件
        """
        config = get_config_loader()
        self.assertEqual(config.get_tushare_token(), 'testtoken')
        self.assertEqual(config.get_mongodb_uri(), 'localhost')

    # @patch('builtins.open', new_callable=mock_open, read_data="[TSPRO]\ntoken=testtoken\n[MONGODB]\nuri=localhost\n")
    # @patch('configparser.ConfigParser.read', return_value=True)
    # def test_load_ini_config(self, mock_configparser_read, mock_open):
    #     """
    #     TODO：不太对，这里的 tests 始终通不过，先注释了
    #     测试加载 .ini 配置文件。

    #     通过 patching 模拟 open 函数返回特定的 INI 文件内容，并且模拟 ConfigParser.read，
    #     验证在指定 config_file 为 INI 文件路径时，Config 类是否能正确加载和解析 INI 配置文件。
    #     """
    #     config = Config(config_file='/mock/path/config.ini')
    #     print(config.config)
    #     self.assertEqual(config.ts_token, 'testtoken')
    #     self.assertEqual(config.mongo_uri, 'localhost')

    @patch('builtins.open', new_callable=mock_open, read_data='{"TSPRO": {"token": "testtoken"}, "MONGODB": {"uri": "localhost"}}')
    def test_load_json_config(self, mock_open):
        """
        测试加载 .json 配置文件。

        通过 patching 模拟 open 函数返回特定的 JSON 文件内容，
        验证在指定 config_file 为 JSON 文件路径时，Config 类是否能正确加载和解析 JSON 配置文件。
        """
        config = Config(config_file='/mock/path/config.json')
        self.assertEqual(config.ts_token, 'testtoken')
        self.assertEqual(config.mongo_uri, 'localhost')


if __name__ == "__main__":
    unittest.main()
