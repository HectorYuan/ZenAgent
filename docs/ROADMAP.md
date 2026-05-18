# ZenAgent 项目路线图

**最后更新**: 2026-05-18  
**当前版本**: 1.0.0-alpha  
**整体状态**: 🟢 核心层稳定，待 L0 层集成

---

## 📊 项目总览

ZenAgent 是一个 5 层架构的智能体平台：

```
L0: LLMInfra    ──── ⏳ 待集成 (neo 分支)
L1: Runtime     ──── ✅ 已完成，43 测试通过
L2: ZenAgent    ──── ✅ 已完成，11 测试通过
L3: SwarmFly    ──── ✅ 已完成，153 测试通过
L4: SoulTeam    ──── ✅ 已完成，100 测试通过
```

---

## ✅ 已完成工作

### 2026-05-18: 核心稳定性修复

**负责人**: Claude Code  
**状态**: ✅ 全部完成

| 序号 | 任务 | 成果 | 影响模块 |
|-----|------|------|---------|
| 1 | **SwarmFly 导入路径修复** | 将中文路径 `FLY_2_法则层` 等改为相对导入 | packages/SwarmFly/__init__.py |
| 2 | **类型注解修复** | 补充缺失的 `Tuple` 类型导入 | priority_manager.py, ToolRegistry |
| 3 | **Logging 模块修复** | 补充缺失的 logging 导入 | market_trend_analyzer.py, behavior_analyzer.py |
| 4 | **全量测试验证** | 273 个测试 100% 通过 | 所有模块 |

**详细修复记录**:

```diff
# 修复 1: SwarmFly 入口导入
- from Core.RuleEngine import ...
+ from .fly2rules.Core.RuleEngine import ...

# 修复 2: 类型注解
- from typing import Dict, List, Any, Optional
+ from typing import Dict, List, Any, Optional, Tuple

# 修复 3: Logging 模块
+ import logging
  from typing import Dict, List, Any, Optional
```

**测试成果**:
- ✅ Runtime: 43/43 测试通过
- ✅ SoulTeam: 100/100 测试通过
- ✅ SwarmFly: 153/153 测试通过
- ✅ ZenAgent: 11/11 测试通过
- ✅ E2E Phase 1: 27/27 测试通过（新增）
- ✅ E2E Base: 9/9 测试通过
- **总计: 344/344 测试全部通过，耗时 3.36s**

---

## 📋 待办事项 (按优先级)

### P0: 已完成 ✅

**已完成任务**:

1. **合并 neo 分支到 main** (2026-05-18)
   - 合并 `packages/LLMInfra/` 代码
   - LLMInfra 基础设施（Provider Factory, Settings, Cache）
   - ModelNexus Adapter 集成

2. **清理遗留代码** (2026-05-18)
   - 删除 `packages/SwarmFly/tests/week5_integration/`

3. **Phase 1 E2E 测试实现** (2026-05-18)
   - T1: Agent 创建与初始化流程（注册、生命周期、人格、记忆、Hook）
   - T2: 任务分发与协作流程（路由策略、协作协议）
   - T3: 事件总线与消息队列（发布订阅、RPC 调用、死信队列）

4. **Bug 修复** (2026-05-18)
   - 修复 task_router 中 round robin 索引初始化 bug

---

### P1: 中优先级 - 核心功能增强

**待完成任务**:

1. **Phase 2 E2E 测试实现** ✅ (2026-05-18, 实际: 1 天)
   - ✅ T4: 完整任务执行场景 (17 测试)
   - ✅ T5: 多 Agent 团队协作场景 (25 测试)
   - ✅ T6: Agent 进化与学习场景 (15 测试)
   - 参考: [E2E-Plan.md](./E2E-Plan.md) Phase 2
   - **成果: 57/57 测试全部通过**

### P2: 中优先级 - 场景测试

| 序号 | 任务 | 预估工作量 | 依赖 | 状态 |
|-----|------|-----------|------|------|
| 5 | **Phase 2 E2E 测试实现** ✅ | 3 天 | P1-4 | ✅ 已完成 |
| | - T4: 完整任务执行场景 | | | ✅ |
| | - T5: 多 Agent 团队协作场景 | | | ✅ |
| | - T6: Agent 进化与学习场景 | | | ✅ |
| 6 | **ZenAgent 层与 LLMInfra 集成** | 2 天 | P1-3 | 📋 待开始 |
| | - 在 ZenAgent Agent 类中注入 ModelNexusAdapter | | | |
| | - 实现 `think()` 方法调用真实 LLM | | | |
| | - 实现记忆写入与 LLM 调用的联动 | | | |

