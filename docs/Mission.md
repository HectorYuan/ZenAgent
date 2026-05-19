# ZenAgent 框架使命

**最后更新**: 2026-05-19
**定位**: ZenAgent 多智能体集群自主运行平台 — 顶层使命文档

---

## 一、框架愿景

ZenAgent 不是一个简单的 Agent 框架。它是一个**多智能体集群自主运行平台**，目标是让一群具备独立灵魂的智能体像人类团队一样协作、学习、进化。

核心公式：

```text
Agent = Model + Harness + Skill + Calendar
```

- **Model**: LLM 推理能力（L0: LLMInfra）
- **Harness**: 运行时约束与安全（L1: Runtime）
- **Skill**: 工具与技能（L4: SwarmFly fly4skills/fly5tools）
- **Calendar**: 任务调度与生命周期（L4: SwarmFly lifecycle/collaboration）

但仅有这些还不够。一个真正的团队，每个成员需要有自己的**灵魂**（记忆、人格、学习能力），而团队本身也需要超越个体之和的**集体智慧**（团队记忆、团队知识、协作编排）。

这就是 ZenAgent 六层架构的由来。

---

## 二、当前架构现状与问题

### 2.1 代码现状

| 层级 | 包名 | 代码量 | 状态 |
| ---- | ---- | ------ | ---- |
| L0 | LLMInfra | ~3,000 行 | ✅ 完整：Provider、缓存、Token 预算、响应校验、重试 |
| L1 | Runtime | ~2,000 行 | ✅ 完整：审计、加密、会话、上下文 |
| L2 | ZenAgent | ~1,500 行 | ✅ 完整：MCP、Hooks、Awakening、Collaboration |
| L3 | SoulTeam（应为 MetaSoul） | 8,651 行 | ⚠️ 功能完整但命名错误 |
| L4 | SwarmFly | 34,297 行 | ⚠️ 代码丰富但大量未整合 |
| L5 | SoulTeam（应新建） | 0 行 | ❌ 不存在 |

### 2.2 核心问题

**问题 1：SoulTeam 名不副实**

当前 `packages/SoulTeam/` 的 8,651 行代码 100% 是**个体级**功能：
- MetaSoul 记忆系统（4 层记忆、遗忘曲线、评分淘汰）
- SelfLearner 学习系统（观察→反思→归纳→验证循环）
- Personality 人格系统（Big Five、信念、价值观）
- Reflector 反思系统（经验分析、模式识别、洞察提取）

没有一行代码涉及团队协作、知识共享、集体记忆。"SoulTeam" 这个名字严重误导。

**问题 2：SwarmFly 代码未充分利用**

`packages/SwarmFly/` 拥有 34,297 行代码，其中大量模块已完整实现但未被整合：

| 模块 | 代码量 | 实现状态 | 整合状态 |
| ---- | ------ | -------- | -------- |
| team/ (TeamBuilder, Membership, Formation, Roles) | 2,685 行 | ✅ 完整 | ❌ 未接入主流程 |
| collaboration/ (Engine, Dispatcher, LoadBalancer, Consensus) | 2,766 行 | ✅ 完整 | ❌ 未接入主流程 |
| memory/ (SharedPool, LockManager, SyncProtocol, Coherence) | 2,382 行 | ✅ 完整 | ❌ 未接入主流程 |
| lifecycle/ (AgentLifecycle, StateManager, Transitions) | 907 行 | ✅ 完整 | ⚠️ 测试覆盖但未集成 |
| fly2rules/ (Rete 引擎、死锁检测、资源仲裁) | 5,380 行 | ✅ 完整 | ❌ 未接入主流程 |
| fly3trends/ (趋势分析、预测引擎、自适应控制) | 3,042 行 | ✅ 完整 | ❌ 未接入主流程 |
| fly5tools/ (消息队列、工具注册、资源池) | 2,062 行 | ✅ 完整 | ❌ 未接入主流程 |
| S1_Evolution/ (EvolveEngine, ZenLoop) | 4,773 行 | ⚠️ Mock 模式 | ❌ 未实现真实逻辑 |

**问题 3：设计愿景未落地**

