# ZenAgent API 文档

**最后更新**: 2026-05-19

## 概述

ZenAgent 是一个基于 monorepo 结构的 Agent 智能体集群完全独立运行平台，采用五层架构（L0-L4）提供多层模块协同工作的能力。

## 核心模块

### 1. L0: LLMInfra 层

LLMInfra 层提供 LLM 调用的基础设施，包括多 Provider 管理、缓存、Token 预算分配、响应校验和重试机制。

#### LLMClient

```python
from packages.LLMInfra import LLMClient, Settings

# 创建配置
settings = Settings.from_env()

# 创建客户端（自动集成 Token 预算、响应校验、缓存）
client = LLMClient(settings=settings)

# 基本调用
response = await client.chat(
    messages=[{"role": "user", "content": "你好"}],
    model="gpt-4"
)

# 流式调用
async for chunk in client.chat_stream(
    messages=[{"role": "user", "content": "你好"}],
    model="gpt-4"
):
    print(chunk.content, end="")
```

#### TokenBudgetManager

```python
from packages.LLMInfra import TokenBudgetManager

budget_mgr = TokenBudgetManager()

# 根据消息自动分配 Token 预算
result = budget_mgr.allocate(messages, caller_max_tokens=None)
print(result.max_tokens)       # 分配的 Token 数
print(result.intent)           # 意图分类: simple_qa / general / complex / creative
print(result.truncated)        # 是否截断了上下文
```

#### ResponseValidator

```python
from packages.LLMInfra import ResponseValidator, ResponseConfig

config = ResponseConfig(
    enabled=True,
    auto_retry_on_truncation=True,
    truncation_threshold=0.95
)
validator = ResponseValidator(config)

# 校验响应
result = validator.validate(response, request)
print(result.is_valid)    # 是否有效
print(result.issue)       # 问题类型: empty / truncated / content_filter / None
```

#### Provider 使用

```python
from packages.LLMInfra.providers import ProviderFactory

# 获取 Provider
provider = ProviderFactory.create("modelnexus", config={...})

# 带重试的调用（自动集成 RetryMixin）
response = await provider.chat(messages=[...])
```

### 2. L1: Runtime 层

Runtime 层提供安全基础设施，包括审计日志和加密功能。

#### 审计日志

```python
from packages.Runtime.audit import AuditLogger, AuditLevel, SensitiveOperation

logger = AuditLogger(name="MyLogger", enable_correlation=True)

# 基本日志
event = logger.log(
    operation="data_processing",
    level=AuditLevel.INFO,
    actor_id="user_001",
    status="success"
)

# 敏感操作日志
sensitive_event = logger.sensitive(
    sensitive_type=SensitiveOperation.AUTHENTICATION,
    operation="login",
    actor_id="user_001",
    status="success"
)
```

#### 加密管理

```python
from packages.Runtime.security import EncryptionManager, EncryptionType

manager = EncryptionManager()

# 加密数据
encrypted = manager.encrypt(
    data="sensitive_data",
    encryption_type=EncryptionType.AES
)

# 解密数据
decrypted = manager.decrypt(
    data=encrypted,
    encryption_type=EncryptionType.AES
)
```

### 3. L2: ZenAgent 层

ZenAgent 层是整个系统的入口点，基于 Model Context Protocol (MCP) 实现 Agent 的注册、管理和通信。

#### 主要类

##### ZenAgent

```python
from packages.core import ZenAgent, ZenAgentConfig

# 创建配置
config = ZenAgentConfig(
    agent_id="agent_001",
    agent_name="MyAgent",
    enable_mcp=True,
    enable_hooks=True,
    enable_awakening=True,
    enable_collaboration=True
)

# 创建 Agent
agent = ZenAgent(config=config)
```

##### ZenAgentConfig

```python
@dataclass
class ZenAgentConfig:
    agent_id: str = "default_agent"
    agent_name: str = "ZenAgent"
    agent_type: str = "general"

    # MCP 配置
    mcp_protocol_version: str = "1.0.0"
    session_idle_timeout: int = 300
    session_max_lifetime: int = 3600

    # Hooks 配置
    enable_logging: bool = True
    enable_metrics: bool = True
    enable_rate_limit: bool = True

    # Awakening 配置
    awakening_threshold: float = 0.8
    enable_evolution: bool = True

    # Collaboration 配置
    collaboration_timeout: int = 60
    max_collaboration_participants: int = 5
```

#### ZenAgent 主要方法

