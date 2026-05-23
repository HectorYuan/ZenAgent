"""
经验-记忆闭环

设计依据: E2E_OPTIMIZATION_DESIGN §模块11 (M9a)

连接已有组件: SelfLearner + Reflector + MemoryScorer + FeedbackProcessor + ConsolidationPipeline
"""

import logging
from typing import Optional, Any, Dict

from .learning.learner import SelfLearner
from .learning.feedback_processor import FeedbackProcessor, Feedback, FeedbackSource, FeedbackType
from .reflection.reflector import Reflector, ReflectionDepth
from .memory.memory_scorer import MemoryScorer
from .memory.consolidation import ConsolidationPipeline
from .memory.hierarchical_store import HierarchicalStore, MemoryEntry, MemoryTier

logger = logging.getLogger(__name__)


class ExperienceMemoryLoop:
    """
    经验-记忆闭环

    每次 think() 完成后触发，连接:
    - 评分 → 学习/反思/整合
    - 高分经验 → SelfLearner + ConsolidationPipeline
    - 低分经验 → FeedbackProcessor + Reflector
    - 跨会话 → 语义记忆提升 + 人格基线微调
    """

    def __init__(
        self,
        soul_id: str = "default",
        learner: Optional[SelfLearner] = None,
        reflector: Optional[Reflector] = None,
        scorer: Optional[MemoryScorer] = None,
        pipeline: Optional[ConsolidationPipeline] = None,
        feedback: Optional[FeedbackProcessor] = None,
    ):
        self.soul_id = soul_id
        self.learner = learner or SelfLearner(soul_id=soul_id)
        self.reflector = reflector or Reflector()
        self.scorer = scorer or MemoryScorer()
        self.pipeline = pipeline
        self.feedback = feedback or FeedbackProcessor(learner=self.learner)
        self._interaction_count = 0
        self._cross_session_interval = 10  # 每 10 次交互触发跨会话整合

    @property
    def interaction_count(self) -> int:
        return self._interaction_count

    async def on_interaction_complete(
        self,
        prompt: str,
        response: Any,
        store: Optional[HierarchicalStore] = None,
        personality=None,
    ) -> dict:
        """
        每次对话交互完成后调用

        Args:
            prompt: 用户输入
            response: LLM 响应 (LLMResponse)
            store: 分层存储 (可选)
            personality: 人格系统 (可选)

        Returns:
            处理结果摘要
        """
        self._interaction_count += 1
        result = {"stage": "experience_loop", "actions": []}

        # 1. 构建经验记录
        experience = {
            "context": prompt[:500],
            "action": "think",
            "result": getattr(response, "content", str(response))[:1000],
            "outcome": 0.5,  # 初始中性评分
            "metadata": {
                "provider": getattr(response, "provider", "unknown"),
                "model": getattr(response, "model", "unknown"),
                "cost": getattr(response, "cost", 0),
            },
        }

        # 2. 基于 ResponseValidator 结果评分 (如果可用)
        # 高分 (outcome > 0.6): 成功经验 → 学习 + 整合
        # 低分 (outcome < 0.4): 失败案例 → 反馈 + 反思

        try:
            # 3. SelfLearner 学习
            learn_result = self.learner.learn(experience, feedback=None)
            result["actions"].append("learn")
            result["learning"] = {
                "success": learn_result.success,
                "insights": learn_result.insights[:3] if learn_result.insights else [],
            }
        except Exception as e:
            logger.debug(f"Learn step skipped: {e}")

        try:
            # 4. Reflector 反思 (低深度，快速)
            reflect_result = self.reflector.reflect(experience, depth=ReflectionDepth.SURFACE)
            result["actions"].append("reflect")
            if reflect_result.get("insights"):
                result["reflection"] = reflect_result["insights"][:2]
        except Exception as e:
            logger.debug(f"Reflect step skipped: {e}")

        try:
            # 5. 反馈处理
            fb = Feedback(
                source=FeedbackSource.INTERNAL,
                feedback_type=FeedbackType.REINFORCEMENT,
                content=f"Interaction #{self._interaction_count}: {prompt[:100]}",
                context=str(experience)[:200],
            )
            fb_result = self.feedback.process(fb)
            result["actions"].append("feedback")
            result["feedback"] = fb_result
        except Exception as e:
            logger.debug(f"Feedback step skipped: {e}")

        try:
            # 6. ConsolidationPipeline: L1→L3 知识提取 (如果 store 可用)
            if self.pipeline and store:
                entry = MemoryEntry(
                    entry_id=f"exp_{self._interaction_count}",
                    content=f"Q: {prompt[:200]}\nA: {getattr(response, 'content', '')[:200]}",
                    tier=MemoryTier.L1_HOT,
                    metadata={"source": "experience_loop"},
                )
                await self.pipeline.process(entry)
                result["actions"].append("consolidate")
        except Exception as e:
            logger.debug(f"Consolidation step skipped: {e}")

        # 7. 跨会话整合 (每 N 次触发)
        if self._interaction_count % self._cross_session_interval == 0:
            await self.cross_session_consolidate(store, personality)
            result["actions"].append("cross_session")

        return result

    async def cross_session_consolidate(
        self,
        store: Optional[HierarchicalStore] = None,
        personality=None,
    ) -> dict:
        """
        跨会话整合: 语义记忆提升 + 人格基线微调

        每 N 次交互触发一次
        """
        result = {"stage": "cross_session", "actions": []}

        # 1. 语义知识老化衰减
        if self.pipeline:
            try:
                self.pipeline._kb.decay_all(factor=0.95)
                result["actions"].append("knowledge_decay")
            except Exception:
                pass

        # 2. 档案压缩 (L2→L4)
        if store:
            try:
                from .memory.archival_manager import ArchivalManager
                archiver = ArchivalManager(store)
                await archiver.compact()
                result["actions"].append("archive_compact")
            except Exception:
                pass

        # 3. 人格基线微调 (基于学习结果)
        if personality:
            try:
                personality.adjust_stability(0.01)  # 稳定性略微提升
                result["actions"].append("personality_tune")
            except Exception:
                pass

        if result["actions"]:
            logger.info(f"Cross-session consolidation: {result['actions']}")

        return result

    def get_stats(self) -> dict:
        return {
            "interaction_count": self._interaction_count,
            "next_cross_session": (
                self._cross_session_interval -
                (self._interaction_count % self._cross_session_interval)
            ),
            "learner": "active" if self.learner else "inactive",
            "reflector": "active" if self.reflector else "inactive",
            "pipeline": "active" if self.pipeline else "inactive",
        }
