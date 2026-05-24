# ZenAgent — 六层智能体平台

**版本**: 1.0.0-beta | **18 里程碑全部交付** | **测试 ~600+**

## 快速开始

```bash
# CLI 对话（真实大模型）
./zena chat "Hello"

# TUI 全屏界面（键盘优先）
./zena tui

# 系统状态
./zena status
./zena personality show
./zena --json status | jq .
```

## 六层架构

```
L0: LLMInfra   Provider责任链 + 熔断 + 缓存 + 意图路由 + 质量管道 + 混合专家
L1: Runtime    限流 + 追踪 + 审计 + Session/Checkpoint/HTL + 优先级队列
L2: ZenAgent   Hook/Awakening/MCP + CLI(13命令) + TUI(6屏键盘优先)
L3: MetaSoul   四层记忆 + SPO知识库 + 5×8人格矩阵 + 经验闭环
L4: SwarmFly   FLY六层 + 四大横切 + 交接桥 + 执行循环 + 自适应LB
L5: SoulTeam   16Agent + 4团队 + 5协作链 + 八卦路由 + 六车道调度
```

## Monorepo 结构

```
packages/
├── LLMInfra/       L0 — LLM 基础设施
├── Runtime/        L1 — 运行时 + 流控 + Session
├── ZenAgent/       L2 — Agent 核心 + CLI/TUI
├── MetaSoul/       L3 — 记忆/人格/学习/反思
├── SwarmFly/       L4 — 集群管理 + FLY六层
├── SoulTeam/       L5 — 团队编排 + 八卦路由
├── modelnexus/     —— ModelNexus API Gateway (子模块)
tests/              共享测试
docs/               设计文档 + 路线图
```

## 常用命令

```bash
./zena chat "..."     # CLI 对话
./zena tui            # TUI 全屏界面
./zena status         # 系统状态
./zena personality show  # 人格查看
./zena memory search "..."  # 记忆搜索
ZENA_LANG=en ./zena tui    # 英文界面
```

## 测试

```bash
pytest packages/ -q
```

## 文档

| 文档 | 说明 |
|------|------|
| [ROADMAP.md](docs/ROADMAP.md) | 路线图 + 里程碑 |
| [Mission.md](docs/Mission.md) | 六层架构顶层定义 |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统架构设计 |
| [API.md](docs/API.md) | API 使用手册 |
| [ZENA_CLI_GUIDE.md](docs/ZENA_CLI_GUIDE.md) | CLI/TUI 使用指南 |
