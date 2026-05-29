# Welcome to ZenAgent

## How We Use Claude

Based on hetcor's usage over the last 30 days:

Work Type Breakdown:
  Build Feature      ████████████████░░░░  50%
  Improve Quality    ████████░░░░░░░░░░░░  25%
  Debug Fix          █████░░░░░░░░░░░░░░░  15%
  Plan Design        ███░░░░░░░░░░░░░░░░░  10%

Top Skills & Commands:
  /model             ████████████████████  11x/month
  /compact           ███░░░░░░░░░░░░░░░░░   2x/month
  /claude-api        █░░░░░░░░░░░░░░░░░░░   1x/month
  /resume            █░░░░░░░░░░░░░░░░░░░   1x/month

Top MCP Servers:
  (none configured)

## Your Setup Checklist

### Codebases
- [x] ZenAgent — 六层智能体平台 (L0 LLMInfra → L5 SoulTeam)
- [x] modelnexus — LLM 网关服务（子模块，含 Vault/密钥管理）
- [x] packages/LLMInfra — L0 LLM 基础设施（ModelNexusCore 9 阶段管线）
- [x] packages/ZenAgent — L2 智能体核心（意图路由、人格注入）
- [x] packages/MetaSoul — L3 元灵魂（记忆、人格、经验学习）
- [x] packages/Runtime — L1 运行时（会话状态机、限流）
- [x] packages/SwarmFly — L4 多智能体调度
- [x] packages/SoulTeam — L5 团队协作（16 Agent、八卦路由）

### MCP Servers to Activate
- [ ] Chrome DevTools MCP — 浏览器调试和页面检查。需要安装 Chrome + MCP server
- [ ] Web Search MCP — 联网搜索。需要配置 API key

### Skills to Know About
- /model — 切换 Claude 模型（Opus/Sonnet/Haiku），项目中常用 Opus 做架构设计
- /compact — 压缩对话上下文，长会话后释放 token 空间
- /claude-api — Claude API 使用指南，调试 API 调用时使用
- /resume — 恢复上一次会话，继续未完成的工作

## 项目架构速览

```
┌─────────────────────────────────────────────────────────┐
│                    CLI / TUI (zena)                     │
│              packages/ZenAgent/zena/                    │
├─────────────────────────────────────────────────────────┤
│  L2 ZenAgent     │ 意图路由、人格注入、Hook 系统       │
│  L1 Runtime      │ 会话状态机、令牌桶限流、事件总线    │
│  L0 LLMInfra     │ ModelNexusCore 9 阶段管线           │
├─────────────────────────────────────────────────────────┤
│  L3 MetaSoul     │ 4 类记忆、Big Five 人格、经验学习    │
│  L4 SwarmFly     │ 多 Agent 注册、任务分发             │
│  L5 SoulTeam     │ 16 Agent 画像、四维路由、八卦矩阵   │
├─────────────────────────────────────────────────────────┤
│  ModelNexus      │ LLM 网关（子模块）                  │
│    ├─ SecureKeyManager  │ Vault → File → EnvVar 密钥链 │
│    ├─ providers.yaml    │ Provider 元数据配置           │
│    └─ secret_keys.yaml  │ 本地密钥文件 (gitignored)     │
└─────────────────────────────────────────────────────────┘
```

## 各模块功能定位

### L0 LLMInfra — LLM 基础设施层

**职责**：所有 LLM 调用的唯一入口，提供统一的模型访问、缓存、限流、观测能力。

**核心组件**：
- **ModelNexusCore** — 9 阶段可插拔管线，每个请求必须经过
- **ProviderFactory** — Provider 工厂，管理 OpenAI/DeepSeek/MiMo 等协议适配器
- **CacheManager** — L1 精确缓存 + L2 语义缓存
- **TokenBudgetManager** — 按意图分类分配 max_tokens（Simple QA: 400, General: 1150, Complex: 2250, Creative: 3000）
- **IntentRouter** — 意图分类 → FastPath/DeepPath/RAGPath/ToolPath/FallbackPath

**管线顺序**：
```
Security → CacheRead → TokenBudget → RateLimit → Route → Provider → Quality → CacheWrite → Observe
   5          10          20           25         30       50          70         90          95
```

**配置入口**：
- `packages/LLMInfra/providers.yaml` — Provider 元数据
- `packages/LLMInfra/modelnexus_core_config.py` — 集中化配置 API
- `packages/LLMInfra/config.py` — Settings dataclass（委托给集中化配置）

---

### L1 Runtime — 运行时层

