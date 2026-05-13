"""
死锁检测器 (Deadlock Detector)

检测和预防智能体间的资源死锁:
- 等待图分析
- 循环等待检测
- 死锁预防策略
- 死锁恢复机制
"""

import time
import threading
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


class DeadlockState(Enum):
    """死锁状态"""
    NONE = "none"
    SUSPECTED = "suspected"
    DETECTED = "detected"
    RESOLVING = "resolving"
    RESOLVED = "resolved"


@dataclass
class WaitEdge:
    """等待边"""
    from_agent: str  # 等待资源的智能体
    to_agent: str    # 持有资源的智能体
    resource_id: str
    created_at: datetime = field(default_factory=datetime.now)
    wait_time: float = 0.0


@dataclass
class DeadlockInfo:
    """死锁信息"""
    deadlock_id: str
    agents_involved: List[str]
    resources_involved: List[str]
    wait_cycle: List[str]  # 等待循环
    detected_at: datetime
    state: DeadlockState = DeadlockState.DETECTED
    resolution_attempts: int = 0
    resolved_at: Optional[datetime] = None


@dataclass
class DeadlockResolution:
    """死锁解决结果"""
    success: bool
    actions_taken: List[str] = field(default_factory=list)
    affected_agents: List[str] = field(default_factory=list)
    resolution_time_ms: float = 0.0
    message: str = ""


class WaitGraph:
    """等待图"""
    
    def __init__(self):
        # 节点: 智能体ID
        self.nodes: Set[str] = set()
        
        # 边: 从 -> [到...]
        self.edges: Dict[str, List[WaitEdge]] = defaultdict(list)
        
        # 反向边: 到 -> [从...]
        self.reverse_edges: Dict[str, List[WaitEdge]] = defaultdict(list)
    
    def add_edge(self, edge: WaitEdge):
        """添加等待边"""
        self.nodes.add(edge.from_agent)
        self.nodes.add(edge.to_agent)
        self.edges[edge.from_agent].append(edge)
        self.reverse_edges[edge.to_agent].append(edge)
    
    def remove_edge(self, from_agent: str, resource_id: str):
        """移除等待边"""
        edges = self.edges.get(from_agent, [])
        for i, edge in enumerate(edges):
            if edge.resource_id == resource_id:
                edges.pop(i)
                # 也要从反向边移除
                rev_edges = self.reverse_edges.get(edge.to_agent, [])
                rev_edges = [e for e in rev_edges if not (e.from_agent == from_agent and e.resource_id == resource_id)]
                self.reverse_edges[edge.to_agent] = rev_edges
                break
    
    def remove_agent(self, agent_id: str):
        """移除智能体相关所有边"""
        # 移除作为等待者的边
        if agent_id in self.edges:
            for edge in self.edges[agent_id]:
                rev_edges = self.reverse_edges.get(edge.to_agent, [])
                rev_edges = [e for e in rev_edges if e.from_agent != agent_id]
                self.reverse_edges[edge.to_agent] = rev_edges
            del self.edges[agent_id]
        
        # 移除作为持有者的边
        if agent_id in self.reverse_edges:
            for edge in self.reverse_edges[agent_id]:
                from_edges = self.edges.get(edge.from_agent, [])
                from_edges = [e for e in from_edges if e.resource_id != edge.resource_id]
                self.edges[edge.from_agent] = from_edges
            del self.reverse_edges[agent_id]
        
        self.nodes.discard(agent_id)
    
    def has_cycle(self) -> Tuple[bool, List[str]]:
        """检测是否有环(死锁)"""
        # 使用DFS检测环
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for edge in self.edges.get(node, []):
                if edge.to_agent not in visited:
                    if dfs(edge.to_agent):
                        return True
                elif edge.to_agent in rec_stack:
                    # 发现环
                    cycle_start = path.index(edge.to_agent)
                    return True
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        for node in self.nodes:
            if node not in visited:
                if dfs(node):
                    # 返回环路径
                    return True, path
        
        return False, []
    
    def get_cycle(self) -> Optional[List[str]]:
        """获取检测到的环"""
        has_cycle, path = self.has_cycle()
        if has_cycle and path:
            # 提取循环部分
            seen = set()
            cycle = []
            for agent in path:
                if agent in seen:
                    # 从重复节点开始是循环
                    idx = cycle.index(agent)
                    return cycle[idx:] + [agent]
                cycle.append(agent)
                seen.add(agent)
        return None


