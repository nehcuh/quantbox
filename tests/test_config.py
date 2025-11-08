"""
配置加载器测试

测试 ConfigLoader 的核心功能，包括：
- TOML 配置文件加载
- Token 获取
- MongoDB URI 获取
"""

import unittest
from quantbox.config.config_loader import get_config_loader
from unittest.mock import patch


class TestConfigLoader(unittest.TestCase):
    """测试 ConfigLoader 类"""

    @patch('os.path.expanduser', return_value='/mock/default/config.toml')
    @patch('toml.load', return_value={
        'TSPRO': {'token': 'testtoken'},
        'MONGODB': {'uri': 'mongodb://localhost:27017'},
        'GM': {'token': 'gm_testtoken'}
    })
    def test_load_toml_config(self, mock_toml_load, mock_expanduser):
        """测试加载 TOML 配置文件"""
        config = get_config_loader()

        # 测试 Tushare token
        self.assertEqual(config.get_tushare_token(), 'testtoken')

        # 测试 MongoDB URI
        self.assertEqual(config.get_mongodb_uri(), 'mongodb://localhost:27017')

        # 测试掘金 token
        self.assertEqual(config.get_gm_token(), 'gm_testtoken')

    @patch('os.path.expanduser', return_value='/mock/default/config.toml')
    @patch('toml.load', return_value={})
    def test_load_empty_config(self, mock_toml_load, mock_expanduser):
        """测试加载空配置文件"""
        config = get_config_loader()

        # 空配置应该返回 None 或默认值
        self.assertIsNone(config.get_tushare_token())
        self.assertIsNone(config.get_gm_token())


if __name__ == "__main__":
    unittest.main()