`docs/design/agent-collaboration/` 描述了完整的多智能体集群运作机制：
- 16 个专业 Agent，4 个团队
- 四维评分路由（能力 40% + 可用性 30% + 负载 20% + 技能 10%）
- 八卦路由机制（8 种任务方向映射）
- 5 条协作链模板
- 任务状态机（6 状态）

这些设计在代码层完全没有体现。

---

## 三、目标六层架构

```text
L0: LLMInfra    ──── LLM 基础设施（Provider、缓存、Token 管理）
L1: Runtime     ──── 运行时（事件总线、会话、安全、审计）
L2: ZenAgent    ──── 单智能体核心（MCP、Hooks、Awakening）
L3: MetaSoul    ──── 个体灵魂引擎（记忆、学习、人格、反思）
L4: SwarmFly    ──── 群体协作基础设施（生命周期、协作、共享内存、工具）
L5: SoulTeam    ──── 团队编排体系（团队记忆、团队知识、协作编排）
```

### 层级关系

```text
┌─────────────────────────────────────────────────────────┐
│                    L5: SoulTeam                          │
│  团队编排 ─ 团队记忆 ─ 团队知识 ─ 协作链 ─ 集体反思       │
│  (总体大于部分之和)                                       │
└───────────────────────────┬─────────────────────────────┘
                            │ 构建于
┌───────────────────────────▼─────────────────────────────┐
│                    L4: SwarmFly                          │
│  生命周期 ─ 协作引擎 ─ 共享内存 ─ 团队管理 ─ 工具/技能    │
│  (34,297 行已有代码，需要整合)                            │
└───────────────────────────┬─────────────────────────────┘
                            │ 为每个 Agent 提供
┌───────────────────────────▼─────────────────────────────┐
│                    L3: MetaSoul                          │
│  个体记忆 ─ 个体学习 ─ 个体人格 ─ 个体反思                │
│  (原 SoulTeam，8,651 行，重命名)                         │
└───────────────────────────┬─────────────────────────────┘
                            │ 运行在
┌───────────────────────────▼─────────────────────────────┐
│              L2: ZenAgent → L1: Runtime → L0: LLMInfra   │
│  (不变)                                                   │
└─────────────────────────────────────────────────────────┘
```

---

## 四、L3: MetaSoul — 个体灵魂引擎

> 原 `packages/SoulTeam/`，重命名为 `packages/MetaSoul/`

MetaSoul 是每个 Agent 的内在认知系统，让 Agent 成为一个有记忆、能学习、会反思、有个性的"思考存在"。

### 4.1 记忆系统 (memory/)

| 模块 | 职责 |
| ---- | ---- |
| MetaSoul | 核心记忆引擎（存储、检索、关联、淘汰） |
| MemoryHierarchy | 四层记忆架构（工作/情景/语义/程序） |
| MemoryStore | 可插拔存储后端（内存/文件） |
| MemoryIndex | 混合检索（倒排索引 + 向量索引） |
| MemoryScorer | 统一评分器（重要性 + 频率 + 时效 + 情感） |
| ForgettingMechanism | 遗忘机制（指数衰减、记忆整合） |

### 4.2 学习系统 (learning/)

| 模块 | 职责 |
| ---- | ---- |
| SelfLearner | 学习循环（观察→反思→归纳→验证→整合） |
| KnowledgeGraph | 知识图谱（实体/关系/推理/遍历） |
| SkillAcquisition | 技能获取（模仿学习、强化学习、知识蒸馏） |
| FeedbackProcessor | 反馈处理（来源评估、权重调整、洞察生成） |
| LearningOptimizer | 学习优化（课程学习、迁移学习、领域掌握） |

### 4.3 反思系统 (reflection/)

| 模块 | 职责 |
| ---- | ---- |
| Reflector | 反思引擎（4 级深度：表面/因果/意义/转化） |
| ExperienceAnalyzer | 经验分析（模式识别、趋势分析、相似度） |
| InsightExtractor | 洞察提取（因果/相关/时间/过程） |
| PatternRecognizer | 模式识别（序列/循环/习惯/异常） |

### 4.4 人格系统 (personality/)

