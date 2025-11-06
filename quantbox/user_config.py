"""
用户配置初始化模块

该模块负责初始化用户配置目录和配置文件，确保用户首次使用时
有完整的配置文件结构。
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def init_user_config(force: bool = False, user_config_dir: Optional[Path] = None) -> bool:
    """
    初始化用户配置目录和文件

    Args:
        force: 是否强制覆盖已存在的配置文件
        user_config_dir: 自定义用户配置目录，默认为 ~/.quantbox/settings

    Returns:
        bool: 初始化是否成功
    """
    try:
        # 确定用户配置目录
        if user_config_dir is None:
            user_config_dir = Path.home() / ".quantbox" / "settings"

        user_config_dir.mkdir(parents=True, exist_ok=True)

        # 获取项目配置模板目录
        project_root = Path(__file__).parent.parent
        template_config_dir = project_root / "config" / "templates"

        # 如果模板目录不存在，创建默认配置
        if not template_config_dir.exists():
            logger.info("模板配置目录不存在，创建默认配置")
            return _create_default_config(user_config_dir, force)

        # 复制模板配置文件
        success = True
        for template_file in template_config_dir.glob("*.toml"):
            target_file = user_config_dir / template_file.name

            if target_file.exists() and not force:
                logger.info(f"配置文件已存在，跳过: {target_file}")
                continue

            try:
                shutil.copy2(template_file, target_file)
                logger.info(f"已复制配置文件: {template_file.name}")
            except Exception as e:
                logger.error(f"复制配置文件失败 {template_file.name}: {e}")
                success = False

        # 如果没有模板文件，创建默认配置
        if not any(template_config_dir.glob("*.toml")):
            success = _create_default_config(user_config_dir, force)

        if success:
            logger.info(f"用户配置初始化完成: {user_config_dir}")
            _print_next_steps(user_config_dir)

        return success

    except Exception as e:
        logger.error(f"初始化用户配置失败: {e}")
        return False


def _create_default_config(user_config_dir: Path, force: bool) -> bool:
    """
    创建默认配置文件

    Args:
        user_config_dir: 用户配置目录
        force: 是否强制覆盖

    Returns:
        bool: 创建是否成功
    """
    try:
        import toml

        # 默认配置内容
        default_config = {
            'TSPRO': {
                'token': '',  # 请从 https://tushare.pro 获取
                '_comment': 'Tushare Pro API 配置'
            },
            'GM': {
                'token': '',  # 请从 https://www.myquant.cn 获取
                '_comment': '掘金量化 API 配置'
            },
            'MONGODB': {
                'uri': 'mongodb://localhost:27017',
                '_comment': 'MongoDB 数据库配置'
            }
        }

        config_file = user_config_dir / "config.toml"

        # 检查文件是否存在
        if config_file.exists() and not force:
            logger.info(f"配置文件已存在: {config_file}")
            return True

        # 写入配置文件
        with open(config_file, 'w', encoding='utf-8') as f:
            toml.dump(default_config, f)

        logger.info(f"已创建默认配置文件: {config_file}")
        return True

    except Exception as e:
        logger.error(f"创建默认配置文件失败: {e}")
        return False


def _print_next_steps(user_config_dir: Path):
    """打印后续步骤说明"""
    config_file = user_config_dir / "config.toml"

    print("\n" + "="*60)
    print("🎉 Quantbox 配置初始化完成！")
    print("="*60)
    print(f"\n📁 配置文件位置: {config_file}")
    print("\n📝 下一步操作:")
    print("1. 编辑配置文件，设置您的 API tokens:")
    print(f"   编辑 {config_file}")
    print("\n2. 获取 Tushare Pro token:")
    print("   - 访问: https://tushare.pro/register")
    print("   - 登录后获取 token")
    print("   - 将 token 填入 [TSPRO] 部分")
    print("\n3. (可选) 配置 MongoDB:")
    print("   - 默认: mongodb://localhost:27017")
    print("   - 可根据需要修改连接字符串")
    print("\n4. 开始使用:")
    print("   from quantbox.services.market_data_service import MarketDataService")
    print("   service = MarketDataService()")
    print("="*60)


def check_config_exists() -> bool:
    """
    检查用户配置文件是否存在

    Returns:
        bool: 配置文件是否存在
    """
    config_file = Path.home() / ".quantbox" / "settings" / "config.toml"
    return config_file.exists()


def get_config_path() -> Path:
    """
    获取用户配置文件路径

    Returns:
        Path: 配置文件路径
    """
    return Path.home() / ".quantbox" / "settings" / "config.toml"


def ensure_user_config() -> bool:
    """
    确保用户配置存在，如果不存在则初始化

    Returns:
        bool: 配置是否就绪
    """
    if not check_config_exists():
        print("🔧 检测到首次使用，正在初始化配置...")
        return init_user_config()

    return True


# 命令行接口
def main():
    """命令行入口点"""
    import argparse

    parser = argparse.ArgumentParser(description="初始化 Quantbox 用户配置")
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制覆盖已存在的配置文件"
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        help="自定义配置目录路径"
    )

    args = parser.parse_args()

    success = init_user_config(force=args.force, user_config_dir=args.config_dir)

    if success:
        print("✅ 配置初始化成功！")
        sys.exit(0)
    else:
        print("❌ 配置初始化失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
