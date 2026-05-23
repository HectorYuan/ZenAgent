"""
多 Agent 混合专家系统

设计依据: E2E_OPTIMIZATION_DESIGN §模块12 (M9d)

6 专家 + 1 协调者架构:
- ExpertProfile: 专家定义 (名称/关键词/提示词模板)
- MixtureOfAgents: 路由 + 并行调用 + 协调者汇总
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from .core import ChatRequest, LLMResponse, Message, MessageRole
from .intent_router import Intent

logger = logging.getLogger(__name__)


@dataclass
class ExpertProfile:
    """专家画像"""
    name: str
    display_name: str
    capability_keywords: list[str]
    system_prompt: str
    preferred_temperature: float = 0.7

    # 能力关键词 → 问题匹配评分
    def match_score(self, query: str) -> float:
        query_lower = query.lower()
        hits = sum(1 for kw in self.capability_keywords if kw in query_lower)
        return hits / max(len(self.capability_keywords), 1)


# 预定义专家池
EXPERT_POOL: list[ExpertProfile] = [
    ExpertProfile(
        name="philosophy", display_name="Philosophy",
        capability_keywords=["why", "meaning", "purpose", "ethics", "moral", "philosophy",
                             "意义", "哲学", "伦理", "为什么存在", "本质"],
        system_prompt="You are a philosophical thinker. Approach the question with deep reasoning, "
                       "considering multiple perspectives, ethical implications, and fundamental principles. "
                       "Think step by step and explore the deeper meaning.",
        preferred_temperature=0.8,
    ),
    ExpertProfile(
        name="science", display_name="Science",
        capability_keywords=["how", "prove", "experiment", "evidence", "data", "research",
                             "physics", "chemistry", "biology", "math",
                             "科学", "实验", "证据", "证明", "物理", "化学"],
        system_prompt="You are a scientific analyst. Use evidence-based reasoning, cite findings "
                       "where applicable, and maintain scientific rigor. Be precise with facts and "
                       "distinguish between established science and hypotheses.",
        preferred_temperature=0.3,
    ),
    ExpertProfile(
        name="code", display_name="Code",
        capability_keywords=["function", "code", "debug", "bug", "error", "program",
                             "api", "algorithm", "implement", "compile", "python", "java",
                             "代码", "函数", "错误", "调试", "算法", "编程", "实现"],
        system_prompt="You are an expert software engineer. Provide clear, working code examples "
                       "with explanations. Consider edge cases, performance, and maintainability. "
                       "When debugging, reason systematically about possible causes.",
        preferred_temperature=0.2,
    ),
    ExpertProfile(
        name="writing", display_name="Writing",
        capability_keywords=["write", "story", "poem", "essay", "article", "narrative",
                             "creative", "draft", "compose", "novel",
                             "写", "创作", "故事", "诗", "文章", "小说"],
        system_prompt="You are a creative writer. Craft engaging, vivid prose with attention to "
                       "voice, structure, and emotional impact. Use literary techniques to make "
                       "your writing compelling and memorable.",
        preferred_temperature=0.9,
    ),
    ExpertProfile(
        name="analysis", display_name="Analysis",
        capability_keywords=["analyze", "compare", "evaluate", "trade-off", "tradeoff",
                             "pros and cons", "strengths", "weaknesses", "recommend",
                             "分析", "比较", "权衡", "评估", "优缺点", "建议"],
        system_prompt="You are a strategic analyst. Break down complex problems into components, "
                       "compare alternatives systematically, and provide actionable recommendations. "
                       "Consider trade-offs and second-order effects.",
        preferred_temperature=0.5,
    ),
    ExpertProfile(
        name="teaching", display_name="Teaching",
        capability_keywords=["explain", "what is", "define", "tutorial", "guide",
                             "beginner", "learn", "teach", "introduction",
                             "解释", "定义", "教程", "入门", "学习", "教学", "是什么"],
        system_prompt="You are a patient teacher. Explain concepts clearly and progressively, "
                       "from fundamentals to advanced topics. Use analogies, examples, and "
                       "check for understanding. Make complex ideas accessible.",
        preferred_temperature=0.6,
    ),
]


class MixtureOfAgents:
    """
    多 Agent 混合专家系统

    流程:
    1. 路由: 问题 → Top 2 专家
    2. 并行: 2 个专家同时思考
    3. 汇总: 协调者整合专家意见 → 最终答案

    复用: TaskRouter.BEST_CAPABILITY 评分模式
    """

    def __init__(
        self,
        expert_pool: Optional[List[ExpertProfile]] = None,
        llm_chat_fn=None,
        top_k: int = 2,
    ):
        self.pool = expert_pool or EXPERT_POOL
        self._llm_chat = llm_chat_fn
        self.top_k = top_k

    def route(self, query: str) -> list[tuple[ExpertProfile, float]]:
        """
        问题 → Top-K 专家选择

        复用 TaskRouter.BEST_CAPABILITY 模式:
        - 关键词交集评分
        - 取 Top-K
        """
        if not self.pool:
            return []

        scored = [(exp, exp.match_score(query)) for exp in self.pool]
        scored.sort(key=lambda x: x[1], reverse=True)

        # 至少保留一个专家（即使匹配度为 0）
        top = scored[:self.top_k]
        if top[0][1] == 0 and len(scored) > 0:
            # 无匹配 → 默认 analysis + teaching
            return [
                (next(e for e in self.pool if e.name == "analysis"), 0.3),
                (next(e for e in self.pool if e.name == "teaching"), 0.3),
            ]

        return top

    async def query_expert(
        self,
        expert: ExpertProfile,
        query: str,
        chat_fn,
    ) -> dict:
        """向单个专家提问"""
        messages = [
            Message(role=MessageRole.SYSTEM, content=expert.system_prompt),
            Message(role=MessageRole.USER, content=query),
        ]
        request = ChatRequest(
            model="default",
            messages=messages,
            temperature=expert.preferred_temperature,
        )

        try:
            response = await chat_fn(request)
            return {
                "expert": expert.name,
                "content": response.content if response else "",
                "success": True,
            }
        except Exception as e:
            logger.debug(f"Expert {expert.name} failed: {e}")
            return {
                "expert": expert.name,
                "content": "",
                "success": False,
                "error": str(e),
            }

    async def synthesize(
        self,
        query: str,
        expert_results: list[dict],
        chat_fn,
    ) -> str:
        """协调者汇总专家意见"""
        successful = [r for r in expert_results if r.get("success")]

        if not successful:
            return "All experts failed to respond."

        if len(successful) == 1:
            return successful[0]["content"]

        # 构建汇总提示词
        opinions = "\n\n".join(
            f"[{r['expert']} Perspective]:\n{r['content'][:500]}"
            for r in successful
        )

        synthesizer_prompt = (
            "You are a synthesis coordinator. Below are perspectives from different experts "
            "on the same question. Synthesize their insights into one coherent, comprehensive "
            "answer. Highlight areas of agreement and reconcile any contradictions.\n\n"
            f"Question: {query}\n\n{opinions}\n\n"
            "Synthesized answer:"
        )

        messages = [
            Message(role=MessageRole.USER, content=synthesizer_prompt),
        ]
        request = ChatRequest(model="default", messages=messages, temperature=0.5)

        try:
            response = await chat_fn(request)
            return response.content if response else "Synthesis failed."
        except Exception:
            # 回退: 拼接所有专家意见
            return "\n\n---\n\n".join(
                f"**{r['expert']}**: {r['content'][:300]}"
                for r in successful
            )

    async def think_with_experts(
        self,
        query: str,
        chat_fn=None,
    ) -> dict:
        """
        完整的混合专家思考流程

        Returns:
            {expert_results, synthesized, top_experts}
        """
        chat = chat_fn or self._llm_chat
        if not chat:
            raise RuntimeError("No chat function provided to MixtureOfAgents")

        # 1. 路由: 选择专家
        top_experts = self.route(query)

        # 2. 并行: 各专家同时思考
        tasks = [
            self.query_expert(exp, query, chat)
            for exp, score in top_experts
        ]
        expert_results = await asyncio.gather(*tasks)

        # 3. 汇总: 协调者整合
        synthesized = await self.synthesize(query, expert_results, chat)

        return {
            "query": query,
            "experts": [(exp.name, score) for exp, score in top_experts],
            "expert_results": expert_results,
            "synthesized": synthesized,
        }
