# Guardrails

ZenAgent 内容安全审核模块，提供 PII（个人隐私信息）检测和违规内容过滤功能。

## 功能特性

- ✅ **PII 检测**：手机号、身份证、银行卡、邮箱、IP 地址
- ✅ **内容过滤**：仇恨言论、暴力内容、成人内容、政治敏感
- ✅ **脱敏处理**：自动对敏感信息进行脱敏（如 `138****5678`）
- ✅ **严格模式**：可配置严格模式，拒绝所有检测到敏感内容的请求
- ✅ **单例模式**：全局单例，方便集成

## 快速开始

```python
from guardrails_config import get_guardrails

# 获取 Guardrails 实例
guardrails = get_guardrails()

# 清理输入
text = "我的手机号是 13812345678"
clean_text, passed = guardrails.sanitize_input(text)

if passed:
    print(f"通过: {clean_text}")  # 输出: 通过: 我的手机号是 138****5678
else:
    print(f"被拒绝: {clean_text}")
```

## API 说明

### `Guardrails` 类

#### 初始化

```python
Guardrails(
    enable_pii: bool = True,           # 是否启用 PII 检测
    enable_content_filter: bool = True, # 是否启用内容过滤
    strict_mode: bool = False,         # 严格模式
)
```

#### 方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `detect_pii(text)` | 检测 PII 信息 | `PIIResult` |
| `filter_content(text)` | 过滤违规内容 | `ContentFilterResult` |
| `sanitize_input(text)` | 综合清理输入 | `(text, passed)` |

### PII 检测

```python
# PII 检测
result = guardrails.detect_pii("我的手机号是 13812345678")

print(f"检测到 PII: {result.detected}")      # True
print(f"PII 类型: {result.pii_types}")        # ['phone']
print(f"处理动作: {result.action.value}")     # 'mask'
print(f"处理后: {result.content}")            # 我的手机号是 138****5678
```

### 内容过滤

```python
# 内容过滤
result = guardrails.filter_content("This text contains hate speech")

print(f"是否阻拦: {result.blocked}")          # True
print(f"匹配类型: {result.matched_types}")    # [ContentType.HATE_SPEECH]
print(f"原因: {result.reason}")               # 检测到违规内容: hate_speech
```

## 配置规则

### PII 检测规则

| 类型 | 模式 | 默认动作 |
|------|------|---------|
| 手机号 | `1[3-9]\d{9}` | 脱敏 |
| 身份证 | `\d{17}[\dXx]` | 拒绝 |
| 银行卡 | `\d{16,19}` | 脱敏 |
| 邮箱 | `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z\|a-z]{2,}\b` | 脱敏 |
| IP 地址 | `\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}` | 脱敏 |

### 内容过滤规则

| 类型 | 关键词（示例） |
|------|----------------|
| 仇恨言论 | hate, discrimination, 仇恨, 歧视 |
| 暴力内容 | violent, weapon, 暴力, 武器 |
| 成人内容 | adult, nsfw, 色情 |
| 政治敏感 | sensitive_political |

## 运行测试

```bash
# 运行单元测试
python test_guardrails.py

# 运行使用示例
python example_usage.py
```

## 集成示例

### 与 Runtime (L1) 集成

```python
from guardrails_config import get_guardrails

# Runtime 层初始化时创建 Guardrails
guardrails = get_guardrails()

async def process_user_input(session_id: str, user_input: str):
    """处理用户输入"""
    # 清理输入
    clean_input, passed = guardrails.sanitize_input(user_input)
    
    if not passed:
        return f"输入包含敏感内容: {clean_input}"
    
    # 继续处理...
    return clean_input
```

### 与 LLM 调用集成

```python
from guardrails_config import get_guardrails

guardrails = get_guardrails()

def call_llm(prompt: str) -> str:
    """调用 LLM"""
    # 清理输入
    clean_prompt, passed = guardrails.sanitize_input(prompt)
    if not passed:
        raise ValueError(f"输入被拒绝: {clean_prompt}")
    
    # 调用 LLM
    response = llm_api.call(clean_prompt)
    
    # 清理输出（可选）
    clean_response, _ = guardrails.sanitize_input(response)
    
    return clean_response
```

## 注意事项

- 严格模式下，所有检测到 PII 或违规内容的请求都会被拒绝
- 脱敏处理会修改原始文本，确保敏感信息不可见
- 内容过滤规则需要根据具体场景调整，避免误判
- 生产环境建议使用更专业的 NLP 模型进行检测

## 文件说明

- `guardrails_config.py` - 核心实现
- `test_guardrails.py` - 单元测试
- `example_usage.py` - 使用示例
- `README.md` - 本文档