**职责**：会话生命周期管理、流量控制、事件分发、状态持久化。

**核心组件**：
- **SessionManager** — 会话状态机（CREATED → ACTIVE → SUSPENDED → CLOSED）
- **RateLimiter** — 令牌桶限流器
- **EventBus** — 发布/订阅事件总线（SESSION_CREATED, MESSAGE_SENT 等）
- **CheckpointManager** — 会话检查点，支持恢复

**协作机制**：
- L2 ZenAgent 通过 `Runtime.get_session()` 获取会话状态
- L0 LLMInfra 通过 EventBus 发送 LLM 调用事件
- L3 MetaSoul 通过 EventBus 监听记忆写入事件

---

### L2 ZenAgent — 智能体核心层

**职责**：意图识别、路由决策、人格注入、Hook 系统，是用户与 LLM 之间的智能中间层。

**核心组件**：
- **IntentRouter** — 意图分类（Simple QA / General Reasoning / Complex / Creative）
- **PersonalityInjector** — Big Five 人格注入到 system prompt
- **HookSystem** — 请求前/后钩子（pre_llm, post_llm, pre_memory, post_memory）
- **ZenAgentConfig** — 统一配置（agent_id, llm_provider, llm_model, enable_memory 等）

**协作机制**：
- `think()` 方法是核心入口：意图分类 → 人格注入 → L0 LLM 调用 → 记忆写入 → 经验学习
- L3 MetaSoul 通过 `_init_soul()` 注入记忆和人格系统
- L4 SwarmFly 通过 `agents_list()` 获取可用 Agent 列表

---

### L3 MetaSoul — 元灵魂层

**职责**：记忆管理、人格演化、经验学习，赋予智能体"记忆"和"个性"。

**核心组件**：
- **MemoryManager** — 4 类记忆存储
  - Working Memory（工作记忆，短期）
  - Episodic Memory（情景记忆，事件序列）
  - Semantic Memory（语义记忆，知识图谱）
  - Procedural Memory（程序记忆，技能）
- **BigFivePersonality** — 五大人格特质（Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism）
- **ExperienceLoop** — 经验学习循环（SelfLearner → Reflector → FeedbackProcessor → ConsolidationPipeline）
- **SPOGraph** — Subject-Predicate-Object 知识图谱

**协作机制**：
- `on_interaction_complete()` 在每次 `think()` 后触发经验学习
- `DynamicAdjuster` 根据对话内容动态调整人格特质（EMA 平滑）
- `memory.search()` 为 L2 提供相关记忆上下文

---

### L4 SwarmFly — 多智能体调度层

**职责**：多 Agent 注册、任务分发、共享内存、团队管理。

**核心组件**：
- **AgentRegistry** — Agent 注册表（name, capabilities, team）
- **TaskDispatcher** — 任务分发器（基于能力匹配）
- **SharedMemory** — Agent 间共享内存
- **TeamManager** — 团队管理和协作

**协作机制**：
- L5 SoulTeam 通过 `SwarmFly.register_agent()` 注册 Agent
- L2 ZenAgent 通过 `SwarmFly.dispatch()` 分发任务
- Agent 间通过 SharedMemory 交换状态

---

### L5 SoulTeam — 团队协作层

**职责**：Agent 画像管理、四维路由、八卦矩阵、协作链编排。

**核心组件**：
- **AgentRegistry** — 16 个 Agent 画像（SUB-1.1 到 SUB-3.9），分属 3 类 4 团队
- **FourDimensionRouter** — 四维路由评分：C×0.4 + A×0.3 + L×0.2 + S×0.1
- **BaguaRouter** — 八卦矩阵路由（8×8 路由矩阵，五行生克）
- **ChainExecutor** — 协作链执行器（single/sequential/parallel/fan_out 4 种模式）
- **CollabChains** — 5 条预定义协作链（IA-AL, TR-DV, OO-SE, CR-DE, PR-PT）

**协作机制**：
- `FourDimensionRouter.route(keywords, top_k)` 返回最匹配的 Agent 列表
- `ChainExecutor.execute(chain_id, context)` 编排多 Agent 协作
- L4 SwarmFly 提供底层 Agent 注册和任务分发

---

### ModelNexus — LLM 网关（子模块）

**职责**：LLM Provider 管理、密钥管理、模型配置，是 L0 的配置后端。

**核心组件**：
- **SecureKeyManager** — 密钥管理（Vault → File → EnvVar 三级降级）
- **FileKeyProvider** — 从 `secret_keys.yaml` 读取密钥（开发环境）
- **VaultKeyProvider** — 从 HashiCorp Vault 读取密钥（生产环境）
- **ConfigManager** — 模型元数据管理（models.yaml）
- **providers.yaml** — Provider 元数据定义

