"""
Guardrails 配置模块
用于 ZenAgent 内容安全审核（PII 检测、内容过滤）
"""

import re
from typing import List, Dict, Optional, Literal
from dataclasses import dataclass
from enum import Enum


class PIIAction(Enum):
    """PII 处理动作"""
    ALLOW = "allow"           # 允许通过
    MASK = "mask"             # 脱敏处理
    REJECT = "reject"         # 拒绝请求


class ContentType(Enum):
    """违规内容类型"""
    HATE_SPEECH = "hate_speech"      # 仇恨言论
    VIOLENCE = "violence"            # 暴力内容
    ADULT = "adult"                  # 成人内容
    POLITICS = "politics"            # 政治敏感
    OTHER = "other"                  # 其他


@dataclass
class PIIResult:
    """PII 检测结果"""
    detected: bool
    content: str
    pii_types: List[str]
    action: PIIAction


@dataclass
class ContentFilterResult:
    """内容过滤结果"""
    blocked: bool
    content: str
    matched_types: List[ContentType]
    reason: str


# ===================
# PII 检测规则
# ===================

PII_DETECTION_RULES: Dict[str, Dict] = {
    "phone": {
        "pattern": r"1[3-9]\d{9}",
        "description": "中国大陆手机号",
        "action": PIIAction.MASK,
        "mask_template": "{first3}****{last4}",
    },
    "id_card": {
        "pattern": r"\d{17}[\dXx]",
        "description": "中国大陆身份证号",
        "action": PIIAction.REJECT,
    },
    "bank_card": {
        "pattern": r"\d{16,19}",
        "description": "银行卡号",
        "action": PIIAction.MASK,
        "mask_template": "{first4}****{last4}",
    },
    "email": {
        "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "description": "邮箱地址",
        "action": PIIAction.MASK,
        "mask_template": "{username}@***.{domain}",
    },
    "ip_address": {
        "pattern": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
        "description": "IP 地址",
        "action": PIIAction.MASK,
        "mask_template": "***.***.***.***",
    },
}


# ===================
# 内容过滤规则
# ===================

CONTENT_FILTER_KEYWORDS: Dict[ContentType, List[str]] = {
    ContentType.HATE_SPEECH: [
        "hate", "discrimination", "racist", "bias", "prejudice",
        "仇恨", "歧视", "种族歧视", "偏见",
    ],
    ContentType.VIOLENCE: [
        "violent", "weapon", "gun", "kill", "murder", "terrorist",
        "暴力", "武器", "枪支", "恐怖分子", "杀人",
    ],
    ContentType.ADULT: [
        "adult", "nsfw", "porn", "xxx", "erotic",
        "色情", "成人内容", "不雅",
    ],
    ContentType.POLITICS: [
        # 政治敏感词（示例，实际需要根据具体场景配置）
        "sensitive_political",
    ],
}


# ===================
# Guardrails 类
# ===================

