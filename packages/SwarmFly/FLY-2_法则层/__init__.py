"""
FLY-2 法则层 - 主模块入口
FLY-2 Core Module Entry Point
"""

from typing import Dict, List, Optional, Any

from .Core.RuleEngine import (
    RuleParser, RuleExecutor, RuleValidator, RuleCache,
    Rule, Condition, Action, ExecutionContext
)
from .Core.ConflictResolver import (
    PriorityManager, ResourceArbiter, DeadlockDetector,
    PriorityLevel, AllocationDecision, DeadlockInfo
)
from .Core.SecurityEnforcer import (
    PermissionChecker, RBACEngine, AuditLogger,
    Permission, Role, AuditAction, EncryptionHandler
)
from .Interfaces import RevolvingInterface, EvolvingInterface

from implementation.shared.logging import get_logger

logger = get_logger("FLY2")


class FLY2Core:
    """FLY-2 法则层核心"""
    
    def __init__(self):
        # 规则引擎
        self.rule_parser = RuleParser()
        self.rule_executor = RuleExecutor()
        self.rule_validator = RuleValidator()
        self.rule_cache = RuleCache()
        
        # 冲突解决
        self.priority_manager = PriorityManager()
        self.resource_arbiter = ResourceArbiter()
        self.deadlock_detector = DeadlockDetector()
        
        # 安全执行
        self.permission_checker = PermissionChecker()
        self.audit_logger = AuditLogger()
        self.encryption_handler = EncryptionHandler()
        
        # 引擎接口
        self.revolving = RevolvingInterface()
        self.evolving = EvolvingInterface()
        
        # 初始化
        self._initialized = False
    
    async def initialize(self):
        """初始化FLY-2"""
        if self._initialized:
            return
        
        logger.info("初始化FLY-2法则层...")
        
        # 启动缓存
        self.rule_cache.start()
        
        # 启动死锁检测
        self.deadlock_detector.start()
        
        # 连接引擎
        await self.revolving.connect("http://revolving:8080")
        await self.evolving.connect("http://evolving:8080")
        
        self._initialized = True
        logger.info("FLY-2法则层初始化完成")
    
    async def shutdown(self):
        """关闭FLY-2"""
        logger.info("关闭FLY-2法则层...")
        
        self.rule_cache.stop()
        self.deadlock_detector.stop()
        await self.revolving.disconnect()
        await self.evolving.disconnect()
        
        self._initialized = False
        logger.info("FLY-2法则层已关闭")
    
    async def execute_rule(
        self,
        rule: Rule,
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行规则"""
        context = ExecutionContext(
            context_id=f"ctx_{rule.rule_id}_{int(datetime.now().timestamp())}",
            data=context_data
        )
        
        # 添加规则到执行器
        self.rule_executor.add_rule(rule)
        
        # 执行
        results = await self.rule_executor.execute(context)
        
        # 同步到Revolving
        await self.revolving.sync_rules_to_revolving([rule.to_dict()])
        
        # 上报结果到Evolving
        for rule_id, result in results.items():
            await self.evolving.report_execution_result(
                agent_id="fly2_rule_engine",
                result=result,
                context={"rule_id": rule_id}
            )
        
        return {rule_id: r.to_dict() for rule_id, r in results.items()}
    
    def validate_rule(self, rule: Rule) -> Dict[str, Any]:
        """验证规则"""
        # 语法验证
        syntax_result = self.rule_validator.validate_syntax(rule)
        
        # 语义验证
        semantic_result = self.rule_validator.validate_semantics(rule)
        
        # 冲突检测
        conflicts = self.rule_validator.validate_conflicts(rule)
        
        return {
            "is_valid": syntax_result.is_valid and semantic_result.is_valid,
            "syntax": syntax_result.to_dict() if hasattr(syntax_result, 'to_dict') else {
                "is_valid": syntax_result.is_valid,
                "errors": syntax_result.errors,
                "warnings": syntax_result.warnings
            },
            "semantic": semantic_result.to_dict() if hasattr(semantic_result, 'to_dict') else {
                "is_valid": semantic_result.is_valid,
                "errors": semantic_result.errors,
                "warnings": semantic_result.warnings
            },
            "conflicts": [
                {"conflict_id": c.conflict_id, "type": c.conflict_type}
                for c in conflicts
            ]
        }
    
    def resolve_conflict(self, agents: List[str], resource: str) -> Dict[str, Any]:
        """解决冲突"""
        from implementation.shared import Conflict
        
        conflict = Conflict(
            conflict_id=f"conflict_{int(datetime.now().timestamp())}",
            agents=agents,
            resource=resource,
            conflict_type="resource_contention"
        )
        
        resolution = self.resource_arbiter.resolve_conflict(conflict)
        
        return {
            "resolved": resolution.resolved,
            "winner": resolution.winner,
            "strategy": resolution.strategy
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "initialized": self._initialized,
            "rule_executor": self.rule_executor.get_statistics(),
            "rule_cache": self.rule_cache.get_statistics(),
            "deadlock_detector": self.deadlock_detector.get_statistics(),
            "revolving": self.revolving.get_statistics(),
            "evolving": self.evolving.get_statistics()
        }


# 全局实例
_fly2_core: Optional[FLY2Core] = None


def get_fly2_core() -> FLY2Core:
    """获取FLY-2核心实例"""
    global _fly2_core
    if _fly2_core is None:
        _fly2_core = FLY2Core()
    return _fly2_core


# 需要导入datetime
from datetime import datetime
