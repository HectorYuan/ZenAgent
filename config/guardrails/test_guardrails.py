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
    
    # 测试用例
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
            "text": "银行卡号是 6222021234567890123",
            "expected_detected": True,
            "expected_types": ["bank_card"],
        },
        {
            "text": "邮箱是 user@example.com",
            "expected_detected": True,
            "expected_types": ["email"],
        },
        {
            "text": "IP 地址是 192.168.1.1",
            "expected_detected": True,
            "expected_types": ["ip_address"],
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
        print(f"  检测结果: {result.detected}")
        print(f"  PII 类型: {result.pii_types}")
        print(f"  处理动作: {result.action.value}")
        print(f"  处理后内容: {result.content}")
        
        # 断言
        assert result.detected == case["expected_detected"], f"检测结果不匹配: {result.detected} != {case['expected_detected']}"
        if case["expected_types"]:
            assert set(result.pii_types) == set(case["expected_types"]), f"PII 类型不匹配"
        
        print("  ✅ 通过")


def test_content_filter():
    """测试内容过滤"""
    print("\n=== 测试内容过滤 ===")
    
    guardrails = Guardrails()
    
    # 测试用例
    test_cases = [
        {
            "text": "这是一段正常的文本",
            "expected_blocked": False,
        },
        {
            "text": "This text contains hate speech",
            "expected_blocked": True,
        },
        {
            "text": "violent content with weapon",
            "expected_blocked": True,
        },
        {
            "text": "adult content nsfw",
            "expected_blocked": True,
        },
    ]
    
    for i, case in enumerate(test_cases, 1):
        result = guardrails.filter_content(case["text"])
        
        print(f"\n用例 {i}: {case['text']}")
        print(f"  阻拦结果: {result.blocked}")
        print(f"  匹配类型: {[t.value for t in result.matched_types]}")
        print(f"  原因: {result.reason}")
        
        # 断言
        assert result.blocked == case["expected_blocked"], f"阻拦结果不匹配: {result.blocked} != {case['expected_blocked']}"
        
        print("  ✅ 通过")


def test_strict_mode():
    """测试严格模式"""
    print("\n=== 测试严格模式 ===")
    
    normal_guardrails = Guardrails(strict_mode=False)
    strict_guardrails = Guardrails(strict_mode=True)
    
    test_text = "我的手机号是 13812345678"
    
    # 普通模式：脱敏
    normal_result = normal_guardrails.sanitize_input(test_text)
    print(f"普通模式: '{normal_result[0]}' (通过: {normal_result[1]})")
    
    # 严格模式：拒绝
    strict_result = strict_guardrails.sanitize_input(test_text)
    print(f"严格模式: '{strict_result[0]}' (通过: {strict_result[1]})")
    
    assert normal_result[1] == True, "普通模式应该通过（脱敏）"
    assert strict_result[1] == False, "严格模式应该拒绝"
    
    print("  ✅ 通过")


def test_sanitize_input():
    """测试综合清理"""
    print("\n=== 测试综合清理 ===")
    
    guardrails = Guardrails()
    
    test_cases = [
        {
            "text": "普通文本，没有问题",
            "expected_pass": True,
        },
        {
            "text": "This text contains hate",
            "expected_pass": False,
        },
    ]
    
    for i, case in enumerate(test_cases, 1):
        result, passed = guardrails.sanitize_input(case["text"])
        
        print(f"\n用例 {i}: {case['text']}")
        print(f"  处理结果: '{result}'")
        print(f"  是否通过: {passed}")
        
        assert passed == case["expected_pass"], f"清理结果不匹配: {passed} != {case['expected_pass']}"
        
        print("  ✅ 通过")


if __name__ == "__main__":
    test_pii_detection()
    test_content_filter()
    test_strict_mode()
    test_sanitize_input()
    
    print("\n" + "="*50)
    print("所有测试通过！ ✅")
    print("="*50)
