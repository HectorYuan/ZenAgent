"""
SwarmFly FLY-2 法·法则层 - 冲突解决模块

实现智能体间的资源冲突检测与解决功能:
- 优先级管理
- 资源仲裁
- 死锁检测与预防
"""

from .priority_manager import PriorityManager, PriorityLevel
from .resource_arbiter import ResourceArbiter, ArbitrationResult
from .deadlock_detector import DeadlockDetector, DeadlockInfo

__all__ = [
    'PriorityManager',
    'ResourceArbiter',
    'DeadlockDetector',
    'PriorityLevel',
    'ArbitrationResult',
    'DeadlockInfo'
]
