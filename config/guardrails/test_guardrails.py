"""
Guardrails 单元测试
"""

from guardrails_config import (
    Guardrails,
    PIIAction,
    ContentType,
    get_guardrails,
    create_guardrails,
)


def test_pii_detection():
    """测试 PII 检测"""
    print("=== 测试 PII 检测 ===")
    
    guardrails = Guardrails()
    
    test_cases = [
        {
            "text": "我的手机号是 13812345678",
            "expected_detected": True,
            "expected_types": ["phone"],
        },
        {
            "text": "身份证号是 110101199001011234",
            "expected_detected": True,
            "expected_types": ["id_card"],
        },
        {
            "text": "这是普通文本，没有敏感信息",
            "expected_detected": False,
            "expected_types": [],
        },
    ]
    
    for i, case in enumerate(test_cases, 1):
        result = guardrails.detect_pii(case["text"])
        print(f"\n用例 {i}: {case['text']}")
        print(f"  检测结果: {result.detected}, PII 类型: {result.pii_types}")
        assert result.detected == case["expected_detected"]
        print("  ✅ 通过")


def test_content_filter():
    """测试内容过滤"""
    print("\n=== 测试内容过滤 ===")
    
    guardrails = Guardrails()
    
    test_cases = [
        {"text": "这是一段正常的文本", "expected_blocked": False},
        {"text": "This text contains hate speech", "expected_blocked": True},
    ]
    
    for i, case in enumerate(test_cases, 1):
        result = guardrails.filter_content(case["text"])
        print(f"\n用例 {i}: {case['text']}")
        print(f"  阻拦结果: {result.blocked}")
        assert result.blocked == case["expected_blocked"]
        print("  ✅ 通过")


if __name__ == "__main__":
    test_pii_detection()
    test_content_filter()
    print("\n所有测试通过！ ✅")