| 模块 | 职责 |
| ---- | ---- |
| Personality | Big Five 人格模型（特质演化、行为预测） |
| TraitDynamics | 特质动力学（环境因素、变化趋势） |
| BeliefSystem | 信念系统（创建/强化/挑战/矛盾解决） |
| ValueEvolution | 价值观演化（优先级、对齐评估、冲突解决） |

---

## 五、L4: SwarmFly — 群体协作基础设施

SwarmFly 是多智能体协作的底层基础设施，已有 **34,297 行代码**。它内部采用 **FLY 六层架构**（FLY-0 至 FLY-5），每层有独立的深层实现目录。当前任务是**整合已有模块**，而非重新实现。

### 5.1 FLY 六层架构

```text
┌─────────────────────────────────────────────────────────────┐
│                     SwarmFly 内部架构                        │
│                                                              │
│  FLY-5: Tools ──── 工具注册、消息队列、资源池、协议层          │
│  FLY-4: Skills ─── 技能注册、搜索、调用、统计                 │
│  FLY-3: Trends ─── 趋势检测、预测引擎、自适应控制、涌现检测    │
│  FLY-2: Rules ──── 规则引擎(Rete)、冲突解决、安全执行、RBAC    │
│  FLY-1: Mission ── 使命对齐、价值体系、Agent 使命评分          │
│  FLY-0: Master ─── 任务提交、分派、完成/失败追踪              │
│                                                              │
│  横切关注点: lifecycle/ | collaboration/ | memory/ | team/    │
│  组合入口: core.py (SwarmFly 主类) + core/fly_layers.py      │
└─────────────────────────────────────────────────────────────┘
```

#### FLY-0: Master Agent（主控层）

**目录**: `core/fly_layers.py` (内联) + `team/` (深层实现)
**代码量**: ~3,065 行 (team/)

| 模块 | 职责 |
| ---- | ---- |
| TeamBuilder | 团队创建/解散/成员管理 |
| MembershipManager | 成员角色、绩效、请求管理 |
| FormationManager | 5 种编队（扁平/层级/星型/环形/链式） |
| RoleRegistry | 8+ 角色定义（leader/worker/specialist...） |
| TeamProtocol | Agent 间消息协议（pub/sub、心跳） |
| SubAgentManager | 4 类子 Agent 工厂 |

**集成点**: → L5 SoulTeam 通过 TeamOrchestrator 调用 TeamBuilder 创建/管理团队

#### FLY-1: Mission（使命层）

**目录**: `fly1mission/` + `core/fly_layers.py`
**代码量**: ~434 行

| 模块 | 职责 |
| ---- | ---- |
| MissionAlignment | Agent 使命对齐评分（当前任务 vs Agent 核心使命） |
| ValueSystem | 价值体系定义与评估 |

**集成点**: → L3 MetaSoul 的 Personality/ValueEvolution 提供个体价值输入 → L5 SoulTeam 的 TeamOrchestrator 用于团队任务分配时的使命匹配

#### FLY-2: Rules（规则层）

**目录**: `fly2rules/` + `core/fly_layers.py`
**代码量**: ~7,091 行

| 模块 | 代码量 | 职责 |
| ---- | ------ | ---- |
| Rete 引擎 (Alpha/Beta 节点) | 693 行 | 前向链推理 |
| 死锁检测 (Wait-for Graph) | 502 行 | 资源死锁检测 |
| 资源仲裁 | 444 行 | 优先级资源分配 |
| RBAC 权限 | 491 行 | 角色权限检查 |
| ConflictResolver | ~550 行 | 6 种冲突解决策略 |
| SecurityEnforcer | ~300 行 | 安全策略执行 |

**集成点**: → L5 SoulTeam 的 TeamOrchestrator 使用规则引擎做任务路由决策 → L4 collaboration/ 的 ConflictResolver 冲突解决时调用 RBAC 和死锁检测

#### FLY-3: Trends（趋势层）

**目录**: `fly3trends/` + `core/fly_layers.py`
**代码量**: ~3,131 行

