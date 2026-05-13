# ZenAgent API 文档索引

> 📅 更新时间: 2026-05-13 | 🎯 版本: 1.0.0

## 📚 文档导航

| 模块 | 文件 | 模块数 | 说明 |
|------|------|--------|------|
| Runtime | [Runtime.md](Runtime.md) | 25 | 运行时核心：会话管理、上下文压缩、检查点、HTL策略、事件总线 |
| ZenAgent | [ZenAgent.md](ZenAgent.md) | 19 | Agent核心：MCP协议、觉醒回路、协作协议、钩子系统 |
| SoulTeam | [SoulTeam.md](SoulTeam.md) | 24 | 灵魂团队：记忆系统、自学习、反思、人格演化 |
| SwarmFly | [SwarmFly.md](SwarmFly.md) | 69 | 群体飞行：生命周期、协作调度、共享内存、团队构建 |

## 🚀 快速开始

### 导入示例

```python
# Runtime - 会话管理
from Runtime.session import Session, SessionManager

# ZenAgent - Agent注册
from ZenAgent.MCP.registry import AgentRegistry

# SoulTeam - 记忆系统
from SoulTeam.memory.context import ContextMemory

# SwarmFly - 团队协作
from SwarmFly.team.builder import TeamBuilder
```

### 核心类速查

| 功能 | 类 | 包 |
|------|-----|-----|
| 会话管理 | `SessionManager` | Runtime.session |
| 上下文压缩 | `ContextManager` | Runtime.context_compaction |
| 检查点快照 | `SnapshotManager` | Runtime.checkpoint |
| 事件总线 | `EventBus` | Runtime.buses |
| 任务队列 | `TaskQueue` | Runtime.buses |
| Agent注册 | `AgentRegistry` | ZenAgent.MCP |
| 协作协议 | `CollaborationProtocol` | ZenAgent.collaboration |
| 记忆管理 | `MemoryManager` | SoulTeam.memory |
| 团队构建 | `TeamBuilder` | SwarmFly.team |

## 📂 项目结构

```
ZenAgent/
├── packages/
│   ├── Runtime/          # 运行时核心
│   │   ├── session/      # 会话生命周期
│   │   ├── context_compaction/  # 上下文压缩
│   │   ├── checkpoint/   # 检查点/快照
│   │   ├── htl/          # HTL策略
│   │   ├── buses/        # 事件总线 + 任务队列
│   │   ├── audit/        # 审计日志
│   │   └── security/     # 安全加密
│   ├── ZenAgent/         # Agent核心
│   │   ├── MCP/          # MCP协议
│   │   ├── hooks/        # 钩子系统
│   │   ├── awakening/    # 觉醒回路
│   │   └── collaboration/# 协作协议
│   ├── SoulTeam/         # 灵魂团队
│   │   ├── memory/       # 四层记忆
│   │   ├── learning/     # 自学习
│   │   ├── reflection/   # 反思系统
│   │   └── personality/  # 人格演化
│   └── SwarmFly/         # 群体飞行
│       ├── layers/       # 协作层
│       ├── memory/       # 共享内存
│       └── team/         # 团队构建
└── tests/                # 测试套件
    ├── unit/             # 单元测试
    └── e2e/               # 端到端测试
```

---

*由 ZenAgent API 文档生成器自动生成*
