"""
上下文压缩器 - Context Compressor

负责对上下文进行实际压缩操作
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field


class CompressionLevel(Enum):
    """压缩级别"""
    LIGHT = "light"           # 轻度压缩：保留大部分细节
    MEDIUM = "medium"         # 中度压缩：平衡压缩率和信息保留
    AGGRESSIVE = "aggressive" # 激进压缩：最大化压缩率
    ADAPTIVE = "adaptive"      # 自适应压缩：根据内容动态调整


@dataclass
class CompressionResult:
    """压缩结果"""
    original_messages: List[Dict[str, Any]]
    compressed_messages: List[Dict[str, Any]]
    summary: Optional[str] = None
    removed_count: int = 0
    compression_ratio: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "original_count": len(self.original_messages),
            "compressed_count": len(self.compressed_messages),
            "summary": self.summary,
            "removed_count": self.removed_count,
            "compression_ratio": self.compression_ratio,
            "timestamp": self.timestamp.isoformat()
        }


class Compressor:
    """
    上下文压缩器
    
    负责对消息历史进行压缩，支持多种压缩策略和级别。
    """
    
    def __init__(
        self,
        level: CompressionLevel = CompressionLevel.MEDIUM,
        preserve_system: bool = True,
        preserve_recent: int = 5
    ):
        """
        初始化压缩器
        
        Args:
            level: 压缩级别
            preserve_system: 是否保留系统消息
            preserve_recent: 保留最近 N 条消息
        """
        self.level = level
        self.preserve_system = preserve_system
        self.preserve_recent = preserve_recent
        self._compression_history: List[CompressionResult] = []
    
    def compress(
        self,
        messages: List[Dict[str, Any]],
        summary: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CompressionResult:
        """
        压缩消息历史
        
        Args:
            messages: 原始消息列表
            summary: 可选的预生成摘要
            metadata: 附加元数据
            
        Returns:
            CompressionResult: 压缩结果
        """
        if not messages:
            return CompressionResult(
                original_messages=[],
                compressed_messages=[]
            )
        
        original_count = len(messages)
        
        # 分离消息类型
        system_msgs, user_msgs, assistant_msgs, other_msgs = self._categorize_messages(messages)
        
        # 根据压缩级别确定保留策略
        if self.level == CompressionLevel.LIGHT:
            compressed = self._compress_light(messages)
        elif self.level == CompressionLevel.MEDIUM:
            compressed = self._compress_medium(messages, system_msgs, other_msgs)
        elif self.level == CompressionLevel.AGGRESSIVE:
            compressed = self._compress_aggressive(messages, system_msgs, other_msgs)
        elif self.level == CompressionLevel.ADAPTIVE:
            compressed = self._compress_adaptive(messages, system_msgs, other_msgs)
        else:
            compressed = self._compress_medium(messages, system_msgs, other_msgs)
        
        # 计算压缩率
        compression_ratio = 1.0 - (len(compressed) / len(messages)) if messages else 1.0
        
        result = CompressionResult(
            original_messages=messages,
            compressed_messages=compressed,
            summary=summary,
            removed_count=len(messages) - len(compressed),
            compression_ratio=compression_ratio
        )
        
        self._compression_history.append(result)
        return result
    
    def _categorize_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> Tuple[List, List, List, List]:
        """分类消息"""
        system_msgs = []
        user_msgs = []
        assistant_msgs = []
        other_msgs = []
        
        for msg in messages:
            role = msg.get("role", "")
            if role == "system":
                system_msgs.append(msg)
            elif role == "user":
                user_msgs.append(msg)
            elif role == "assistant":
                assistant_msgs.append(msg)
            else:
                other_msgs.append(msg)
        
        return system_msgs, user_msgs, assistant_msgs, other_msgs
    
    def _compress_light(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """轻度压缩：移除空消息和重复内容"""
        compressed = []
        seen_content = set()
        
        for msg in messages:
            content = msg.get("content", "")
            
            # 跳过空消息
            if not content or not content.strip():
                continue
            
            # 跳过完全重复的内容
            content_hash = hash(content)
            if content_hash in seen_content:
                continue
            
            seen_content.add(content_hash)
            compressed.append(msg)
        
        # 保留最近的少量消息
        return self._preserve_recent_messages(compressed)
    
    def _compress_medium(
        self,
        messages: List[Dict[str, Any]],
        system_msgs: List[Dict],
        other_msgs: List[Dict]
    ) -> List[Dict[str, Any]]:
        """中度压缩：合并相似消息，保留关键信息"""
        compressed = []
        
        # 保留系统消息
        if self.preserve_system:
            compressed.extend(system_msgs)
        
        # 合并用户消息（保留用户意图）
        merged_user = self._merge_consecutive_messages(messages, "user")
        compressed.extend(merged_user)
        
        # 保留助手的关键回复
        merged_assistant = self._merge_consecutive_messages(messages, "assistant")
        compressed.extend(merged_assistant)
        
        # 添加其他消息
        compressed.extend(other_msgs)
        
        return self._preserve_recent_messages(compressed)
    
    def _compress_aggressive(
        self,
        messages: List[Dict[str, Any]],
        system_msgs: List[Dict],
        other_msgs: List[Dict]
    ) -> List[Dict[str, Any]]:
        """激进压缩：最大化压缩"""
        compressed = []
        
        # 保留系统消息（最多2条）
        if self.preserve_system:
            compressed.extend(system_msgs[:2])
        
        # 保留关键用户消息（每隔一条取一条）
        user_msgs = [m for m in messages if m.get("role") == "user"]
        for i, msg in enumerate(user_msgs):
            if i % 2 == 0:
                compressed.append(msg)
        
        # 保留关键助手消息（每隔一条取一条）
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
        for i, msg in enumerate(assistant_msgs):
            if i % 2 == 0:
                compressed.append(msg)
        
        # 添加摘要标记
        if compressed:
            summary_msg = {
                "role": "system",
                "content": f"[Context compressed: {len(messages)} messages reduced to {len(compressed)}]"
            }
            compressed.insert(0, summary_msg)
        
        return self._preserve_recent_messages(compressed)
    
    def _compress_adaptive(
        self,
        messages: List[Dict[str, Any]],
        system_msgs: List[Dict],
        other_msgs: List[Dict]
    ) -> List[Dict[str, Any]]:
        """自适应压缩：根据内容重要性动态调整"""
        # 评估消息重要性
        important_messages = []
        normal_messages = []
        
        important_keywords = ["重要", "必须", "关键", "记住", "确认", "注意", "需要"]
        
        for msg in messages:
            content = msg.get("content", "")
            is_important = any(kw in content for kw in important_keywords)
            
            if is_important:
                important_messages.append(msg)
            else:
                normal_messages.append(msg)
        
        compressed = []
        
        # 保留系统消息
        if self.preserve_system:
            compressed.extend(system_msgs)
        
        # 保留所有重要消息
        compressed.extend(important_messages)
        
        # 对普通消息进行采样
        if normal_messages:
            sample_rate = self._calculate_sample_rate(len(messages))
            sampled = self._sample_messages(normal_messages, sample_rate)
            compressed.extend(sampled)
        
        # 添加摘要
        summary_msg = {
            "role": "system",
            "content": f"[Adaptive compression: kept {len(important_messages)} important, {len(normal_messages) - len(sampled) if normal_messages else 0} normal messages sampled]"
        }
        compressed.insert(len(system_msgs), summary_msg)
        
        return self._preserve_recent_messages(compressed)
    
    def _merge_consecutive_messages(
        self,
        messages: List[Dict[str, Any]],
        role: str
    ) -> List[Dict[str, Any]]:
        """合并连续的角色消息"""
        merged = []
        current_content = []
        current_msg = None
        
        for msg in messages:
            if msg.get("role") == role:
                if current_msg is None:
                    current_msg = msg.copy()
                else:
                    content = msg.get("content", "")
                    if content:
                        current_content.append(content)
            else:
                if current_msg is not None:
                    current_msg["content"] = " ".join(current_content) if current_content else current_msg.get("content", "")
                    merged.append(current_msg)
                    current_msg = None
                    current_content = []
                merged.append(msg)
        
        if current_msg is not None:
            merged.append(current_msg)
        
        return [m for m in merged if m.get("role") == role]
    
    def _preserve_recent_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """保留最近的消息"""
        if len(messages) <= self.preserve_recent:
            return messages
        
        # 先提取并移除最近的消息
        recent = messages[-self.preserve_recent:]
        remaining = messages[:-self.preserve_recent]
        
        # 对剩余消息进行精简
        trimmed = self._trim_messages(remaining)
        
        return trimmed + recent
    
    def _trim_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """精简消息内容"""
        trimmed = []
        for msg in messages:
            content = msg.get("content", "")
            if len(content) > 500:
                # 截断长内容，保留关键部分
                trimmed_msg = msg.copy()
                trimmed_msg["content"] = content[:500] + "..."
                trimmed.append(trimmed_msg)
            else:
                trimmed.append(msg)
        return trimmed
    
    def _calculate_sample_rate(self, total_count: int) -> float:
        """计算采样率"""
        if total_count < 10:
            return 1.0
        elif total_count < 50:
            return 0.5
        elif total_count < 100:
            return 0.3
        else:
            return 0.2
    
    def _sample_messages(
        self,
        messages: List[Dict[str, Any]],
        sample_rate: float
    ) -> List[Dict[str, Any]]:
        """采样消息"""
        if sample_rate >= 1.0:
            return messages
        
        sample_count = max(1, int(len(messages) * sample_rate))
        step = len(messages) / sample_count if sample_count > 0 else 1
        
        return [messages[int(i * step)] for i in range(sample_count)]
    
    def get_compression_history(self) -> List[CompressionResult]:
        """获取压缩历史"""
        return self._compression_history.copy()
    
    def get_total_saved_tokens(self) -> int:
        """获取总共节省的 Token 估计"""
        total = 0
        for result in self._compression_history:
            original_tokens = sum(len(m.get("content", "")) for m in result.original_messages)
            compressed_tokens = sum(len(m.get("content", "")) for m in result.compressed_messages)
            total += original_tokens - compressed_tokens
        return total