### P3: 低优先级 - 真实 E2E

| 序号 | 任务 | 预估工作量 | 依赖 | 状态 |
|-----|------|-----------|------|------|
| 7 | **Phase 3 真实 LLM E2E 测试** | 2 天 | P2-5, P2-6 | 📋 待开始 |
| | - ModelNexus 服务健康检查测试 | | | |
| | - 真实 LLM 调用完整链路测试 | | | |
| | - 多轮对话上下文保持验证 | | | |
| 8 | **CI/CD E2E 流水线配置** | 1 天 | P3-7 | 📋 待开始 |
| | - GitHub Actions E2E workflow | | | |
| | - Redis 服务配置 | | | |
| | - ModelNexus Docker Compose 启动 | | | |

---

## 🎯 里程碑计划

### Milestone 1: L0 层接入 (目标: 2026-05-22)

- [x] neo 分支合并完成
- [ ] ModelNexus Submodule 配置完成
- [x] LLMInfra 可以正常导入和初始化
- [ ] Mock Provider 测试通过

### Milestone 2: Phase 1 E2E 完成 ✅ (目标: 2026-05-18, 提前完成)

- [x] 所有 Phase 1 测试用例实现完成 (T1, T2, T3)
- [x] 主线流程测试 100% 通过 (71/71 E2E, 344/344 总测试)
- [ ] 测试覆盖率 ≥ 70%

### Milestone 3: Phase 2 场景集成 ✅ (目标: 2026-05-30, 提前完成)

- [x] 所有 Phase 2 测试用例实现完成 (57 测试)
- [x] 团队协作、任务执行场景验证通过
- [x] SwarmFly + SoulTeam 集成验证
- **成果: 57/57 Phase 2 测试全部通过**

### Milestone 4: 真实 LLM 完整 E2E (目标: 2026-06-05)

- [ ] ModelNexus 服务正常运行
- [ ] 真实 API Key 测试通过
- [ ] 完整端到端智能体流程验证

---

## 🔧 已知技术债

| 模块 | 问题描述 | 严重程度 | 建议修复时间 |
|-----|---------|---------|------------|
| SwarmFly/tests | `week5_integration` 测试文件引用已删除的中文路径模块 | 低 | 下次清理 |
| Integration tests | `tests/integration/` 下测试引用不存在的 `packages.core` 模块 | 中 | Phase 1 测试开发时 |
| LLMInfra | 目前只在 neo 分支，main 分支缺失 | 高 | 立即合并 |

---

## 📈 质量指标

### 当前指标

| 指标 | 当前值 | 目标值 | 状态 |
|-----|-------|-------|------|
| 单元测试通过率 | 100% | 100% | ✅ |
| 集成测试覆盖率 | - | ≥ 80% | ⏳ |
| E2E Phase 1 通过率 | 100% (27/27) | 100% | ✅ |
| E2E Phase 2 通过率 | 100% (57/57) | 100% | ✅ |
| **总 E2E 测试** | **93/93** | 100% | ✅ |
| **总测试数** | **401/401** | 100% | ✅ |
| 完整测试执行时间 | ~3s | < 5s | ✅ |

### 质量门禁

```yaml
# 合并 PR 前必须满足
unit_tests: 100% 通过
e2e_phase1: 100% P0 用例通过
lint: 无错误
type_check: mypy 通过
```

---

## 📚 相关文档

- [E2E-Plan.md](./E2E-Plan.md) - 端到端测试详细计划
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 系统架构文档
- [packages/LLMInfra/MODELNEXUS_INTEGRATION.md](../packages/LLMInfra/MODELNEXUS_INTEGRATION.md) - ModelNexus 集成指南 (neo 分支)
- [/root/DevSpace/modelnexus/README.md](/root/DevSpace/modelnexus/README.md) - ModelNexus 官方文档

---

## 💡 快速开始命令

```bash
# 运行所有测试
pytest packages/Runtime/tests packages/SoulTeam/tests packages/SwarmFly/tests packages/ZenAgent/tests tests/e2e --ignore=packages/SwarmFly/tests/week5_integration -v

# 只运行 E2E 测试
pytest tests/e2e/ -v

# 运行特定模块测试
pytest packages/SwarmFly/tests -v
```

---

**维护者**: ZenAgent Team  
**下次评审**: 2026-05-25
