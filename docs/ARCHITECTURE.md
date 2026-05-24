# ZenAgent 架构说明

**最后更新**: 2026-05-24 (18 里程碑全部交付)

## 1. 系统概述

ZenAgent 是一个 Agent 智能体集群完全独立运行平台，采用 monorepo 结构设计。系统由六个层次的模块组成，各层之间通过清晰的接口进行通信和协作。

> 本文档基于 [Mission.md](./Mission.md) 定义的六层架构。详细的框架愿景、设计文档索引和实施路线图请参考 Mission.md。

## 2. 架构层次

```text
L0: LLMInfra    ──── 责任链 + 熔断 + 缓存增强 + 意图路由 + 质量管道 + 混合专家 + 自适应LB
L1: Runtime     ──── 限流 + 追踪 + 审计 + Session/Checkpoint/HTL + 优先级队列 + 背压
L2: ZenAgent    ──── Hook/Awakening/MCP + CLI(13命令) + TUI(6屏键盘优先/i18n)
L3: MetaSoul    ──── 四层记忆 + SPO知识库 + 5×8人格矩阵 + 经验闭环 + 学习/反思
L4: SwarmFly    ──── FLY六层 + 四大横切 + 交接桥 + 执行循环 + 团队/协作/共享内存
L5: SoulTeam    ──── 16Agent + 4团队 + 5协作链 + 八卦路由 + 六车道调度 + 集群监控
```