| 模块 | 代码量 | 职责 |
| ---- | ------ | ---- |
| TrendAnalyzer | 356 行 | 趋势聚合与评分 |
| PredictionEngine | 373 行 | 线性/指数/移动平均预测 |
| AdaptiveController | 412 行 | 策略优化、资源弹性伸缩 |
| EmergentDetector | 323 行 | 涌现模式检测 |

**集成点**: → L3 MetaSoul 的 Reflector 提供个体反思数据 → L5 SoulTeam 的 TeamReflector 聚合为团队级趋势洞察

#### FLY-4: Skills（技能层）

**目录**: `fly4skills/` + `core/fly_layers.py`
**代码量**: ~582 行

| 模块 | 职责 |
| ---- | ---- |
| SkillRegistry | 技能注册、搜索、调用 |
| SkillMatcher | 按任务需求匹配最佳技能 |
| SkillStats | 技能调用成功率/延迟统计 |

**集成点**: → L3 MetaSoul 的 SelfLearner/SkillAcquisition 提供个体技能学习 → L5 SoulTeam 的 TeamKnowledgeGraph 管理团队级技能图谱

#### FLY-5: Tools（工具层）

**目录**: `fly5tools/` + `core/fly_layers.py`
**代码量**: ~1,701 行

| 模块 | 代码量 | 职责 |
| ---- | ------ | ---- |
| MessageQueue | 467 行 | Pub/Sub、RPC、死信队列 |
| ToolRegistry | 471 行 | 工具注册、发现、能力匹配 |
| ResourcePool | 345 行 | 计算/连接池管理 |
| ProtocolLayer | 365 行 | 调用协议、重试、超时 |

**集成点**: → L0 LLMInfra 的 ProviderFactory 通过 ToolRegistry 注册为可用工具 → L2 ZenAgent 的 MCP 协议通过 ProtocolLayer 调用外部工具

### 5.2 横切关注点

SwarmFly 除了 FLY 六层外，还有四个横切模块，被所有 FLY 层共享：

#### 生命周期 (lifecycle/) — 1,307 行

| 模块 | 职责 |
| ---- | ---- |
| AgentLifecycle | 8 状态机（CREATED→RUNNING→PAUSED→DISPOSED） |
| TransitionValidator | 转换规则验证 |
| StateManager | 多 Agent 生命周期批量管理 |

#### 协作引擎 (collaboration/) — 2,766 行

| 模块 | 职责 |
| ---- | ---- |
| CollaborationEngine | 统一协作引擎（集成调度+负载+共识+冲突） |
| TaskDispatcher | 优先级队列、依赖检查、重试 |
| LoadBalancer | 5 种策略（最少负载/轮询/加权/能力/自适应） |
| ConsensusMechanism | 3 种共识（Quorum/加权/全票） |
| ConflictResolver | 6 种解决策略 |

#### 共享内存 (memory/) — 2,382 行

| 模块 | 职责 |
| ---- | ---- |
| SharedMemoryPool | 统一内存池（段管理+锁+缓存+同步） |
| LockManager | 读/写/公平锁（33 方法） |
| CacheCoherence | MESI 协议缓存一致性 |
| SyncProtocol | 节点间同步协议 |

#### 组合入口 (core/) — 1,108 行

| 模块 | 职责 |
| ---- | ---- |
| SwarmFly | 主入口，组合 lifecycle + collaboration + memory + team |
| fly_layers.py | FLY-0~5 层定义（FLYLayer 基类 + 状态管理 + 监听器） |

### 5.3 SwarmFly 与各层集成全景

```text
L5: SoulTeam (团队编排)
    ├── TeamOrchestrator ──────→ FLY-0 TeamBuilder (创建/管理团队)
    ├── TeamOrchestrator ──────→ FLY-2 Rules (任务路由决策)
    ├── TeamReflector ─────────→ FLY-3 Trends (团队趋势洞察)
    ├── TeamKnowledgeGraph ───→ FLY-4 Skills (团队技能图谱)
    └── TeamMemory ────────────→ memory/ SharedMemoryPool (团队共享记忆)

L3: MetaSoul (个体灵魂)
    ├── Personality/ValueEvolution → FLY-1 Mission (个体价值对齐)
    ├── Reflector ─────────────→ FLY-3 Trends (个体反思数据)
    ├── SelfLearner ───────────→ FLY-4 Skills (个体技能学习)
    └── MetaSoul Memory ───────→ memory/ (个体记忆持久化)

L2: ZenAgent (单智能体)
    ├── MCP Protocol ──────────→ FLY-5 Tools/ProtocolLayer (工具调用)
    └── Think() ───────────────→ collaboration/ (任务分发)

L0: LLMInfra (LLM 基础设施)
    └── ProviderFactory ───────→ FLY-5 Tools/ToolRegistry (Provider 注册)
```

