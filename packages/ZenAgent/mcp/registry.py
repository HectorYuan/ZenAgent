"""
Agent 注册表
管理 Agent 的注册、发现和能力查询
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from datetime import datetime
import uuid


class AgentStatus(Enum):
    """Agent 状态枚举"""
    OFFLINE = "offline"      # 离线
    ONLINE = "online"        # 在线
    BUSY = "busy"            # 忙碌
    AWAKENING = "awakening"  # 觉醒中
    EVOLVING = "evolving"    # 进化中


class AgentCapability(Enum):
    """Agent 能力枚举"""
    # 基础能力
    TEXT_GENERATION = "text_generation"     # 文本生成
    CODE_GENERATION = "code_generation"     # 代码生成
    IMAGE_UNDERSTANDING = "image_understanding"  # 图像理解
    AUDIO_UNDERSTANDING = "audio_understanding"  # 音频理解
    
    # 高级能力
    REASONING = "reasoning"                 # 推理能力
    PLANNING = "planning"                   # 规划能力
    MULTI_MODAL = "multi_modal"             # 多模态
    TOOL_USE = "tool_use"                   # 工具使用
    MEMORY = "memory"                        # 记忆能力
    
    # 协作能力
    COLLABORATION = "collaboration"         # 协作能力
    NEGOTIATION = "negotiation"              # 协商能力
    TASK_DELEGATION = "task_delegation"     # 任务委派
    
    # 觉醒能力
    SELF_AWARENESS = "self_awareness"        # 自我意识
    EMOTION = "emotion"                      # 情感能力
    CREATIVITY = "creativity"                # 创造力


@dataclass
class AgentMetadata:
    """Agent 元数据"""
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    
    # 分类信息
    category: str = "general"  # general, specialist, coordinator
    tags: List[str] = field(default_factory=list)
    
    # 能力信息
    capabilities: Set[AgentCapability] = field(default_factory=set)
    max_concurrent_tasks: int = 5
    
    # 资源信息
    memory_limit_mb: int = 512
    cpu_cores: int = 1
    
    # 自定义元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """检查是否具有指定能力"""
        return capability in self.capabilities
    
    def supports_capabilities(self, capabilities: List[AgentCapability]) -> bool:
        """检查是否支持所有指定能力"""
        return all(cap in self.capabilities for cap in capabilities)
    
    def add_capability(self, capability: AgentCapability) -> None:
        """添加能力"""
        self.capabilities.add(capability)
    
    def remove_capability(self, capability: AgentCapability) -> None:
        """移除能力"""
        self.capabilities.discard(capability)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "category": self.category,
            "tags": self.tags,
            "capabilities": [cap.value for cap in self.capabilities],
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "memory_limit_mb": self.memory_limit_mb,
            "cpu_cores": self.cpu_cores,
            "metadata": self.metadata,
        }


@dataclass
class RegisteredAgent:
    """
    已注册的 Agent
    
    包含 Agent 的完整注册信息
    """
    metadata: AgentMetadata
    status: AgentStatus = AgentStatus.OFFLINE
    
    # 连接信息
    endpoint: Optional[str] = None
    session_id: Optional[str] = None
    
    # 统计信息
    registered_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    total_requests: int = 0
    successful_requests: int = 0
    
    # 负载信息
    current_tasks: int = 0
    
    def update_heartbeat(self) -> None:
        """更新心跳时间"""
        self.last_heartbeat = datetime.now()
    
    def increment_request(self, success: bool = True) -> None:
        """
        增加请求计数
        
        Args:
            success: 请求是否成功
        """
        self.total_requests += 1
        if success:
            self.successful_requests += 1
    
    def start_task(self) -> bool:
        """
        开始任务
        
        Returns:
            bool: 是否成功开始任务
        """
        if self.current_tasks >= self.metadata.max_concurrent_tasks:
            return False
        self.current_tasks += 1
        if self.current_tasks == self.metadata.max_concurrent_tasks:
            self.status = AgentStatus.BUSY
        return True
    
    def end_task(self) -> None:
        """结束任务"""
        if self.current_tasks > 0:
            self.current_tasks -= 1
        if self.current_tasks < self.metadata.max_concurrent_tasks:
            if self.status == AgentStatus.BUSY:
                self.status = AgentStatus.ONLINE
    
    @property
    def success_rate(self) -> float:
        """获取成功率"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def is_available(self) -> bool:
        """检查是否可用"""
        return (
            self.status in [AgentStatus.ONLINE, AgentStatus.BUSY]
            and self.current_tasks < self.metadata.max_concurrent_tasks
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            **self.metadata.to_dict(),
            "status": self.status.value,
            "endpoint": self.endpoint,
            "session_id": self.session_id,
            "registered_at": self.registered_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "success_rate": self.success_rate,
            "current_tasks": self.current_tasks,
            "is_available": self.is_available,
        }


