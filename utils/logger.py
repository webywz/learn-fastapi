"""
===========================================
日志配置模块 (Logger Module)
===========================================

作用：
  配置应用的日志系统

为什么需要日志？
  1. 调试：记录程序运行过程，方便定位问题
  2. 监控：记录异常和错误，及时发现问题
  3. 审计：记录用户操作，追踪问题根源

日志级别（从低到高）：
  DEBUG → INFO → WARNING → ERROR → CRITICAL
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from core.config import settings


# 创建 logs 目录
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def setup_logging():
    """
    配置全局日志系统

    输出目标：
      1. 控制台（Console）: INFO 及以上级别
      2. 文件（app.log）: DEBUG 及以上级别（所有日志）
      3. 错误文件（error.log）: ERROR 及以上级别（只记录错误）

    日志格式：
      2024-01-01 12:00:00 - module_name - INFO - [file.py:123] - 日志消息

    日志轮转：
      - 单个文件最大 10MB
      - 保留 5 个备份文件
      - 防止日志文件过大
    """
    # 获取根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 避免重复添加 handler
    if root_logger.handlers:
        return

    # 日志格式
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件 Handler（所有日志）
    file_handler = RotatingFileHandler(
        LOGS_DIR / "app.log",
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 错误日志 Handler
    error_handler = RotatingFileHandler(
        LOGS_DIR / "error.log",
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)


def get_logger(name: str) -> logging.Logger:
    """
    获取 logger 实例

    使用示例:
        from utils.logger import get_logger

        logger = get_logger(__name__)
        logger.info("这是一条信息")
        logger.error("这是一个错误")
    """
    return logging.getLogger(name)
