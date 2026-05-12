"""
Guardrails 内容审核配置
支持 PII 检测、有害内容过滤、敏感词检测
"""
from guardrails.validator_base import RegisterValidator
from guardrails.validators import (RegexMatch, TwoTokens, OneLine, 
                                     ContainNoRepeatChars, QACorrectnessGrader,
                                     CompetitorCheck, ToxicLanguage, Profanity)

# PII 检测规则
pii_validators = {
    "email": RegexMatch(
        regex="[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        on_fail="reask",
        description="检测邮箱地址"
    ),
    "phone": RegexMatch(
        regex="1[3-9]\d{9}",
        on_fail="reask",
        description="检测手机号码"
    ),
    "id_card": RegexMatch(
        regex="[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]",
        on_fail="reask",
        description="检测身份证号"
    ),
    "bank_card": RegexMatch(
        regex="\d{16,19}",
        on_fail="reask",
        description="检测银行卡号"
    ),
}

# 内容安全规则
content_safety_validators = {
    "toxic": ToxicLanguage(
        threshold=0.5,
        on_fail="reask",
        description="检测有毒/有害语言"
    ),
    "profanity": Profanity(
        on_fail="reask",
        description="检测脏话/粗俗语言"
    ),
    "competitor": CompetitorCheck(
        competitors=["竞品1", "竞品2"],
        on_fail="flag",
        description="检测竞品提及"
    ),
}

# 输出格式化规则
format_validators = [
    TwoTokens(token="```", on_fail="fix"),
    OneLine(on_fail="fix"),
    ContainNoRepeatChars(chars=4, on_fail="fix"),
]

# QA 正确性评分
qa_validator = QACorrectnessGrader(
    llm_callable="gpt-3.5-turbo",
    threshold=0.5,
    on_fail="reask"
)

# Guardrails 配置
GUARDRAILS_CONFIG = {
    "pii_detection": pii_validators,
    "content_safety": content_safety_validators,
    "format": format_validators,
    "qa": qa_validator,
}

def get_guardrails_config():
    """获取完整的 Guardrails 配置"""
    return GUARDRAILS_CONFIG
