"""
FLY深度实现 - 日志模块
"""

import logging
import sys
from datetime import datetime
from typing import Optional
from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class SwarmFlyFormatter(logging.Formatter):
    """自定义日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m',
    }
    
    def format(self, record):
        # 添加颜色
        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            levelname = record.levelname
            record.levelname = f"{self.COLORS.get(levelname, '')}{levelname}{self.COLORS['RESET']}"
        
        # 添加时间戳
        record.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        return super().format(record)


class SwarmFlyLogger:
    """SwarmFly日志管理器"""
    
    _loggers = {}
    
    def __init__(self, name: str, level: LogLevel = LogLevel.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level.value)
        self._setup_handlers()
    
    def _setup_handlers(self):
        """设置处理器"""
        if not self.logger.handlers:
            # 控制台处理器
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            
            # 格式化
            formatter = SwarmFlyFormatter(
                '[%(timestamp)s] [%(name)s] [%(levelname)s] %(message)s'
            )
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(console_handler)
    
    def debug(self, message: str, **kwargs):
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        self.logger.critical(message, extra=kwargs)
    
    @classmethod
    def get_logger(cls, name: str, level: LogLevel = LogLevel.INFO) -> 'SwarmFlyLogger':
        """获取日志记录器"""
        if name not in cls._loggers:
            cls._loggers[name] = cls(name, level)
        return cls._loggers[name]


def get_logger(name: str, level: LogLevel = LogLevel.INFO) -> SwarmFlyLogger:
    """获取日志记录器快捷函数"""
    return SwarmFlyLogger.get_logger(name, level)
