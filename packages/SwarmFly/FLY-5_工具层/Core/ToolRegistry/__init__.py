"""
工具注册中心 (Tool Registry)

提供工具的注册、发现和匹配功能。
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import asyncio

logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """工具状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


class CapabilityLevel(Enum):
    """能力等级"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class Capability:
    """能力描述"""
    name: str
    category: str
    level: CapabilityLevel = CapabilityLevel.BASIC
    description: str = ""
    keywords: List[str] = field(default_factory=list)


@dataclass
class ToolMetadata:
    """工具元数据"""
    tool_id: str
    name: str
    description: str
    version: str
    capabilities: List[Capability] = field(default_factory=list)
    endpoints: List[str] = field(default_factory=list)  # 可用端点
    status: ToolStatus = ToolStatus.ACTIVE
    health_check_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    owner: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_capability(self, capability_name: str) -> bool:
        """检查是否具有指定能力"""
        return any(c.name == capability_name for c in self.capabilities)
    
    def has_category(self, category: str) -> bool:
        """检查是否属于指定类别"""
        return any(c.category == category for c in self.capabilities)


@dataclass
class HealthStatus:
    """健康状态"""
    tool_id: str
    is_healthy: bool
    latency_ms: float = 0.0
    last_check: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None


@dataclass
class DiscoveryResult:
    """发现结果"""
    tool: ToolMetadata
    match_score: float  # 0-1
    match_reasons: List[str] = field(default_factory=list)


class ToolRegistry:
    """
    工具注册中心
    
    功能:
    - 工具注册/注销
    - 能力发现
    - 智能匹配
    - 健康检查
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 工具存储
        self.tools: Dict[str, ToolMetadata] = {}
        
        # 能力索引
        self.capability_index: Dict[str, List[str]] = {}  # capability -> [tool_ids]
        self.category_index: Dict[str, List[str]] = {}  # category -> [tool_ids]
        self.tag_index: Dict[str, List[str]] = {}  # tag -> [tool_ids]
        
        # 健康状态
        self.health_status: Dict[str, HealthStatus] = {}
        
        # 心跳检测任务
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False
        
        # 配置
        self.health_check_interval = self.config.get('health_check_interval', 60)
        self.health_check_timeout = self.config.get('health_check_timeout', 5)
    
    async def start(self):
        """启动注册中心"""
        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Tool registry started")
    
    async def stop(self):
        """停止注册中心"""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        logger.info("Tool registry stopped")
    
    # ==================== 注册管理 ====================
    
    async def register(self, tool: ToolMetadata) -> bool:
        """
        注册工具
        
        Args:
            tool: 工具元数据
            
        Returns:
            bool: 是否成功
        """
        tool.updated_at = datetime.now()
        self.tools[tool.tool_id] = tool
        
        # 更新索引
        self._update_indexes(tool)
        
        # 初始化健康状态
        self.health_status[tool.tool_id] = HealthStatus(
            tool_id=tool.tool_id,
            is_healthy=True
        )
        
        logger.info(f"Tool registered: {tool.tool_id} - {tool.name}")
        return True
    
    async def unregister(self, tool_id: str) -> bool:
        """
        注销工具
        
        Args:
            tool_id: 工具ID
            
        Returns:
            bool: 是否成功
        """
        if tool_id not in self.tools:
            return False
        
        tool = self.tools[tool_id]
        
        # 清理索引
        self._remove_from_indexes(tool)
        
        # 删除工具
        del self.tools[tool_id]
        
        # 删除健康状态
        if tool_id in self.health_status:
            del self.health_status[tool_id]
        
        logger.info(f"Tool unregistered: {tool_id}")
        return True
    
    def update(self, tool_id: str, updates: Dict[str, Any]) -> bool:
        """更新工具信息"""
        if tool_id not in self.tools:
            return False
        
        tool = self.tools[tool_id]
        
        # 更新字段
        for key, value in updates.items():
            if hasattr(tool, key):
                setattr(tool, key, value)
        
        tool.updated_at = datetime.now()
        
        # 重建索引
        self._remove_from_indexes(tool)
        self._update_indexes(tool)
        
        return True
    
    # ==================== 发现 ====================
    
    def discover(
        self,
        capability: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: ToolStatus = ToolStatus.ACTIVE
    ) -> List[ToolMetadata]:
        """
        发现工具
        
        Args:
            capability: 能力名称
            category: 能力类别
            tags: 标签
            status: 状态过滤
            
        Returns:
            List[ToolMetadata]: 匹配的工具列表
        """
        candidate_ids = set(self.tools.keys())
        
        # 按能力过滤
        if capability:
            cap_ids = set(self.capability_index.get(capability, []))
            candidate_ids &= cap_ids
        
        # 按类别过滤
        if category:
            cat_ids = set(self.category_index.get(category, []))
            candidate_ids &= cat_ids
        
        # 按标签过滤
        if tags:
            for tag in tags:
                tag_ids = set(self.tag_index.get(tag, []))
                candidate_ids &= tag_ids
        
        # 获取工具并过滤状态
        results = []
        for tool_id in candidate_ids:
            tool = self.tools[tool_id]
            if status is None or tool.status == status:
                results.append(tool)
        
        return results
    
    def find_capability(self, capability_name: str) -> List[ToolMetadata]:
        """查找具有指定能力的工具"""
        tool_ids = self.capability_index.get(capability_name, [])
        return [self.tools[tid] for tid in tool_ids if tid in self.tools]
    
    # ==================== 匹配 ====================
    
    def match(
        self,
        required_capabilities: List[str],
        preferred_tags: Optional[List[str]] = None,
        max_results: int = 5
    ) -> List[DiscoveryResult]:
        """
        智能匹配工具
        
        Args:
            required_capabilities: 必需的能力列表
            preferred_tags: 偏好的标签
            max_results: 最大结果数
            
        Returns:
            List[DiscoveryResult]: 匹配结果，按得分排序
        """
        results = []
        
        for tool in self.tools.values():
            if tool.status != ToolStatus.ACTIVE:
                continue
            
            # 计算匹配得分
            score, reasons = self._calculate_match_score(
                tool, required_capabilities, preferred_tags
            )
            
            if score > 0:
                results.append(DiscoveryResult(
                    tool=tool,
                    match_score=score,
                    match_reasons=reasons
                ))
        
        # 按得分排序
        results.sort(key=lambda r: r.match_score, reverse=True)
        
        return results[:max_results]
    
    def _calculate_match_score(
        self,
        tool: ToolMetadata,
        required_capabilities: List[str],
        preferred_tags: Optional[List[str]]
    ) -> Tuple[float, List[str]]:
        """计算匹配得分"""
        reasons = []
        score = 0.0
        
        # 能力匹配(最高50分)
        matched_caps = []
        for cap in required_capabilities:
            if tool.has_capability(cap):
                matched_caps.append(cap)
        
        cap_score = len(matched_caps) / len(required_capabilities) * 50 if required_capabilities else 50
        score += cap_score
        
        if matched_caps:
            reasons.append(f"Matches capabilities: {', '.join(matched_caps)}")
        
        # 标签匹配(最高30分)
        if preferred_tags:
            matched_tags = set(tool.tags) & set(preferred_tags)
            tag_score = len(matched_tags) / len(preferred_tags) * 30
            score += tag_score
            
            if matched_tags:
                reasons.append(f"Matches tags: {', '.join(matched_tags)}")
        
        # 健康状态(最高20分)
        health = self.health_status.get(tool.tool_id)
        if health and health.is_healthy:
            score += 20
            reasons.append("Healthy")
        elif health:
            score += 10
            reasons.append("Degraded")
        
        return min(1.0, score / 100), reasons
    
    # ==================== 健康检查 ====================
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while self._running:
            try:
                await self._check_all_health()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def _check_all_health(self):
        """检查所有工具健康状态"""
        tasks = []
        for tool_id, tool in self.tools.items():
            if tool.health_check_url:
                tasks.append(self._check_tool_health(tool))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_tool_health(self, tool: ToolMetadata):
        """检查单个工具健康状态"""
        if not tool.health_check_url:
            return
        
        start = asyncio.get_event_loop().time()
        
        try:
            # 简化实现: 使用aiohttp检查
            async with asyncio.timeout(self.health_check_timeout):
                # 模拟健康检查
                await asyncio.sleep(0.1)
                
                self.health_status[tool.tool_id] = HealthStatus(
                    tool_id=tool.tool_id,
                    is_healthy=True,
                    latency_ms=(asyncio.get_event_loop().time() - start) * 1000
                )
                
        except asyncio.TimeoutError:
            self.health_status[tool.tool_id] = HealthStatus(
                tool_id=tool.tool_id,
                is_healthy=False,
                error="Health check timeout"
            )
        except Exception as e:
            self.health_status[tool.tool_id] = HealthStatus(
                tool_id=tool.tool_id,
                is_healthy=False,
                error=str(e)
            )
    
    def get_health_status(self, tool_id: str) -> Optional[HealthStatus]:
        """获取工具健康状态"""
        return self.health_status.get(tool_id)
    
    # ==================== 辅助方法 ====================
    
    def _update_indexes(self, tool: ToolMetadata):
        """更新索引"""
        # 能力索引
        for cap in tool.capabilities:
            if cap.name not in self.capability_index:
                self.capability_index[cap.name] = []
            if tool.tool_id not in self.capability_index[cap.name]:
                self.capability_index[cap.name].append(tool.tool_id)
            
            if cap.category not in self.category_index:
                self.category_index[cap.category] = []
            if tool.tool_id not in self.category_index[cap.category]:
                self.category_index[cap.category].append(tool.tool_id)
        
        # 标签索引
        for tag in tool.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = []
            if tool.tool_id not in self.tag_index[tag]:
                self.tag_index[tag].append(tool.tool_id)
    
    def _remove_from_indexes(self, tool: ToolMetadata):
        """从索引移除"""
        for cap in tool.capabilities:
            if cap.name in self.capability_index:
                self.capability_index[cap.name] = [
                    tid for tid in self.capability_index[cap.name]
                    if tid != tool.tool_id
                ]
            
            if cap.category in self.category_index:
                self.category_index[cap.category] = [
                    tid for tid in self.category_index[cap.category]
                    if tid != tool.tool_id
                ]
        
        for tag in tool.tags:
            if tag in self.tag_index:
                self.tag_index[tag] = [
                    tid for tid in self.tag_index[tag]
                    if tid != tool.tool_id
                ]
    
    def get_tool(self, tool_id: str) -> Optional[ToolMetadata]:
        """获取工具"""
        return self.tools.get(tool_id)
    
    def list_tools(self, status: Optional[ToolStatus] = None) -> List[ToolMetadata]:
        """列出工具"""
        if status is None:
            return list(self.tools.values())
        return [t for t in self.tools.values() if t.status == status]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            'total_tools': len(self.tools),
            'active_tools': sum(1 for t in self.tools.values() if t.status == ToolStatus.ACTIVE),
            'healthy_tools': sum(1 for h in self.health_status.values() if h.is_healthy),
            'capabilities': len(self.capability_index),
            'categories': len(self.category_index)
        }
