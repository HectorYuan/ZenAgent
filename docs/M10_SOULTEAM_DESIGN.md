# M10: SoulTeam 团队编排体系 — A-Z 完整设计

**日期**: 2026-05-24
**设计依据**: 7 份设计文档 + 现有 SwarmFly 基础设施
**总工作量**: ~12 天

---

## 设计文档基础

| 文档 | 定义 | 组件数 |
|------|------|--------|
| 集群运行机制 v1.2 | 16 Agent + 4 团队 + 5 协作链 + 四维路由 | 31 |
| 协作编排机制 v1.0 | 决策分离 + 6 评审角色 + 加权聚合 | 14 |
| 八卦路由机制 v2.5 | 8 卦位 + 五行能量 + 640 Agent 扩展 | 30 |
| context 传递规范 v1.0 | 5 JSON 文件 + 双向上下文流 | 10 |
| 调度指南 v2.1 | 六车道 + 3 组 Agent + 29 技能 | 35 |
| 子 Agent 运行机制 v1.0 | 生命周期 + 7 工具 + 修炼维度 | 16 |
| 集群运作机制 v1.0 | S2 架构 + 4 拓扑 + 事件驱动 | 15 |

---

## A-Z 环节总览 (26 环节)

| # | 环节 | 模块 | 天数 | 文件 |
|---|------|------|------|------|
| A | 集群核心协议 | protocol.py + registry.py | 1d | 3 新 |
| B | Agent 注册表 | 16 Agent 3 类 8 卦 4 队 | (A 内) | — |
| C | 四维评分路由 | router.py | 0.5d | 1 新 |
| D | 协作链定义 | 5 YAML 链定义 | 0.5d | 6 新 |
| E | 协作链执行器 | ChainExecutor | 0.5d | 1 新 |
| F | 上下文传递协议 | context.py + 5 JSON Schema | 0.5d | 7 新 |
| G | 六车道调度器 | dispatcher.py + config | 0.5d | 2 新 |
| H | 子 Agent 生命周期 | lifecycle.py | 0.5d | 1 新 |
| I | 八卦坐标系 | coordinates.py | 0.5d | 1 新 |
| J | 八卦路由引擎 | router.py (bagua) | 0.5d | 1 新 |
| K | 八卦拓扑管理 | topology.py | 0.5d | 1 新 |
| L | 八卦消息队列 | message_queue.py | 0.5d | 1 新 |
| M | 集群事件总线 | event_bus.py | 0.5d | 1 新 |
| N | 集群协商器 | negotiator.py | 0.5d | 1 新 |
| O | 集群共识机制 | consensus.py | 0.5d | 1 新 |
| P | 集群冲突解决 | conflict.py | 0.5d | 1 新 |
| Q | 方案编排流水线 | proposal_flow.py | 0.5d | 1 新 |
| R | 评审角色系统 | review.py | 0.5d | 1 新 |
| S | 集群监控采集 | monitor.py | 0.5d | 1 新 |
| T | 集群监控告警 | alerts.py | 0.5d | 1 新 |
| U | SoulTeam TUI 屏 | soulteam.py (TUI) | 0.5d | 1 新 |
| V | SwarmFly↔SoulTeam | bridge.py | 0.5d | 1 新 |
| W | 集群集成测试 | test_cluster_integration.py | 0.5d | 1 新 |
| X | 协作链集成测试 | test_collab_chain.py | 0.5d | 1 新 |
| Y | 八卦路由集成测试 | test_bagua.py | 0.5d | 1 新 |
| Z | 端到端验收+文档 | docs/M10_SOULTEAM_DESIGN.md | 0.5d | 1 文档 |

---

## 已完成

| 环节 | 状态 | 文件 |
|------|------|------|
| A | ✅ | protocol.py (7 消息类型 + Baton) |
| B | ✅ | registry.py (16 Agent) |
| C | ✅ | router.py (FourDimensionRouter) |

---

## 验证

```bash
pytest packages/SoulTeam/tests/ -v
```