```python
# 注册 MCP 处理器
agent.register_handler(
    method="custom_method",
    handler=my_handler_function
)

# 注册生命周期钩子
agent.register_hook(
    event=LifecycleEvent.ON_CREATE,
    handler=my_hook_handler
)

# 注册 Agent
from packages.mcp import AgentMetadata, AgentCapability, AgentStatus

metadata = AgentMetadata(
    agent_id="agent_002",
    name="AnotherAgent",
    agent_type="worker",
    capabilities=[AgentCapability.TASK_EXECUTION],
    status=AgentStatus.ACTIVE
)

registered = agent.register_agent(metadata)

# 触发生命周期事件
import asyncio
asyncio.run(agent.emit_lifecycle_event(LifecycleEvent.ON_START))
```

### 4. L3: SoulTeam 层

SoulTeam 层提供 Agent 的记忆系统、自学习、反思和人格演化功能。

#### 主要类

##### SoulTeam

```python
from packages.SoulTeam.core import SoulTeam, SoulTeamConfig
from packages.SoulTeam.memory import MemoryType

config = SoulTeamConfig(
    soul_id="soul_001",
    soul_name="MySoul",
    enable_memory=True,
    enable_learning=True,
    enable_reflection=True,
    enable_personality=True
)

soul = SoulTeam(config=config)
```

##### 记忆操作

```python
# 存储记忆
memory_id = soul.store_memory(
    content="这是一个重要的记忆",
    memory_type=MemoryType.EPISODIC,
    metadata={"source": "experience"}
)

# 检索记忆
memories = soul.retrieve_memory(
    query="重要",
    memory_type=MemoryType.EPISODIC,
    limit=10
)

# 获取记忆统计
stats = soul.get_memory_stats()
```

##### 学习操作

```python
from packages.SoulTeam.learning import Feedback, FeedbackType

# 处理反馈
feedback = Feedback(
    content="任务执行效果良好",
    feedback_type=FeedbackType.POSITIVE,
    source="supervisor"
)

soul.process_feedback(feedback)
```

##### 人格操作

```python
# 获取人格特质
traits = soul.get_personality_traits()
# 返回: {'openness': 0.7, 'conscientiousness': 0.6, ...}

# 更新人格特质
soul.update_personality_traits({
    "openness": 0.8,
    "conscientiousness": 0.75
})

# 演化人格
result = soul.evolve_personality()
```

##### 反思操作

```python
# 添加经验
experience_id = soul.add_experience(
    content="完成了一个复杂任务",
    context={"difficulty": "high", "duration": 3600}
)

# 触发反思
insights = soul.reflect()
# 返回反思产生的洞察列表
```

### 5. L4: SwarmFly 层

SwarmFly 层负责 Agent 的生命周期管理、协作引擎和共享内存池。

#### 主要类

##### SwarmFly

```python
from packages.SwarmFly.core import SwarmFly, SwarmFlyConfig

config = SwarmFlyConfig(
    node_id="swarm_001",
    node_name="MySwarm",
    enable_lifecycle_management=True,
    enable_collaboration=True,
    enable_shared_memory=True,
    enable_teams=True
)

swarm = SwarmFly(config=config)
```

##### AgentLifecycle

```python
from packages.SwarmFly.lifecycle import AgentLifecycle, AgentState

# 创建生命周期
lifecycle = AgentLifecycle(
    agent_id="agent_001",
    initial_state=AgentState.INITIAL
)

# 状态转换
lifecycle.transition_to(AgentState.STARTING)
lifecycle.transition_to(AgentState.RUNNING)
lifecycle.transition_to(AgentState.IDLE)
lifecycle.transition_to(AgentState.STOPPED)

# 获取当前状态
current_state = lifecycle.state
```

##### SharedMemoryPool

```python
from packages.SwarmFly.memory import SegmentType

# 写入数据
segment_id = swarm.memory_pool.write(
    key="my_data",
    value={"content": "data"},
    segment_type=SegmentType.SHARED
)

# 读取数据
data = swarm.memory_pool.read("my_data")

# 删除数据
swarm.memory_pool.delete("my_data")
```

##### Task

```python
from packages.SwarmFly.collaboration import Task, TaskPriority, TaskStatus

# 创建任务
task = Task(
    task_id="task_001",
    description="分析数据",
    priority=TaskPriority.HIGH,
    created_by="agent_001",
    assigned_to=["agent_002", "agent_003"]
)

# 分发任务
dispatcher = TaskDispatcher(
    collaboration_engine=swarm.collaboration_engine
)
result = dispatcher.dispatch_task(task, task.assigned_to)

# 更新任务状态
task.update_status(TaskStatus.IN_PROGRESS)
task.update_status(TaskStatus.COMPLETED)
```

## 集成使用示例

### Agent 创建流程

