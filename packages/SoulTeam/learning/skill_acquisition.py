"""
技能获取

模仿学习、强化学习和知识蒸馏的实现
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import threading
import uuid


class SkillLevel(Enum):
    """技能等级"""
    NOVICE = 1      # 新手
    BEGINNER = 2    # 初学者
    COMPETENT = 3   # 胜任
    PROFICIENT = 4  # 熟练
    EXPERT = 5      # 专家


@dataclass
class SkillRecord:
    """技能记录"""
    skill_id: str
    skill_name: str
    description: str
    level: SkillLevel = SkillLevel.NOVICE
    experience_points: float = 0.0
    
    # 学习信息
    learning_method: str = ""  # imitative, reinforcement, discovery
    demonstrations: List[str] = field(default_factory=list)
    practice_sessions: int = 0
    successful_applications: int = 0
    
    # 依赖
    prerequisites: List[str] = field(default_factory=list)
    related_skills: List[str] = field(default_factory=list)
    
    # 状态
    created_at: datetime = field(default_factory=datetime.now)
    last_practiced: Optional[datetime] = None
    last_applied: Optional[datetime] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_experience(self, amount: float) -> None:
        """添加经验值"""
        self.experience_points += amount
        self._update_level()
    
    def _update_level(self) -> None:
        """更新等级"""
        # 经验值阈值
        thresholds = {
            SkillLevel.NOVICE: 0,
            SkillLevel.BEGINNER: 100,
            SkillLevel.COMPETENT: 300,
            SkillLevel.PROFICIENT: 600,
            SkillLevel.EXPERT: 1000,
        }
        
        for level, threshold in sorted(thresholds.items(), key=lambda x: x[1], reverse=True):
            if self.experience_points >= threshold:
                self.level = level
                break
    
    def practice(self, success: bool) -> float:
        """
        练习技能
        
        Args:
            success: 是否成功
            
        Returns:
            float: 获得的经验值
        """
        self.practice_sessions += 1
        self.last_practiced = datetime.now()
        
        # 根据成功率计算经验
        if success:
            exp_gained = 10.0
            self.successful_applications += 1
        else:
            exp_gained = 2.0
        
        self.add_experience(exp_gained)
        return exp_gained


@dataclass
class Demonstration:
    """示范"""
    demo_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    teacher_id: str = ""
    content: str = ""
    steps: List[str] = field(default_factory=list)
    success: bool = True
    rating: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningAttempt:
    """学习尝试"""
    attempt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    skill_id: str = ""
    success: bool = False
    outcome: str = ""
    feedback: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class SkillAcquisition:
    """
    技能获取系统
    
    实现模仿学习、强化学习和知识蒸馏
    """
    
    def __init__(self, knowledge_graph=None):
        """
        初始化技能获取
        
        Args:
            knowledge_graph: 知识图谱
        """
        self.knowledge_graph = knowledge_graph
        
        # 技能存储
        self._skills: Dict[str, SkillRecord] = {}
        
        # 示范存储
        self._demonstrations: Dict[str, Demonstration] = {}
        
        # 学习历史
        self._learning_history: List[LearningAttempt] = []
        
        self._lock = threading.RLock()
    
    # ==================== 模仿学习 ====================
    
    def learn_from_demonstration(
        self,
        skill_name: str,
        demonstration: Demonstration,
    ) -> str:
        """
        从示范中学习
        
        Args:
            skill_name: 技能名称
            demonstration: 示范
            
        Returns:
            str: 技能 ID
        """
        with self._lock:
            # 获取或创建技能
            skill_id = self._get_or_create_skill(skill_name)
            skill = self._skills[skill_id]
            
            # 记录示范
            skill.demonstrations.append(demonstration.demo_id)
            self._demonstrations[demonstration.demo_id] = demonstration
            
            # 设置学习方法
            skill.learning_method = "imitative"
            
            # 从示范中提取知识
            self._extract_from_demonstration(demonstration, skill)
            
            # 给予经验值
            exp_gained = 20.0 * demonstration.rating
            skill.add_experience(exp_gained)
            
            return skill_id
    
    def _extract_from_demonstration(
        self,
        demo: Demonstration,
        skill: SkillRecord,
    ) -> None:
        """从示范中提取知识"""
        # 简单实现：记录步骤
        if demo.steps:
            skill.metadata["demonstrated_steps"] = demo.steps.copy()
        
        # 如果示范成功，增加成功应用
        if demo.success:
            skill.successful_applications += 1
    
    def provide_demonstration(
        self,
        teacher_id: str,
        content: str,
        steps: List[str],
        success: bool = True,
    ) -> Demonstration:
        """
        提供示范
        
        Args:
            teacher_id: 教师 ID
            content: 内容
            steps: 步骤
            success: 是否成功
            
        Returns:
            Demonstration: 示范对象
        """
        demo = Demonstration(
            teacher_id=teacher_id,
            content=content,
            steps=steps,
            success=success,
            rating=1.0 if success else 0.5,
        )
        
        self._demonstrations[demo.demo_id] = demo
        return demo
    
    # ==================== 强化学习 ====================
    
    def reinforce_learning(
        self,
        skill_id: str,
        outcome: float,
    ) -> LearningAttempt:
        """
        强化学习
        
        Args:
            skill_id: 技能 ID
            outcome: 结果 (-1 to 1)
            
        Returns:
            LearningAttempt: 学习尝试
        """
        with self._lock:
            if skill_id not in self._skills:
                raise ValueError(f"Skill {skill_id} not found")
            
            skill = self._skills[skill_id]
            
            # 记录尝试
            attempt = LearningAttempt(
                skill_id=skill_id,
                success=outcome > 0,
                outcome="成功" if outcome > 0 else "失败",
                feedback=outcome,
            )
            self._learning_history.append(attempt)
            
            # 更新技能
            skill.learning_method = "reinforcement"
            
            # 练习
            skill.practice(outcome > 0)
            
            # 根据结果给予额外经验
            if outcome > 0.5:
                skill.add_experience(15.0)
            elif outcome > 0:
                skill.add_experience(5.0)
            elif outcome < -0.5:
                skill.add_experience(-5.0)  # 惩罚
            
            skill.last_applied = datetime.now()
            
            return attempt
    
    def apply_skill(
        self,
        skill_id: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        应用技能
        
        Args:
            skill_id: 技能 ID
            context: 上下文
            
        Returns:
            Dict[str, Any]: 应用结果
        """
        with self._lock:
            if skill_id not in self._skills:
                return {"success": False, "error": "Skill not found"}
            
            skill = self._skills[skill_id]
            
            # 检查前置条件
            for prereq_id in skill.prerequisites:
                if prereq_id not in self._skills:
                    return {
                        "success": False,
                        "error": f"Prerequisite {prereq_id} not met"
                    }
            
            # 根据技能等级决定成功率
            success_rate = {
                SkillLevel.NOVICE: 0.3,
                SkillLevel.BEGINNER: 0.5,
                SkillLevel.COMPETENT: 0.7,
                SkillLevel.PROFICIENT: 0.85,
                SkillLevel.EXPERT: 0.95,
            }
            
            import random
            success = random.random() < success_rate.get(skill.level, 0.5)
            
            # 记录应用
            outcome = 1.0 if success else -1.0
            attempt = self.reinforce_learning(skill_id, outcome)
            
            return {
                "success": success,
                "skill_id": skill_id,
                "skill_level": skill.level.value,
                "attempt_id": attempt.attempt_id,
            }
    
    # ==================== 知识蒸馏 ====================
    
    def distill_knowledge(
        self,
        source_skill_id: str,
        target_skill_id: str,
        transfer_rate: float = 0.5,
    ) -> bool:
        """
        知识蒸馏
        
        将一个技能的知识转移到另一个技能
        
        Args:
            source_skill_id: 源技能 ID
            target_skill_id: 目标技能 ID
            transfer_rate: 转移率
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            if source_skill_id not in self._skills:
                return False
            if target_skill_id not in self._skills:
                return False
            
            source = self._skills[source_skill_id]
            target = self._skills[target_skill_id]
            
            # 转移经验值
            transferred_exp = source.experience_points * transfer_rate
            target.add_experience(transferred_exp * 0.3)  # 经验值折扣
            
            # 复制相关技能关系
            for related_id in source.related_skills:
                if related_id not in target.related_skills:
                    target.related_skills.append(related_id)
            
            # 标记知识来源
            target.metadata["distilled_from"] = source_skill_id
            
            return True
    
    # ==================== 技能管理 ====================
    
    def _get_or_create_skill(self, skill_name: str) -> str:
        """获取或创建技能"""
        # 查找同名技能
        for skill_id, skill in self._skills.items():
            if skill.skill_name == skill_name:
                return skill_id
        
        # 创建新技能
        skill_id = str(uuid.uuid4())
        self._skills[skill_id] = SkillRecord(
            skill_id=skill_id,
            skill_name=skill_name,
            description="",
        )
        
        return skill_id
    
    def register_skill(
        self,
        skill_name: str,
        description: str = "",
        prerequisites: Optional[List[str]] = None,
    ) -> str:
        """
        注册技能
        
        Args:
            skill_name: 技能名称
            description: 描述
            prerequisites: 前置技能
            
        Returns:
            str: 技能 ID
        """
        with self._lock:
            skill_id = self._get_or_create_skill(skill_name)
            skill = self._skills[skill_id]
            skill.description = description
            if prerequisites:
                skill.prerequisites = prerequisites
            
            return skill_id
    
    def get_skill(self, skill_id: str) -> Optional[SkillRecord]:
        """获取技能"""
        return self._skills.get(skill_id)
    
    def get_skill_by_name(self, skill_name: str) -> Optional[SkillRecord]:
        """通过名称获取技能"""
        for skill in self._skills.values():
            if skill.skill_name == skill_name:
                return skill
        return None
    
    def get_skills_by_level(
        self,
        min_level: SkillLevel = SkillLevel.NOVICE,
    ) -> List[SkillRecord]:
        """获取达到一定等级的技能"""
        return [
            s for s in self._skills.values()
            if s.level.value >= min_level.value
        ]
    
    def get_ready_to_learn(
        self,
        available_contexts: List[str],
    ) -> List[SkillRecord]:
        """获取可以开始学习的技能"""
        ready = []
        
        for skill in self._skills.values():
            if skill.level != SkillLevel.NOVICE:
                continue
            
            # 检查前置条件
            prereqs_met = all(
                prereq in self._skills
                for prereq in skill.prerequisites
            )
            
            if prereqs_met:
                ready.append(skill)
        
        return ready
    
    def link_skills(
        self,
        skill_id1: str,
        skill_id2: str,
    ) -> bool:
        """关联两个技能"""
        with self._lock:
            if skill_id1 not in self._skills or skill_id2 not in self._skills:
                return False
            
            skill1 = self._skills[skill_id1]
            skill2 = self._skills[skill_id2]
            
            if skill_id2 not in skill1.related_skills:
                skill1.related_skills.append(skill_id2)
            if skill_id1 not in skill2.related_skills:
                skill2.related_skills.append(skill_id1)
            
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        by_level: Dict[str, int] = {}
        for skill in self._skills.values():
            level_name = skill.level.name
            by_level[level_name] = by_level.get(level_name, 0) + 1
        
        return {
            "total_skills": len(self._skills),
            "by_level": by_level,
            "total_demonstrations": len(self._demonstrations),
            "total_learning_attempts": len(self._learning_history),
            "successful_applications": sum(
                s.successful_applications for s in self._skills.values()
            ),
        }
