# Guardrails

ZenAgent 内容安全审核模块。

## 功能

- PII 检测（手机号、身份证、银行卡、邮箱、IP）
- 内容过滤（仇恨言论、暴力内容、成人内容）
- 脱敏处理
- 严格模式

## 使用

```python
from guardrails_config import get_guardrails

guardrails = get_guardrails()
result, passed = guardrails.sanitize_input("我的手机号是 13812345678")
```
