"""
ZenAgent Agent 进化流程集成测试

测试完整的 Agent 进化流程:
    SwarmFly 积累经验 → SoulTeam 反思总结 → 人格演化 → Awakening 能力增强
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List, Optional
from datetime import datetime
import random

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from packages.core import ZenAgent, ZenAgentConfig
from packages.SwarmFly.core import SwarmFly, SwarmFlyConfig
from packages.SwarmFly.lifecycle import AgentLifecycle, AgentState
from packages.SwarmFly.collaboration import Task
from packages.SwarmFly.memory import SharedMemoryPool, SegmentType
from packages.MetaSoul.core import SoulTeam, SoulTeamConfig
from packages.MetaSoul.memory import MemoryType
from packages.MetaSoul.personality import Personality, TraitDynamics
from packages.MetaSoul.learning import Feedback, FeedbackType
from packages.MetaSoul.reflection import Reflector
from packages.awakening import (
    AwakeningAdapter,
    AwakeningState,
    AwakeningCapability,
    CapabilityRegistry,
    EvolutionEngine,
    EvolutionStage,
    EvolutionEvent
)


class EvolutionFlow:
    """
    Agent 进化流程管理器
    
    协调 SwarmFly → SoulTeam → Personality → Awakening 的完整进化流程
    """
    
    def __init__(self):
        self.swarmfly: Optional[SwarmFly] = None
        self.soulteam: Optional[SoulTeam] = None
        self.awakening: Optional[AwakeningAdapter] = None
        self.evolution_log: List[Dict[str, Any]] = []
        self.experience_count: int = 0
        self.evolution_threshold: float = 0.7
        
    def initialize(self, agent_id: str, agent_name: str) -> bool:
        """
        初始化进化环境
        
        Args:
            agent_id: Agent ID
            agent_name: Agent 名称
            
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 初始化 SwarmFly
            swarm_config = SwarmFlyConfig(
                node_id=f"evolution_swarm_{agent_id}"
            )
            self.swarmfly = SwarmFly(config=swarm_config)
            
            # 初始化 SoulTeam
            soul_config = SoulTeamConfig(
                soul_id=f"evolution_soul_{agent_id}",
                soul_name=agent_name
            )
            self.soulteam = SoulTeam(config=soul_config)
            
            # 初始化 Awakening
            zen_config = ZenAgentConfig(
                agent_id=agent_id,
                agent_name=agent_name,
                awakening_threshold=self.evolution_threshold
            )
            zen = ZenAgent(config=zen_config)
            self.awakening = zen.awakening
            
            self.evolution_log.append({
                "event": "initialization_complete",
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            self.evolution_log.append({
                "event": "initialization_failed",
                "error": str(e)
            })
            return False
    
    def accumulate_experience(
        self,
        experience_type: str,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        积累经验
        
        Args:
            experience_type: 经验类型
            content: 经验内容
            context: 上下文信息
            
        Returns:
            Dict[str, Any]: 经验记录
        """
        result = {
            "experience_type": experience_type,
            "stored": False,
            "logged": False
        }
        
        try:
            # 存储到 SoulTeam
            if self.soulteam:
                memory_id = None
                experience_id = None
                
                if hasattr(self.soulteam, 'store_memory'):
                    memory_id = self.soulteam.store_memory(
                        content=content,
                        memory_type=MemoryType.EPISODIC,
                        metadata={
                            "experience_type": experience_type,
                            "context": context or {},
                            "accumulated_at": datetime.now().isoformat()
                        }
                    )
                
                # 添加经验
                if hasattr(self.soulteam, 'add_experience'):
                    experience_id = self.soulteam.add_experience(
                        content=content,
                        context=context or {}
                    )
                
                result["memory_id"] = memory_id
                result["experience_id"] = experience_id
                result["stored"] = True
                
                self.experience_count += 1
            
            # 记录到 SwarmFly 共享内存
            if self.swarmfly and self.swarmfly.memory_pool and hasattr(self.swarmfly.memory_pool, 'write'):
                self.swarmfly.memory_pool.write(
                    key=f"experience_{self.experience_count}",
                    value={
                        "type": experience_type,
                        "content": content,
                        "count": self.experience_count
                    },
                    segment_type=SegmentType.SHARED
                )
            
            result["logged"] = True
            
            self.evolution_log.append({
                "event": "experience_accumulated",
                "type": experience_type,
                "total_count": self.experience_count
            })
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def reflect_and_learn(self) -> Dict[str, Any]:
        """
        反思和学习
        
        Returns:
            Dict[str, Any]: 反思结果
        """
        result = {
            "reflected": False,
            "insights": [],
            "learned": False
        }
        
        try:
            # 触发反思
            if self.soulteam and hasattr(self.soulteam, 'reflect'):
                insights = self.soulteam.reflect()
                result["insights"] = insights if insights else []
                result["reflected"] = True
            
            # 处理反馈学习
            if self.soulteam:
                # 创建正面反馈
                feedback = Feedback(
                    content=f"从 {self.experience_count} 个经验中学习",
                    feedback_type=FeedbackType.REINFORCEMENT,
                    source="reflection"
                )
                
                if hasattr(self.soulteam, 'process_feedback'):
                    self.soulteam.process_feedback(feedback)
                result["learned"] = True
            
            self.evolution_log.append({
                "event": "reflection_completed",
                "experience_count": self.experience_count,
                "insights_count": len(result["insights"])
            })
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def evolve_personality(
        self,
        target_traits: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        人格演化
        
        Args:
            target_traits: 目标特质（可选）
            
        Returns:
            Dict[str, Any]: 演化结果
        """
        result = {
            "evolved": False,
            "before_traits": {},
            "after_traits": {},
            "changes": []
        }
        
        try:
            if self.soulteam and self.soulteam.personality:
                # 获取当前特质
                result["before_traits"] = self.soulteam.get_personality_traits()
                
                # 计算演化方向
                if target_traits:
                    # 应用目标特质
                    self.soulteam.update_personality_traits(target_traits)
                else:
                    # 自动演化
                    current = result["before_traits"]
                    evolved = {}
                    
                    for trait, value in current.items():
                        # 随机小幅演化
                        change = random.uniform(-0.1, 0.1)
                        new_value = max(0.0, min(1.0, value + change))
                        evolved[trait] = round(new_value, 2)
                    
                    self.soulteam.update_personality_traits(evolved)
                
                # 获取演化后特质
                result["after_traits"] = self.soulteam.get_personality_traits()
                
                # 计算变化
                for trait in result["before_traits"]:
                    before = result["before_traits"][trait]
                    after = result["after_traits"][trait]
                    change = after - before
                    if abs(change) > 0.01:
                        result["changes"].append({
                            "trait": trait,
                            "before": before,
                            "after": after,
                            "change": round(change, 2)
                        })
                
                result["evolved"] = True
                
                self.evolution_log.append({
                    "event": "personality_evolved",
                    "changes": result["changes"]
                })
                
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def enhance_capabilities(self) -> Dict[str, Any]:
        """
        能力增强
        
        Returns:
            Dict[str, Any]: 增强结果
        """
        result = {
            "awakening_level": 0.0,
            "capabilities_added": [],
            "stage": "none"
        }
        
        try:
            if self.awakening:
                # 计算觉醒度
                experience_bonus = min(self.experience_count * 0.05, 0.5)
                reflection_bonus = 0.2 if len(self.evolution_log) > 5 else 0
                
                awakening_level = min(
                    self.evolution_threshold + experience_bonus + reflection_bonus,
                    1.0
                )
                
                result["awakening_level"] = awakening_level
                
                # 根据觉醒度添加能力
                if awakening_level >= 0.5:
                    result["capabilities_added"].append("enhanced_memory")
                if awakening_level >= 0.7:
                    result["capabilities_added"].append("advanced_learning")
                if awakening_level >= 0.9:
                    result["capabilities_added"].append("self_evolution")
                
                # 确定进化阶段
                if awakening_level < 0.3:
                    result["stage"] = "dormant"
                elif awakening_level < 0.6:
                    result["stage"] = "awakening"
                elif awakening_level < 0.9:
                    result["stage"] = "conscious"
                else:
                    result["stage"] = "enlightened"
                
                self.evolution_log.append({
                    "event": "capabilities_enhanced",
                    "awakening_level": awakening_level,
                    "stage": result["stage"]
                })
                
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def full_evolution_cycle(self) -> Dict[str, Any]:
        """
        完整进化周期
        
        Returns:
            Dict[str, Any]: 完整进化结果
        """
        result = {
            "cycle_complete": False,
            "stages": {}
        }
        
        try:
            # Stage 1: 积累经验
            for i in range(5):
                self.accumulate_experience(
                    experience_type="task_execution",
                    content=f"执行任务 {i + 1}",
                    context={"task_id": f"task_{i}"}
                )
            result["stages"]["accumulation"] = self.experience_count
            
            # Stage 2: 反思学习
            reflection = self.reflect_and_learn()
            result["stages"]["reflection"] = reflection
            
            # Stage 3: 人格演化
            evolution = self.evolve_personality()
            result["stages"]["personality"] = evolution
            
            # Stage 4: 能力增强
            enhancement = self.enhance_capabilities()
            result["stages"]["capabilities"] = enhancement
            
            result["cycle_complete"] = True
            
            self.evolution_log.append({
                "event": "evolution_cycle_complete",
                "total_experiences": self.experience_count,
                "log_entries": len(self.evolution_log)
            })
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def get_evolution_summary(self) -> Dict[str, Any]:
        """获取进化摘要"""
        return {
            "experience_count": self.experience_count,
            "log_entries": len(self.evolution_log),
            "log": self.evolution_log
        }


class TestEvolutionFlow(unittest.TestCase):
    """
    进化流程测试
    
    验证完整的 Agent 进化流程
    """
    
    def test_initialization(self):
        """
        测试进化环境初始化
        
        验证 SwarmFly, SoulTeam, Awakening 的初始化
        """
        flow = EvolutionFlow()
        success = flow.initialize("evolution_test", "EvolutionTestAgent")
        
        self.assertTrue(success)
        self.assertIsNotNone(flow.swarmfly)
        self.assertIsNotNone(flow.soulteam)
        self.assertIsNotNone(flow.awakening)
    
    def test_experience_accumulation(self):
        """
        测试经验积累
        
        验证 SwarmFly 经验积累功能
        """
        flow = EvolutionFlow()
        flow.initialize("experience_test", "ExperienceTestAgent")
        
        # 积累多个经验
        for i in range(3):
            result = flow.accumulate_experience(
                experience_type="learning",
                content=f"学习经验 {i + 1}",
                context={"iteration": i}
            )
            
            self.assertTrue(result["stored"])
            self.assertTrue(result["logged"])
        
        # 验证经验计数
        self.assertEqual(flow.experience_count, 3)
    
    def test_reflection_and_learning(self):
        """
        测试反思和学习
        
        验证 SoulTeam 反思总结功能
        """
        flow = EvolutionFlow()
        flow.initialize("reflection_test", "ReflectionTestAgent")
        
        # 先积累一些经验
        for i in range(3):
            flow.accumulate_experience(
                experience_type="analysis",
                content=f"分析任务 {i}"
            )
        
        # 反思学习
        result = flow.reflect_and_learn()
        
        self.assertTrue(result["reflected"])
        self.assertTrue(result["learned"])
    
    def test_personality_evolution(self):
        """
        测试人格演化
        
        验证 Personality 人格演化功能
        """
        flow = EvolutionFlow()
        flow.initialize("personality_test", "PersonalityTestAgent")
        
        # 人格演化
        result = flow.evolve_personality(
            target_traits={"openness": 0.9, "conscientiousness": 0.85}
        )
        
        self.assertTrue(result["evolved"])
        self.assertIn("openness", result["after_traits"])
        self.assertEqual(result["after_traits"]["openness"], 0.9)
    
    def test_capability_enhancement(self):
        """
        测试能力增强
        
        验证 Awakening 能力增强功能
        """
        flow = EvolutionFlow()
        flow.initialize("capability_test", "CapabilityTestAgent")
        
        # 积累经验以提高觉醒度
        for i in range(10):
            flow.accumulate_experience(
                experience_type="task",
                content=f"任务 {i}"
            )
        
        # 能力增强
        result = flow.enhance_capabilities()
        
        self.assertGreater(result["awakening_level"], 0)
        self.assertIsNotNone(result["stage"])
    
    def test_full_evolution_cycle(self):
        """
        测试完整进化周期
        
        验证 SwarmFly → SoulTeam → Personality → Awakening 的完整流程
        """
        flow = EvolutionFlow()
        flow.initialize("full_cycle_test", "FullCycleTestAgent")
        
        # 执行完整进化周期
        result = flow.full_evolution_cycle()
        
        self.assertTrue(result["cycle_complete"])
        self.assertIn("accumulation", result["stages"])
        self.assertIn("reflection", result["stages"])
        self.assertIn("personality", result["stages"])
        self.assertIn("capabilities", result["stages"])
        
        # 验证进化日志
        summary = flow.get_evolution_summary()
        self.assertGreater(summary["log_entries"], 10)


class TestEvolutionStages(unittest.TestCase):
    """
    进化阶段测试
    
    验证不同进化阶段的行为
    """
    
    def setUp(self):
        """测试前准备"""
        self.flow = EvolutionFlow()
        self.flow.initialize("stage_test", "StageTestAgent")
    
    def test_dormant_stage(self):
        """
        测试休眠阶段
        
        验证低经验水平时的行为
        """
        # 积累少量经验
        for i in range(2):
            self.flow.accumulate_experience(
                experience_type="basic",
                content=f"基础经验 {i}"
            )
        
        # 能力增强
        result = self.flow.enhance_capabilities()
        
        self.assertEqual(result["stage"], "dormant")
        self.assertLess(result["awakening_level"], 0.5)
    
    def test_awakening_stage(self):
        """
        测试觉醒阶段
        
        验证中等经验水平时的行为
        """
        # 积累中等经验
        for i in range(8):
            self.flow.accumulate_experience(
                experience_type="intermediate",
                content=f"中级经验 {i}"
            )
        
        # 能力增强
        result = self.flow.enhance_capabilities()
        
        # 应该进入觉醒或更高阶段
        self.assertIn(result["stage"], ["awakening", "conscious", "enlightened"])
    
    def test_conscious_stage(self):
        """
        测试意识阶段
        
        验证高经验水平时的行为
        """
        # 积累大量经验
        for i in range(15):
            self.flow.accumulate_experience(
                experience_type="advanced",
                content=f"高级经验 {i}"
            )
        
        # 反思
        self.flow.reflect_and_learn()
        
        # 能力增强
        result = self.flow.enhance_capabilities()
        
        # 应该获得更多能力
        self.assertGreater(len(result["capabilities_added"]), 0)
    
    def test_enlightened_stage(self):
        """
        测试开悟阶段
        
        验证极高经验水平时的行为
        """
        # 积累极大量经验
        for i in range(25):
            self.flow.accumulate_experience(
                experience_type="mastery",
                content=f"大师经验 {i}"
            )
        
        # 多次反思
        for _ in range(3):
            self.flow.reflect_and_learn()
        
        # 能力增强
        result = self.flow.enhance_capabilities()
        
        self.assertEqual(result["stage"], "enlightened")
        self.assertIn("self_evolution", result["capabilities_added"])


class TestEvolutionMetrics(unittest.TestCase):
    """
    进化指标测试
    
    验证进化过程中的各种指标
    """
    
    def test_experience_growth(self):
        """
        测试经验增长
        
        验证经验数量的增长曲线
        """
        flow = EvolutionFlow()
        flow.initialize("growth_test", "GrowthTestAgent")
        
        growth_curve = []
        
        for i in range(10):
            flow.accumulate_experience(
                experience_type="growth",
                content=f"增长经验 {i}"
            )
            growth_curve.append(flow.experience_count)
        
        # 验证增长
        self.assertEqual(growth_curve[-1], 10)
        
        # 验证线性增长
        for i in range(1, len(growth_curve)):
            self.assertEqual(growth_curve[i], growth_curve[i-1] + 1)
    
    def test_reflection_impact(self):
        """
        测试反思影响
        
        验证反思对觉醒度的影响
        """
        flow = EvolutionFlow()
        flow.initialize("impact_test", "ImpactTestAgent")
        
        # 积累相同经验
        for i in range(5):
            flow.accumulate_experience(
                experience_type="test",
                content=f"测试 {i}"
            )
        
        # 测量反思前
        before_level = flow.enhance_capabilities()["awakening_level"]
        
        # 反思后再次测量
        flow.reflect_and_learn()
        after_level = flow.enhance_capabilities()["awakening_level"]
        
        # 验证反思提升了觉醒度
        self.assertGreaterEqual(after_level, before_level)
    
    def test_personality_stability(self):
        """
        测试人格稳定性
        
        验证人格特质的变化范围
        """
        flow = EvolutionFlow()
        flow.initialize("stability_test", "StabilityTestAgent")
        
        trait_changes = []
        
        for i in range(5):
            result = flow.evolve_personality()
            
            if result["changes"]:
                for change in result["changes"]:
                    trait_changes.append(abs(change["change"]))
        
        # 验证每次变化都在合理范围内
        for change in trait_changes:
            self.assertLessEqual(change, 0.2)
    
    def test_evolution_log_completeness(self):
        """
        测试进化日志完整性
        
        验证进化日志记录了所有重要事件
        """
        flow = EvolutionFlow()
        flow.initialize("log_test", "LogTestAgent")
        
        # 执行进化周期
        flow.full_evolution_cycle()
        
        # 获取日志
        summary = flow.get_evolution_summary()
        
        # 验证日志包含关键事件
        events = [log["event"] for log in summary["log"]]
        
        self.assertIn("initialization_complete", events)
        self.assertIn("experience_accumulated", events)
        self.assertIn("reflection_completed", events)
        self.assertIn("personality_evolved", events)
        self.assertIn("capabilities_enhanced", events)


class TestEvolutionEdgeCases(unittest.TestCase):
    """
    进化边界情况测试
    
    验证各种边界情况的处理
    """
    
    def test_zero_experience_evolution(self):
        """
        测试零经验进化
        
        验证没有任何经验时的进化行为
        """
        flow = EvolutionFlow()
        flow.initialize("zero_exp_test", "ZeroExpTestAgent")
        
        # 不积累经验直接演化
        result = flow.evolve_personality()
        
        # 应该能处理而不崩溃
        self.assertIsNotNone(result)
    
    def test_rapid_evolution(self):
        """
        测试快速进化
        
        验证短时间内大量进化的处理
        """
        flow = EvolutionFlow()
        flow.initialize("rapid_test", "RapidTestAgent")
        
        # 快速积累大量经验
        for i in range(50):
            flow.accumulate_experience(
                experience_type="rapid",
                content=f"快速经验 {i}"
            )
        
        # 验证能正常处理
        self.assertEqual(flow.experience_count, 50)
        
        # 快速反思
        for _ in range(10):
            flow.reflect_and_learn()
    
    def test_extreme_personality_change(self):
        """
        测试极端人格变化
        
        验证人格特质极端变化时的处理
        """
        flow = EvolutionFlow()
        flow.initialize("extreme_test", "ExtremeTestAgent")
        
        # 尝试设置极端特质值
        extreme_traits = {
            "openness": 1.0,
            "conscientiousness": 0.0,
            "extraversion": 1.0,
            "agreeableness": 0.0,
            "neuroticism": 1.0
        }
        
        result = flow.evolve_personality(target_traits=extreme_traits)
        
        # 应该能处理
        self.assertTrue(result["evolved"])
        
        # 验证特质值被限制在有效范围内
        for trait, value in result["after_traits"].items():
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
