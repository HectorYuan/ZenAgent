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
from Core.RuleEngine import RuleParser, RuleExecutor, RuleValidator, RuleCache
from Core.ConflictResolver import PriorityManager, ResourceArbiter, DeadlockDetector
from Core.SecurityEnforcer import PermissionChecker, AuditLogger, EncryptionHandler
from Interfaces import RevolvingInterface, EvolvingInterface

# FLY-3 势·趋势层
from Core.TrendAnalyzer import TrendAnalyzer, TechTrendAnalyzer, MarketTrendAnalyzer, BehaviorAnalyzer
from Core.PredictionEngine import PredictionEngine, TimeSeriesModel, AnomalyDetector
from Core.AdaptiveController import AdaptiveController, StrategyOptimizer, ResourceScaler
from Core.Convolv import TrendConvolv, EmergentDetector

# FLY-5 器·工具层
from Core.ToolRegistry import ToolRegistry, ToolMetadata, Capability
from Core.MessageQueue import MessageQueue, Message
from Core.ProtocolLayer import ToolCallProtocol
from Core.ResourcePool import PoolManager

__all__ = [
    # FLY-2
    'RuleParser', 'RuleExecutor', 'RuleValidator', 'RuleCache',
    'PriorityManager', 'ResourceArbiter', 'DeadlockDetector',
    'PermissionChecker', 'AuditLogger', 'EncryptionHandler',
    'RevolvingInterface', 'EvolvingInterface',
    
    # FLY-3
    'TrendAnalyzer', 'TechTrendAnalyzer', 'MarketTrendAnalyzer', 'BehaviorAnalyzer',
    'PredictionEngine', 'TimeSeriesModel', 'AnomalyDetector',
    'AdaptiveController', 'StrategyOptimizer', 'ResourceScaler',
    'TrendConvolv', 'EmergentDetector',
    
    # FLY-5
    'ToolRegistry', 'ToolMetadata', 'Capability',
    'MessageQueue', 'Message',
    'ToolCallProtocol',
    'PoolManager'
]


class SwarmFlyCore:
    """
    SwarmFly核心类
    
    整合FLY-2/3/5三层功能，提供统一的系统入口。
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        
        # FLY-2 法·法则层
        self.rule_parser = RuleParser()
        self.rule_executor = RuleExecutor()
        self.rule_validator = RuleValidator()
        self.rule_cache = RuleCache()
        self.priority_manager = PriorityManager()
        self.resource_arbiter = ResourceArbiter()
        self.deadlock_detector = DeadlockDetector()
        self.permission_checker = PermissionChecker()
        self.audit_logger = AuditLogger()
        self.encryption = EncryptionHandler()
        
        # FLY-3 势·趋势层
        self.trend_analyzer = TrendAnalyzer()
        self.tech_trend_analyzer = TechTrendAnalyzer()
        self.market_trend_analyzer = MarketTrendAnalyzer()
        self.behavior_analyzer = BehaviorAnalyzer()
        self.prediction_engine = PredictionEngine()
        self.adaptive_controller = AdaptiveController()
        self.trend_convolv = TrendConvolv()
        self.emergent_detector = EmergentDetector()
        
        # FLY-5 器·工具层
        self.tool_registry = ToolRegistry()
        self.message_queue = MessageQueue()
        self.tool_protocol = ToolCallProtocol()
        self.pool_manager = PoolManager()
    
    async def initialize(self):
        """初始化系统"""
        # 启动各组件
        await self.tool_registry.start()
        await self.message_queue.start()
        
        # 启动死锁检测
        self.deadlock_detector.start_detection()
    
    async def shutdown(self):
        """关闭系统"""
        # 停止各组件
        await self.tool_registry.stop()
        await self.message_queue.stop()
        self.deadlock_detector.stop_detection()
    
    def get_system_status(self) -> dict:
        """获取系统状态"""
        return {
            'fly2_rules': {
                'total': len(self.rule_cache.l1_cache),
                'versions': len(self.rule_cache.l2_cache)
            },
            'fly3_trends': self.trend_analyzer.get_stats(),
            'fly5_tools': self.tool_registry.get_stats(),
            'fly5_messages': self.message_queue.get_stats()
        }