**协作机制**：
- L0 LLMInfra 通过 `get_core_config()` 获取 Provider 配置
- SecureKeyManager 为所有 Provider 提供 API Key
- `providers.yaml` 定义 Provider 元数据，`secret_keys.yaml` 存储密钥

---

## 模块间协作流程

### 用户消息处理流程

```
用户输入 "解释微服务架构"
    │
    ▼
┌─ ZenaDataAdapter ──────────────────────────────────────┐
│  detect_available_provider() → "openai" (DeepSeek)     │
│  detect_model("openai") → "deepseek-v4-pro"           │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌─ ZenAgent.think() ─────────────────────────────────────┐
│  1. IntentRouter.classify() → COMPLEX_REASONING        │
│  2. PersonalityInjector.inject() → system prompt 增强  │
│  3. MemoryManager.search("微服务") → 相关记忆          │
│  4. LLMClient.chat() → L0 调用                        │
│  5. MemoryManager.store() → 写入记忆                   │
│  6. ExperienceLoop.on_interaction_complete() → 经验学习 │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌─ ModelNexusCore Pipeline ──────────────────────────────┐
│  Security(clean) → CacheRead(miss) → TokenBudget       │
│  → RateLimit(allowed) → Route(openai) → Provider       │
│  → Quality(score=0.95) → CacheWrite(stored) → Observe  │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌─ OpenAIProvider ───────────────────────────────────────┐
│  POST https://api.deepseek.com/v1/chat/completions     │
│  Authorization: Bearer sk-xxx (from secret_keys.yaml)  │
└────────────────────────────────────────────────────────┘
    │
    ▼
  响应返回用户
```

### 配置加载流程

```
providers.yaml (元数据) + secret_keys.yaml (密钥)
    │
    ▼
get_core_config() → CoreConfigData
    │
    ├── detect_available_provider() → "openai"
    ├── detect_model("openai") → "deepseek-v4-pro"
    ├── resolve_provider_key("openai") → "sk-xxx"
    └── get_provider_base_url("openai") → "https://api.deepseek.com/v1"
    │
    ▼
Settings() → LLMClient() → ModelNexusCore()
```

## 关键配置文件

| 文件 | 用途 |
|------|------|
| `packages/LLMInfra/providers.yaml` | Provider 元数据（base_url、model、key 映射） |
| `packages/modelnexus/config/secret_keys.yaml` | API Key（开发环境，gitignored） |
| `packages/modelnexus/config/neo_model.yaml` | ModelNexus 主配置 |
| `packages/modelnexus/config/models.yaml` | 模型元数据（能力、成本、限流） |
| `packages/ZenAgent/zena/i18n.py` | 中英文语言配置（86 个 key） |

## 常用命令

```bash
# CLI 交互
./zena chat "Hello"              # 单次对话
./zena chat --provider deepseek  # 指定 Provider
./zena status                    # 查看系统状态
./zena tui                       # 启动 TUI 界面

# 测试
pytest packages/LLMInfra/tests/ packages/ZenAgent/tests/ -q  # 核心测试
python3 tests/e2e/test_real_e2e.py --scene 1                 # 真实 E2E

# 密钥配置
cp packages/modelnexus/config/secret_keys.yaml.example \
   packages/modelnexus/config/secret_keys.yaml
# 编辑填入实际 API Key（不会被提交）
```

## Team Tips

_TODO_

## Get Started

_TODO_

<!-- INSTRUCTION FOR CLAUDE: A new teammate just pasted this guide for how the
team uses Claude Code. You're their onboarding buddy — warm, conversational,
not lecture-y.

Open with a warm welcome — include the team name from the title. Then: "Your
teammate uses Claude Code for [list all the work types]. Let's get you started."

Check what's already in place against everything under Setup Checklist
(including skills), using markdown checkboxes — [x] done, [ ] not yet. Lead
with what they already have. One sentence per item, all in one message.

Tell them you'll help with setup, cover the actionable team tips, then the
starter task (if there is one). Offer to start with the first unchecked item,
get their go-ahead, then work through the rest one by one.

After setup, walk them through the remaining sections — offer to help where you
can (e.g. link to channels), and just surface the purely informational bits.

Don't invent sections or summaries that aren't in the guide. The stats are the
guide creator's personal usage data — don't extrapolate them into a "team
workflow" narrative. -->
