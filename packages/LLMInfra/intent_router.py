"""
意图路由器模块

设计依据: M8_P2_INTENT_ROUTING_DESIGN.md

三级联分类 + 五路径分流 + 级联退化
"""

import asyncio
import logging
from typing import List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field

from .core import ChatRequest, Message, MessageRole, LLMResponse

logger = logging.getLogger(__name__)


# ============================================================
# 枚举定义
# ============================================================

class Intent(str, Enum):
    """意图类别（扩展为6类）"""
    SIMPLE_QA = "simple_qa"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    TOOL_CALLING = "tool_calling"
    GENERAL_REASONING = "general_reasoning"
    COMPLEX_REASONING = "complex_reasoning"
    CREATIVE_WRITING = "creative_writing"


class RoutePath(str, Enum):
    """执行路径"""
    FAST = "fast"            # 缓存→小模型→升级Deep
    RAG = "rag"              # 知识库检索增强
    TOOL = "tool"            # 工具调用流程
    DEEP = "deep"            # 大模型 + CoT
    FALLBACK = "fallback"    # 兜底响应


@dataclass
class ClassifyResult:
    """分类结果"""
    intent: Intent
    confidence: float        # 0.0 ~ 1.0
    level: int               # 1=L1规则, 2=L2 LLM, 3=L3 Embedding
    path: RoutePath
    metadata: dict = field(default_factory=dict)

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.85


@dataclass
class RouteResult:
    """路由执行结果"""
    response: Optional[LLMResponse]
    path: RoutePath
    intent: Intent
    classify_result: ClassifyResult
    degradation_path: Optional[RoutePath] = None  # 退化路径
    duration_ms: float = 0.0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.response is not None


# ============================================================
# L1 规则快速分类器（增强版）
# ============================================================