### 5.4 需要整合的模块

| 模块 | 当前状态 | 整合目标 |
| ---- | -------- | -------- |
| SubAgentManager._execute() | 返回硬编码字典 | 接入真实 LLM 调用 |
| S1_Evolution (EvolveEngine, ZenLoop) | mock_mode=True | 实现真实 API 调用 |
| team/team_collaboration.py 与 team/builder.py | 两个独立 Team 类 | 统一为一个 Team 接口 |
| layers/collaboration.py | 与 collaboration/engine.py 重叠 | 合并或弃用 |
| FLY-1 Mission | 仅在 fly_layers.py 有框架 | 接入 MetaSoul Personality 数据 |
| FLY-3 Trends | 数据源为空 | 接入 MetaSoul Reflector 产出 |

---

## 六、L5: SoulTeam — 团队编排体系（新建）

SoulTeam 构建于 SwarmFly 之上，提供**超越个体之和**的团队级能力。

### 6.1 设计原则

> 总体大于部分之和（The whole is greater than the sum of its parts）

个体 Agent 有自己的 MetaSoul（记忆、人格、学习），但团队作为一个整体，需要：
- **团队记忆**：集体经验、共享上下文、团队历史
- **团队知识**：整合个体知识形成的团队知识图谱
- **团队反思**：集体复盘、模式识别、策略调整
- **协作编排**：任务分解、角色分配、协作链执行

### 6.2 团队定义

基于 `docs/design/agent-collaboration/智能体集群运行机制.md`：

| 团队 | Leader | 成员 | 职责 |
| ---- | ------ | ---- | ---- |
| TEAM-INVEST | IA (投资分析师) | IA | 投资分析与决策支持 |
| TEAM-RD | TR (科技研究员) | TR, DV, DE, CR, AR, PT, PM, WE | 技术研究与产品开发 |
| TEAM-LEARN | AL (AI学习教练) | AL, SE | 知识学习与自我提升 |
| TEAM-OPS | EE (效率专家) | OO, EE, SA, PR, EN | 信息追踪与效率优化 |

主智能体（AGENT-000）为全局枢纽，不属于任何团队。

### 6.3 核心模块规划

#### 团队记忆 (team_memory/)

```python
class TeamMemory:
    """团队记忆 — 集体经验与共享上下文"""

    def store_collective_experience(self, experience):
        """存储团队级经验（多 Agent 协作的结果）"""

    def share_knowledge(self, from_agent, to_agent, knowledge):
        """Agent 间知识传递"""

    def get_team_context(self, team_id):
        """获取团队上下文（最近任务、关键决策、共识）"""

    def query_team_history(self, query, time_range):
        """查询团队历史（按任务类型、参与 Agent、结果）"""
```

#### 团队知识 (team_knowledge/)

```python
class TeamKnowledgeGraph:
    """团队知识图谱 — 整合个体知识形成集体智慧"""

    def merge_agent_knowledge(self, agent_ids):
        """合并多个 Agent 的个体知识图谱"""

    def find_knowledge_gaps(self, team_id):
        """识别团队知识盲区"""

    def transfer_skill(self, from_agent, to_agent, skill):
        """技能传递（基于 SkillAcquisition 的团队级扩展）"""

    def get_team_expertise(self, team_id):
        """获取团队能力画像（综合所有成员的技能和知识）"""
```

#### 团队反思 (team_reflection/)

```python
class TeamReflector:
    """团队反思 — 集体复盘与策略调整"""

    def collective_review(self, task_id):
        """集体复盘（所有参与 Agent 分享视角）"""

    def identify_team_patterns(self, team_id):
        """识别团队协作模式（高效/低效/冲突模式）"""

    def suggest_process_improvement(self, team_id):
        """建议流程改进（基于历史数据分析）"""

    def update_team_strategy(self, team_id, insights):
        """更新团队策略（基于反思洞察）"""
```

