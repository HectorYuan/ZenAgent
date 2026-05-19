# ZenAgent 计划文档索引

> **归档声明 (2026-05-19)**: 以下文档为早期设计阶段草稿，整合自 Knowledge/ 目录。当前系统架构以 [ARCHITECTURE.md](../ARCHITECTURE.md) 为准，优化方案以 [E2E_OPTIMIZATION_DESIGN.md](../E2E_OPTIMIZATION_DESIGN.md) 为准。本文档不再维护，仅作历史参考。

## 目录结构

```
docs/plan/
├── README.md              # 本索引文件
├── AGENT_TEAM_ARCHITECTURE.md    # Agent Team 架构设计
├── SWARMFLY_INTEGRATION.md       # SwarmFly 框架集成方案
├── COLLABORATION_ARCHITECTURE.md # 协作架构设计
├── SUB_AGENT_MECHANISM.md        # 子智能体运行机制
└── CI_CD_SYSTEM.md               # CI/CD 持续集成体系
```

## 文档关联图

```
                    ┌──────────────────────┐
                    │ Agent Team Architecture│
                    │   (顶层架构设计)       │
                    └──────────┬───────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│Collaboration      │ │Sub-Agent          │ │CI/CD System       │
│Architecture       │ │Mechanism          │ │                   │
│(协作模式/协议)     │ │(生命周期/状态管理) │ │(测试/发布流水线)   │
└───────────────────┘ └───────────────────┘ └───────────────────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │SwarmFly Integration │
                    │   (FLY L1-L5 支撑)   │
                    └──────────────────────┘
```

## 核心概念

| 概念 | 说明 | 文档位置 |
|------|------|----------|
| Master Agent | 主智能体，任务理解/分派/验收 | AGENT_TEAM_ARCHITECTURE |
| Sub Agent | 子智能体，任务执行 | SUB_AGENT_MECHANISM |
| FLY Layer | 六层架构 (L0-L5) | SWARMFLY_INTEGRATION |
| Collaboration | 协作模式/协议 | COLLABORATION_ARCHITECTURE |
| CI/CD | 持续集成/部署 | CI_CD_SYSTEM |

## 设计原则

1. **分层解耦**：各 FLY 层独立演进
2. **协议驱动**：协作通过标准协议
3. **测试前置**：CI 覆盖所有代码
4. **可观测性**：完整日志/监控/追踪

## 待完善项

- [ ] L1 使命层代码实现
- [ ] L4 技能层完整实现
- [ ] L5 工具层核心组件
- [ ] Agent Team 单元测试
- [ ] E2E 集成测试

---

*最后更新：2026-05-14*
*来源：Knowledge/ 目录整合*
