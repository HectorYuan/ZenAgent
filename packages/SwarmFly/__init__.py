"""
SwarmFly FLY-2/3/5 深度实现

SwarmFly智能体系统的三层核心实现:
- FLY-2 法·法则层: 规则引擎、冲突解决、安全执行
- FLY-3 势·趋势层: 趋势分析、预测引擎、自适应控制
- FLY-5 器·工具层: 工具注册、消息队列、资源池
"""

__version__ = "1.0.0"
__author__ = "SwarmFly Team"

# FLY-2 法·法则层
from .fly2rules.Core.RuleEngine import RuleParser, RuleExecutor, RuleValidator, RuleCache
from .fly2rules.Core.ConflictResolver import PriorityManager, ResourceArbiter, DeadlockDetector
from .fly2rules.Core.SecurityEnforcer import PermissionChecker, AuditLogger, EncryptionHandler
from .fly2rules.Interfaces import RevolvingInterface, EvolvingInterface

# FLY-3 势·趋势层
from .fly3trends.Core.TrendAnalyzer import TrendAnalyzer, TechTrendAnalyzer, MarketTrendAnalyzer, BehaviorAnalyzer
from .fly3trends.Core.PredictionEngine import PredictionEngine, Prediction, PredictionModel, PredictionHorizon, TimeSeriesPoint
from .fly3trends.Core.AdaptiveController import AdaptiveController
from .fly3trends.Convolv import TrendConvolv, EmergentDetector

# FLY-5 器·工具层
from .fly5tools.Core.ToolRegistry import ToolRegistry, ToolMetadata, Capability
from .fly5tools.Core.MessageQueue import MessageQueue, Message
from .fly5tools.Core.ProtocolLayer import ToolCallProtocol
from .fly5tools.Core.ResourcePool import PoolManager

__all__ = [
    # FLY-2
    'RuleParser', 'RuleExecutor', 'RuleValidator', 'RuleCache',
    'PriorityManager', 'ResourceArbiter', 'DeadlockDetector',
    'PermissionChecker', 'AuditLogger', 'EncryptionHandler',
    'RevolvingInterface', 'EvolvingInterface',

    # FLY-3
    'TrendAnalyzer', 'TechTrendAnalyzer', 'MarketTrendAnalyzer', 'BehaviorAnalyzer',
    'PredictionEngine', 'Prediction', 'PredictionModel', 'PredictionHorizon', 'TimeSeriesPoint',
    'AdaptiveController',

    # FLY-5
    'ToolRegistry', 'ToolMetadata', 'Capability',
    'MessageQueue', 'Message',
    'ToolCallProtocol',
    'PoolManager',

    # SwarmFly 完整核心
    'SwarmFly',
    'SwarmFlyConfig',
]

# 完整 FLY 六层 + 横切模块
from .swarmfly import SwarmFly, SwarmFlyConfig


class SwarmFlyCore(SwarmFly):
    """
    SwarmFly 核心类

    整合 FLY-0 到 FLY-5 六层 + 四大横切模块，提供统一的系统入口。
    继承 SwarmFly，添加 FLY-2/3/5 的便捷访问器。
    """

    def __init__(self, config=None):
        super().__init__(config.swarmfly_config if hasattr(config, 'swarmfly_config') else None)
        self.config = config or {}

    async def initialize(self):
        """初始化系统"""
        await super().initialize() if hasattr(super(), 'initialize') else None

    async def shutdown(self):
        """关闭系统"""
        await super().shutdown() if hasattr(super(), 'shutdown') else None

    def get_system_status(self) -> dict:
        """获取系统状态（含 FLY-2/3/5 统计）"""
        return self.get_detailed_status()
