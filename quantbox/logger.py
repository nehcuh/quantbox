"""
日志管理模块

本模块提供了一个统一的日志管理系统，用于记录和跟踪系统中的各种操作和事件。
支持多种日志级别、格式化输出和灵活的处理器配置。

功能特性：
- 统一的日志格式
- 多级别日志支持
- 文件和控制台输出
- 可配置的日志级别
- 自动日志轮转

配置项：
- 日志文件路径
- 日志级别设置
- 格式化模板
- 轮转策略

依赖：
    - logging
    - os
    - sys
    - typing

English Version:
---------------
Logging Management Module

This module provides a unified logging system for recording and tracking various
operations and events within the system. It supports multiple log levels,
formatted output, and flexible handler configuration.

Features:
- Unified log format
- Multi-level logging support
- File and console output
- Configurable log levels
- Automatic log rotation

Configuration:
- Log file paths
- Log level settings
- Format templates
- Rotation policies

Dependencies:
    - logging
    - os
    - sys
    - typing
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logger(
    name: str,
    log_dir: Optional[str] = None,
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    设置和配置日志记录器。

    为指定的模块创建和配置一个日志记录器实例。支持文件和控制台输出，
    可自定义日志级别和输出文件。

    参数：
        name: 日志记录器名称，通常为模块名
        log_dir: 日志文件目录，默认为 ~/.quantbox/logs
        level: 日志级别，默认为 logging.INFO
        max_bytes: 日志文件最大大小，默认为 10MB
        backup_count: 日志文件备份数量，默认为 5

    返回：
        logging.Logger: 配置好的日志记录器实例

    用法示例：
        >>> logger = setup_logger(__name__)
        >>> logger.info("操作成功完成")
        >>> logger.error("发生错误")

    注意：
        - 默认配置来自配置文件
        - 支持文件和控制台同时输出
        - 自动创建日志目录
        - 使用统一的日志格式

    English Version:
    ---------------
    Set up and configure a logger.

    Creates and configures a logger instance for the specified module. Supports both
    file and console output with customizable log levels and output files.

    Args:
        name: Logger name, typically the module name
        log_dir: Log file directory, defaults to ~/.quantbox/logs
        level: Logging level, defaults to logging.INFO
        max_bytes: Maximum log file size, defaults to 10MB
        backup_count: Number of log file backups, defaults to 5

    Returns:
        logging.Logger: Configured logger instance

    Example:
        >>> logger = setup_logger(__name__)
        >>> logger.info("Operation completed successfully")
        >>> logger.error("An error occurred")

    Note:
        - Default configuration from config file
        - Supports both file and console output
        - Automatically creates log directory
        - Uses unified log format
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Return existing logger if already configured
    if logger.handlers:
        return logger
        
    # Create formatter with detailed output format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add console handler for immediate feedback
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Set up file handler if log directory is specified
    if log_dir is None:
        log_dir = os.path.expanduser('~/.quantbox/logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Use current date as log file name
    log_file = os.path.join(
        log_dir,
        f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    )
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger
