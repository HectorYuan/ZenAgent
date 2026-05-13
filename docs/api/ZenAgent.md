# ZenAgent 模块

> 路径: `packages/ZenAgent/`

## 模块列表

### `awakening.adapter`

觉醒能力适配器
提供 Agent 觉醒能力的统一访问接口

**类:** `AwakeningState`, `AwakeningContext`, `AwakeningAdapter`

**函数:** `add_experience`, `record_success`, `record_failure`, `update_progress`, `should_awaken`, `success_rate`, `__post_init__`, `state`, `is_awakened`, `progress` ... (+16 more)

---

### `awakening.capabilities`

能力定义和发现
定义 Agent 的觉醒能力体系

**类:** `AwakeningCapability`, `CapabilityInfo`, `CapabilityRegistry`

**函数:** `unlock_capability`, `lock_capability`, `is_unlocked`, `get_unlocked_capabilities`, `get_locked_capabilities`, `get_capability_info`, `record_usage`, `get_usage_stats`, `list_all_capabilities`, `list_by_category` ... (+1 more)

---

### `awakening.evolution`

Agent 进化机制
提供 Agent 持续进化的框架

**类:** `EvolutionStage`, `EvolutionEvent`, `EvolutionConfig`, `AgentEvolution`, `EvolutionEngine`

**函数:** `success_rate`, `add_experience`, `record_interaction`, `__init__`, `register_agent`, `get_evolution`, `get_current_stage`, `get_experience`, `can_evolve`, `_get_next_stage` ... (+9 more)

---

### `collaboration.negotiator`

协作协商器
处理 Agent 间的协作协商过程

**类:** `NegotiationStatus`, `NegotiationResponse`, `NegotiationResult`, `CollaborationNegotiator`

**函数:** `to_dict`, `is_successful`, `is_completed`, `to_dict`, `__init__`, `create_negotiation`, `get_negotiation`, `get_request`, `accept_request`, `decline_request` ... (+9 more)

---

### `collaboration.protocols`

协作协议定义
定义 Agent 间协作的通信协议

**类:** `ProtocolType`, `MessagePriority`, `CollaborationMessage`, `CollaborationRequest`, `CollaborationResponse`, `CollaborationProtocol`

**函数:** `is_broadcast`, `is_reply`, `is_expired`, `set_expiry`, `to_dict`, `from_dict`, `to_dict`, `from_dict`, `to_dict`, `from_dict` ... (+5 more)

---

### `collaboration.task_router`

任务路由
将任务智能路由到合适的 Agent

**类:** `RouteStrategy`, `TaskRoute`, `RoutingRule`, `TaskRouter`

**函数:** `is_valid`, `to_dict`, `matches`, `__post_init__`, `set_registry`, `_add_default_rules`, `add_rule`, `remove_rule`, `get_rule`, `list_rules` ... (+6 more)

---

### `core`

ZenAgent 核心入口

整合 MCP、Hooks、Awakening 和 Collaboration 模块的统一入口

**类:** `ZenAgentConfig`, `ZenAgent`

**函数:** `__init__`, `_initialize_modules`, `protocol`, `session_manager`, `handler_registry`, `agent_registry`, `hook_manager`, `lifecycle_manager`, `metrics`, `awakening` ... (+12 more)

---

### `hooks.builtin_hooks`

内置钩子实现
提供常用的内置钩子：日志、监控、限流等

**类:** `LoggingHook`, `MetricsHook`, `RateLimitHook`, `MonitoringHook`

**函数:** `__post_init__`, `_handle_log`, `__post_init__`, `_handle_metrics`, `get_counts`, `get_error_counts`, `get_event_rate`, `get_uptime`, `get_summary`, `reset` ... (+18 more)

---

### `hooks.hook_manager`

钩子管理器
提供统一的钩子注册、触发和管理功能

**类:** `HookPriority`, `HookRegistration`, `HookEvent`, `HookManager`

**函数:** `__post_init__`, `should_execute`, `mark_executed`, `__init__`, `register`, `unregister`, `enable`, `disable`, `is_enabled`, `_get_hook` ... (+10 more)

---

### `hooks.lifecycle`

生命周期钩子
提供 Agent 生命周期的标准钩子定义和装饰器

**类:** `LifecycleEvent`, `LifecycleHook`, `LifecycleManager`

**函数:** `__post_init__`, `my_handler`, `decorator`, `my_handler`, `decorator`, `my_handler`, `decorator`, `my_handler`, `decorator`, `my_handler` ... (+5 more)

---

### `mcp.handlers`

MCP 协议处理器
提供方法处理器注册和消息路由功能

**类:** `MCPHandler`, `MCPHandlerRegistry`, `MCPProtocolHandler`

**函数:** `register`, `register_notification`, `get_handler`, `has_handler`, `list_methods`, `get_method_info`, `list_all_methods`, `__init__`, `_setup_default_handlers`, `decorator`

---

### `mcp.message`

MCP 消息格式和序列化
提供消息对象的类型化封装

**类:** `MCPMessage`, `MCPRequest`, `MCPResponse`, `MCPErrorResponse`, `MCPNotification`, `MessageBuilder`

**函数:** `message_type`, `to_dict`, `from_dict`, `message_type`, `to_dict`, `from_dict`, `create`, `message_type`, `to_dict`, `from_dict` ... (+13 more)

---

### `mcp.protocol`

MCP 协议核心定义
定义 Model Context Protocol 的基础协议结构

**类:** `MCPMessageType`, `MCPErrorCode`, `MCPProtocol`

**函数:** `__post_init__`, `version_info`, `validate_message`, `create_request`, `create_response`, `create_notification`, `create_error_response`, `serialize`, `deserialize`, `get_capabilities`

---

### `mcp.registry`

Agent 注册表
管理 Agent 的注册、发现和能力查询

**类:** `AgentStatus`, `AgentCapability`, `AgentMetadata`, `RegisteredAgent`, `AgentRegistry`

**函数:** `has_capability`, `supports_capabilities`, `add_capability`, `remove_capability`, `to_dict`, `update_heartbeat`, `increment_request`, `start_task`, `end_task`, `success_rate` ... (+17 more)

---

### `mcp.session`

MCP 会话管理和上下文传递
提供会话生命周期管理和状态追踪

**类:** `MCPSessionState`, `MCPSessionContext`, `MCPSession`, `MCPSessionManager`

**函数:** `add_message`, `get_recent_messages`, `set_metadata`, `get_metadata`, `age_seconds`, `idle_seconds`, `__post_init__`, `is_alive`, `is_ready`, `is_idle` ... (+20 more)

---

### `tests.test_awakening`

Awakening适配器测试

**类:** `TestAwakeningAdapter`

**函数:** `test_adapter_creation`, `test_adapter_has_capability`, `test_adapter_awaken`

---

### `tests.test_collaboration`

协作测试

**类:** `TestCollaboration`

**函数:** `test_negotiator_creation`, `test_router_creation`

---

### `tests.test_hooks`

钩子管理器测试

**类:** `TestHookManager`

**函数:** `test_manager_creation`, `test_manager_has_register`, `test_manager_has_trigger`

---

### `tests.test_mcp`

MCP协议测试

**类:** `TestMCPProtocol`

**函数:** `test_protocol_creation`, `test_validate_message_valid`, `test_create_request`

---