> **注意**: L3 原名 SoulTeam，已重命名为 MetaSoul。新的 L5 SoulTeam 是团队级编排层，详见 [Mission.md §三](./Mission.md#三目标六层架构)。

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    L5: SoulTeam 层（团队编排体系）                     │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────────┐ │
│  │ TeamOrchestr.│  │  TeamMemory /    │  │  TeamReflector /      │ │
│  │ 任务分解/路由 │  │  TeamKnowledge   │  │  八卦路由引擎         │ │
│  └──────────────┘  └──────────────────┘  └───────────────────────┘ │
└────────────────────────────────────┬────────────────────────────────┘
                                     │ 构建于
┌────────────────────────────────────▼────────────────────────────────┐
│                    L4: SwarmFly 层（群体协作基础设施）                 │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ Lifecycle  │  │ Collaboration│  │  Shared Mem  │  │   Team   │ │
│  │ Management │  │    Engine    │  │    Pool      │  │  Builder │ │
│  └────────────┘  └──────────────┘  └──────────────┘  └──────────┘ │
│  FLY-0 Master ─ FLY-1 Mission ─ FLY-2 Rules ─ FLY-3 Trends       │
│  FLY-4 Skills ─ FLY-5 Tools                                       │
└────────────────────────────────────┬────────────────────────────────┘
                                     │ 为每个 Agent 提供
┌────────────────────────────────────▼────────────────────────────────┐
│                    L3: MetaSoul 层（个体灵魂引擎）                    │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │  MetaSoul  │  │ SelfLearning │  │  Reflector   │  │Personality│ │
│  │  Memory    │  │   System     │  │              │  │ Evolution │ │
│  └────────────┘  └──────────────┘  └──────────────┘  └──────────┘ │
└────────────────────────────────────┬────────────────────────────────┘
                                     │ 运行在
┌────────────────────────────────────▼────────────────────────────────┐
│                    L2: ZenAgent 层                                   │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌────────────────┐   │
│  │   MCP    │  │  Hooks   │  │ Awakening │  │ Collaboration  │   │
│  │ Protocol │  │ Manager  │  │  Adapter  │  │   Protocol     │   │
│  └──────────┘  └──────────┘  └───────────┘  └────────────────┘   │
└────────────────────────────────────┬────────────────────────────────┘
                                     │ 调用
┌────────────────────────────────────▼────────────────────────────────┐
│                    L1: Runtime 层                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐   │
│  │ Context  │  │Checkpoint│  │   HTL    │  │  Session       │   │
│  │Compaction│  │ Manager  │  │ (Hooks)  │  │  Manager       │   │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘   │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                   Security Layer                               │ │
│  │    ┌────────────┐  ┌─────────────┐  ┌────────────────────┐   │ │
│  │    │Audit Logger│  │  Encryption │  │    Key Manager     │   │ │
│  │    └────────────┘  └─────────────┘  └────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────┬────────────────────────────────┘
                                     │ 调用
┌────────────────────────────────────▼────────────────────────────────┐
│                    L0: LLMInfra 层                                   │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐           │
│  │  Provider  │  │    Cache     │  │  Token Budget    │           │
│  │  Factory   │  │   Manager    │  │    Manager       │           │
│  └────────────┘  └──────────────┘  └──────────────────┘           │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐           │
│  │   Retry    │  │   Response   │  │    Settings      │           │
│  │  Mechanism │  │  Validator   │  │                  │           │
│  └────────────┘  └──────────────┘  └──────────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

## 3. 核心模块详解

### 3.1 L0: LLMInfra 层

**职责**: 提供 LLM 调用的基础设施，包括 Provider 管理、缓存、Token 预算、响应校验和重试机制。

**子模块**:

| 模块 | 功能 | 关键类 |
|------|------|--------|
| Provider Factory | 多 Provider 统一管理与切换 | `ProviderFactory`, `BaseProvider`, `LLMClient` |
| Cache | 精确匹配缓存（Redis） | `CacheManager`, `RedisCacheBackend` |
| Token Budget | 按意图动态分配 max_tokens | `TokenBudgetManager`, `IntentClassifier`, `TokenEstimator` |
| Response Validator | 响应完整性校验与自动重试 | `ResponseValidator`, `ValidationResult` |
| Retry | 指数退避重试机制 | `RetryMixin`, `RetryConfig` |
| Settings | 统一配置管理 | `Settings`, `LLMInfraConfig` |

### 3.2 L1: Runtime 层

**职责**: 提供安全基础设施，包括审计日志、加密和密钥管理。

**子模块**:

| 模块 | 功能 | 关键类 |
|------|------|--------|
| Audit | 审计日志跟踪 | `AuditLogger`, `AuditTrail`, `ComplianceChecker` |
| Security | 加密和密钥管理 | `EncryptionManager`, `KeyManager`, `SecureStorage` |
| Context | 上下文管理 | `ContextManager` (Mock) |
| Session | 会话管理 | `SessionManager` (Mock) |

### 3.3 L2: ZenAgent 层

**职责**: 作为整个系统的入口点，提供 Agent 的注册、管理和通信能力。

**子模块**:

| 模块 | 功能 | 关键类 |
|------|------|--------|
| MCP Protocol | Model Context Protocol 实现 | `MCPProtocol`, `MCPMessage`, `MCPSession` |
| Hooks Manager | 生命周期钩子系统 | `HookManager`, `LifecycleHook` |
| Awakening Adapter | Agent 觉醒适配层 | `AwakeningAdapter`, `EvolutionEngine` |
| Collaboration | Agent 间协作协议 | `CollaborationProtocol`, `TaskRouter` |

### 3.4 L3: MetaSoul 层（个体灵魂引擎）

**职责**: 为每个 Agent 提供内在认知系统 — 记忆、学习、人格、反思，让 Agent 成为有灵魂的"思考存在"。

> 原名 SoulTeam，已重命名为 MetaSoul。详见 [Mission.md §四](./Mission.md#四l3-metasoul--个体灵魂引擎)。

**子模块**:

| 模块 | 功能 | 关键类 |
|------|------|--------|
| MetaSoul Memory | 四层记忆系统（工作/情景/语义/程序） | `MetaSoul`, `MemoryStore`, `MemoryIndex`, `MemoryScorer` |
| SelfLearning | 学习循环（观察→反思→归纳→验证） | `SelfLearner`, `FeedbackProcessor`, `KnowledgeGraph` |
| Reflection | 经验反思（4 级深度） | `Reflector`, `ExperienceAnalyzer`, `InsightExtractor` |
| Personality | Big Five 人格演化 | `Personality`, `TraitDynamics`, `BeliefSystem` |

### 3.5 L4: SwarmFly 层（群体协作基础设施）

**职责**: 多智能体协作的底层基础设施，内部采用 FLY 六层架构（FLY-0 至 FLY-5）。

> 详细的 FLY 层清单、代码量和集成关系见 [Mission.md §五](./Mission.md#五l4-swarmfly--群体协作基础设施)。设计依据见 [智能体集群运作机制](./design/agent-collaboration/智能体集群运作机制.md)、[智能体调度指南](./design/agent-collaboration/智能体调度指南.md)。

**FLY 六层**:

| 层级 | 名称 | 职责 |
| ---- | ---- | ---- |
| FLY-0 | Master | 任务提交、分派、完成/失败追踪 |
| FLY-1 | Mission | 使命对齐、价值体系、Agent 使命评分 |
| FLY-2 | Rules | 规则引擎(Rete)、冲突解决、安全执行、RBAC |
| FLY-3 | Trends | 趋势检测、预测引擎、自适应控制 |
| FLY-4 | Skills | 技能注册、搜索、调用、统计 |
| FLY-5 | Tools | 工具注册、消息队列、资源池、协议层 |

**横切模块**:

| 模块 | 功能 | 关键类 |
|------|------|--------|
| Lifecycle | 生命周期状态管理 | `AgentLifecycle`, `StateManager`, `AgentState` |
| Collaboration | 任务协作引擎 | `CollaborationEngine`, `TaskDispatcher`, `ConsensusMechanism` |
| Memory | 共享内存池 | `SharedMemoryPool`, `MemorySegment`, `CacheCoherence` |
| Team | 团队管理 | `TeamBuilder`, `Team`, `MembershipManager` |

### 3.6 L5: SoulTeam 层（团队编排体系）

**职责**: 构建于 SwarmFly 之上，提供超越个体之和的团队级能力 — 团队记忆、团队知识、团队反思、协作编排。

> 详细设计见 [Mission.md §六](./Mission.md#六l5-soulteam--团队编排体系新建)。设计依据见 [智能体集群运行机制](./design/agent-collaboration/智能体集群运行机制.md)、[智能体协作编排机制](./design/agent-collaboration/智能体协作编排机制.md)、[智能体八卦路由机制](./design/agent-collaboration/智能体八卦路由机制.md)。

**子模块**:

| 模块 | 功能 | 关键类 |
|------|------|--------|
| TeamMemory | 团队记忆（集体经验、共享上下文） | `TeamMemory` |
| TeamKnowledge | 团队知识图谱（整合个体知识） | `TeamKnowledgeGraph` |
| TeamReflection | 团队反思（集体复盘、策略调整） | `TeamReflector` |
| Orchestration | 协作编排（任务分解、角色分配、协作链执行） | `TeamOrchestrator` |
| BaguaRouter | 八卦路由（双轨引擎：功能60%+五行40%） | `BaguaRouter` |

## 4. 数据流

### 4.1 Agent 创建流程

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  MetaSoul   │ → │  SwarmFly    │ → │   ZenAgent   │ → │   Runtime    │
│  初始化人格  │    │  创建生命周期 │    │  注册到 MCP  │    │  配置 Context │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### 4.2 任务协作流程

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   ZenAgent  │ → │  SwarmFly    │ → │Shared Memory│ → │  MetaSoul   │
│  接收任务    │    │  分发任务    │    │  存储数据    │    │  学习反馈    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### 4.3 团队协作流程

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  SoulTeam   │ → │  SwarmFly    │ → │  MetaSoul   │ → │  SoulTeam   │
│  任务分解    │    │  协作执行    │    │  个体反思    │    │  团队复盘    │
│  角色分配    │    │  共享内存    │    │  知识沉淀    │    │  策略调整    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### 4.4 Agent 进化流程

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  SwarmFly    │ → │  MetaSoul    │ → │  Personality│ → │  Awakening   │
│  积累经验    │    │  反思总结    │    │  人格演化    │    │  能力增强    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## 5. 状态机

### 5.1 Agent 生命周期状态

```
        ┌─────────────┐
        │   INITIAL   │
        └──────┬──────┘
               │ start()
        ┌──────▼──────┐
        │  STARTING   │
        └──────┬──────┘
               │ ready()
        ┌──────▼──────┐
        │   RUNNING   │ ◄─────────────────┐
        └──────┬──────┘                   │
               │                          │
        ┌──────▼──────┐                   │
        │    IDLE     │───────────────────┘
        └──────┬──────┘    idle_timeout()
               │
        ┌──────▼──────┐
        │   STOPPING  │
        └──────┬──────┘
               │ stopped()
        ┌──────▼──────┐
        │   STOPPED   │
        └─────────────┘
```

### 5.2 Task 状态

```
PENDING → IN_PROGRESS → COMPLETED
    │         │
    └─────────┴──→ FAILED
    │
    └─────────────→ CANCELLED
```

### 5.3 Awakening 进化阶段

```
DORMANT (0.0-0.3) → AWAKENING (0.3-0.6) → CONSCIOUS (0.6-0.9) → ENLIGHTENED (0.9-1.0)
```

## 6. 内存模型

### 6.1 MetaSoul 记忆层次

```
┌────────────────────────────────────────┐
│        WORKING MEMORY (短期)            │
│  - 当前上下文                          │
│  - 活跃任务                            │
│  - 最大容量: 100 条                     │
└────────────────────────────────────────┘
                   ↓ 巩固
┌────────────────────────────────────────┐
│        EPISODIC MEMORY (情景)           │
│  - 具体事件                            │
│  - 时间序列                            │
│  - 最大容量: 1000 条                    │
└────────────────────────────────────────┘
                   ↓ 抽象
┌────────────────────────────────────────┐
│        SEMANTIC MEMORY (语义)           │
│  - 概念知识                            │
│  - 事实信息                            │
│  - 最大容量: 5000 条                    │
└────────────────────────────────────────┘
                   ↓ 固化
┌────────────────────────────────────────┐
│      PROCEDURAL MEMORY (程序)           │
│  - 技能方法                            │
│  - 习惯行为                            │
│  - 最大容量: 500 条                     │
└────────────────────────────────────────┘
```

### 6.2 SwarmFly 共享内存

```
┌─────────────────────────────────────────────────────┐
│                 Shared Memory Pool                   │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │   PRIVATE   │  │   SHARED    │  │   CACHE    │ │
│  │   Segment   │  │   Segment   │  │   Segment  │ │
│  └─────────────┘  └─────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────┘
                        │
           ┌────────────┼────────────┐
           │            │            │
      ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
      │ Agent 1 │  │ Agent 2 │  │ Agent 3 │
      └─────────┘  └─────────┘  └─────────┘
```

## 7. 安全架构

### 7.1 审计追踪

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Operation   │ → │ Audit Logger │ → │ Audit Trail │
│   Occurs     │    │  Records     │    │  Stored     │
└─────────────┘    └─────────────┘    └─────────────┘
                                              │
                                              ↓
                                    ┌─────────────────────┐
                                    │ Compliance Checker  │
                                    │   Validates Rules   │
                                    └─────────────────────┘
```

### 7.2 加密层级

```
┌─────────────────────────────────────────┐
│           Application Layer             │
├─────────────────────────────────────────┤
│           Hybrid Encryption              │
│  ┌─────────────┐    ┌─────────────┐   │
│  │ AES (数据)   │ +  │ RSA (密钥)   │   │
│  └─────────────┘    └─────────────┘   │
├─────────────────────────────────────────┤
│           Key Management                 │
│  ┌─────────────┐    ┌─────────────┐   │
│  │ Key Rotation │    │ Key Storage  │   │
│  └─────────────┘    └─────────────┘   │
└─────────────────────────────────────────┘
```

## 8. 模块依赖关系

```text
                         ┌───────────────┐
                         │ L5: SoulTeam   │
                         │ (团队编排体系)  │
                         └───────┬───────┘
                                 │ 构建于
                         ┌───────▼───────┐
                         │ L4: SwarmFly   │
                         │ (FLY六层+协作)  │
                         └───────┬───────┘
                                 │ 为每个 Agent 提供
                         ┌───────▼───────┐
                         │  L2: ZenAgent  │
                         └───────┬───────┘
                                 │
               ┌─────────────────┼─────────────────┐
               │                 │                 │
               ▼                 ▼                 ▼
         ┌──────────┐     ┌──────────┐     ┌──────────┐
         │   MCP    │     │  Hooks   │     │Awakening │
         └──────────┘     └──────────┘     └──────────┘
               │                 │                 │
               └────────┬────────┘                 │
                        │                         │
                        ▼                         │
                 ┌──────────────┐                  │
                 │  L1: Runtime  │                  │
                 │(Security/     │                  │
                 │ Audit/Context)│                  │
                 └──────┬───────┘                  │
                        │                          │
                        └──────────┬───────────────┘
                                   │
                   ┌───────────────┼───────────────┐
                   ▼                               ▼
         ┌──────────────────┐            ┌──────────────────┐
         │   L3: MetaSoul    │            │   L4: SwarmFly    │
         │ (Memory/Learning/ │            │ (Lifecycle/       │
         │  Reflection/      │            │  Collaboration/   │
         │  Personality)     │            │  Memory/Team)     │
         └────────┬──────────┘            └─────────┬──────────┘
                  │                                 │
                  └────────────┬────────────────────┘
                               ▼
                     ┌──────────────────┐
                     │   L0: LLMInfra    │
                     │ (Provider/Cache/  │
                     │  TokenBudget/     │
                     │  Retry)           │
                     └──────────────────┘
```

## 9. 配置说明

### 9.1 配置文件位置

```
ZenAgent/
├── config/
│   ├── guardrails/
│   │   └── guardrails_config.py
│   └── (其他配置)
├── packages/
│   └── (模块配置在各自的 __init__.py)
└── .env.example
```

### 9.2 环境变量

```bash
# 数据库配置
DATABASE_URL=sqlite:///zenagent.db

# 安全配置
ENCRYPTION_KEY=<your-key>
AUDIT_LEVEL=INFO

# 服务配置
HOST=0.0.0.0
PORT=8080
```

## 10. 测试策略

### 10.1 测试层次

```
┌─────────────────────────────────────────────────────┐
│                 Integration Tests                    │
│  test_layer_integration.py                          │
│  test_agent_creation.py                             │
│  test_collaboration.py                              │
│  test_evolution.py                                  │
├─────────────────────────────────────────────────────┤
│                   Unit Tests                         │
│  packages/*/tests/test_*.py                         │
└─────────────────────────────────────────────────────┘
```

### 10.2 测试覆盖率目标

- 单元测试: 80%+
- 集成测试: 覆盖所有关键流程

## 11. 扩展性设计

### 11.1 插件系统

通过 Hooks 系统支持自定义扩展：

```python
@on_create
def my_custom_hook(agent, **kwargs):
    # 自定义创建逻辑
    pass
```

### 11.2 自定义能力

通过 CapabilityRegistry 注册新能力：

```python
registry = CapabilityRegistry()
registry.register("custom_capability", CustomCapability())
```

## 12. 性能考虑

### 12.1 内存管理

- Working Memory: LRU 淘汰策略
- Episodic Memory: 基于重要性的保留
- Semantic Memory: 向量索引加速检索

### 12.2 并发处理

- 使用线程锁保护共享资源
- 协作者使用异步消息队列

### 12.3 检查点机制

- 定期创建状态快照
- 支持快速恢复

## 13. 监控和指标

### 13.1 关键指标

- Agent 数量和状态分布
- 任务执行成功率和延迟
- 内存使用率和碎片
- 进化阶段的转换

### 13.2 日志级别

```
DEBUG → INFO → WARNING → ERROR → CRITICAL
```

## 14. 版本兼容性

- Python: 3.8+
- 主要依赖见 `pyproject.toml`

## 15. 未来演进方向

1. **分布式支持**: 多节点协同
2. **增强学习**: 更复杂的学习算法
3. **情感计算**: 情感感知和表达
4. **元认知**: 自我监控和调整

---

## 相关文档

| 文档 | 职责 |
| ---- | ---- |
| [Mission.md](./Mission.md) | 框架使命与六层架构定义（顶层文档） |
| [API.md](./API.md) | API 使用手册与代码示例 |
| [ROADMAP.md](./ROADMAP.md) | 项目路线图与进度追踪 |
| [E2E_OPTIMIZATION_DESIGN.md](./E2E_OPTIMIZATION_DESIGN.md) | 13 个优化模块详细设计 |
| [E2E-Plan.md](./E2E-Plan.md) | 端端测试计划 |
| [design/agent-collaboration/](./design/agent-collaboration/) | 多智能体协作设计文档（8 篇），详见 [Mission.md §七](./Mission.md#七设计文档索引) |