class AgentRegistry:
    """
    Agent 注册表
    
    管理所有 Agent 的注册、发现和查询
    """
    
    def __init__(self):
        """初始化注册表"""
        self._agents: Dict[str, RegisteredAgent] = {}
        self._categories: Dict[str, Set[str]] = {}  # category -> agent_ids
        self._capabilities_index: Dict[AgentCapability, Set[str]] = {}  # capability -> agent_ids
        self._tags_index: Dict[str, Set[str]] = {}  # tag -> agent_ids
    
    def register(
        self,
        metadata: AgentMetadata,
        endpoint: Optional[str] = None
    ) -> RegisteredAgent:
        """
        注册 Agent
        
        Args:
            metadata: Agent 元数据
            endpoint: 连接端点
            
        Returns:
            RegisteredAgent: 注册的 Agent 对象
        """
        agent = RegisteredAgent(
            metadata=metadata,
            status=AgentStatus.ONLINE,
            endpoint=endpoint,
        )
        
        self._agents[metadata.agent_id] = agent
        
        # 更新索引
        self._update_indexes(agent, is_add=True)
        
        return agent
    
    def unregister(self, agent_id: str) -> bool:
        """
        注销 Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否成功注销
        """
        agent = self._agents.pop(agent_id, None)
        if agent is None:
            return False
        
        # 更新索引
        self._update_indexes(agent, is_add=False)
        
        return True
    
    def get(self, agent_id: str) -> Optional[RegisteredAgent]:
        """
        获取 Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Optional[RegisteredAgent]: Agent 对象
        """
        return self._agents.get(agent_id)
    
    def list_all(self) -> List[RegisteredAgent]:
        """
        列出所有 Agent
        
        Returns:
            List[RegisteredAgent]: Agent 列表
        """
        return list(self._agents.values())
    
    def list_by_status(self, status: AgentStatus) -> List[RegisteredAgent]:
        """
        按状态列出 Agent
        
        Args:
            status: 状态
            
        Returns:
            List[RegisteredAgent]: 符合条件的 Agent 列表
        """
        return [a for a in self._agents.values() if a.status == status]
    
    def list_available(self) -> List[RegisteredAgent]:
        """
        列出可用的 Agent
        
        Returns:
            List[RegisteredAgent]: 可用的 Agent 列表
        """
        return [a for a in self._agents.values() if a.is_available]
    
    def list_by_category(self, category: str) -> List[RegisteredAgent]:
        """
        按类别列出 Agent
        
        Args:
            category: 类别
            
        Returns:
            List[RegisteredAgent]: 符合条件的 Agent 列表
        """
        agent_ids = self._categories.get(category, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]
    
    def list_by_capabilities(
        self,
        capabilities: List[AgentCapability],
        match_all: bool = False
    ) -> List[RegisteredAgent]:
        """
        按能力列出 Agent
        
        Args:
            capabilities: 能力列表
            match_all: 是否必须匹配所有能力
            
        Returns:
            List[RegisteredAgent]: 符合条件的 Agent 列表
        """
        if match_all:
            # 所有能力都匹配
            result_ids = set(self._agents.keys())
            for cap in capabilities:
                cap_ids = self._capabilities_index.get(cap, set())
                result_ids &= cap_ids
            return [self._agents[aid] for aid in result_ids if aid in self._agents]
        else:
            # 匹配任一能力
            result_ids = set()
            for cap in capabilities:
                cap_ids = self._capabilities_index.get(cap, set())
                result_ids |= cap_ids
            return [self._agents[aid] for aid in result_ids if aid in self._agents]
    
    def list_by_tags(self, tags: List[str]) -> List[RegisteredAgent]:
        """
        按标签列出 Agent
        
        Args:
            tags: 标签列表
            
        Returns:
            List[RegisteredAgent]: 符合条件的 Agent 列表
        """
        result_ids = set()
        for tag in tags:
            tag_ids = self._tags_index.get(tag, set())
            result_ids |= tag_ids
        return [self._agents[aid] for aid in result_ids if aid in self._agents]
    
    def search(
        self,
        query: str,
        category: Optional[str] = None,
        capabilities: Optional[List[AgentCapability]] = None,
        tags: Optional[List[str]] = None,
        available_only: bool = True
    ) -> List[RegisteredAgent]:
        """
        搜索 Agent
        
        Args:
            query: 搜索关键词（匹配名称和描述）
            category: 类别筛选
            capabilities: 能力筛选
            tags: 标签筛选
            available_only: 仅返回可用的
            
        Returns:
            List[RegisteredAgent]: 符合条件的 Agent 列表
        """
        results = list(self._agents.values())
        
        # 关键词筛选
        if query:
            query_lower = query.lower()
            results = [
                a for a in results
                if query_lower in a.metadata.name.lower()
                or query_lower in a.metadata.description.lower()
            ]
        
        # 类别筛选
        if category:
            results = [a for a in results if a.metadata.category == category]
        
        # 能力筛选
        if capabilities:
            results = [
                a for a in results
                if a.metadata.supports_capabilities(capabilities)
            ]
        
        # 标签筛选
        if tags:
            results = [
                a for a in results
                if any(tag in a.metadata.tags for tag in tags)
            ]
        
        # 可用性筛选
        if available_only:
            results = [a for a in results if a.is_available]
        
        return results
    
    def update_status(self, agent_id: str, status: AgentStatus) -> bool:
        """
        更新 Agent 状态
        
        Args:
            agent_id: Agent ID
            status: 新状态
            
        Returns:
            bool: 是否成功
        """
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        agent.status = status
        return True
    
    def heartbeat(self, agent_id: str) -> bool:
        """
        Agent 心跳
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否成功
        """
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        agent.update_heartbeat()
        return True
    
    def _update_indexes(
        self,
        agent: RegisteredAgent,
        is_add: bool = True
    ) -> None:
        """更新索引"""
        # 类别索引
        category = agent.metadata.category
        if is_add:
            if category not in self._categories:
                self._categories[category] = set()
            self._categories[category].add(agent.metadata.agent_id)
        else:
            if category in self._categories:
                self._categories[category].discard(agent.metadata.agent_id)
        
        # 能力索引
        for cap in agent.metadata.capabilities:
            if is_add:
                if cap not in self._capabilities_index:
                    self._capabilities_index[cap] = set()
                self._capabilities_index[cap].add(agent.metadata.agent_id)
            else:
                if cap in self._capabilities_index:
                    self._capabilities_index[cap].discard(agent.metadata.agent_id)
        
        # 标签索引
        for tag in agent.metadata.tags:
            if is_add:
                if tag not in self._tags_index:
                    self._tags_index[tag] = set()
                self._tags_index[tag].add(agent.metadata.agent_id)
            else:
                if tag in self._tags_index:
                    self._tags_index[tag].discard(agent.metadata.agent_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        total = len(self._agents)
        by_status = {}
        for status in AgentStatus:
            by_status[status.value] = len(self.list_by_status(status))
        
        available = len(self.list_available())
        
        total_requests = sum(a.total_requests for a in self._agents.values())
        total_success = sum(a.successful_requests for a in self._agents.values())
        
        return {
            "total_agents": total,
            "by_status": by_status,
            "available_agents": available,
            "total_requests": total_requests,
            "total_successful_requests": total_success,
            "overall_success_rate": (
                total_success / total_requests if total_requests > 0 else 0.0
            ),
            "categories": list(self._categories.keys()),
            "capabilities_count": len(self._capabilities_index),
        }


# 全局注册表实例
_default_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """获取全局 Agent 注册表"""
    global _default_registry
    if _default_registry is None:
        _default_registry = AgentRegistry()
    return _default_registry
