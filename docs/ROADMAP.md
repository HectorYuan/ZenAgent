# ZenAgent 项目路线图

**最后更新**: 2026-05-20
**当前版本**: 1.0.0-beta
**整体状态**: 🟢 M7 + M7.5 双里程碑完成，S1_Evolution 特色功能已全部合并

---

## 📊 项目总览

ZenAgent 是一个 6 层架构的智能体平台：

```text
L0: LLMInfra    ──── ✅ 已完成，熔断器 + 重试/预算/校验
L1: Runtime     ──── ✅ 已完成，限流 + 追踪 + 审计 + Session/Checkpoint/HTL
L2: ZenAgent    ──── ✅ 已完成，Hook 系统 + Awakening + MCP
L3: MetaSoul    ──── ✅ 已完成，四层记忆 + 学习 + 人格 + 反思（原 SoulTeam）
L4: SwarmFly    ──── ✅ 已完成，FLY 六层 + 四大横切 + 交接桥 + 执行循环
L5: SoulTeam    ──── ❌ 待新建，团队编排体系
```

**当前测试**: 341 passed, 6 skipped, 0 failures （M7 + M7.5 验证集）

---

## 📐 设计文档索引

以下设计文档是开发实施的直接依据，详见 [Mission.md 第七章](./Mission.md#七设计文档索引)：

| 设计文档 | 关联层级 |
| -------- | -------- |
| [智能体集群运行机制](./design/agent-collaboration/智能体集群运行机制.md) | L5 SoulTeam — 16 Agent + 4 团队 + 协作链 + 四维评分路由 |
| [智能体协作编排机制](./design/agent-collaboration/智能体协作编排机制.md) | L5 SoulTeam — 决策层分离 + 执行模式 + 加权聚合 + 决策树 |
| [智能体八卦路由机制](./design/agent-collaboration/智能体八卦路由机制.md) | L5 SoulTeam — 双轨路由 + 能量阈值 + 六爻扩展 |
| [智能体调度指南](./design/agent-collaboration/智能体调度指南.md) | L4 SwarmFly — 六车道调度 + 并发控制 + SLA |
| [子智能体运行机制](./design/agent-collaboration/子智能体运行机制.md) | L4 SwarmFly — 生命周期 + 培养体系 + 境界晋升 |
| [智能体 context 传递规范](./design/agent-collaboration/智能体context传递规范.md) | L2+L4 — 5 个 JSON 文件 + 双向上下文流 |
| [智能体集群运作机制](./design/agent-collaboration/智能体集群运作机制.md) | L4 SwarmFly — S2 系统 + 4 种协作拓扑 + 事件驱动 |
| [智能体协作开发体系迭代方案](./design/agent-collaboration/智能体协作开发体系迭代方案.md) | Phase 2-3 — 5 个协作层组件 + 10 周迭代计划 |

---

## ✅ 已完成工作

### 基础设施 (2026-05-18)

| 任务 | 成果 | 提交 |
| ---- | ---- | ---- |
| neo 分支合并 | LLMInfra 基础设施、ModelNexus Adapter | `32e54e5` |
| SwarmFly 导入路径修复 | 中文路径改为相对导入 | `3d650d3` |
| 类型注解/Logging 修复 | 补充缺失导入 | `3d650d3` |
| 遗留代码清理 | 删除 `week5_integration/` | - |

### E2E 测试体系 (2026-05-18)

| 阶段 | 内容 | 测试数 | 提交 |
| ---- | ---- | ------ | ---- |
| Phase 1 | Agent 创建、任务分发、事件总线 | 27 | `69af576` |
| Phase 2 | 完整任务执行、团队协作、Agent 进化 | 57 | `6f1315e` |
| Phase 3 | ZenAgent + LLMInfra + MetaSoul 联动 | 11 | `b65dc66` |
| Phase 4 | CI/CD 流水线、分阶段 E2E | 149 | `ff569a5` |
| Phase 5 | ModelNexus 真实 LLM 测试 | 11+6 skip | `ff569a5` |

### LLMInfra Provider 增强 (2026-05-18)

| 任务 | 成果 | 提交 |
| ---- | ---- | ---- |
| 重试机制 | 指数退避、4 种策略、RetryMixin | `53a792d` |
| 会话管理 | aiohttp 复用、TCP 连接池、自动清理 | `53a792d` |
| 响应空值防护 | None/空字符串自动触发 Fallback | `53a792d` |

### M7 生产优化 (2026-05-20) ✅ 已完成

**M7 里程碑全部完成，新增 105 个测试，195 个测试全部通过。**

| 任务 | 成果 | 设计依据 | 提交 |
| ---- | ---- | -------- | ---- |
| 重试机制 | 指数退避 + 抖动 + 预设配置 | [E2E_OPTIMIZATION_DESIGN §模块1](./E2E_OPTIMIZATION_DESIGN.md) | `53a792d` |
| Token 预算管理器 | 意图分类 + 动态 max_tokens + 上下文截断 | [E2E_OPTIMIZATION_DESIGN §模块2](./E2E_OPTIMIZATION_DESIGN.md) | `cfb27fa` |
| 响应完整性校验 | 截断/空响应/内容过滤检测 + 自动重试 | [E2E_OPTIMIZATION_DESIGN §模块7](./E2E_OPTIMIZATION_DESIGN.md) | `f03e766` |
| 记忆评分与自动淘汰 | 统一评分器 + 排序 bug 修复 + 淘汰周期 | [E2E_OPTIMIZATION_DESIGN §模块9](./E2E_OPTIMIZATION_DESIGN.md) | `734c25b` |
| 令牌桶限流器 | TokenBucket + Priority (P0/P1/P2) + 背压 | [E2E_OPTIMIZATION_DESIGN §模块4](./E2E_OPTIMIZATION_DESIGN.md) | `c0a908f` |
| 熔断器 | 三态机 (CLOSED→OPEN→HALF_OPEN) + 错误率触发 | [E2E_OPTIMIZATION_DESIGN §模块5](./E2E_OPTIMIZATION_DESIGN.md) | `c0a908f` |
| 全链路 Trace + Metrics | trace_id + Span 嵌套 + Counter/Histogram/Gauge | [E2E_OPTIMIZATION_DESIGN §模块8](./E2E_OPTIMIZATION_DESIGN.md) | `c0a908f` |
| E2E 鲁棒性测试 | 长对话/限流/熔断/校验/重试/降级 7 大场景 | [E2E-Plan.md](./E2E-Plan.md) | `c0a908f` |
| 测试覆盖率补充 | audit_logger (16) + session 状态机 (17) | - | `c0a908f` |

### M7.5 架构重构 Phase 0-2 (2026-05-20) ✅ 全部完成

**M7.5 里程碑全部完成，包含 S1_Evolution 全部特色功能合并。**

| 阶段 | 任务 | 关键成果 |
| ---- | ---- | -------- |
| Phase 0 | 文档对齐 | Mission.md 六层架构定义 + 设计文档索引体系 |
| Phase 1 | MetaSoul 重命名 | SoulTeam → MetaSoul 完整重命名，四层认知引擎整合 |
| Phase 2 | SwarmFly 整合 | FLY 六层架构 + 四大横切模块 + Runtime 统一入口 |

**S1_Evolution 特色功能已全部合并：**

| 模块 | 功能 | 说明 |
| ---- | ---- | ---- |
| 横切模块 | ConfigManager | 统一配置管理 + 环境变量覆盖 + 热更新 |
| 横切模块 | LifecycleManager | 组件生命周期 + 三态机 + hooks 系统 |
| 横切模块 | UnifiedLogger | 统一日志 + JSON 格式化 + 多目标输出 |
| 横切模块 | MetricsExporter | Counter/Histogram/Gauge + Prometheus 导出 |
| Agent桥接 | HandoffBridge | Agent 间任务交接协议 + 优先级调度 |
| 执行循环 | ZenLoopClient | 自主执行循环控制 + 状态追踪 |

---

## 📋 计划事项 (M8+)

### P1 - M8 核心功能增强 (12 天)

| 模块 | 任务 | 设计依据 | 工作量 |
| ---- | ---- | -------- | ---- |
| L0 | 多 Provider 责任链 + 容灾切换 | [E2E_OPTIMIZATION_DESIGN §模块1](./E2E_OPTIMIZATION_DESIGN.md) | 2 天 |
| L0 | 精确匹配缓存 + 预缓存热点 | [E2E_OPTIMIZATION_DESIGN §模块3](./E2E_OPTIMIZATION_DESIGN.md) | 1.5 天 |
| L2 | 意图分类 + Fast/Deep 路径分流 | [E2E_OPTIMIZATION_DESIGN §模块6](./E2E_OPTIMIZATION_DESIGN.md) | 2.5 天 |
| L3 | 记忆分层架构 (L1/L2/L3) | [E2E_OPTIMIZATION_DESIGN §模块9](./E2E_OPTIMIZATION_DESIGN.md) | 3 天 |
| L3 | 人格动态权重矩阵 | [E2E_OPTIMIZATION_DESIGN §模块10](./E2E_OPTIMIZATION_DESIGN.md) | 1.5 天 |
| L1 | 优先级队列 + 背压机制 | [智能体调度指南](./design/agent-collaboration/智能体调度指南.md) 六车道调度 | 1.5 天 |

### P2 - M9 智能优化 (15 天)

语义缓存、响应质量评分、经验记忆进化、混合专家系统。

| 模块 | 任务 | 设计依据 | 工作量 | 状态 |
| ---- | ---- | -------- | ---- | ---- |
| L0 | 语义缓存 HNSW 向量索引 | [E2E_OPTIMIZATION_DESIGN §模块3](./E2E_OPTIMIZATION_DESIGN.md) | 3 天 | 📋 计划 |
| L2 | 响应质量评分管道 | [E2E_OPTIMIZATION_DESIGN §模块7](./E2E_OPTIMIZATION_DESIGN.md) | 2 天 | 📋 计划 |
| L3 | 经验-记忆闭环进化 | [E2E_OPTIMIZATION_DESIGN §模块11](./E2E_OPTIMIZATION_DESIGN.md) | 3 天 | 📋 计划 |
| L4 | 多 Agent 混合专家系统 | [E2E_OPTIMIZATION_DESIGN §模块12](./E2E_OPTIMIZATION_DESIGN.md) | 4 天 | 📋 计划 |
| L4 | Provider 负载均衡 + A/B 测试 | [E2E_OPTIMIZATION_DESIGN §模块13](./E2E_OPTIMIZATION_DESIGN.md) | 3 天 | 📋 计划 |

### P3a - M7.5 架构重构 Phase 0-2（详见 [Mission.md](./Mission.md)）

**M7.5 总览**: 2 阶段 × 11 任务 = 22 项重构任务，总预估 5-7 天。

---

#### Phase 1: MetaSoul 重命名（原 SoulTeam → MetaSoul）—— 11 任务，预估 2-3 天

| # | 任务 | 说明 | 设计依据 | 状态 |
|---|------|------| -------- | ---- |
| 1 | 目录重命名 | `packages/SoulTeam/` → `packages/MetaSoul/` | [Mission.md §四](./Mission.md#四l3-metasoul--个体灵魂引擎) | ✅ 已完成 |
| 2 | 类名批量替换 | `SoulTeam` → `MetaSoul` 类名 | [Mission.md §四](./Mission.md#四l3-metasoul--个体灵魂引擎) | ✅ 已完成 |
| 3 | import 路径批量修复 | 所有引用 SoulTeam 的 import 替换为 MetaSoul | [Mission.md §四](./Mission.md#四l3-metasoul--个体灵魂引擎) | ✅ 已完成 |
| 4 | 内存层整合 | MetaMemory → MetaSoul core，统一内存管理 | [Mission.md §4.1](./Mission.md#41-meta-memory--四层记忆系统) | ✅ 已完成 |
| 5 | 认知层整合 | MetaCognition → MetaSoul core，统一反思/学习 | [Mission.md §4.2](./Mission.md#42-meta-cognition--认知引擎) | ✅ 已完成 |
| 6 | 人格层整合 | MetaPersonality → MetaSoul core，统一人格/情感 | [Mission.md §4.3](./Mission.md#43-meta-personality--人格引擎) | ✅ 已完成 |
| 7 | `__init__.py` 导出重构 | SoulTeam 导出列表重命名为 MetaSoul | - | ✅ 已完成 |
| 8 | Runtime 层引用更新 | `packages/Runtime/` 中所有 SoulTeam 引用 | - | ✅ 已完成 |
| 9 | LLMInfra 层引用更新 | `packages/LLMInfra/` 中所有 SoulTeam 引用 | - | ✅ 已完成 |
| 10 | 所有文档中名称替换 | README/设计文档/注释中的 SoulTeam | - | ✅ 已完成 |
| 11 | 回归测试验证 | 确保所有 195 测试通过 | - | ✅ 已完成 |

---

#### Phase 2: SwarmFly 整合（FLY 六层 + 横切模块）—— 11 任务，预估 3-4 天

| # | 任务 | 说明 | 设计依据 | 状态 |
|---|------|------| -------- | ---- |
| 1 | FLY-0 Master 接入 | 任务提交/分派/状态追踪接入 Runtime | [Mission.md §5.1](./Mission.md#51-fly-六层架构) | ✅ 已完成 |
| 2 | FLY-1 Mission 接入 | 使命对齐、价值体系、Agent 使命评分 | [Mission.md §5.1](./Mission.md#51-fly-六层架构) | ✅ 已完成 |
| 3 | FLY-2 Rules 接入 | Rete 规则引擎 + 冲突解决 + RBAC | [Mission.md §5.1](./Mission.md#51-fly-六层架构) | ✅ 已完成 |
| 4 | FLY-3 Trends 接入 | 趋势检测 + 预测引擎 + 自适应控制 | [Mission.md §5.1](./Mission.md#51-fly-六层架构) | ✅ 已完成 |
| 5 | FLY-4 Skills 接入 | 技能注册/搜索/调用/统计系统 | [Mission.md §5.1](./Mission.md#51-fly-六层架构) | ✅ 已完成 |
| 6 | FLY-5 Tools 接入 | 工具注册 + 消息队列 + 资源池 + 协议层 | [Mission.md §5.1](./Mission.md#51-fly-六层架构) | ✅ 已完成 |
| 7 | Lifecycle 横切接入 | Agent 生命周期 + 状态机 + 监听回调 | [Mission.md §5.2](./Mission.md#52-四个横切模块) | ✅ 已完成 |
| 8 | Collaboration 横切接入 | 冲突解决 + 死锁检测 + 协作流程 | [Mission.md §5.2](./Mission.md#52-四个横切模块) | ✅ 已完成 |
| 9 | Shared Memory 横切接入 | 共享内存 + 分布式同步 | [Mission.md §5.2](./Mission.md#52-四个横切模块) | ✅ 已完成 |
| 10 | Team 横切接入 | 团队构建 + 角色指派 + 通信层 | [Mission.md §5.2](./Mission.md#52-四个横切模块) | ✅ 已完成 |
| 11 | Runtime 总入口整合 | `SwarmFly` 类挂载 Runtime，供 L5 SoulTeam 调用 | [Mission.md §5.3](./Mission.md#53-swarmfly-与各层集成全景) | ✅ 已完成 |

---

### P3b - M10 多 Agent 团队编排

全新 L5 层：SoulTeam 团队编排体系，支持 16 Agent + 4 团队 + 八卦路由。

| 阶段 | 任务 | 设计依据 | 工作量 | 状态 |
| ---- | ---- | -------- | ------ | ---- |
| Phase 3 | SoulTeam 新建（团队编排体系） | [智能体集群运行机制](./design/agent-collaboration/智能体集群运行机制.md)、[智能体协作编排机制](./design/agent-collaboration/智能体协作编排机制.md)、[智能体八卦路由机制](./design/agent-collaboration/智能体八卦路由机制.md)、[智能体 context 传递规范](./design/agent-collaboration/智能体context传递规范.md) | 5-7 天 | 📋 计划 |
| Phase 4 | 集成验证（16 Agent + 4 团队 + 协作链） | [智能体集群运行机制](./design/agent-collaboration/智能体集群运行机制.md) | 2-3 天 | 📋 计划 |

---

## 🎯 里程碑

| 里程碑 | 目标日期 | 状态 | 关键成果 |
| ------ | --------- | ---- | --------- |
| M1: L0 层接入 | 2026-05-18 | ✅ | neo 合并、ModelNexus Provider |
| M2: Phase 1 E2E | 2026-05-18 | ✅ | 27 E2E 测试通过 |
| M3: Phase 2 场景集成 | 2026-05-30 | ✅ 提前 | 57 测试、团队协作验证 |
| M4: Phase 3 LLM 集成 | 2026-06-05 | ✅ 提前 | think() + 记忆 + 人格联动 |
| M5: Phase 4 CI/CD | 2026-06-10 | ✅ 提前 | GitHub Actions 分阶段流水线 |
| M6: 真实 LLM E2E | 2026-05-18 | ✅ | ModelNexus 端到端验证 |
| M7: 生产优化 | 2026-05-20 | ✅ 提前完成 | 9 项全完成 · 195 测试 · 105 新增 · 2315 行代码 |
| M7.5: 架构重构 Phase 0-2 | - | ✅ 全部完成 | Phase 0 文档对齐 ✅，Phase 1 MetaSoul 重命名 ✅，Phase 2 SwarmFly 整合 ✅ |
| M8: 核心功能增强 | - | 📋 计划 | 多 Provider 容灾、意图分流、记忆分层、人格矩阵 |
| M9: 智能优化 | - | 📋 计划 | 语义缓存、响应质量评分、经验记忆进化、混合专家 |
| M10: SoulTeam 团队编排 | - | 📋 计划 | 团队编排体系、八卦路由、16 Agent 协作链验证 |

---

## 🔧 已知技术债

| 模块 | 问题 | 严重程度 | 状态 |
| ---- | ---- | --------- | ---- |
| SwarmFly/tests | week5_integration 引用已删除的中文路径 | 低 | 文档引用 |
| LLMInfra | Pydantic v2 `.dict()` 弃用警告 | 低 | ✅ 已修复 |
| ModelNexus | chat_completion API 签名不匹配 | 中 | ✅ 已修复 |
| LLMInfra | aiohttp ClientSession 资源泄漏 | 低 | ✅ 已修复 |

---

## 📈 质量指标

| 指标 | 当前值 | 目标值 | 状态 |
| ---- | ------- | ------- | ---- |
| 单元测试通过率 | 100% (511/511) | 100% | ✅ |
| E2E 测试 | 160 pass + 6 skip | 100% | ✅ |
| 测试覆盖率 | - | ≥ 70% | ⏳ |
| 测试执行时间 | ~21s | < 30s | ✅ |

---

## 🚀 常用命令

```bash
# 运行所有测试
pytest packages/Runtime/tests packages/MetaSoul/tests packages/SwarmFly/tests packages/ZenAgent/tests packages/LLMInfra/tests tests/e2e --ignore=packages/SwarmFly/tests/week5_integration -v

# 只运行 E2E 测试
pytest tests/e2e/ -v

# 运行特定模块测试
pytest packages/SwarmFly/tests -v
```

---

## 📚 相关文档

### 核心文档

| 文档 | 职责 |
| ---- | ---- |
| [Mission.md](./Mission.md) | 框架使命与六层架构定义（顶层文档） |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 系统架构设计 |
| [API.md](./API.md) | API 使用手册 |
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

### 其他

| 文档 | 职责 |
| ---- | ---- |
| [packages/LLMInfra/MODELNEXUS_INTEGRATION.md](../packages/LLMInfra/MODELNEXUS_INTEGRATION.md) | ModelNexus 集成指南 |

---

**维护者**: ZenAgent Team
**下次评审**: 2026-05-25
