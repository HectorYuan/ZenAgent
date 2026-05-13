"""
学习优化器

课程学习、迁移学习的实现
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
from enum import Enum
import threading


class CurriculumStage(Enum):
    """课程阶段"""
    FOUNDATION = "foundation"      # 基础阶段
    INTERMEDIATE = "intermediate"  # 中级阶段
    ADVANCED = "advanced"           # 高级阶段
    MASTERY = "mastery"             # 精通阶段


@dataclass
class TransferLearningResult:
    """迁移学习结果"""
    source_domain: str
    target_domain: str
    transfer_ratio: float  # 迁移效率
    adapted_knowledge: List[str] = field(default_factory=list)
    new_insights: List[str] = field(default_factory=list)
    performance_delta: float = 0.0


@dataclass
class CurriculumItem:
    """课程项目"""
    item_id: str
    name: str
    description: str
    stage: CurriculumStage
    difficulty: float = 0.5  # 0-1
    prerequisites: List[str] = field(default_factory=list)
    estimated_duration: int = 60  # 分钟
    skills_taught: List[str] = field(default_factory=list)
    completed: bool = False
    mastery_level: float = 0.0  # 0-1
    attempts: int = 0
    last_attempt: Optional[datetime] = None


class LearningOptimizer:
    """
    学习优化器
    
    实现课程学习和迁移学习优化
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化学习优化器
        
        Args:
            config: 配置
        """
        self.config = config or {}
        
        # 课程存储
        self._curriculum: Dict[str, List[CurriculumItem]] = {
            stage.value: [] for stage in CurriculumStage
        }
        
        # 领域知识
        self._domain_knowledge: Dict[str, Dict[str, float]] = {}
        
        # 学习历史
        self._learning_records: List[Dict[str, Any]] = []
        
        # 参数
        self._learning_rate = self.config.get("learning_rate", 0.01)
        self._batch_size = self.config.get("batch_size", 32)
        
        self._lock = threading.RLock()
    
    # ==================== 课程学习 ====================
    
    def create_curriculum(
        self,
        domain: str,
        items: List[CurriculumItem],
    ) -> str:
        """
        创建课程
        
        Args:
            domain: 领域
            items: 课程项目列表
            
        Returns:
            str: 课程 ID
        """
        with self._lock:
            curriculum_id = domain
            
            for item in items:
                self._curriculum[item.stage.value].append(item)
            
            # 初始化领域知识
            if domain not in self._domain_knowledge:
                self._domain_knowledge[domain] = {}
            
            return curriculum_id
    
    def add_curriculum_item(
        self,
        item: CurriculumItem,
    ) -> None:
        """
        添加课程项目
        
        Args:
            item: 课程项目
        """
        with self._lock:
            self._curriculum[item.stage.value].append(item)
    
    def get_next_learning_item(
        self,
        domain: str,
        current_mastery: float = 0.0,
    ) -> Optional[CurriculumItem]:
        """
        获取下一个学习项目
        
        Args:
            domain: 领域
            current_mastery: 当前掌握度
            
        Returns:
            Optional[CurriculumItem]: 下一个学习项目
        """
        with self._lock:
            # 根据当前掌握度确定阶段
            if current_mastery < 0.25:
                target_stages = [CurriculumStage.FOUNDATION]
            elif current_mastery < 0.5:
                target_stages = [
                    CurriculumStage.FOUNDATION,
                    CurriculumStage.INTERMEDIATE,
                ]
            elif current_mastery < 0.75:
                target_stages = [
                    CurriculumStage.INTERMEDIATE,
                    CurriculumStage.ADVANCED,
                ]
            else:
                target_stages = [
                    CurriculumStage.ADVANCED,
                    CurriculumStage.MASTERY,
                ]
            
            # 查找未完成的项目
            for stage in target_stages:
                items = self._curriculum[stage.value]
                for item in items:
                    if not item.completed and item.mastery_level < 0.8:
                        return item
            
            return None
    
    def update_progress(
        self,
        item_id: str,
        performance: float,
    ) -> Tuple[bool, float]:
        """
        更新学习进度
        
        Args:
            item_id: 项目 ID
            performance: 表现 (0-1)
            
        Returns:
            Tuple[bool, float]: (是否完成, 掌握度)
        """
        with self._lock:
            for items in self._curriculum.values():
                for item in items:
                    if item.item_id == item_id:
                        item.attempts += 1
                        item.last_attempt = datetime.now()
                        
                        # 更新掌握度
                        item.mastery_level = (
                            item.mastery_level * 0.7 + performance * 0.3
                        )
                        
                        # 检查是否完成
                        if item.mastery_level >= 0.8:
                            item.completed = True
                            return True, item.mastery_level
                        
                        return False, item.mastery_level
            
            return False, 0.0
    
    def get_curriculum_progress(
        self,
        domain: str,
    ) -> Dict[str, Any]:
        """
        获取课程进度
        
        Args:
            domain: 领域
            
        Returns:
            Dict[str, Any]: 进度信息
        """
        with self._lock:
            total_items = 0
            completed_items = 0
            total_mastery = 0.0
            
            by_stage = {}
            
            for stage in CurriculumStage:
                items = self._curriculum[stage.value]
                stage_total = len(items)
                stage_completed = sum(1 for i in items if i.completed)
                stage_mastery = sum(i.mastery_level for i in items) / max(stage_total, 1)
                
                by_stage[stage.value] = {
                    "total": stage_total,
                    "completed": stage_completed,
                    "mastery": stage_mastery,
                }
                
                total_items += stage_total
                completed_items += stage_completed
                total_mastery += stage_mastery * stage_total
            
            return {
                "total_items": total_items,
                "completed_items": completed_items,
                "progress_rate": completed_items / max(total_items, 1),
                "average_mastery": total_mastery / max(total_items, 1),
                "by_stage": by_stage,
            }
    
    # ==================== 迁移学习 ====================
    
    def analyze_transferability(
        self,
        source_domain: str,
        target_domain: str,
    ) -> float:
        """
        分析迁移能力
        
        Args:
            source_domain: 源领域
            target_domain: 目标领域
            
        Returns:
            float: 迁移能力分数 (0-1)
        """
        with self._lock:
            source_knowledge = self._domain_knowledge.get(source_domain, {})
            target_knowledge = self._domain_knowledge.get(target_domain, {})
            
            if not source_knowledge or not target_knowledge:
                return 0.0
            
            # 计算重叠度
            source_keys = set(source_knowledge.keys())
            target_keys = set(target_knowledge.keys())
            
            if not source_keys:
                return 0.0
            
            overlap = len(source_keys & target_keys)
            union = len(source_keys | target_keys)
            
            if union == 0:
                return 0.0
            
            jaccard_similarity = overlap / union
            
            # 考虑知识水平差异
            level_similarity = 1.0
            for key in source_keys & target_keys:
                level_diff = abs(
                    source_knowledge[key] - target_knowledge[key]
                )
                level_similarity -= level_diff * 0.1
            
            level_similarity = max(0.0, level_similarity)
            
            return (jaccard_similarity + level_similarity) / 2
    
    def transfer_learning(
        self,
        source_domain: str,
        target_domain: str,
        focus_areas: Optional[List[str]] = None,
    ) -> TransferLearningResult:
        """
        执行迁移学习
        
        Args:
            source_domain: 源领域
            target_domain: 目标领域
            focus_areas: 重点领域
            
        Returns:
            TransferLearningResult: 迁移学习结果
        """
        with self._lock:
            # 分析迁移能力
            transferability = self.analyze_transferability(
                source_domain, target_domain
            )
            
            source_knowledge = self._domain_knowledge.get(source_domain, {})
            target_knowledge = self._domain_knowledge.get(
                target_domain, 
                {}
            )
            
            result = TransferLearningResult(
                source_domain=source_domain,
                target_domain=target_domain,
                transfer_ratio=transferability,
            )
            
            # 迁移知识
            if focus_areas:
                keys_to_transfer = [
                    k for k in source_knowledge.keys()
                    if k in focus_areas
                ]
            else:
                keys_to_transfer = source_knowledge.keys()
            
            for key in keys_to_transfer:
                if key in target_knowledge:
                    # 融合知识
                    old_value = target_knowledge[key]
                    new_value = (
                        old_value * (1 - transferability) +
                        source_knowledge[key] * transferability
                    )
                    target_knowledge[key] = new_value
                    result.adapted_knowledge.append(key)
                else:
                    # 迁移新知识
                    target_knowledge[key] = (
                        source_knowledge[key] * transferability
                    )
                    result.adapted_knowledge.append(key)
            
            # 更新领域知识
            self._domain_knowledge[target_domain] = target_knowledge
            
            # 生成洞察
            if transferability > 0.5:
                result.new_insights.append(
                    f"{source_domain} 和 {target_domain} 有较高相似度"
                )
            
            return result
    
    def learn_in_domain(
        self,
        domain: str,
        topic: str,
        knowledge_gain: float,
    ) -> None:
        """
        在领域中学习
        
        Args:
            domain: 领域
            topic: 主题
            knowledge_gain: 知识增益
        """
        with self._lock:
            if domain not in self._domain_knowledge:
                self._domain_knowledge[domain] = {}
            
            current = self._domain_knowledge[domain].get(topic, 0.0)
            self._domain_knowledge[domain][topic] = min(
                1.0, current + knowledge_gain * self._learning_rate
            )
            
            # 记录学习
            self._learning_records.append({
                "domain": domain,
                "topic": topic,
                "knowledge_gain": knowledge_gain,
                "timestamp": datetime.now().isoformat(),
            })
    
    def get_domain_mastery(self, domain: str) -> float:
        """
        获取领域掌握度
        
        Args:
            domain: 领域
            
        Returns:
            float: 掌握度 (0-1)
        """
        knowledge = self._domain_knowledge.get(domain, {})
        if not knowledge:
            return 0.0
        
        return sum(knowledge.values()) / len(knowledge)
    
    def suggest_next_domains(
        self,
        current_domain: str,
        limit: int = 3,
    ) -> List[Tuple[str, float]]:
        """
        建议下一个领域
        
        Args:
            current_domain: 当前领域
            limit: 建议数量
            
        Returns:
            List[Tuple[str, float]]: (领域, 迁移能力)
        """
        with self._lock:
            suggestions = []
            
            for domain in self._domain_knowledge.keys():
                if domain == current_domain:
                    continue
                
                transferability = self.analyze_transferability(
                    current_domain, domain
                )
                
                if transferability > 0.3:
                    suggestions.append((domain, transferability))
            
            # 按迁移能力排序
            suggestions.sort(key=lambda x: x[1], reverse=True)
            
            return suggestions[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total_items = sum(
                len(items) for items in self._curriculum.values()
            )
            completed_items = sum(
                sum(1 for i in items if i.completed)
                for items in self._curriculum.values()
            )
            
            return {
                "total_curriculum_items": total_items,
                "completed_items": completed_items,
                "completion_rate": completed_items / max(total_items, 1),
                "domains": len(self._domain_knowledge),
                "learning_records": len(self._learning_records),
                "learning_rate": self._learning_rate,
                "batch_size": self._batch_size,
            }