```python
from packages.core import ZenAgent, ZenAgentConfig
from packages.SwarmFly.core import SwarmFly, SwarmFlyConfig
from packages.SoulTeam.core import SoulTeam, SoulTeamConfig
from packages.mcp import AgentMetadata, AgentCapability, AgentStatus

# 1. 初始化 SoulTeam
soul_config = SoulTeamConfig(
    soul_id="soul_agent_001",
    soul_name="MyAgentSoul",
    enable_personality=True
)
soul = SoulTeam(config=soul_config)

# 2. 初始化 SwarmFly
swarm_config = SwarmFlyConfig(
    node_id="swarm_agent_001",
    enable_lifecycle_management=True
)
swarm = SwarmFly(config=swarm_config)

# 3. 初始化 ZenAgent
zen_config = ZenAgentConfig(
    agent_id="agent_001",
    agent_name="MyAgent",
    enable_mcp=True
)
zen = ZenAgent(config=zen_config)

# 4. 注册 Agent
metadata = AgentMetadata(
    agent_id="agent_001",
    name="MyAgent",
    capabilities=[AgentCapability.TASK_EXECUTION],
    status=AgentStatus.ACTIVE
)
zen.register_agent(metadata)
```

### 任务协作流程

```python
# 创建任务
task = Task(
    task_id="collab_task_001",
    description="协作分析任务",
    priority=TaskPriority.HIGH,
    created_by="agent_leader",
    assigned_to=["agent_worker_1", "agent_worker_2"]
)

# 存储到共享内存
swarm.memory_pool.write(
    key=f"task_{task.task_id}",
    value={"description": task.description, "status": "pending"},
    segment_type=SegmentType.SHARED
)

# 记录到 SoulTeam
soul.store_memory(
    content=f"任务 {task.task_id} 已分发",
    memory_type=MemoryType.EPISODIC
)
```

### Agent 进化流程

```python
# 1. 积累经验
for i in range(10):
    soul.store_memory(
        content=f"经验 {i}: 执行任务",
        memory_type=MemoryType.EPISODIC
    )
    soul.add_experience(
        content=f"任务执行经验 {i}",
        context={"task_id": i}
    )

# 2. 反思学习
insights = soul.reflect()

# 3. 人格演化
soul.evolve_personality()

# 4. 能力增强
awakening_level = zen.awakening.calculate_awakening_level()
```

## 配置参考

### SoulTeamConfig 完整配置

```python
SoulTeamConfig(
    soul_id="unique_soul_id",
    soul_name="SoulName",
    
    memory_config={
        "max_working_memory": 100,
        "max_episodic_memory": 1000,
        "max_semantic_memory": 5000,
        "max_procedural_memory": 500,
        "vector_dim": 128,
    },
    
    learning_config={
        "learning_rate": 0.01,
        "batch_size": 32,
        "reflection_interval": 10,
        "skill_acquisition_enabled": True,
    },
    
    personality_config={
        "openness": 0.7,
        "conscientiousness": 0.6,
        "extraversion": 0.5,
        "agreeableness": 0.6,
        "neuroticism": 0.3,
    },
    
    enable_memory=True,
    enable_learning=True,
    enable_reflection=True,
    enable_personality=True
)
```

### SwarmFlyConfig 完整配置

```python
SwarmFlyConfig(
    node_id="unique_node_id",
    node_name="NodeName",
    
    enable_lifecycle_management=True,
    default_transition_rules=get_default_rules(),
    
    enable_collaboration=True,
    collaboration_config=CollaborationConfig(),
    
    enable_shared_memory=True,
    memory_pool_config=MemoryPoolConfig(),
    
    enable_teams=True,
    default_team_config=TeamConfig(),
    
    enable_monitoring=True,
    stats_interval=60
)
```

## 错误处理

所有模块都遵循统一的错误处理模式：

```python
try:
    # 操作
    result = agent.register_agent(metadata)
except Exception as e:
    # 错误处理
    print(f"Error: {e}")
```

## 最佳实践

1. **初始化顺序**: SoulTeam → SwarmFly → ZenAgent
2. **配置管理**: 使用配置文件管理各层配置
3. **资源清理**: 使用上下文管理器或显式清理
4. **错误处理**: 实施适当的错误处理机制
5. **日志记录**: 启用审计日志跟踪重要操作

---

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 系统架构设计与模块详解
- [ROADMAP.md](./ROADMAP.md) - 项目路线图与进度追踪
- [E2E-Plan.md](./E2E-Plan.md) - 端到端测试计划
- [E2E_OPTIMIZATION_DESIGN.md](./E2E_OPTIMIZATION_DESIGN.md) - 优化模块设计方案
