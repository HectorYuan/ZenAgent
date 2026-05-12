"""
摘要提取器 - Message Summarizer

从对话历史中提取关键信息，生成简洁的摘要
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import hashlib
import json


class SummarizerStrategy(Enum):
    """摘要提取策略"""
    TRUNCATE = "truncate"                       # 截断策略
    EXTRACT_KEY_POINTS = "extract_key_points"   # 关键点提取
    ABSTRACTIVE = "abstractive"                 # 生成式摘要
    HYBRID = "hybrid"                           # 混合策略


class MessageSummary:
    """消息摘要"""
    
    def __init__(
        self,
        content: str,
        key_points: List[str],
        token_count: int,
        original_count: int,
        created_at: datetime = None
    ):
        self.content = content
        self.key_points = key_points
        self.token_count = token_count
        self.original_count = original_count
        self.created_at = created_at or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "key_points": self.key_points,
            "token_count": self.token_count,
            "original_count": self.original_count,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageSummary":
        """从字典创建"""
        data = data.copy()
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


class Summarizer:
    """
    消息摘要提取器
    
    负责从对话历史中提取关键信息，生成简洁的摘要，
    支持多种摘要策略以适应不同场景需求。
    """
    
    def __init__(
        self,
        strategy: SummarizerStrategy = SummarizerStrategy.ABSTRACTIVE,
        max_summary_tokens: int = 500,
        preserve_recent_count: int = 3
    ):
        """
        初始化摘要器
        
        Args:
            strategy: 摘要策略
            max_summary_tokens: 最大摘要 Token 数
            preserve_recent_count: 保留最近 N 条消息
        """
        self.strategy = strategy
        self.max_summary_tokens = max_summary_tokens
        self.preserve_recent_count = preserve_recent_count
    
    def summarize(
        self,
        messages: List[Dict[str, Any]],
        task_context: Optional[str] = None
    ) -> MessageSummary:
        """
        生成消息历史摘要
        
        Args:
            messages: 消息列表
            task_context: 任务上下文提示
            
        Returns:
            MessageSummary: 消息摘要对象
        """
        if not messages:
            return MessageSummary(
                content="",
                key_points=[],
                token_count=0,
                original_count=0
            )
        
        original_count = len(messages)
        
        if self.strategy == SummarizerStrategy.TRUNCATE:
            return self._truncate_summarize(messages, task_context)
        elif self.strategy == SummarizerStrategy.EXTRACT_KEY_POINTS:
            return self._extract_key_points(messages, task_context)
        elif self.strategy == SummarizerStrategy.ABSTRACTIVE:
            return self._abstractive_summarize(messages, task_context)
        elif self.strategy == SummarizerStrategy.HYBRID:
            return self._hybrid_summarize(messages, task_context)
        else:
            return self._truncate_summarize(messages, task_context)
    
    def _truncate_summarize(
        self,
        messages: List[Dict[str, Any]],
        task_context: Optional[str]
    ) -> MessageSummary:
        """截断式摘要：保留首尾消息"""
        if len(messages) <= self.preserve_recent_count:
            content = self._messages_to_text(messages)
            return MessageSummary(
                content=content,
                key_points=[],
                token_count=self._estimate_tokens(content),
                original_count=len(messages)
            )
        
        recent = messages[-self.preserve_recent_count:]
        summary_intro = "[Previous conversation summarized]"
        
        content = f"{summary_intro}\n{self._messages_to_text(recent)}"
        
        return MessageSummary(
            content=content,
            key_points=[],
            token_count=self._estimate_tokens(content),
            original_count=len(messages)
        )
    
    def _extract_key_points(
        self,
        messages: List[Dict[str, Any]],
        task_context: Optional[str]
    ) -> MessageSummary:
        """关键点提取：识别和保留关键信息"""
        key_points = []
        important_keywords = ["需要", "必须", "重要", "关键", "记住", "确认", "注意"]
        
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            
            for keyword in important_keywords:
                if keyword in content:
                    if len(content) > 100:
                        content = content[:100] + "..."
                    key_points.append(f"[{role}] {content}")
                    break
        
        key_points = list(dict.fromkeys(key_points))
        key_points = key_points[:10]
        
        content = "\n".join(key_points) if key_points else "[No key points extracted]"
        
        return MessageSummary(
            content=content,
            key_points=key_points,
            token_count=self._estimate_tokens(content),
            original_count=len(messages)
        )
    
    def _abstractive_summarize(
        self,
        messages: List[Dict[str, Any]],
        task_context: Optional[str]
    ) -> MessageSummary:
        """生成式摘要：生成新的摘要内容"""
        summary_parts = []
        
        themes = self._extract_themes(messages)
        if themes:
            summary_parts.append(f"Topics: {', '.join(themes)}")
        
        decisions = self._extract_decisions(messages)
        if decisions:
            summary_parts.append(f"Decisions: {'; '.join(decisions)}")
        
        todos = self._extract_todos(messages)
        if todos:
            summary_parts.append(f"Pending tasks: {'; '.join(todos)}")
        
        if task_context:
            summary_parts.insert(0, f"Task context: {task_context}")
        
        content = "\n".join(summary_parts) if summary_parts else "[Conversation summary]"
        
        return MessageSummary(
            content=content,
            key_points=themes,
            token_count=self._estimate_tokens(content),
            original_count=len(messages)
        )
    
    def _hybrid_summarize(
        self,
        messages: List[Dict[str, Any]],
        task_context: Optional[str]
    ) -> MessageSummary:
        """混合策略：结合多种方法"""
        key_summary = self._extract_key_points(messages, task_context)
        abstract_summary = self._abstractive_summarize(messages, task_context)
        
        combined_content = f"{key_summary.content}\n\n{abstract_summary.content}"
        combined_key_points = list(set(key_summary.key_points + abstract_summary.key_points))
        
        return MessageSummary(
            content=combined_content,
            key_points=combined_key_points,
            token_count=self._estimate_tokens(combined_content),
            original_count=len(messages)
        )
    
    def _messages_to_text(self, messages: List[Dict[str, Any]]) -> str:
        """将消息列表转换为文本"""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"[{role}] {content}")
        return "\n".join(lines)
    
    def _estimate_tokens(self, text: str) -> int:
        """估算 Token 数量（粗略估计：中文约 2 字符/token，英文约 4 字符/token）"""
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 2 + other_chars / 4)
    
    def _extract_themes(self, messages: List[Dict[str, Any]]) -> List[str]:
        """提取对话主题"""
        themes = []
        theme_keywords = {
            "代码开发": ["代码", "函数", "类", "实现", "开发", "API"],
            "数据分析": ["分析", "数据", "统计", "图表", "报告"],
            "文档撰写": ["文档", "文章", "报告", "撰写", "写作"],
            "问题排查": ["问题", "错误", "bug", "修复", "排查"],
            "系统配置": ["配置", "设置", "安装", "部署", "环境"]
        }
        
        all_content = " ".join(msg.get("content", "") for msg in messages)
        
        for theme, keywords in theme_keywords.items():
            if any(kw in all_content for kw in keywords):
                themes.append(theme)
        
        return themes[:5]
    
    def _extract_decisions(self, messages: List[Dict[str, Any]]) -> List[str]:
        """提取决策信息"""
        decisions = []
        decision_keywords = ["决定", "选择", "采用", "确定", "最终方案"]
        
        for msg in messages:
            content = msg.get("content", "")
            for keyword in decision_keywords:
                if keyword in content and len(content) < 200:
                    decisions.append(content)
                    break
        
        return decisions[:5]
    
    def _extract_todos(self, messages: List[Dict[str, Any]]) -> List[str]:
        """提取待办事项"""
        todos = []
        todo_keywords = ["待办", "TODO", "需要做", "下一步", "计划"]
        
        for msg in messages:
            content = msg.get("content", "")
            for keyword in todo_keywords:
                if keyword in content:
                    todos.append(content)
                    break
        
        return todos[:5]
