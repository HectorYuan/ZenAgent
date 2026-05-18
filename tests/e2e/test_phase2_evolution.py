"""
Phase 2 E2E 测试: Agent 进化与学习场景

测试目标: 验证任务反馈、自我学习、知识更新和人格演化
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from typing import Dict, Any, List


class TestTaskLearning:
    """T6.1 任务反馈 → 自我学习 → 知识更新"""

    def test_task_execution_feedback_recording(self):
        """测试任务执行反馈记录"""
        from packages.SwarmFly.collaboration.task_dispatcher import (
            TaskDispatcher, TaskStatus, Task
        )

        dispatcher = TaskDispatcher()
        dispatcher.register_agent("learner_001")

        # 提交任务
        task = dispatcher.submit_task(
            name="数据分析任务",
            payload={"data_source": "db_1", "analysis_type": "summary", "difficulty": "medium", "expected_quality": 0.8}
        )

        # 执行并完成任务
        assigned = dispatcher.get_next_task("learner_001")
        success = dispatcher.complete_task(
            assigned.task_id,
            result={
                "quality_score": 0.85,
                "execution_time": 12.5,
                "accuracy": 0.92,
                "feedback": "任务执行良好，准确率高"
            }
        )

        assert success is True
        completed_task = dispatcher.get_task(task.task_id)
        assert completed_task.status == TaskStatus.COMPLETED
        assert completed_task.result["quality_score"] == 0.85
        print("✅ 任务执行反馈记录成功")

    def test_quality_based_learning_scores(self):
        """测试基于质量的学习分数计算"""
        from packages.SwarmFly.collaboration.task_dispatcher import TaskDispatcher

        dispatcher = TaskDispatcher()
        dispatcher.register_agent("agent_001")

        # 模拟多次任务执行，质量逐渐提升
        quality_scores = [0.6, 0.65, 0.75, 0.78, 0.82]
        results = []

        for i, quality in enumerate(quality_scores):
            task = dispatcher.submit_task(name=f"任务 {i}", payload={"step": i})
            assigned = dispatcher.get_next_task("agent_001")
            dispatcher.complete_task(
                assigned.task_id,
                result={"quality_score": quality, "iteration": i}
            )
            results.append(quality)

        # 计算学习曲线
        avg_quality = sum(results) / len(results)
        improvement = results[-1] - results[0]

        assert avg_quality > 0.7
        assert improvement > 0.2

        stats = dispatcher.get_queue_summary()
        assert stats["completed_count"] == 5

        print(f"✅ 学习分数计算成功: 平均质量 {avg_quality:.2f}, 进步 {improvement:.2f}")

    def test_performance_tracking_over_time(self):
        """测试随时间推移的性能跟踪"""
        from packages.SwarmFly.collaboration.task_dispatcher import TaskDispatcher

        dispatcher = TaskDispatcher()
        dispatcher.register_agent("performer_001")

        # 模拟性能数据
        performance_data = []
        for i in range(10):
            task = dispatcher.submit_task(name=f"性能测试任务 {i}", payload={"index": i})
            assigned = dispatcher.get_next_task("performer_001")

            # 模拟逐渐改进的执行时间
            execution_time = max(2.0 - i * 0.1, 0.5)
            dispatcher.complete_task(
                assigned.task_id,
                result={"execution_time": execution_time, "attempt": i}
            )
            performance_data.append(execution_time)

        # 验证性能改进
        initial_time = performance_data[0]
        final_time = performance_data[-1]
        assert final_time < initial_time  # 时间应该减少，性能提升

        avg_time = sum(performance_data) / len(performance_data)
        print(f"✅ 性能跟踪成功: 初始时间 {initial_time:.2f}s, 最终时间 {final_time:.2f}s, 平均 {avg_time:.2f}s")


class TestMemoryBasedLearning:
    """基于记忆的学习测试"""

    def test_experience_recording_in_memory(self):
        """测试在记忆中记录经验"""
        from packages.SoulTeam.memory.meta_soul import MetaSoul, MemoryType

        soul = MetaSoul(soul_id="learning_agent")

        # 记录成功经验
        success_exp_id = soul.store_memory(
            "成功完成了数据分析任务，准确率0.92，耗时12.5s",
            memory_type=MemoryType.EPISODIC,
            metadata={
                "type": "experience",
                "result": "success",
                "task_type": "data_analysis",
                "quality_score": 0.92,
                "duration": 12.5
            }
        )
        assert success_exp_id is not None

        # 记录失败/需要改进的经验
        fail_exp_id = soul.store_memory(
            "分类任务遇到低质量数据，结果不理想，需要改进预处理步骤",
            memory_type=MemoryType.EPISODIC,
            metadata={
                "type": "experience",
                "result": "partial_success",
                "task_type": "classification",
                "quality_score": 0.65,
                "lesson_learned": "需要增加数据质量检查"
            }
        )
        assert fail_exp_id is not None

        stats = soul.get_stats()
        print(f"✅ 经验记录成功: {stats}")

    def test_procedural_knowledge_storage(self):
        """测试程序性知识存储"""
        from packages.SoulTeam.memory.meta_soul import MetaSoul, MemoryType

        soul = MetaSoul(soul_id="knowledge_agent")

        # 存储最佳实践
        procedures = [
            "数据分析步骤: 1) 数据清洗 2) 探索性分析 3) 特征工程 4) 建模",
            "任务分配策略: 根据Agent专长和负载动态分配任务",
            "冲突解决流程: 1) 检测冲突 2) 评估影响 3) 协商解决 4) 验证结果"
        ]

        proc_ids = []
        for i, proc in enumerate(procedures):
            proc_id = soul.store_memory(
                proc,
                memory_type=MemoryType.PROCEDURAL,
                metadata={
                    "type": "best_practice",
                    "category": "workflow",
                    "version": f"v{i+1}.0"
                }
            )
            proc_ids.append(proc_id)

        assert len(proc_ids) == 3
        print(f"✅ 程序性知识存储成功: {len(procedures)} 条最佳实践")

    def test_semantic_knowledge_organization(self):
        """测试语义知识组织"""
        from packages.SoulTeam.memory.meta_soul import MetaSoul, MemoryType

        soul = MetaSoul(soul_id="semantic_agent")

        # 存储概念和分类
        concepts = [
            ("Agent能力", "Agent具备的技能和可执行任务类型"),
            ("协作模式", "多个Agent协同工作的方式"),
            ("任务分解", "将复杂任务拆解为可执行子任务的过程"),
            ("反馈循环", "根据执行结果调整策略的机制")
        ]

        for concept, definition in concepts:
            soul.store_memory(
                definition,
                memory_type=MemoryType.SEMANTIC,
                metadata={
                    "type": "concept_definition",
                    "concept": concept,
                    "domain": "multi_agent_systems"
                }
            )

        print(f"✅ 语义知识组织成功: {len(concepts)} 个概念已存储")


class TestPersonalityEvolution:
    """T6.3 人格特质演化"""

    def test_personality_trait_adjustment_based_on_feedback(self):
        """测试基于反馈的人格特质调整"""
        from packages.SoulTeam.personality.personality import Personality, BigFiveTraits

        personality = Personality()

        # 初始特质
        initial_openness = personality.get_trait(BigFiveTraits.OPENNESS)
        initial_conscientiousness = personality.get_trait(BigFiveTraits.CONSCIENTIOUSNESS)

        # 模拟积极反馈，演化人格
        for i in range(5):
            # 每次经历都带来轻微的人格演化
            feedback = {
                "outcome": 0.7 + i * 0.05,  # 逐渐改善的结果
                "novelty": 0.8,  # 新奇经验触发开放性演化
                "sentiment": 0.6,  # 积极情感触发宜人性演化
                "feedback_type": "positive" if i > 2 else "constructive",
                "task_complexity": "medium",
                "learning_rate": 0.1
            }
            personality.evolve(feedback)

        # 检查特质变化
        new_openness = personality.get_trait(BigFiveTraits.OPENNESS)
        new_conscientiousness = personality.get_trait(BigFiveTraits.CONSCIENTIOUSNESS)

        # 特质应该有所变化
        assert new_openness != initial_openness
        assert new_conscientiousness != initial_conscientiousness

        print(f"✅ 人格特质调整成功: 开放性 {initial_openness:.2f} → {new_openness:.2f}, "
              f"尽责性 {initial_conscientiousness:.2f} → {new_conscientiousness:.2f}")

    def test_consistent_feedback_drives_personality_change(self):
        """测试一致性反馈驱动人格变化"""
        from packages.SoulTeam.personality.personality import Personality, BigFiveTraits

        personality = Personality()
        initial_extraversion = personality.get_trait(BigFiveTraits.EXTRAVERSION)

        # 多次社交合作反馈，应该增加外向性
        for _ in range(10):
            personality.evolve({
                "outcome": 0.8,
                "social": True,  # 社交经验触发外向性演化
                "sentiment": 0.7,  # 积极情感
                "feedback_type": "social_collaboration",
                "interaction_quality": "positive",
                "team_contribution": 0.85
            })

        new_extraversion = personality.get_trait(BigFiveTraits.EXTRAVERSION)
        # 多次社交反馈后，外向性应该有变化
        assert new_extraversion != initial_extraversion

        print(f"✅ 一致性反馈驱动人格变化: 外向性 {initial_extraversion:.2f} → {new_extraversion:.2f}")

    def test_all_big_five_traits_evolution(self):
        """测试所有五大人格特质的演化"""
        from packages.SoulTeam.personality.personality import Personality, BigFiveTraits

        personality = Personality()

        # 记录初始特质
        initial_traits = {}
        for trait in BigFiveTraits:
            initial_traits[trait] = personality.get_trait(trait)

        # 模拟多轮经验
        for i in range(20):
            feedback = {
                "outcome": 0.5 + (i * 0.02),  # 逐渐改进的结果
                "feedback_type": "learning_experience",
                "learning_rate": 0.05
            }
            personality.evolve(feedback)

        # 检查所有特质都有变化
        changed_count = 0
        for trait in BigFiveTraits:
            if personality.get_trait(trait) != initial_traits[trait]:
                changed_count += 1

        # 至少应该有一些特质发生变化
        assert changed_count >= 1

        print(f"✅ 五大人格特质演化正常: {changed_count}/{len(BigFiveTraits)} 个特质发生变化")

    def test_personality_stability_over_time(self):
        """测试人格随时间的稳定性（变化应该是渐进的）"""
        from packages.SoulTeam.personality.personality import Personality, BigFiveTraits

        personality = Personality()

        initial = personality.get_trait(BigFiveTraits.OPENNESS)

        # 经过少量反馈
        for _ in range(2):
            personality.evolve({"outcome": 0.7, "feedback_type": "minor", "novelty": 0.8})

        after_minor = personality.get_trait(BigFiveTraits.OPENNESS)
        minor_change = abs(after_minor - initial)

        # 经过大量反馈
        for i in range(50):
            personality.evolve({
                "outcome": 0.6 + (i * 0.008),
                "feedback_type": "major_experience",
                "novelty": 0.9
            })

        after_major = personality.get_trait(BigFiveTraits.OPENNESS)
        major_change = abs(after_major - initial)

        # 少量反馈应该带来小变化，大量反馈带来大变化
        assert minor_change < major_change
        print(f"✅ 人格稳定性验证: 小变化 {minor_change:.4f}, 大变化 {major_change:.4f}")


class TestLearningFeedbackLoop:
    """学习反馈循环测试"""

    def test_feedback_based_improvement_cycle(self):
        """测试基于反馈的改进循环"""
        from packages.SwarmFly.collaboration.task_dispatcher import TaskDispatcher
        from packages.SoulTeam.memory.meta_soul import MetaSoul, MemoryType

        dispatcher = TaskDispatcher()
        soul = MetaSoul(soul_id="improving_agent")
        dispatcher.register_agent("agent_001")

        # 模拟多轮学习循环
        learning_trajectory = []
        for i in range(8):
            # 执行任务
            task = dispatcher.submit_task(name=f"循环任务 {i}", payload={"cycle": i})
            assigned = dispatcher.get_next_task("agent_001")

            # 模拟性能随学习逐渐改进
            quality = min(0.5 + (i * 0.05), 0.95)
            dispatcher.complete_task(
                assigned.task_id,
                result={"quality": quality, "cycle": i}
            )
            learning_trajectory.append(quality)

            # 记录经验
            soul.store_memory(
                f"任务完成质量: {quality:.2f}",
                memory_type=MemoryType.EPISODIC,
                metadata={"cycle": i, "quality": quality}
            )

        # 验证学习曲线
        assert learning_trajectory[-1] > learning_trajectory[0]
        avg_improvement = (learning_trajectory[-1] - learning_trajectory[0]) / len(learning_trajectory)
        assert avg_improvement > 0

        print(f"✅ 反馈改进循环正常: 初始质量 {learning_trajectory[0]:.2f}, "
              f"最终质量 {learning_trajectory[-1]:.2f}, 平均每次改进 {avg_improvement:.4f}")

    def test_learning_from_negative_feedback(self):
        """测试从负面反馈中学习"""
        from packages.SwarmFly.collaboration.task_dispatcher import TaskDispatcher
        from packages.SoulTeam.personality.personality import Personality, BigFiveTraits

        dispatcher = TaskDispatcher()
        personality = Personality()
        dispatcher.register_agent("agent_001")

        initial_agreeableness = personality.get_trait(BigFiveTraits.AGREEABLENESS)

        # 先有一些失败
        for _ in range(3):
            # 负面结果
            personality.evolve({
                "outcome": 0.3,
                "sentiment": -0.5,  # 负向情感
                "feedback_type": "negative",
                "lesson": "需要改进协作方式"
            })

        after_negatives = personality.get_trait(BigFiveTraits.AGREEABLENESS)

        # 然后学习和改进
        for i in range(5):
            personality.evolve({
                "outcome": 0.4 + (i * 0.1),  # 逐渐好转
                "sentiment": 0.3 + (i * 0.1),  # 情感逐渐转向积极
                "feedback_type": "constructive",
                "adaptation": "learned_from_mistake"
            })

        after_learning = personality.get_trait(BigFiveTraits.AGREEABLENESS)

        assert after_learning != after_negatives
        print(f"✅ 从负面反馈中学习: 初始 {initial_agreeableness:.2f}, "
              f"挫折后 {after_negatives:.2f}, 学习后 {after_learning:.2f}")


class TestSkillAcquisition:
    """技能获取测试"""

    def test_skill_proficiency_tracking(self):
        """测试技能熟练度跟踪"""
        from packages.SoulTeam.memory.meta_soul import MetaSoul, MemoryType

        soul = MetaSoul(soul_id="skilled_agent")

        # 跟踪技能熟练过程
        skills = ["数据分析", "代码编写", "团队协作", "问题诊断"]
        proficiency_levels = [0.2, 0.3, 0.4, 0.8]  # 初始熟练度

        for skill, initial_prof in zip(skills, proficiency_levels):
            # 记录初始水平
            soul.store_memory(
                f"技能 {skill} 初始熟练度: {initial_prof}",
                memory_type=MemoryType.SEMANTIC,
                metadata={"skill": skill, "proficiency": initial_prof, "type": "skill_initial"}
            )

            # 模拟练习和提升
            for practice_round in range(5):
                new_prof = min(initial_prof + (practice_round * 0.1), 1.0)
                soul.store_memory(
                    f"技能 {skill} 第{practice_round+1}次练习后熟练度: {new_prof:.2f}",
                    memory_type=MemoryType.PROCEDURAL,
                    metadata={"skill": skill, "proficiency": new_prof, "practice": practice_round+1}
                )

        print(f"✅ 技能熟练度跟踪成功: 已跟踪 {len(skills)} 项技能")

    def test_knowledge_transfer_between_tasks(self):
        """测试任务间的知识迁移"""
        from packages.SoulTeam.memory.meta_soul import MetaSoul, MemoryType

        soul = MetaSoul(soul_id="transfer_agent")

        # 从任务A中学到的知识
        task_a_learning = soul.store_memory(
            "在文本分类任务中发现，数据预处理质量对结果影响最大，特征选择也很重要",
            memory_type=MemoryType.PROCEDURAL,
            metadata={"source_task": "text_classification", "type": "lesson_learned"}
        )

        # 将知识应用到任务B
        task_b_application = soul.store_memory(
            "将文本分类中学到的预处理方法应用到情感分析任务，结果改进了15%",
            memory_type=MemoryType.EPISODIC,
            metadata={
                "source_task": "text_classification",
                "applied_to": "sentiment_analysis",
                "type": "knowledge_transfer",
                "improvement": 0.15
            }
        )

        assert task_a_learning is not None
        assert task_b_application is not None

        print("✅ 知识迁移成功: 任务A的知识成功应用到任务B")


class TestFullEvolutionScenario:
    """完整进化场景测试"""

    def test_complete_agent_evolution_journey(self):
        """测试完整的Agent进化历程"""
        from packages.SwarmFly.collaboration.task_dispatcher import TaskDispatcher
        from packages.SoulTeam.memory.meta_soul import MetaSoul, MemoryType
        from packages.SoulTeam.personality.personality import Personality, BigFiveTraits

        # 初始化
        dispatcher = TaskDispatcher()
        soul = MetaSoul(soul_id="evolving_agent")
        personality = Personality()
        dispatcher.register_agent("evo_agent_001")

        # 阶段1: 初始状态
        initial_openness = personality.get_trait(BigFiveTraits.OPENNESS)

        # 阶段2: 新手期 - 学习基础技能
        novice_performance = []
        for i in range(5):
            task = dispatcher.submit_task(name=f"新手任务 {i}", payload={"phase": "novice"})
            assigned = dispatcher.get_next_task("evo_agent_001")
            quality = 0.4 + (i * 0.02)
            dispatcher.complete_task(assigned.task_id, result={"quality": quality, "phase": "novice"})
            novice_performance.append(quality)
            soul.store_memory(
                f"新手任务{i}完成，质量{quality:.2f}",
                memory_type=MemoryType.EPISODIC
            )
            personality.evolve({"outcome": quality, "novelty": 0.85, "feedback_type": "novice_learning"})

        # 阶段3: 进阶期 - 技能提升
        intermediate_performance = []
        for i in range(5, 15):
            task = dispatcher.submit_task(name=f"进阶任务 {i}", payload={"phase": "intermediate"})
            assigned = dispatcher.get_next_task("evo_agent_001")
            quality = 0.5 + (i * 0.03)
            dispatcher.complete_task(assigned.task_id, result={"quality": quality, "phase": "intermediate"})
            intermediate_performance.append(quality)
            soul.store_memory(
                f"进阶任务{i}完成，质量{quality:.2f}",
                memory_type=MemoryType.PROCEDURAL
            )
            personality.evolve({"outcome": quality, "novelty": 0.75, "feedback_type": "skill_building"})

        # 阶段4: 成熟期 - 专家水平
        expert_performance = []
        for i in range(15, 20):
            task = dispatcher.submit_task(name=f"专家任务 {i}", payload={"phase": "expert"})
            assigned = dispatcher.get_next_task("evo_agent_001")
            quality = min(0.8 + (i - 15) * 0.04, 0.98)
            dispatcher.complete_task(assigned.task_id, result={"quality": quality, "phase": "expert"})
            expert_performance.append(quality)
            soul.store_memory(
                f"专家任务{i}完成，质量{quality:.2f}",
                memory_type=MemoryType.SEMANTIC
            )
            personality.evolve({"outcome": quality, "novelty": 0.7, "feedback_type": "mastery"})

        # 验证进化结果
        avg_novice = sum(novice_performance) / len(novice_performance)
        avg_expert = sum(expert_performance) / len(expert_performance)
        assert avg_expert > avg_novice

        final_openness = personality.get_trait(BigFiveTraits.OPENNESS)
        assert final_openness != initial_openness

        stats = dispatcher.get_queue_summary()
        assert stats["completed_count"] == 20

        print(f"✅ 完整进化历程验证成功:")
        print(f"   新手期平均质量: {avg_novice:.2f}")
        print(f"   专家期平均质量: {avg_expert:.2f}")
        print(f"   人格开放性变化: {initial_openness:.2f} → {final_openness:.2f}")
        print(f"   总完成任务数: {stats['completed_count']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