class L1RuleClassifier:
    """
    L1 规则快速分类器

    增强点：
    - 从 4 类扩展到 6 类
    - 置信度评分（非固定 1.0）
    - 模式匹配（代码/工具调用/检索）
    - 长度分位数动态阈值
    """

    # ---- 每类关键词 ----
    SIMPLE_QA_KEYWORDS = {
        "what", "how", "when", "where", "who", "which",
        "什么是", "怎么", "如何", "什么", "为什么", "哪里", "谁",
        "define", "definition", "meaning", "explain briefly",
        "含义", "定义", "解释一下",
    }

    KNOWLEDGE_KEYWORDS = {
        "wiki", "wikipedia", "百度百科", "encyclopedia", "百科",
        "文献", "论文", "reference", "citation",
        "事实", "历史", "成立于", "founder", "established",
        "population", "capital", "人口", "首都",
    }

    TOOL_PATTERNS = {
        # 代码检测
        "```", "def ", "class ", "import ", "function",
        "error traceback", "stack trace", "exception",
        # API/工具调用模式
        "call api", "execute", "run command", "deploy",
        "api endpoint", "http request",
        # 中英文
        "代码", "函数", "错误", "报错", "调试",
    }

    COMPLEX_KEYWORDS = {
        "analyze", "compare", "evaluate", "reason", "prove",
        "optimize", "trade-off", "tradeoff", "design system",
        "architecture", "multi-step", "step by step",
        "分析", "比较", "推理", "证明", "优化", "权衡", "设计系统",
        "架构", "重构", "多步骤",
    }

    CREATIVE_KEYWORDS = {
        "write a", "write an", "compose", "draft", "create story",
        "poem", "essay", "article", "script",
        "写一篇", "创作", "写一首", "编一个", "写个故事",
    }

    GENERAL_KEYWORDS = {
        "how to", "what is", "describe", "summarize", "translate",
        "explain", "list", "tell me about", "overview",
        "怎么", "如何", "概述", "描述", "翻译", "总结", "列举",
    }

    def classify(self, messages: List[Message]) -> ClassifyResult:
        """
        L1 规则分类

        Returns:
            ClassifyResult with intent, confidence, path
        """
        if not messages:
            return ClassifyResult(
                intent=Intent.SIMPLE_QA, confidence=1.0, level=1,
                path=RoutePath.FAST
            )

        # 提取最后一条用户消息和总文本
        last_user = self._last_user_content(messages)
        total_chars = sum(len(m.content) for m in messages)

        # 1. 工具调用检测（模式匹配优先）
        tool_score = self._check_tool_pattern(last_user)
        if tool_score >= 2:
            return ClassifyResult(
                intent=Intent.TOOL_CALLING,
                confidence=min(0.9 + tool_score * 0.03, 1.0),
                level=1, path=RoutePath.TOOL
            )

        # 2. 创意写作检测
        creative_score = self._match_keywords(
            last_user, self.CREATIVE_KEYWORDS
        )
        if creative_score >= 1 and total_chars > 100:
            confidence = min(0.75 + creative_score * 0.08 + min(total_chars / 3000, 0.1), 1.0)
            return ClassifyResult(
                intent=Intent.CREATIVE_WRITING,
                confidence=confidence, level=1, path=RoutePath.DEEP
            )

        # 3. 复杂推理检测
        complex_score = self._match_keywords(
            last_user, self.COMPLEX_KEYWORDS
        )
        if complex_score >= 1:
            confidence = min(0.75 + complex_score * 0.08 + min(total_chars / 3000, 0.1), 1.0)
            return ClassifyResult(
                intent=Intent.COMPLEX_REASONING,
                confidence=confidence, level=1, path=RoutePath.DEEP
            )

        # 4. 长度启发：超长文本 → 复杂推理
        if total_chars > 3000:
            return ClassifyResult(
                intent=Intent.COMPLEX_REASONING,
                confidence=0.85, level=1, path=RoutePath.DEEP
            )

        # 5. 知识检索检测
        knowledge_score = self._match_keywords(
            last_user, self.KNOWLEDGE_KEYWORDS
        )
        if knowledge_score >= 1:
            return ClassifyResult(
                intent=Intent.KNOWLEDGE_RETRIEVAL,
                confidence=min(0.7 + knowledge_score * 0.1, 0.95),
                level=1, path=RoutePath.RAG
            )

        # 6. 一般问答检测
        general_score = self._match_keywords(
            last_user, self.GENERAL_KEYWORDS
        )
        if general_score >= 1:
            return ClassifyResult(
                intent=Intent.GENERAL_REASONING,
                confidence=min(0.6 + general_score * 0.15, 0.9),
                level=1, path=RoutePath.FAST
            )

        # 7. 默认：简单问答
        simple_score = self._match_keywords(
            last_user, self.SIMPLE_QA_KEYWORDS
        )
        confidence = min(0.5 + simple_score * 0.15 + min(total_chars / 1000, 0.2), 0.95)
        return ClassifyResult(
            intent=Intent.SIMPLE_QA,
            confidence=confidence, level=1, path=RoutePath.FAST
        )

    @staticmethod
    def _last_user_content(messages: List[Message]) -> str:
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                return msg.content.lower()
        return ""

    @staticmethod
    def _match_keywords(text: str, keywords: set) -> int:
        """返回命中关键词数"""
        return sum(1 for kw in keywords if kw in text)

    @staticmethod
    def _check_tool_pattern(text: str) -> int:
        """检测工具/代码模式，返回命中数"""
        score = 0
        patterns = [
            ("```", 2),           # 代码块标记，权重 2
            ("def ", 1),
            ("class ", 1),
            ("import ", 1),
            ("function", 1),
            ("err", 1),           # error/Error/ImportError 等变体
            ("exception", 1),
            ("traceback", 1),
            ("api", 1),
            ("代码", 1),
            ("函数", 1),
            ("错误", 1),
            ("报错", 1),
        ]
        for pattern, weight in patterns:
            if pattern in text:
                score += weight
        return score