#### 协作编排 (orchestration/)

```python
class TeamOrchestrator:
    """协作编排 — 任务分解与协作链执行"""

    def decompose_task(self, task, team_id):
        """任务分解（基于团队能力矩阵）"""

    def assign_roles(self, task, team_members):
        """角色分配（四维评分路由：能力40%+可用性30%+负载20%+技能10%）"""

    def execute_collaboration_chain(self, chain_id, input_data):
        """执行协作链（5 条模板：IA-AL, TR-DV, OO-SE, CR-DE, PR-PT）"""

    def aggregate_results(self, task_id, sub_results):
        """结果聚合（加权评分、异常值处理、共识达成）"""
```

### 6.4 八卦路由机制

基于任务类型自动选择最优协作路径：

| 任务类型 | 八卦方向 | 主要 Agent | 辅助 Agent |
|---------|---------|-----------|-----------|
| 投资分析 | 兑☱发现 + 坎☵磨砺 | IA | EN |
| 科技前沿 | 离☲智慧 + 巽☴扩张 | TR | WE |
| AI学习 | 离☲智慧 + 乾☰创新 | AL | SE |
| 内容创作 | 乾☰创新 + 离☲智慧 | CR | DE |
| 技术开发 | 坎☵磨砺 + 艮☶规范 | DV | AR |
| 方案评审 | 坎☵磨砺 + 坤☷归真 | PR | AR |
| 产品设计 | 坤☷归真 + 乾☰创新 | PM | PR |

### 6.5 协作链模板

| 链 ID | 名称 | 组合 | 协议 | 模式 | 场景 | SLA |
| ------ | ---- | ---- | ---- | ---- | ---- | ---- |
| IA-AL | 投资学习链 | IA→AL | 主从 | 顺序 | 投资分析报告 | 24h |
| TR-DV | 技术研究链 | TR→DV | 层级 | 扇出扇入 | 新技术研究开发 | 48h |
| OO-SE | 信息整理链 | OO↔SE | 对等 | 并行 | 信息收集整理 | - |
| CR-DE | 内容创作链 | CR→DE | 主从 | 顺序 | PPT/文案创作 | - |
| PR-PT | 方案评审链 | PR→PT | 层级 | 扇出扇入 | 方案评审测试 | - |

---

## 七、设计文档索引

以下设计文档定义了框架各层的架构、机制和逻辑，是开发实施的**直接依据**。

| 设计文档 | 关联层级 | 核心内容 |
| -------- | -------- | -------- |
| [智能体集群运行机制](./design/agent-collaboration/智能体集群运行机制.md) | L5 SoulTeam | 16 Agent 定义、4 团队配置（INVEST/RD/LEARN/OPS）、5 条协作链模板、四维评分路由（能力40%+可用性30%+负载20%+技能10%）、6 级优先级（P0-P5）、JSON 消息协议与状态机、八卦路由表、Zone 心跳中继 |
| [智能体协作编排机制](./design/agent-collaboration/智能体协作编排机制.md) | L5 SoulTeam | 决策层分离架构（A3）、配置驱动角色分配、3 种执行模式（顺序/并行/快速）、加权聚合算法（异常值修剪）、决策树（approve≥0.75 / conditional 0.60-0.75 / revise 0.40-0.60 / reject<0.40） |
| [智能体八卦路由机制](./design/agent-collaboration/智能体八卦路由机制.md) | L5 SoulTeam | 八卦空间坐标路由、双轨引擎（功能协作60% + 五行能量40%）、冲突仲裁规则、能量阈值区间（高>100ζ强制分流 / 低<20ζ紧急补给 / 危<5ζ休眠）、六爻扩展模型（最多640 Agent） |
| [智能体调度指南](./design/agent-collaboration/智能体调度指南.md) | L4 SwarmFly | 三级协作模型（计划执行组/任务执行组/系统支撑组）、六车道调度（FAST/NORMAL/SLOW × P/E）、车道并发限制与晋升规则、重试策略、响应 SLA、故障处理流程 |
| [子智能体运行机制](./design/agent-collaboration/子智能体运行机制.md) | L4 SwarmFly | Agent 公式（Model+Harness+Skill+Calendar）、静态声明（TEAM.md）+ 动态创建（sessions_spawn 5 种触发）、生命周期状态机（6 状态）、培养体系（技能获取/知识沉淀）、境界晋升（双维度评分） |
| [智能体 context 传递规范](./design/agent-collaboration/智能体context传递规范.md) | L2 ZenAgent + L4 SwarmFly | 5 个标准化 JSON 文件（enlightenment_context / task_context / agent_instruction / task_result / enlightenment_insight）、双向上下文流、上下文链可追溯性 |
| [智能体集群运作机制](./design/agent-collaboration/智能体集群运作机制.md) | L4 SwarmFly | S2 系统架构、Master Agent 4 组件（Negotiator/Router/Arbiter/Consensus）、4 种协作拓扑（星型/网状/链式/涌现）、事件驱动（40+ 事件主题）、Agent 注册表（91,240 matches/s） |
| [智能体协作开发体系迭代方案](./design/agent-collaboration/智能体协作开发体系迭代方案.md) | Phase 2-3 参考 | 5 个协作层组件规划（协商器/路由器/仲裁器/共识器/协作记忆）、10 周迭代计划、SwarmFly S2 桥接模块复用 |

