# Guardrails 使用示例

from guardrails_config import Guardrails, get_guardrails, create_guardrails


def example_1_basic_usage():
    """示例 1: 基本使用"""
    print("=== 示例 1: 基本使用 ===\n")
    
    # 获取默认 Guardrails 实例
    guardrails = get_guardrails()
    
    # 检测 PII
    text = "我的手机号是 13812345678，邮箱是 user@example.com"
    pii_result = guardrails.detect_pii(text)
    
    print(f"原始文本: {text}")
    print(f"检测到 PII: {pii_result.detected}")
    print(f"PII 类型: {pii_result.pii_types}")
    print(f"处理后: {pii_result.content}")
    
    print()


def example_2_content_filter():
    """示例 2: 内容过滤"""
    print("=== 示例 2: 内容过滤 ===\n")
    
    guardrails = get_guardrails()
    
    # 过滤违规内容
    text = "This text contains hate speech"
    filter_result = guardrails.filter_content(text)
    
    print(f"原始文本: {text}")
    print(f"是否阻拦: {filter_result.blocked}")
    print(f"原因: {filter_result.reason}")
    
    print()


def example_3_sanitize_input():
    """示例 3: 综合清理"""
    print("=== 示例 3: 综合清理 ===\n")
    
    guardrails = get_guardrails()
    
    test_inputs = [
        "这是正常文本，没有问题",
        "This contains hate speech",  # 会被阻拦
        "我的手机号是 13812345678",  # 会被脱敏
    ]
    
    for text in test_inputs:
        result, passed = guardrails.sanitize_input(text)
        print(f"输入: {text}")
        print(f"输出: {result}")
        print(f"通过: {passed}")
        print("---")
    
    print()


def example_4_strict_mode():
    """示例 4: 严格模式"""
    print("=== 示例 4: 严格模式 ===\n")
    
    # 创建严格模式的 Guardrails
    strict_guardrails = create_guardrails(strict_mode=True)
    
    text = "我的手机号是 13812345678"
    result, passed = strict_guardrails.sanitize_input(text)
    
    print(f"输入: {text}")
    print(f"输出: {result}")
    print(f"通过: {passed} (严格模式下拒绝 PII)")
    
    print()


def example_5_custom_config():
    """示例 5: 自定义配置"""
    print("=== 示例 5: 自定义配置 ===\n")
    
    # 只启用 PII 检测，禁用内容过滤
    guardrails = create_guardrails(
        enable_pii=True,
        enable_content_filter=False,
        strict_mode=False,
    )
    
    text = "This text contains hate speech but no PII"
    result, passed = guardrails.sanitize_input(text)
    
    print(f"输入: {text}")
    print(f"输出: {result}")
    print(f"通过: {passed} (内容过滤已禁用)")
    
    print()


def example_6_integration_with_llm():
    """示例 6: 与 LLM 调用集成"""
    print("=== 示例 6: 与 LLM 调用集成 ===\n")
    
    def mock_llm_call(prompt: str) -> str:
        """模拟 LLM 调用"""
        return f"LLM 对 '{prompt}' 的回复"
    
    guardrails = get_guardrails()
    
    user_prompt = "我的手机号是 13812345678，请帮我分析数据"
    
    # 清理输入
    clean_prompt, passed = guardrails.sanitize_input(user_prompt)
    
    if not passed:
        print(f"输入被拒绝: {clean_prompt}")
        return
    
    # 调用 LLM
    response = mock_llm_call(clean_prompt)
    print(f"清理后输入: {clean_prompt}")
    print(f"LLM 回复: {response}")
    
    # 清理输出（如果有需要）
    clean_response, _ = guardrails.sanitize_input(response)
    print(f"清理后回复: {clean_response}")
    
    print()


if __name__ == "__main__":
    example_1_basic_usage()
    example_2_content_filter()
    example_3_sanitize_input()
    example_4_strict_mode()
    example_5_custom_config()
    example_6_integration_with_llm()
