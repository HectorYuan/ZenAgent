# Guardrails 使用示例

from guardrails_config import get_guardrails, create_guardrails


def example_basic():
    """基本使用"""
    guardrails = get_guardrails()
    
    text = "我的手机号是 13812345678"
    result, passed = guardrails.sanitize_input(text)
    
    print(f"原始: {text}")
    print(f"处理后: {result}")
    print(f"通过: {passed}")


def example_strict_mode():
    """严格模式"""
    strict_guardrails = create_guardrails(strict_mode=True)
    
    text = "我的手机号是 13812345678"
    result, passed = strict_guardrails.sanitize_input(text)
    
    print(f"严格模式 - 通过: {passed}")


if __name__ == "__main__":
    print("=== 示例 1: 基本使用 ===")
    example_basic()
    
    print("\n=== 示例 2: 严格模式 ===")
    example_strict_mode()