---

## 八、实施路线图

### Phase 0: 文档对齐 (1 天)

Mission.md 是框架的顶层使命文档。Phase 0 的目标是将 Mission.md 中的架构决策同步到所有核心文档，确保整个文档体系一致。

| 目标文档 | 需同步内容 |
| -------- | ---------- |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 4 层→6 层架构图、新增 L5 SoulTeam 层定义、更新依赖关系图、MetaSoul 重命名 |
| [API.md](./API.md) | 新增 L5 SoulTeam API 章节、MetaSoul 重命名、SwarmFly FLY 层 API 分组 |
| [ROADMAP.md](./ROADMAP.md) | 新增 MetaSoul 重命名任务、SoulTeam 新建任务、FLY 层整合任务、引用设计文档 |
| [E2E_OPTIMIZATION_DESIGN.md](./E2E_OPTIMIZATION_DESIGN.md) | MetaSoul 重命名、新增 L5 层优化模块 |
| [E2E-Plan.md](./E2E-Plan.md) | MetaSoul 重命名、新增 L5 层测试计划 |

### Phase 1: MetaSoul 重命名 (1-2 天)

- `packages/SoulTeam/` → `packages/MetaSoul/`
- 更新所有 import 路径
- 更新测试文件
- 更新文档（ARCHITECTURE.md, API.md, ROADMAP.md）

### Phase 2: SwarmFly 整合 (3-5 天)

**依据**: [智能体集群运作机制](./design/agent-collaboration/智能体集群运作机制.md)（S2 系统架构、4 种协作拓扑、事件驱动机制）、[智能体协作开发体系迭代方案](./design/agent-collaboration/智能体协作开发体系迭代方案.md)（5 个协作层组件、SwarmFly S2 桥接模块复用）、[智能体调度指南](./design/agent-collaboration/智能体调度指南.md)（六车道调度、并发控制）

- 统一两个 Team 类（builder.py + team_collaboration.py）
- 实现 SubAgentManager 的真实执行逻辑
  - 依据 [子智能体运行机制](./design/agent-collaboration/子智能体运行机制.md) 的 sessions_spawn 5 种触发和生命周期状态机
- 连接 CollaborationEngine 到 ZenAgent 层
  - 依据 [智能体 context 传递规范](./design/agent-collaboration/智能体context传递规范.md) 的 5 个标准化 JSON 文件协议
- 整合 SharedMemoryPool 到主流程
- 实现六车道调度系统
  - 依据 [智能体调度指南](./design/agent-collaboration/智能体调度指南.md) 的 FAST/NORMAL/SLOW 车道定义
- 移除或合并 layers/collaboration.py 重叠代码

### Phase 3: SoulTeam 新建 (5-7 天)