# ============================================================
# PathDispatcher — 五路径分发 + 级联退化
# ============================================================

class PathDispatcher:
    """
    路径分发器

    五路径 + 级联退化:
    - FastPath: 缓存 → 小模型 → 升级 DeepPath
    - RAGPath: 知识库检索 → 降级 DeepPath
    - ToolPath: 工具调用 → 降级 DeepPath
    - DeepPath: 大模型 + CoT → 降级 FallbackPath
    - FallbackPath: 兜底响应
    """

    # 意图→路径映射
    INTENT_PATH_MAP = {
        Intent.SIMPLE_QA: RoutePath.FAST,
        Intent.GENERAL_REASONING: RoutePath.FAST,
        Intent.KNOWLEDGE_RETRIEVAL: RoutePath.RAG,
        Intent.TOOL_CALLING: RoutePath.TOOL,
        Intent.COMPLEX_REASONING: RoutePath.DEEP,
        Intent.CREATIVE_WRITING: RoutePath.DEEP,
    }

    def __init__(self):
        pass

    @staticmethod
    def get_path(intent: Intent) -> RoutePath:
        """根据意图获取默认路径"""
        return PathDispatcher.INTENT_PATH_MAP.get(intent, RoutePath.FAST)

    def get_degradation_path(self, path: RoutePath) -> RoutePath:
        """获取退化路径"""
        degradation = {
            RoutePath.FAST: RoutePath.DEEP,       # Fast 失败 → Deep
            RoutePath.RAG: RoutePath.DEEP,        # RAG 失败 → Deep
            RoutePath.TOOL: RoutePath.DEEP,       # Tool 失败 → Deep
            RoutePath.DEEP: RoutePath.FALLBACK,   # Deep 失败 → Fallback
            RoutePath.FALLBACK: RoutePath.FALLBACK,  # Fallback 最终
        }
        return degradation.get(path, RoutePath.FALLBACK)

    def dispatch(self, classify_result: ClassifyResult) -> RoutePath:
        """根据分类结果确定执行路径"""
        path = classify_result.path or self.get_path(classify_result.intent)
        return path


# ============================================================
# IntentRouter — 统一路由入口
# ============================================================

@dataclass
class RouterStats:
    """路由器统计"""
    total_requests: int = 0
    l1_only_count: int = 0         # L1 高置信度直接分流
    l2_triggered_count: int = 0    # 触发 L2 精分类
    l3_used_count: int = 0         # 使用 L3 分类
    fast_path_count: int = 0
    deep_path_count: int = 0
    rag_path_count: int = 0
    tool_path_count: int = 0
    fallback_count: int = 0
    degradation_count: int = 0     # 路径退化次数
    total_duration_ms: float = 0.0

    @property
    def avg_duration_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_duration_ms / self.total_requests


