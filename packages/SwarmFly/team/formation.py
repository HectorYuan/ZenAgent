"""
编队管理

管理团队的阵型和位置
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime
import threading


class FormationType(Enum):
    """编队类型枚举"""
    FLAT = "flat"               # 扁平结构
    HIERARCHICAL = "hierarchical"  # 层级结构
    CIRCULAR = "circular"       # 环形结构
    STAR = "star"               # 星形结构
    MESH = "mesh"               # 网状结构
    CHAIN = "chain"             # 链式结构
    TREE = "tree"               # 树形结构


@dataclass
class Position:
    """
    位置
    
    表示编队中的位置
    """
    position_id: str
    name: str
    x: float = 0.0  # 虚拟坐标
    y: float = 0.0
    z: float = 0.0
    
    # 连接
    connected_positions: Set[str] = field(default_factory=set)  # 位置 ID
    
    # 角色要求
    required_role: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def coordinates(self) -> Tuple[float, float, float]:
        """获取坐标"""
        return (self.x, self.y, self.z)
    
    def distance_to(self, other: 'Position') -> float:
        """计算到另一个位置的距离"""
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return (dx*dx + dy*dy + dz*dz) ** 0.5
    
    def is_adjacent_to(self, position_id: str) -> bool:
        """检查是否与指定位置相邻"""
        return position_id in self.connected_positions
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "position_id": self.position_id,
            "name": self.name,
            "coordinates": self.coordinates,
            "connected_positions": list(self.connected_positions),
            "required_role": self.required_role,
        }


@dataclass
class Formation:
    """
    编队
    
    定义团队的组织结构
    """
    formation_id: str
    name: str
    formation_type: FormationType
    
    # 位置
    positions: Dict[str, Position] = field(default_factory=dict)
    
    # 位置分配
    assignments: Dict[str, str] = field(default_factory=dict)  # position_id -> agent_id
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def size(self) -> int:
        """编队大小"""
        return len(self.positions)
    
    @property
    def filled_positions(self) -> int:
        """已填充位置"""
        return len(self.assignments)
    
    @property
    def is_full(self) -> bool:
        """是否已满"""
        return self.filled_positions >= self.size
    
    @property
    def available_positions(self) -> List[str]:
        """可用位置"""
        return [pid for pid in self.positions if pid not in self.assignments]
    
    def assign(self, position_id: str, agent_id: str) -> bool:
        """
        分配位置
        
        Args:
            position_id: 位置 ID
            agent_id: Agent ID
            
        Returns:
            bool: 是否成功
        """
        if position_id not in self.positions:
            return False
        
        if position_id in self.assignments:
            return False
        
        self.assignments[position_id] = agent_id
        return True
    
    def unassign(self, position_id: str) -> Optional[str]:
        """
        取消分配
        
        Args:
            position_id: 位置 ID
            
        Returns:
            Optional[str]: 被移除的 Agent ID
        """
        return self.assignments.pop(position_id, None)
    
    def get_position(self, agent_id: str) -> Optional[Position]:
        """获取 Agent 所在位置"""
        for pos_id, ag_id in self.assignments.items():
            if ag_id == agent_id:
                return self.positions.get(pos_id)
        return None
    
    def get_adjacent_agents(self, agent_id: str) -> List[str]:
        """获取相邻的 Agent"""
        position = self.get_position(agent_id)
        if not position:
            return []
        
        adjacent = []
        for pos_id in position.connected_positions:
            if pos_id in self.assignments:
                adjacent.append(self.assignments[pos_id])
        
        return adjacent
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "formation_id": self.formation_id,
            "name": self.name,
            "formation_type": self.formation_type.value,
            "size": self.size,
            "filled_positions": self.filled_positions,
            "positions": [p.to_dict() for p in self.positions.values()],
            "assignments": self.assignments,
        }


class FormationManager:
    """
    编队管理器
    
    管理预定义的编队模板
    """
    
    def __init__(self):
        """初始化管理器"""
        self._formations: Dict[str, Formation] = {}
        self._lock = threading.RLock()
        self._register_default_formations()
    
    def _register_default_formations(self) -> None:
        """注册默认编队"""
        # 扁平结构
        self.register(self._create_flat_formation())
        
        # 层级结构
        self.register(self._create_hierarchical_formation())
        
        # 星形结构
        self.register(self._create_star_formation())
        
        # 环形结构
        self.register(self._create_circular_formation())
        
        # 链式结构
        self.register(self._create_chain_formation())
    
    def _create_flat_formation(self) -> Formation:
        """创建扁平编队"""
        formation = Formation(
            formation_id="flat",
            name="Flat Structure",
            formation_type=FormationType.FLAT,
        )
        
        # 添加位置（所有 Agent 平级）
        for i in range(10):
            pos = Position(
                position_id=f"pos_{i}",
                name=f"Position {i}",
                x=float(i),
                y=0,
                z=0,
            )
            formation.positions[pos.position_id] = pos
        
        # 全连接
        for pos_id1 in formation.positions:
            for pos_id2 in formation.positions:
                if pos_id1 != pos_id2:
                    formation.positions[pos_id1].connected_positions.add(pos_id2)
        
        return formation
    
    def _create_hierarchical_formation(self) -> Formation:
        """创建层级编队"""
        formation = Formation(
            formation_id="hierarchical",
            name="Hierarchical Structure",
            formation_type=FormationType.HIERARCHICAL,
        )
        
        # 层级结构：1 Leader -> 3 Coordinator -> 6 Worker
        positions = [
            # 顶层
            Position("L1", "Leader", 0, 2, 0),
            # 第二层
            Position("C1", "Coordinator 1", -1, 1, 0),
            Position("C2", "Coordinator 2", 0, 1, 0),
            Position("C3", "Coordinator 3", 1, 1, 0),
            # 第三层
            Position("W1", "Worker 1", -1.5, 0, 0),
            Position("W2", "Worker 2", -0.5, 0, 0),
            Position("W3", "Worker 3", 0.5, 0, 0),
            Position("W4", "Worker 4", 1.5, 0, 0),
        ]
        
        for pos in positions:
            formation.positions[pos.position_id] = pos
        
        # 设置连接
        formation.positions["L1"].connected_positions = {"C1", "C2", "C3"}
        formation.positions["C1"].connected_positions = {"L1", "W1", "W2"}
        formation.positions["C2"].connected_positions = {"L1", "W2", "W3"}
        formation.positions["C3"].connected_positions = {"L1", "W3", "W4"}
        formation.positions["W1"].connected_positions = {"C1"}
        formation.positions["W2"].connected_positions = {"C1", "C2"}
        formation.positions["W3"].connected_positions = {"C2", "C3"}
        formation.positions["W4"].connected_positions = {"C3"}
        
        return formation
    
    def _create_star_formation(self) -> Formation:
        """创建星形编队"""
        formation = Formation(
            formation_id="star",
            name="Star Structure",
            formation_type=FormationType.STAR,
        )
        
        # 中心 + 周边
        center = Position("center", "Center", 0, 0, 0)
        formation.positions["center"] = center
        
        for i in range(6):
            angle = i * 60  # 度
            rad = angle * 3.14159 / 180
            x, y = 2 * (1 if i % 2 == 0 else -1) * 0.5, 2 * (i - 3) * 0.3
            
            pos = Position(
                position_id=f"satellite_{i}",
                name=f"Satellite {i}",
                x=x,
                y=y,
                z=0,
            )
            formation.positions[pos.position_id] = pos
            
            # 连接到中心
            pos.connected_positions.add("center")
            center.connected_positions.add(pos.position_id)
        
        return formation
    
    def _create_circular_formation(self) -> Formation:
        """创建环形编队"""
        formation = Formation(
            formation_id="circular",
            name="Circular Structure",
            formation_type=FormationType.CIRCULAR,
        )
        
        count = 8
        radius = 2.0
        
        for i in range(count):
            angle = i * 360 / count
            rad = angle * 3.14159 / 180
            x, y = radius * (1 if i % 2 == 0 else 0.8) * 0.5, radius * (i - count/2) / (count/2) * 0.5
            
            pos = Position(
                position_id=f"node_{i}",
                name=f"Node {i}",
                x=x,
                y=y,
                z=0,
            )
            formation.positions[pos.position_id] = pos
            
            # 连接到相邻节点
            next_id = (i + 1) % count
            prev_id = (i - 1 + count) % count
            pos.connected_positions.add(f"node_{next_id}")
            pos.connected_positions.add(f"node_{prev_id}")
        
        return formation
    
    def _create_chain_formation(self) -> Formation:
        """创建链式编队"""
        formation = Formation(
            formation_id="chain",
            name="Chain Structure",
            formation_type=FormationType.CHAIN,
        )
        
        for i in range(10):
            pos = Position(
                position_id=f"chain_{i}",
                name=f"Chain Node {i}",
                x=float(i),
                y=0,
                z=0,
            )
            formation.positions[pos.position_id] = pos
            
            # 连接相邻节点
            if i > 0:
                pos.connected_positions.add(f"chain_{i-1}")
            if i < 9:
                pos.connected_positions.add(f"chain_{i+1}")
        
        return formation
    
    def register(self, formation: Formation) -> None:
        """注册编队"""
        with self._lock:
            self._formations[formation.formation_id] = formation
    
    def get_formation(self, formation_id: str) -> Optional[Formation]:
        """获取编队"""
        return self._formations.get(formation_id)
    
    def get_all_formations(self) -> List[Formation]:
        """获取所有编队"""
        return list(self._formations.values())
    
    def create_custom_formation(
        self,
        formation_id: str,
        name: str,
        formation_type: FormationType,
        positions: List[Position],
        connections: List[Tuple[str, str]],
    ) -> Formation:
        """
        创建自定义编队
        
        Args:
            formation_id: 编队 ID
            name: 名称
            formation_type: 编队类型
            positions: 位置列表
            connections: 连接列表 [(pos_id1, pos_id2), ...]
            
        Returns:
            Formation: 创建的编队
        """
        formation = Formation(
            formation_id=formation_id,
            name=name,
            formation_type=formation_type,
        )
        
        for pos in positions:
            formation.positions[pos.position_id] = pos
        
        for pos_id1, pos_id2 in connections:
            if pos_id1 in formation.positions and pos_id2 in formation.positions:
                formation.positions[pos_id1].connected_positions.add(pos_id2)
                formation.positions[pos_id2].connected_positions.add(pos_id1)
        
        self.register(formation)
        return formation
