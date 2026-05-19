# ZenAgent 项目路线图

**最后更新**: 2026-05-19
**当前版本**: 1.0.0-beta
**整体状态**: 🟢 核心功能完成，M7 优化任务推进中

---

## 📊 项目总览

ZenAgent 是一个 5 层架构的智能体平台：

```text
L0: LLMInfra    ──── ✅ 已完成，ModelNexus Provider + 重试/预算/校验
L1: Runtime     ──── ✅ 已完成，43 测试通过
L2: ZenAgent    ──── ✅ 已完成，11 测试通过
L3: SoulTeam    ──── ✅ 已完成，记忆评分与自动淘汰
L4: SwarmFly    ──── ✅ 已完成，153 测试通过
```

**当前测试**: 511 passed, 6 skipped, 0 failures

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
| Phase 3 | ZenAgent + LLMInfra + SoulTeam 联动 | 11 | `b65dc66` |
| Phase 4 | CI/CD 流水线、分阶段 E2E | 149 | `ff569a5` |
| Phase 5 | ModelNexus 真实 LLM 测试 | 11+6 skip | `ff569a5` |

### LLMInfra Provider 增强 (2026-05-18)

| 任务 | 成果 | 提交 |
| ---- | ---- | ---- |
| 重试机制 | 指数退避、4 种策略、RetryMixin | `53a792d` |
| 会话管理 | aiohttp 复用、TCP 连接池、自动清理 | `53a792d` |
| 响应空值防护 | None/空字符串自动触发 Fallback | `53a792d` |

### M7 优化任务 (2026-05-19)

| 任务 | 成果 | 提交 |
| ---- | ---- | ---- |
| Token 预算管理器 | 意图分类 + 动态 max_tokens + 上下文截断 | `cfb27fa` |
| 响应完整性校验 | 截断/空响应/内容过滤检测 + 自动重试 | `f03e766` |
| 记忆评分与自动淘汰 | 统一评分器 + 排序 bug 修复 + 淘汰周期 | `734c25b` |

---

## ⏳ 待办事项 (M7 剩余)

| 任务 | 说明 | 预计工作量 | 状态 |
| ---- | ---- | ----------- | ---- |
| 基础令牌桶限流 + 熔断开关 | Runtime 层流控保护 | 1 天 | ⏳ 待开始 |
| 全链路 Trace ID + 关键节点 Metrics | 可观测性基础设施 | 1 天 | ⏳ 待开始 |
| E2E 测试补充 | 长对话、压力、异常场景 | 2 天 | ⏳ 待开始 |
| 测试覆盖率达到 70% | 核心模块单元测试补充 | 3 天 | ⏳ 待开始 |

---

## 📋 计划事项 (M8+)

### P1 - M8 核心功能增强 (12 天)

| 模块 | 任务 | 工作量 |
| ---- | ---- | ------ |
| L0 | 多 Provider 责任链 + 容灾切换 | 2 天 |
| L0 | 精确匹配缓存 + 预缓存热点 | 1.5 天 |
| L2 | 意图分类 + Fast/Deep 路径分流 | 2.5 天 |
| L3 | 记忆分层架构 (L1/L2/L3) | 3 天 |
| L3 | 人格动态权重矩阵 | 1.5 天 |
| L1 | 优先级队列 + 背压机制 | 1.5 天 |

### P2 - M9+ 远期优化 (15 天)

| 模块 | 任务 | 工作量 |
| ---- | ---- | ------ |
| L0 | 语义缓存 HNSW 向量索引 | 3 天 |
| L2 | 响应质量评分管道 | 2 天 |
| L3 | 经验-记忆闭环进化 | 3 天 |
| L4 | 多 Agent 混合专家系统 | 4 天 |
| L4 | Provider 负载均衡 + A/B 测试 | 3 天 |

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
| M7: 生产优化 | 2026-05-30 | ⏳ 进行中 | 重试/预算/校验/淘汰 ✅，限流/可观测/测试待做 |
| M8: 核心增强 | - | 📋 计划 | 多 Provider 容灾、意图分流、记忆分层 |

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
pytest packages/Runtime/tests packages/SoulTeam/tests packages/SwarmFly/tests packages/ZenAgent/tests packages/LLMInfra/tests tests/e2e --ignore=packages/SwarmFly/tests/week5_integration -v

# 只运行 E2E 测试
pytest tests/e2e/ -v

# 运行特定模块测试
pytest packages/SwarmFly/tests -v
```

---

## 📚 相关文档

- [E2E_OPTIMIZATION_DESIGN.md](./E2E_OPTIMIZATION_DESIGN.md) - 13 个模块的详细设计方案（代码草图、架构图、工作量估算）
- [E2E-Plan.md](./E2E-Plan.md) - 端到端测试详细计划
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 系统架构文档
- [packages/LLMInfra/MODELNEXUS_INTEGRATION.md](../packages/LLMInfra/MODELNEXUS_INTEGRATION.md) - ModelNexus 集成指南

---

**维护者**: ZenAgent Team
**下次评审**: 2026-05-25