**依据**: [智能体集群运行机制](./design/agent-collaboration/智能体集群运行机制.md)（16 Agent、4 团队、协作链模板、四维评分路由）、[智能体协作编排机制](./design/agent-collaboration/智能体协作编排机制.md)（决策层分离、执行模式、加权聚合、决策树）、[智能体八卦路由机制](./design/agent-collaboration/智能体八卦路由机制.md)（双轨路由引擎、能量阈值、六爻扩展）

- 创建 `packages/SoulTeam/` 包
- 实现 TeamMemory（基于 SwarmFly SharedMemoryPool 扩展）
- 实现 TeamKnowledgeGraph（基于 MetaSoul KnowledgeGraph 扩展）
- 实现 TeamReflector（基于 MetaSoul Reflector 扩展）
- 实现 TeamOrchestrator
  - 依据 [智能体协作编排机制](./design/agent-collaboration/智能体协作编排机制.md) 的 A3 决策层分离架构
  - 依据 [智能体集群运行机制](./design/agent-collaboration/智能体集群运行机制.md) 的四维评分路由算法
- 实现八卦路由引擎
  - 依据 [智能体八卦路由机制](./design/agent-collaboration/智能体八卦路由机制.md) 的双轨引擎（功能60%+五行40%）和冲突仲裁规则
- 实现协作链模板
  - 依据 [智能体集群运行机制](./design/agent-collaboration/智能体集群运行机制.md) 的 5 条链模板（IA-AL / TR-DV / OO-SE / CR-DE / PR-PT）
- 实现 context 传递协议
  - 依据 [智能体 context 传递规范](./design/agent-collaboration/智能体context传递规范.md) 的 5 个 JSON 文件和双向流

### Phase 4: 集成验证 (2-3 天)

- 16 Agent 集群端到端测试（依据 [智能体集群运行机制](./design/agent-collaboration/智能体集群运行机制.md) 的完整集群定义）
- 4 团队协作场景测试（TEAM-INVEST / TEAM-RD / TEAM-LEARN / TEAM-OPS）
- 协作链执行测试（5 条链模板）
- 八卦路由引擎测试（双轨路由 + 能量阈值）
- 性能基准测试（Agent 注册表匹配速率、路由延迟、协作吞吐）

---

## 九、相关文档

### 核心文档

| 文档 | 职责 |
| ---- | ---- |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 系统架构设计（六层定义、模块依赖） |
| [API.md](./API.md) | API 使用手册（各层接口） |
| [ROADMAP.md](./ROADMAP.md) | 项目路线图与进度追踪 |
| [E2E_OPTIMIZATION_DESIGN.md](./E2E_OPTIMIZATION_DESIGN.md) | 13 个优化模块详细设计 |
| [E2E-Plan.md](./E2E-Plan.md) | 端到端测试计划 |

### 设计文档

| 文档 | 职责 |
| ---- | ---- |
| [智能体集群运行机制](./design/agent-collaboration/智能体集群运行机制.md) | 16 Agent + 4 团队 + 协作链 + 八卦路由 + 四维评分 |
| [智能体协作编排机制](./design/agent-collaboration/智能体协作编排机制.md) | 决策层分离 + 执行模式 + 聚合算法 + 决策树 |
| [智能体八卦路由机制](./design/agent-collaboration/智能体八卦路由机制.md) | 双轨路由引擎 + 能量阈值 + 六爻扩展 |
| [智能体调度指南](./design/agent-collaboration/智能体调度指南.md) | 六车道调度 + 并发控制 + SLA + 故障处理 |
| [子智能体运行机制](./design/agent-collaboration/子智能体运行机制.md) | 子 Agent 生命周期 + 培养体系 + 境界晋升 |
| [智能体 context 传递规范](./design/agent-collaboration/智能体context传递规范.md) | 5 个 JSON 文件协议 + 双向上下文流 |
| [智能体集群运作机制](./design/agent-collaboration/智能体集群运作机制.md) | S2 系统 + 4 种协作拓扑 + 事件驱动 |
| [智能体协作开发体系迭代方案](./design/agent-collaboration/智能体协作开发体系迭代方案.md) | 协作层组件规划 + 10 周迭代计划 |