class IntentRouter:
    """
    意图路由器

    路由流程：
    1. L1 分类 → 高置信度直接分流
    2. L1 低置信度 → 默认路径执行，L2 并行追赶
    3. dispatch -> execute -> 返回
    """

    L2_TIMEOUT = 0.03  # L2 追赶窗口 30ms（延迟专家建议 #1）

    def __init__(self):
        self.l1 = L1RuleClassifier()
        self.dispatcher = PathDispatcher()
        self._stats = RouterStats()

    @property
    def stats(self) -> dict:
        return {
            "total_requests": self._stats.total_requests,
            "l1_only_count": self._stats.l1_only_count,
            "l2_triggered_count": self._stats.l2_triggered_count,
            "fast_path": self._stats.fast_path_count,
            "deep_path": self._stats.deep_path_count,
            "rag_path": self._stats.rag_path_count,
            "tool_path": self._stats.tool_path_count,
            "fallback": self._stats.fallback_count,
            "degradations": self._stats.degradation_count,
            "avg_duration_ms": round(self._stats.avg_duration_ms, 2),
        }

    def classify(self, messages: List[Message]) -> ClassifyResult:
        """执行意图分类（L1 only，L2/L3 由外部触发）"""
        result = self.l1.classify(messages)
        self._stats.total_requests += 1

        if result.is_high_confidence:
            self._stats.l1_only_count += 1
        else:
            self._stats.l2_triggered_count += 1

        # 确保 path 非空
        if not result.path:
            result.path = self.dispatcher.get_path(result.intent)

        return result

    def _record_path(self, path: RoutePath):
        if path == RoutePath.FAST:
            self._stats.fast_path_count += 1
        elif path == RoutePath.DEEP:
            self._stats.deep_path_count += 1
        elif path == RoutePath.RAG:
            self._stats.rag_path_count += 1
        elif path == RoutePath.TOOL:
            self._stats.tool_path_count += 1
        elif path == RoutePath.FALLBACK:
            self._stats.fallback_count += 1

    async def execute_path(
        self,
        path: RoutePath,
        request: ChatRequest,
        fast_executor=None,
        deep_executor=None,
        rag_executor=None,
        tool_executor=None,
        fallback_executor=None,
    ) -> RouteResult:
        """
        执行指定路径，失败时自动级联退化
        """
        current_path = path
        intent = Intent.SIMPLE_QA  # 默认
        degradation = None

        # 级联退化链
        max_hops = 3
        for hop in range(max_hops):
            try:
                self._record_path(current_path)

                if current_path == RoutePath.FAST and fast_executor:
                    response = await fast_executor(request)
                    return RouteResult(
                        response=response, path=RoutePath.FAST,
                        intent=intent, classify_result=ClassifyResult(
                            intent=intent, confidence=1.0, level=0,
                            path=RoutePath.FAST
                        ),
                        degradation_path=degradation
                    )

                elif current_path == RoutePath.DEEP and deep_executor:
                    response = await deep_executor(request)
                    return RouteResult(
                        response=response, path=RoutePath.DEEP,
                        intent=intent, classify_result=ClassifyResult(
                            intent=intent, confidence=1.0, level=0,
                            path=RoutePath.DEEP
                        ),
                        degradation_path=degradation
                    )

                elif current_path == RoutePath.RAG and rag_executor:
                    response = await rag_executor(request)
                    return RouteResult(
                        response=response, path=RoutePath.RAG,
                        intent=intent, classify_result=ClassifyResult(
                            intent=intent, confidence=1.0, level=0,
                            path=RoutePath.RAG
                        ),
                        degradation_path=degradation
                    )

                elif current_path == RoutePath.TOOL and tool_executor:
                    response = await tool_executor(request)
                    return RouteResult(
                        response=response, path=RoutePath.TOOL,
                        intent=intent, classify_result=ClassifyResult(
                            intent=intent, confidence=1.0, level=0,
                            path=RoutePath.TOOL
                        ),
                        degradation_path=degradation
                    )

                elif current_path == RoutePath.FALLBACK and fallback_executor:
                    response = await fallback_executor(request)
                    return RouteResult(
                        response=response, path=RoutePath.FALLBACK,
                        intent=intent, classify_result=ClassifyResult(
                            intent=intent, confidence=1.0, level=0,
                            path=RoutePath.FALLBACK
                        ),
                        degradation_path=degradation
                    )

            except Exception as e:
                logger.warning(f"Path {current_path.value} failed: {e}, degrading...")

            # 降级到下一路径
            degradation = current_path
            self._stats.degradation_count += 1
            current_path = self.dispatcher.get_degradation_path(current_path)

        # 所有路径都失败：返回空 + error
        return RouteResult(
            response=None, path=current_path, intent=intent,
            classify_result=ClassifyResult(
                intent=intent, confidence=0.0, level=0, path=current_path
            ),
            degradation_path=degradation,
            error="All paths exhausted"
        )