class Guardrails:
    """Guardrails 内容安全审核器"""
    
    def __init__(
        self,
        enable_pii: bool = True,
        enable_content_filter: bool = True,
        strict_mode: bool = False,
    ):
        """
        初始化 Guardrails
        
        Args:
            enable_pii: 是否启用 PII 检测
            enable_content_filter: 是否启用内容过滤
            strict_mode: 严格模式（拒绝所有检测到 PII/违规内容）
        """
        self.enable_pii = enable_pii
        self.enable_content_filter = enable_content_filter
        self.strict_mode = strict_mode
        
        # 编译正则表达式
        self._pii_patterns = {
            name: re.compile(rule["pattern"])
            for name, rule in PII_DETECTION_RULES.items()
        }
    
    def detect_pii(self, text: str) -> PIIResult:
        """
        检测 PII 信息
        
        Args:
            text: 输入文本
            
        Returns:
            PIIResult: 检测结果
        """
        if not self.enable_pii:
            return PIIResult(
                detected=False,
                content=text,
                pii_types=[],
                action=PIIAction.ALLOW,
            )
        
        detected_pii = []
        content = text
        
        # 检测各类 PII
        for pii_type, rule in PII_DETECTION_RULES.items():
            pattern = self._pii_patterns[pii_type]
            matches = pattern.findall(content)
            
            if matches:
                detected_pii.append(pii_type)
                
                # 根据动作处理
                action = rule["action"]
                
                if action == PIIAction.REJECT or self.strict_mode:
                    return PIIResult(
                        detected=True,
                        content="",
                        pii_types=detected_pii,
                        action=PIIAction.REJECT,
                    )
                elif action == PIIAction.MASK:
                    content = self._mask_pii(content, matches, rule.get("mask_template"))
        
        return PIIResult(
            detected=len(detected_pii) > 0,
            content=content,
            pii_types=detected_pii,
            action=PIIAction.MASK if detected_pii else PIIAction.ALLOW,
        )
    
    def _mask_pii(self, text: str, matches: List[str], template: Optional[str]) -> str:
        """脱敏处理"""
        if not template:
            return text
        
        masked = text
        for match in matches:
            if template == "{first3}****{last4}" and len(match) >= 7:
                masked = masked.replace(match, f"{match[:3]}****{match[-4:]}")
            elif template == "{first4}****{last4}" and len(match) >= 8:
                masked = masked.replace(match, f"{match[:4]}****{match[-4:]}")
            elif template == "{username}@***.{domain}" and "@" in match:
                username, domain = match.split("@", 1)
                masked = masked.replace(match, f"{username}@***.{domain.split('.')[-1]}")
            elif template == "***.***.***.***":
                masked = masked.replace(match, "***.***.***.***")
            else:
                masked = masked.replace(match, "***")
        
        return masked
    
    def filter_content(self, text: str) -> ContentFilterResult:
        """
        过滤违规内容
        
        Args:
            text: 输入文本
            
        Returns:
            ContentFilterResult: 过滤结果
        """
        if not self.enable_content_filter:
            return ContentFilterResult(
                blocked=False,
                content=text,
                matched_types=[],
                reason="",
            )
        
        matched_types = []
        text_lower = text.lower()
        
        # 检测各类违规内容
        for content_type, keywords in CONTENT_FILTER_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    matched_types.append(content_type)
                    if self.strict_mode:
                        return ContentFilterResult(
                            blocked=True,
                            content="",
                            matched_types=[content_type],
                            reason=f"Strict mode: 检测到 {content_type.value}",
                        )
                    break
        
        if matched_types:
            return ContentFilterResult(
                blocked=True,
                content="",
                matched_types=matched_types,
                reason=f"检测到违规内容: {', '.join([t.value for t in matched_types])}",
            )
        
        return ContentFilterResult(
            blocked=False,
            content=text,
            matched_types=[],
            reason="",
        )
    
    def sanitize_input(self, text: str) -> tuple[str, bool]:
        """
        综合清理输入（PII 检测 + 内容过滤）
        
        Args:
            text: 输入文本
            
        Returns:
            (清理后的文本, 是否通过)
        """
        # 内容过滤
        filter_result = self.filter_content(text)
        if filter_result.blocked:
            return filter_result.reason, False
        
        # PII 检测
        pii_result = self.detect_pii(filter_result.content)
        if pii_result.action == PIIAction.REJECT:
            return f"检测到敏感信息: {', '.join(pii_result.pii_types)}", False
        
        return pii_result.content, True


# ===================
# 单例
# ===================

_default_guardrails: Optional[Guardrails] = None


def get_guardrails() -> Guardrails:
    """获取 Guardrails 单例"""
    global _default_guardrails
    if _default_guardrails is None:
        _default_guardrails = Guardrails()
    return _default_guardrails


def create_guardrails(
    enable_pii: bool = True,
    enable_content_filter: bool = True,
    strict_mode: bool = False,
) -> Guardrails:
    """创建 Guardrails 实例"""
    return Guardrails(
        enable_pii=enable_pii,
        enable_content_filter=enable_content_filter,
        strict_mode=strict_mode,
    )
