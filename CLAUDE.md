# ZenAgent 项目指南

## 语言要求

- 所有对话、思考过程、回复内容默认使用中文
- 代码变量名、函数名、类名保持英文（遵循编程惯例）
- commit message 可以中英混合

## 项目架构

ZenAgent 是一个六层智能体平台：

- **L0 LLMInfra** — ModelNexusCore 9 阶段管线（Security→CacheRead→TokenBudget→RateLimit→Route→Provider→Quality→CacheWrite→Observe）
- **L1 Runtime** — 会话状态机、令牌桶限流、事件总线、检查点/恢复
- **L2 ZenAgent** — 意图路由（Fast/Deep/Fallback）、人格注入、Hook 系统
- **L3 MetaSoul** — 4 类记忆（Working/Episodic/Semantic/Procedural）、Big Five 人格、经验学习循环
- **L4 SwarmFly** — 多 Agent 注册、任务分发、共享内存
- **L5 SoulTeam** — 16 Agent 画像、四维路由（C×0.4+A×0.3+L×0.2+S×0.1）、八卦矩阵、协作链

## 核心配置

所有 LLM 配置集中管理，不在代码中直接读取系统环境变量：

- `packages/LLMInfra/providers.yaml` — Provider 元数据（base_url、model、key 映射）
- `packages/modelnexus/config/secret_keys.yaml` — API Key（开发环境，gitignored）
- `packages/modelnexus/security/secure_key_manager.py` — 密钥管理（Vault → File → EnvVar 降级链）
- `packages/LLMInfra/modelnexus_core_config.py` — 集中化配置入口

## 密钥管理

```bash
# 开发环境：复制模板填入真实 Key
cp packages/modelnexus/config/secret_keys.yaml.example \
   packages/modelnexus/config/secret_keys.yaml

# 生产环境：写入 HashiCorp Vault
vault kv put secret/neo_model/llm/{key_name} value="{api_key}"
```

## 测试

```bash
# 核心单元测试
pytest packages/LLMInfra/tests/ packages/ZenAgent/tests/ packages/Runtime/tests/ -q

# 真实 E2E 测试（需要 API Key）
python3 tests/e2e/test_real_e2e.py --scene 1

# 全量 E2E
python3 tests/e2e/test_real_e2e.py
```

## 常用命令

```bash
./zena chat "Hello"              # 单次对话
./zena chat --provider deepseek  # 指定 Provider
./zena status                    # 系统状态
./zena tui                       # TUI 界面
./zena e2e                       # 运行 E2E 测试
```

## 注意事项

- `secret_keys.yaml` 包含真实 API Key，绝对不能提交
- `neo_model.yaml` 中不应出现硬编码 API Key，使用 `secure_key_name` 引用
- ModelNexusCore 是唯一 LLM 调用路径，不走 legacy 直连 Provider
- 所有新 Provider 配置在 `providers.yaml` 中定义，不直接写 env var
