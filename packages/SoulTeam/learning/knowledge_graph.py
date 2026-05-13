"""
知识图谱

实体、关系和推理的实现
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
from enum import Enum
import threading
import uuid


class EntityType(Enum):
    """实体类型"""
    CONCEPT = "concept"       # 概念
    OBJECT = "object"         # 对象
    EVENT = "event"          # 事件
    FACT = "fact"            # 事实
    RULE = "rule"            # 规则
    AGENT = "agent"          # Agent


class RelationType(Enum):
    """关系类型"""
    IS_A = "is_a"            # 是...的一种
    PART_OF = "part_of"     # 是...的一部分
    CAUSES = "causes"        # 导致
    ENABLES = "enables"      # 使能
    CONTRADICTS = "contradicts"  # 矛盾
    SIMILAR_TO = "similar_to"    # 类似于
    DEPENDS_ON = "depends_on"    # 取决于
    RELATED_TO = "related_to"    # 相关于


@dataclass
class Entity:
    """实体"""
    entity_id: str
    name: str
    entity_type: EntityType
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    """关系"""
    relation_id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeQuery:
    """知识查询"""
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query_type: str = "general"
    entities: List[str] = field(default_factory=list)
    relations: List[RelationType] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    limit: int = 10


class KnowledgeGraph:
    """
    知识图谱
    
    存储和管理实体、关系及其推理
    """
    
    def __init__(self):
        """初始化知识图谱"""
        self._entities: Dict[str, Entity] = {}
        self._relations: Dict[str, Relation] = {}
        
        # 索引
        self._entity_by_type: Dict[EntityType, Set[str]] = {}
        self._entity_by_name: Dict[str, str] = {}  # name -> entity_id
        self._adjacency: Dict[str, Dict[str, List[str]]] = {}  # entity_id -> relation_type -> [target_ids]
        
        self._lock = threading.RLock()
    
    def add_entity(
        self,
        name: str,
        entity_type: EntityType,
        description: str = "",
        properties: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
    ) -> str:
        """
        添加实体
        
        Args:
            name: 实体名称
            entity_type: 实体类型
            description: 描述
            properties: 属性
            confidence: 置信度
            
        Returns:
            str: 实体 ID
        """
        with self._lock:
            # 检查是否已存在
            if name in self._entity_by_name:
                entity_id = self._entity_by_name[name]
                self.update_entity(entity_id, description, properties)
                return entity_id
            
            entity_id = str(uuid.uuid4())
            
            entity = Entity(
                entity_id=entity_id,
                name=name,
                entity_type=entity_type,
                description=description,
                properties=properties or {},
                confidence=confidence,
            )
            
            self._entities[entity_id] = entity
            self._entity_by_name[name] = entity_id
            
            # 更新类型索引
            if entity_type not in self._entity_by_type:
                self._entity_by_type[entity_type] = set()
            self._entity_by_type[entity_type].add(entity_id)
            
            # 初始化邻接表
            self._adjacency[entity_id] = {}
            
            return entity_id
    
    def update_entity(
        self,
        entity_id: str,
        description: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        confidence_delta: float = 0.0,
    ) -> bool:
        """
        更新实体
        
        Args:
            entity_id: 实体 ID
            description: 新描述
            properties: 新属性
            confidence_delta: 置信度变化
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            if entity_id not in self._entities:
                return False
            
            entity = self._entities[entity_id]
            
            if description is not None:
                entity.description = description
            
            if properties is not None:
                entity.properties.update(properties)
            
            if confidence_delta != 0.0:
                entity.confidence = max(
                    0.0, min(1.0, entity.confidence + confidence_delta)
                )
            
            entity.last_updated = datetime.now()
            return True
    
    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        weight: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        添加关系
        
        Args:
            source_id: 源实体 ID
            target_id: 目标实体 ID
            relation_type: 关系类型
            weight: 权重
            properties: 属性
            
        Returns:
            Optional[str]: 关系 ID
        """
        with self._lock:
            # 检查实体是否存在
            if source_id not in self._entities or target_id not in self._entities:
                return None
            
            relation_id = str(uuid.uuid4())
            
            relation = Relation(
                relation_id=relation_id,
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type,
                weight=weight,
                properties=properties or {},
            )
            
            self._relations[relation_id] = relation
            
            # 更新邻接表
            if relation_type not in self._adjacency[source_id]:
                self._adjacency[source_id][relation_type] = []
            self._adjacency[source_id][relation_type].append(target_id)
            
            return relation_id
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """获取实体"""
        return self._entities.get(entity_id)
    
    def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """通过名称获取实体"""
        entity_id = self._entity_by_name.get(name)
        return self._entities.get(entity_id) if entity_id else None
    
    def get_entities_by_type(
        self,
        entity_type: EntityType,
    ) -> List[Entity]:
        """按类型获取实体"""
        entity_ids = self._entity_by_type.get(entity_type, set())
        return [self._entities[eid] for eid in entity_ids if eid in self._entities]
    
    def get_relations_from(
        self,
        entity_id: str,
        relation_type: Optional[RelationType] = None,
    ) -> List[Relation]:
        """获取从实体出发的关系"""
        relations = []
        for rel in self._relations.values():
            if rel.source_id == entity_id:
                if relation_type is None or rel.relation_type == relation_type:
                    relations.append(rel)
        return relations
    
    def get_relations_to(
        self,
        entity_id: str,
        relation_type: Optional[RelationType] = None,
    ) -> List[Relation]:
        """获取指向实体的关系"""
        relations = []
        for rel in self._relations.values():
            if rel.target_id == entity_id:
                if relation_type is None or rel.relation_type == relation_type:
                    relations.append(rel)
        return relations
    
    def query(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """
        查询知识
        
        Args:
            query: 查询对象
            
        Returns:
            List[Dict[str, Any]]: 查询结果
        """
        with self._lock:
            results = []
            
            # 按实体过滤
            entities = list(self._entities.values())
            if query.entities:
                entities = [
                    e for e in entities
                    if e.entity_id in query.entities or e.name in query.entities
                ]
            
            # 按关系过滤
            for entity in entities[:query.limit]:
                result = {
                    "entity": entity,
                    "outgoing_relations": self.get_relations_from(entity.entity_id),
                    "incoming_relations": self.get_relations_to(entity.entity_id),
                }
                results.append(result)
            
            return results
    
    def traverse(
        self,
        start_id: str,
        relation_types: List[RelationType],
        max_depth: int = 3,
    ) -> List[Tuple[str, str, int]]:
        """
        遍历图
        
        Args:
            start_id: 起始实体 ID
            relation_types: 关系类型列表
            max_depth: 最大深度
            
        Returns:
            List[Tuple[str, str, int]]: (实体ID, 关系类型, 深度)
        """
        with self._lock:
            visited: Set[str] = set()
            results: List[Tuple[str, str, int]] = []
            queue: List[Tuple[str, int]] = [(start_id, 0)]
            
            while queue:
                current_id, depth = queue.pop(0)
                
                if current_id in visited or depth > max_depth:
                    continue
                
                visited.add(current_id)
                
                if depth > 0:
                    results.append((current_id, "", depth))
                
                # 获取邻居
                for rel_type in relation_types:
                    neighbors = self._adjacency.get(current_id, {}).get(rel_type, [])
                    for neighbor_id in neighbors:
                        if neighbor_id not in visited:
                            results.append((neighbor_id, rel_type.value, depth + 1))
                            queue.append((neighbor_id, depth + 1))
            
            return results
    
    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> Optional[List[str]]:
        """
        查找路径
        
        Args:
            source_id: 源实体 ID
            target_id: 目标实体 ID
            max_depth: 最大深度
            
        Returns:
            Optional[List[str]]: 路径（实体 ID 列表）
        """
        with self._lock:
            if source_id == target_id:
                return [source_id]
            
            visited: Set[str] = set()
            queue: List[Tuple[str, List[str]]] = [(source_id, [source_id])]
            
            while queue:
                current_id, path = queue.pop(0)
                
                if len(path) > max_depth:
                    continue
                
                if current_id in visited:
                    continue
                
                visited.add(current_id)
                
                # 遍历所有关系
                for rel in self._relations.values():
                    if rel.source_id == current_id and rel.target_id not in visited:
                        new_path = path + [rel.target_id]
                        
                        if rel.target_id == target_id:
                            return new_path
                        
                        queue.append((rel.target_id, new_path))
            
            return None
    
    def infer(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        推理
        
        基于现有知识进行推理
        
        Args:
            entity_id: 实体 ID
            
        Returns:
            List[Dict[str, Any]]: 推理结果
        """
        with self._lock:
            inferences = []
            
            # 获取实体的 IS_A 关系
            is_a_relations = self.get_relations_from(entity_id, RelationType.IS_A)
            for rel in is_a_relations:
                target = self._entities.get(rel.target_id)
                if target:
                    inferences.append({
                        "type": "generalization",
                        "from": entity_id,
                        "to": rel.target_id,
                        "confidence": rel.confidence,
                    })
            
            # 获取实体的 CAUSES 关系
            causes_relations = self.get_relations_from(entity_id, RelationType.CAUSES)
            for rel in causes_relations:
                target = self._entities.get(rel.target_id)
                if target:
                    inferences.append({
                        "type": "causation",
                        "cause": entity_id,
                        "effect": rel.target_id,
                        "confidence": rel.confidence,
                    })
            
            return inferences
    
    def delete_entity(self, entity_id: str) -> bool:
        """删除实体及其关系"""
        with self._lock:
            if entity_id not in self._entities:
                return False
            
            # 删除相关关系
            relations_to_delete = [
                rid for rid, rel in self._relations.items()
                if rel.source_id == entity_id or rel.target_id == entity_id
            ]
            for rid in relations_to_delete:
                del self._relations[rid]
            
            # 从索引中删除
            entity = self._entities[entity_id]
            self._entity_by_name.pop(entity.name, None)
            self._entity_by_type.get(entity.entity_type, set()).discard(entity_id)
            self._adjacency.pop(entity_id, None)
            
            # 删除实体
            del self._entities[entity_id]
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_entities": len(self._entities),
            "total_relations": len(self._relations),
            "entities_by_type": {
                etype.value: len(eids)
                for etype, eids in self._entity_by_type.items()
            },
            "relations_by_type": {
                rtype.value: len([
                    r for r in self._relations.values()
                    if r.relation_type == rtype
                ])
                for rtype in RelationType
            },
        }
    
    def clear(self) -> None:
        """清空知识图谱"""
        with self._lock:
            self._entities.clear()
            self._relations.clear()
            self._entity_by_type.clear()
            self._entity_by_name.clear()
            self._adjacency.clear()
