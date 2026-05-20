"""
知识提取器 — 实体识别/关系抽取/事实提取

设计依据: M8_P3_MEMORY_HIERARCHY_DESIGN.md §五.3
"""

import re
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

from .semantic_kb import KnowledgeTriple, SemanticKnowledgeBase

logger = logging.getLogger(__name__)


# ============================================================
# 预定义关系模式
# ============================================================

RELATION_PATTERNS: list[tuple[str, str, str]] = [
    # (predicate, 英文模式_regex, 中文模式_regex)
    ("is_a", r"(\w+)\s+is\s+(?:a|an|the)\s+(\w+)", r"(\w+)是(?:一个|一种|的)?(\w+)"),
    ("created_by", r"(\w+)\s+(?:was|is)\s+created\s+by\s+(\w+)", r"(\w+)(?:由|被)(\w+)(?:创建|发明)"),
    ("located_in", r"(\w+)\s+(?:is\s+)?(?:located\s+)?in\s+(\w+)", r"(\w+)位于(\w+)"),
    ("has_property", r"(\w+)\s+has\s+(\w+)", r"(\w+)有(\w+)"),
    ("part_of", r"(\w+)\s+is\s+part\s+of\s+(\w+)", r"(\w+)是(\w+)(?:的)?一部分"),
    ("related_to", r"(\w+)\s+(?:relates\s+to|associated\s+with)\s+(\w+)", r"(\w+)与(\w+)(?:相关|关联)"),
]

# 简单实体模式 (专有名词、大写开头词)
ENTITY_PATTERN = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b')

# SQL 注入关键词检测（安全保护）
BLOCKED_KEYWORDS = {"DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "EXEC", "EXECUTE"}


class KnowledgeExtractor:
    """
    知识提取器

    从记忆文本中提取: 实体 / 关系 / 事实
    纯规则提取（无 LLM 调用），$0 成本
    """

    def __init__(self):
        pass

    def extract_entities(self, text: str) -> list[str]:
        """
        实体识别

        提取: 专有名词 + 技术术语 + 大写缩写
        """
        if not text:
            return []

        entities = set()

        # 1. 专有名词 (大写开头连续词)
        for match in ENTITY_PATTERN.finditer(text):
            entity = match.group(1).strip()
            if len(entity) > 2 and entity.upper() not in BLOCKED_KEYWORDS:
                entities.add(entity)

        # 2. 常见技术术语 (小写但重要的词)
        tech_terms = {
            "python", "java", "javascript", "golang", "rust", "c++", "typescript",
            "docker", "kubernetes", "redis", "postgresql", "mongodb",
            "machine learning", "deep learning", "ai", "llm", "gpt",
            "api", "http", "rest", "graphql",
            "机器学习", "深度学习", "人工智能",
        }
        text_lower = text.lower()
        for term in tech_terms:
            if term in text_lower:
                entities.add(term)

        # 3. 安全过滤
        return [e for e in entities if e.upper() not in BLOCKED_KEYWORDS]

    def extract_relations(self, text: str) -> list[tuple[str, str, str]]:
        """
        关系抽取

        Returns:
            list of (subject, predicate, object)
        """
        if not text:
            return []

        relations = []

        for predicate, en_pattern, cn_pattern in RELATION_PATTERNS:
            # 英文模式
            for match in re.finditer(en_pattern, text, re.IGNORECASE):
                subj, obj = match.group(1).strip(), match.group(2).strip()
                if subj and obj and len(subj) > 1 and len(obj) > 1:
                    relations.append((subj.lower(), predicate, obj.lower()))

            # 中文模式
            for match in re.finditer(cn_pattern, text):
                subj, obj = match.group(1).strip(), match.group(2).strip()
                if subj and obj and len(subj) > 0 and len(obj) > 0:
                    relations.append((subj, predicate, obj))

        return relations

    def extract_facts(self, text: str, source_id: str = "") -> list[KnowledgeTriple]:
        """
        事实提取: 从文本中提取声明性事实为 SPO 三元组

        Args:
            text: 输入文本
            source_id: 来源记忆 ID

        Returns:
            KnowledgeTriple 列表
        """
        if not text:
            return []

        triples = []

        # 1. 关系抽取 → 三元组
        relations = self.extract_relations(text)
        for subj, pred, obj in relations:
            triple = KnowledgeTriple(
                subject=subj,
                predicate=pred,
                object=obj,
                confidence=0.5,  # 规则提取默认置信度
                sources=[source_id] if source_id else [],
            )
            triples.append(triple)

        # 2. 实体共现 → weak related_to
        entities = self.extract_entities(text)
        if len(entities) >= 2:
            for i in range(len(entities)):
                for j in range(i + 1, len(entities)):
                    # 只对距离近的实体创建关联
                    e1, e2 = entities[i], entities[j]
                    if e1.lower() != e2.lower():
                        triple = KnowledgeTriple(
                            subject=e1.lower(),
                            predicate="co_occurs_with",
                            object=e2.lower(),
                            confidence=0.3,  # 共现置信度较低
                            sources=[source_id] if source_id else [],
                        )
                        triples.append(triple)

        return triples

    def extract_and_upsert(self, text: str, kb: SemanticKnowledgeBase,
                           source_id: str = "") -> list[KnowledgeTriple]:
        """
        提取事实并写入知识库（合并流程）

        Returns:
            新写入/更新的三元组列表
        """
        facts = self.extract_facts(text, source_id)
        results = []

        for triple in facts:
            result = kb.upsert(
                subject=triple.subject,
                predicate=triple.predicate,
                object=triple.object,
                confidence=triple.confidence,
                source_id=source_id,
            )
            results.append(result)

        return results
