"""
Quantbox 安装脚本

包含安装后配置初始化功能。
"""

from setuptools import setup
from setuptools.command.install import install
import sys
from pathlib import Path


class PostInstallCommand(install):
    """安装后自动初始化用户配置"""

    def run(self):
        # 执行标准安装
        install.run(self)

        # 安装后初始化配置
        try:
            from quantbox.user_config import init_user_config

            print("\n" + "="*60)
            print("🔧 正在初始化 Quantbox 配置...")
            print("="*60)

            success = init_user_config()

            if success:
                print("✅ 配置初始化成功！")
                print("\n📝 下一步:")
                print("1. 编辑配置文件设置您的 API tokens")
                print("2. 运行: quantbox --help 查看使用说明")
            else:
                print("❌ 配置初始化失败")
                print("请运行: quantbox-config 手动初始化配置")

            print("="*60)

        except ImportError:
            print("⚠️  配置初始化失败，请运行: quantbox-config")
        except Exception as e:
            print(f"❌ 配置初始化失败: {e}")
            print("请运行: quantbox-config 手动初始化配置")


if __name__ == "__main__":
    setup(
        cmdclass={
            'install': PostInstallCommand,
        },
    )