class DeadlockDetector:
    """
    死锁检测器
    
    功能和特性:
    - 等待图分析
    - 循环等待检测
    - 死锁预防(资源排序等)
    - 死锁恢复(回滚、抢占)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 等待图
        self.wait_graph = WaitGraph()
        
        # 锁
        self.lock = threading.RLock()
        
        # 检测配置
        self.check_interval = self.config.get('check_interval', 5.0)  # 秒
        self.max_wait_time = self.config.get('max_wait_time', 60.0)  # 秒
        self.enable_auto_resolution = self.config.get('enable_auto_resolution', True)
        
        # 检测到的死锁
        self.deadlocks: Dict[str, DeadlockInfo] = {}
        
        # 资源持有关系
        self.resource_holders: Dict[str, str] = {}  # resource_id -> agent_id
        self.agent_waiting_for: Dict[str, Set[str]] = defaultdict(set)  # agent -> {resource_ids}
        
        # 历史记录
        self.resolution_history: List[DeadlockResolution] = []
        
        # 回调
        self.on_deadlock_detected: List[callable] = []
        self.on_deadlock_resolved: List[callable] = []
        
        # 状态
        self.is_running = False
        self._detection_thread: Optional[threading.Thread] = None
    
    def start_detection(self):
        """启动死锁检测"""
        if self.is_running:
            return
        
        self.is_running = True
        self._detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._detection_thread.start()
        logger.info("Deadlock detection started")
    
    def stop_detection(self):
        """停止死锁检测"""
        self.is_running = False
        if self._detection_thread:
            self._detection_thread.join(timeout=5)
        logger.info("Deadlock detection stopped")
    
    def _detection_loop(self):
        """检测循环"""
        while self.is_running:
            try:
                self._check_for_deadlocks()
            except Exception as e:
                logger.error(f"Deadlock detection error: {e}")
            
            time.sleep(self.check_interval)
    
    def request_resource(self, agent_id: str, resource_id: str) -> bool:
        """
        记录资源请求
        
        Args:
            agent_id: 智能体ID
            resource_id: 资源ID
            
        Returns:
            是否可能导致死锁
        """
        with self.lock:
            self.agent_waiting_for[agent_id].add(resource_id)
            
            # 检查资源是否被其他智能体持有
            if resource_id in self.resource_holders:
                holder_id = self.resource_holders[resource_id]
                
                # 添加等待边
                edge = WaitEdge(
                    from_agent=agent_id,
                    to_agent=holder_id,
                    resource_id=resource_id
                )
                self.wait_graph.add_edge(edge)
                
                # 立即检测是否形成死锁
                if self.wait_graph.has_cycle()[0]:
                    logger.warning(f"Potential deadlock detected after request: {agent_id} -> {resource_id}")
                    return True
            
            return False
    
    def release_resource(self, agent_id: str, resource_id: str):
        """释放资源"""
        with self.lock:
            # 移除等待关系
            self.agent_waiting_for[agent_id].discard(resource_id)
            
            # 移除等待边
            self.wait_graph.remove_edge(agent_id, resource_id)
            
            # 更新资源持有关系
            if self.resource_holders.get(resource_id) == agent_id:
                del self.resource_holders[resource_id]
    
    def acquire_resource(self, agent_id: str, resource_id: str):
        """获取资源持有权"""
        with self.lock:
            self.resource_holders[resource_id] = agent_id
    
    def _check_for_deadlocks(self):
        """执行死锁检测"""
        with self.lock:
            # 检查等待超时(可能死锁)
            now = datetime.now()
            for agent_id, resources in list(self.agent_waiting_for.items()):
                for resource_id in resources:
                    # 查找等待边
                    for edge in self.wait_graph.edges.get(agent_id, []):
                        if edge.resource_id == resource_id:
                            edge.wait_time = (now - edge.created_at).total_seconds()
                            
                            if edge.wait_time > self.max_wait_time:
                                logger.warning(
                                    f"Agent {agent_id} waiting for resource {resource_id} "
                                    f"for {edge.wait_time:.1f}s - possible deadlock"
                                )
            
            # 检测等待图中的环
            has_cycle, cycle_path = self.wait_graph.has_cycle()
            
            if has_cycle:
                self._handle_deadlock_detected(cycle_path)
    
    def _handle_deadlock_detected(self, cycle_path: List[str]):
        """处理检测到的死锁"""
        # 生成死锁ID
        deadlock_id = f"DL_{int(time.time() * 1000)}"
        
        # 获取涉及的资源和智能体
        agents = list(set(cycle_path))
        resources = []
        for agent in agents:
            for edge in self.wait_graph.edges.get(agent, []):
                if edge.to_agent in agents:
                    resources.append(edge.resource_id)
        
        resources = list(set(resources))
        
        # 创建死锁信息
        deadlock = DeadlockInfo(
            deadlock_id=deadlock_id,
            agents_involved=agents,
            resources_involved=resources,
            wait_cycle=cycle_path,
            detected_at=datetime.now()
        )
        
        self.deadlocks[deadlock_id] = deadlock
        
        logger.error(
            f"Deadlock detected: {deadlock_id} | "
            f"Agents: {agents} | Resources: {resources}"
        )
        
        # 触发回调
        for callback in self.on_deadlock_detected:
            try:
                callback(deadlock)
            except Exception as e:
                logger.error(f"Deadlock callback error: {e}")
        
        # 自动解决
        if self.enable_auto_resolution:
            self.resolve_deadlock(deadlock_id)
    
    def resolve_deadlock(self, deadlock_id: str) -> Optional[DeadlockResolution]:
        """
        解决死锁
        
        策略:
        1. 选择牺牲者(等待时间最长/优先级最低)
        2. 回滚其操作
        3. 释放其持有的资源
        """
        with self.lock:
            deadlock = self.deadlocks.get(deadlock_id)
            if not deadlock:
                return None
            
            start_time = time.time()
            resolution = DeadlockResolution(success=False)
            
            deadlock.state = DeadlockState.RESOLVING
            
            try:
                # 选择牺牲者
                victim = self._select_victim(deadlock)
                if not victim:
                    resolution.message = "No victim selected"
                    return resolution
                
                resolution.affected_agents.append(victim)
                
                # 释放牺牲者持有的所有资源
                held_resources = [
                    res_id for res_id, holder in self.resource_holders.items()
                    if holder == victim
                ]
                
                for resource_id in held_resources:
                    self.release_resource(victim, resource_id)
                    resolution.actions_taken.append(f"Released {resource_id} from {victim}")
                
                # 更新死锁状态
                deadlock.state = DeadlockState.RESOLVED
                deadlock.resolved_at = datetime.now()
                deadlock.resolution_attempts += 1
                
                resolution.success = True
                resolution.message = f"Resolved by releasing victim {victim}"
                resolution.resolution_time_ms = (time.time() - start_time) * 1000
                
                # 触发解决回调
                for callback in self.on_deadlock_resolved:
                    try:
                        callback(deadlock, resolution)
                    except Exception as e:
                        logger.error(f"Deadlock resolved callback error: {e}")
                
                # 记录历史
                self.resolution_history.append(resolution)
                
                logger.info(f"Deadlock {deadlock_id} resolved: {resolution.message}")
                
            except Exception as e:
                resolution.message = f"Resolution failed: {str(e)}"
                logger.error(f"Deadlock resolution error: {e}")
            
            return resolution
    
    def _select_victim(self, deadlock: DeadlockInfo) -> Optional[str]:
        """选择牺牲者"""
        candidates = deadlock.agents_involved
        
        if not candidates:
            return None
        
        # 选择等待时间最长的智能体
        victim_scores = []
        
        for agent_id in candidates:
            max_wait = 0.0
            for edge in self.wait_graph.edges.get(agent_id, []):
                if edge.wait_time > max_wait:
                    max_wait = edge.wait_time
            
            # 考虑优先级(优先级低的优先被牺牲)
            priority_score = 50  # 默认优先级
            
            # 综合评分(等待时间越长得分为负)
            score = -max_wait + priority_score
            victim_scores.append((agent_id, score, max_wait))
        
        # 选择得分最高的(等待最长，优先级低)
        victim_scores.sort(key=lambda x: x[1])
        
        return victim_scores[0][0] if victim_scores else None
    
    def prevent_deadlock(self, agent_id: str, requested_resources: List[str]) -> bool:
        """
        死锁预防 - 资源排序法
        
        确保智能体按照固定顺序请求资源，避免循环等待
        
        Args:
            agent_id: 智能体ID
            requested_resources: 请求的资源列表
            
        Returns:
            请求是否安全
        """
        with self.lock:
            # 检查是否会产生循环
            requested_resources = sorted(requested_resources)
            
            # 简单检查: 是否已有较低优先级的资源
            for resource_id in requested_resources:
                if resource_id in self.resource_holders:
                    holder = self.resource_holders[resource_id]
                    # 检查是否形成环
                    if holder in self.agent_waiting_for.get(agent_id, set()):
                        return False  # 会形成环
            
            return True
    
    def get_wait_graph(self) -> Dict[str, List[str]]:
        """获取等待图(用于可视化)"""
        with self.lock:
            result = {}
            for from_agent, edges in self.wait_graph.edges.items():
                result[from_agent] = [
                    {"to": edge.to_agent, "resource": edge.resource_id}
                    for edge in edges
                ]
            return result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'active_deadlocks': sum(
                1 for d in self.deadlocks.values()
                if d.state != DeadlockState.RESOLVED
            ),
            'resolved_deadlocks': sum(
                1 for d in self.deadlocks.values()
                if d.state == DeadlockState.RESOLVED
            ),
            'total_resolutions': len(self.resolution_history),
            'is_running': self.is_running,
            'wait_graph_nodes': len(self.wait_graph.nodes),
            'wait_graph_edges': sum(
                len(edges) for edges in self.wait_graph.edges.values()
            )
        }
