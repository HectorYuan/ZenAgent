"""
技能注册中心
"""
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class SkillStatus(Enum):
    """技能状态"""
    REGISTERED = "registered"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUSPENDED = "suspended"


@dataclass
class SkillMetadata:
    """技能元数据"""
    skill_id: str = field(default_factory=lambda: f"skill_{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    version: str = "1.0"
    author: str = "system"
    tags: List[str] = field(default_factory=list)
    input_params: List[Dict[str, Any]] = field(default_factory=list)
    output_format: str = "json"
    status: SkillStatus = SkillStatus.REGISTERED
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "tags": self.tags,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class Skill:
    """技能定义"""
    metadata: SkillMetadata
    implementation: Optional[Callable] = None
    
    def __call__(self, *args, **kwargs):
        if self.implementation:
            return self.implementation(*args, **kwargs)
        raise NotImplementedError(f"Skill {self.metadata.name} has no implementation")


class SkillRegistry:
    """
    技能注册中心
    
    管理和维护所有技能元数据和实现
    """
    
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.name_index: Dict[str, str] = {}  # name -> skill_id
        self.tag_index: Dict[str, List[str]] = {}  # tag -> [skill_ids]
        self.version_history: Dict[str, List[SkillMetadata]] = {}
    
    def register_skill(self, 
                       name: str,
                       description: str,
                       implementation: Callable,
                       tags: Optional[List[str]] = None,
                       input_params: Optional[List[Dict[str, Any]]] = None,
                       version: str = "1.0",
                       author: str = "system") -> str:
        """
        注册新技能
        
        Args:
            name: 技能名称
            description: 技能描述
            implementation: 技能实现
            tags: 技能标签
            input_params: 输入参数定义
            version: 版本号
            author: 作者
            
        Returns:
            skill_id: 技能ID
        """
        # 检查是否已存在
        if name in self.name_index:
            skill_id = self.name_index[name]
            skill = self.skills[skill_id]
            # 更新版本历史
            self.version_history[skill_id].append(skill.metadata)
            # 更新元数据
            skill.metadata.version = version
            skill.metadata.updated_at = datetime.now()
            skill.metadata.status = SkillStatus.ACTIVE
        else:
            # 创建新技能
            metadata = SkillMetadata(
                name=name,
                description=description,
                tags=tags or [],
                input_params=input_params or [],
                version=version,
                author=author
            )
            skill = Skill(metadata=metadata, implementation=implementation)
            skill_id = metadata.skill_id
            
            # 添加到索引
            self.name_index[name] = skill_id
            self.skills[skill_id] = skill
            self.version_history[skill_id] = [metadata]
            
            # 更新标签索引
            for tag in (tags or []):
                if tag not in self.tag_index:
                    self.tag_index[tag] = []
                self.tag_index[tag].append(skill_id)
        
        return skill_id
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取技能"""
        return self.skills.get(skill_id)
    
    def get_by_name(self, name: str) -> Optional[Skill]:
        """按名称获取技能"""
        skill_id = self.name_index.get(name)
        return self.skills.get(skill_id)
    
    def search_by_tag(self, tag: str) -> List[Skill]:
        """按标签搜索"""
        skill_ids = self.tag_index.get(tag, [])
        return [self.skills[sid] for sid in skill_ids if sid in self.skills]
    
    def search(self, query: str) -> List[Skill]:
        """全文搜索"""
        results = []
        query_lower = query.lower()
        for skill in self.skills.values():
            if (query_lower in skill.metadata.name.lower() or
                query_lower in skill.metadata.description.lower() or
                any(query_lower in tag.lower() for tag in skill.metadata.tags)):
                results.append(skill)
        return results
    
    def list_all(self) -> List[SkillMetadata]:
        """列出所有技能"""
        return [s.metadata for s in self.skills.values()]
    
    def deprecate(self, skill_id: str) -> bool:
        """废弃技能"""
        skill = self.skills.get(skill_id)
        if skill:
            skill.metadata.status = SkillStatus.DEPRECATED
            return True
        return False
