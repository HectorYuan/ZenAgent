"""
技能调用器
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio


class CallStatus(Enum):
    """调用状态"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    PENDING = "pending"


@dataclass
class CallResult:
    """调用结果"""
    status: CallStatus
    skill_id: str
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    version: str = "1.0"
    
    def is_success(self) -> bool:
        return self.status == CallStatus.SUCCESS


class SkillCaller:
    """
    技能调用器
    
    提供同步和异步技能调用能力
    """
    
    def __init__(self, registry):
        self.registry = registry
        self.call_history: List[CallResult] = []
    
    def call_sync(self, skill_id: str, params: Dict[str, Any], 
                  timeout: float = 30.0) -> CallResult:
        """
        同步调用技能
        
        Args:
            skill_id: 技能ID
            params: 调用参数
            timeout: 超时时间(秒)
            
        Returns:
            CallResult: 调用结果
        """
        start_time = datetime.now()
        
        skill = self.registry.get_skill(skill_id)
        if not skill:
            return CallResult(
                status=CallStatus.FAILED,
                skill_id=skill_id,
                error=f"Skill {skill_id} not found",
                execution_time=0.0
            )
        
        try:
            # 检查参数
            self._validate_params(skill, params)
            
            # 调用技能
            result = skill(**params)
            
            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            
            call_result = CallResult(
                status=CallStatus.SUCCESS,
                skill_id=skill_id,
                data=result,
                execution_time=execution_time,
                version=skill.metadata.version
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            call_result = CallResult(
                status=CallStatus.FAILED,
                skill_id=skill_id,
                error=str(e),
                execution_time=execution_time
            )
        
        self.call_history.append(call_result)
        return call_result
    
    async def call_async(self, skill_id: str, params: Dict[str, Any],
                         timeout: float = 30.0) -> CallResult:
        """异步调用技能"""
        return await asyncio.wait_for(
            asyncio.to_thread(self.call_sync, skill_id, params, timeout),
            timeout=timeout
        )
    
    def _validate_params(self, skill, params: Dict[str, Any]):
        """验证参数"""
        required = [p['name'] for p in skill.metadata.input_params if p.get('required')]
        missing = [p for p in required if p not in params]
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")
    
    def get_statistics(self, skill_id: Optional[str] = None) -> Dict[str, Any]:
        """获取调用统计"""
        if skill_id:
            calls = [c for c in self.call_history if c.skill_id == skill_id]
        else:
            calls = self.call_history
        
        if not calls:
            return {"total": 0, "success_rate": 100.0}
        
        total = len(calls)
        success = len([c for c in calls if c.is_success()])
        avg_time = sum(c.execution_time for c in calls) / total
        
        return {
            "total": total,
            "success": success,
            "failed": total - success,
            "success_rate": (success / total) * 100,
            "avg_execution_time": avg_time
        }
