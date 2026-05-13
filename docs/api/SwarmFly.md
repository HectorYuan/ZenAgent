# SwarmFly 模块

> 路径: `packages/SwarmFly/`

## 模块列表

### `FLY-2_法则层.Core.ConflictResolver.deadlock_detector`

死锁检测器 (Deadlock Detector)

检测和预防智能体间的资源死锁:
- 等待图分析
- 循环等待检测
- 死锁预防策略
- 死锁恢复机制

**类:** `DeadlockState`, `WaitEdge`, `DeadlockInfo`, `DeadlockResolution`, `WaitGraph`, `DeadlockDetector`

**函数:** `__init__`, `add_edge`, `remove_edge`, `remove_agent`, `has_cycle`, `dfs`, `get_cycle`, `__init__`, `start_detection`, `stop_detection` ... (+11 more)

---

### `FLY-2_法则层.Core.ConflictResolver.priority_manager`

优先级管理器 (Priority Manager)

管理智能体的优先级计算、动态调整和竞争解决。
支持多种优先级算法和实时优先级更新。

**类:** `PriorityLevel`, `PriorityScore`, `AgentPriority`, `PriorityCalculator`, `PriorityManager`

**函数:** `__lt__`, `__gt__`, `effective_priority`, `__init__`, `_normalize_weights`, `calculate`, `_score_to_level`, `__init__`, `register_agent`, `unregister_agent` ... (+10 more)

---

### `FLY-2_法则层.Core.ConflictResolver.resource_arbiter`

资源仲裁器 (Resource Arbiter)

提供资源分配决策和冲突仲裁功能。
支持多种分配策略: 优先级、公平、轮询等。

**类:** `ResourceType`, `AllocationStrategy`, `ResourceRequest`, `ResourceAllocation`, `ArbitrationResult`, `ResourcePool`, `ResourceArbiter`

**函数:** `is_expired`, `is_valid`, `__init__`, `available_capacity`, `utilization`, `can_allocate`, `allocate`, `release`, `reserve`, `release_reservation` ... (+16 more)

---

### `FLY-2_法则层.Core.RuleEngine.rule_cache`

规则缓存 (Rule Cache)

提供LRU缓存 + 版本控制的规则缓存实现。
支持规则版本管理、回滚和一致性验证。

**类:** `CacheEntry`, `VersionSnapshot`, `RuleCache`, `RuleCacheManager`

**函数:** `touch`, `is_expired`, `__init__`, `get`, `_l1_get`, `_l2_get`, `set`, `_l1_set`, `invalidate`, `invalidate_pattern` ... (+25 more)

---

### `FLY-2_法则层.Core.RuleEngine.rule_executor`

规则执行器 (Rule Executor)

基于向前链推理(Forward Chaining)的规则执行引擎。
使用Rete算法优化实现，支持并行执行和条件缓存。

**类:** `ExecutionStatus`, `ExecutionContext`, `ExecutionResult`, `ReteNode`, `AlphaNode`, `BetaNode`, `TerminalNode`, `RuleExecutor`

**函数:** `get_value`, `set_value`, `success`, `__init__`, `add_child`, `activate`, `__init__`, `test`, `__init__`, `activate` ... (+18 more)

---

### `FLY-2_法则层.Core.RuleEngine.rule_parser`

规则解析器 (Rule Parser)

支持YAML/JSON格式的规则定义，解析为内部规则对象。
使用PyYAML进行YAML解析，JSON Schema进行规则验证。

**类:** `RuleType`, `ConditionOperator`, `RuleCondition`, `RuleAction`, `Rule`, `RuleParseResult`, `RuleParser`, `RuleGraph`

**函数:** `evaluate`, `_get_nested_value`, `_compare`, `__post_init__`, `_generate_id`, `get_checksum`, `__init__`, `parse`, `_detect_format`, `_parse_single_rule` ... (+11 more)

---

### `FLY-2_法则层.Core.RuleEngine.rule_validator`

规则验证器 (Rule Validator)

提供规则语法验证、语义验证、冲突检测和依赖验证功能。
确保规则的正确性、一致性和可执行性。

**类:** `ValidationLevel`, `ValidationError`, `Conflict`, `ValidationResult`, `RuleValidator`

**函数:** `add_error`, `add_warning`, `add_conflict`, `__init__`, `validate_syntax`, `_validate_condition`, `_validate_action`, `validate_semantics`, `_find_condition_contradictions`, `validate_conflicts` ... (+7 more)

---

### `FLY-2_法则层.Core.SecurityEnforcer.audit_logger`

审计日志 (Audit Logger)

记录系统操作和事件:
- 操作审计
- 安全事件
- 合规报告
- 日志查询与分析

**类:** `AuditLevel`, `AuditEventType`, `AuditEvent`, `AuditLogger`

**函数:** `to_dict`, `get_checksum`, `__init__`, `log`, `_generate_event_id`, `_cleanup_old_events`, `_rebuild_index`, `_update_stats`, `_should_alert`, `query` ... (+13 more)

---

### `FLY-2_法则层.Core.SecurityEnforcer.encryption_handler`

加密处理器 (Encryption Handler)

提供数据加密、传输安全和密钥管理功能:
- 对称加密(AES)
- 非对称加密(RSA)
- 密钥派生
- 数字签名
- 安全传输

**类:** `EncryptionAlgorithm`, `KeyType`, `EncryptionKey`, `EncryptedData`, `Signature`, `EncryptionConfig`, `KeyManager`, `EncryptionHandler`

**函数:** `is_expired`, `__init__`, `generate_key`, `get_key`, `revoke_key`, `_generate_key_id`, `list_active_keys`, `__init__`, `_init_default_keys`, `encrypt` ... (+13 more)

---

### `FLY-2_法则层.Core.SecurityEnforcer.permission_checker`

权限检查器 (Permission Checker)

实现基于RBAC的权限管理:
- 角色定义与权限分配
- 权限验证与检查
- 权限继承与委托
- 动态权限调整

**类:** `Permission`, `PermissionLevel`, `Role`, `User`, `PermissionContext`, `PermissionCheckResult`, `ResourcePolicy`, `PermissionChecker`

**函数:** `has_permission`, `add_permission`, `remove_permission`, `has_permission`, `__init__`, `_init_default_roles`, `create_role`, `update_role`, `delete_role`, `get_role` ... (+15 more)

---

### `FLY-2_法则层.Interfaces.evolving_interface`

Evolving引擎接口

提供与Evolving引擎的双向通信:
- 能力上报
- 进化请求
- 境界跃迁

**类:** `EvolutionStatus`, `CapabilityType`, `CapabilityMetrics`, `ExecutionResult`, `EvolutionRequest`, `EvolutionResult`, `RealmTransition`, `EvolvingInterface`

**函数:** `__init__`, `_analyze_execution`, `_update_capability_history`, `_generate_recommendations`, `_generate_request_id`, `get_stats`

---

### `FLY-2_法则层.Interfaces.revolving_interface`

Revolving引擎接口

提供与Revolving引擎的双向通信:
- 规则同步
- 任务路由
- 状态同步

**类:** `SyncDirection`, `RuleSyncStatus`, `RuleSyncEvent`, `TaskRouteEvent`, `TaskRouteRequest`, `TaskRouteResult`, `RevolvingInterface`

**函数:** `__init__`, `_select_target_agent`, `_generate_event_id`, `get_stats`

---

### `FLY-2_法则层.Tests.test_fly2`

FLY-2 法则层 - 单元测试
Unit Tests for FLY-2

**类:** `TestRuleParser`, `TestRuleExecutor`, `TestRuleValidator`, `TestPriorityManager`, `TestResourceArbiter`, `TestPermissionChecker`, `TestAuditLogger`, `TestRevolvingInterface`, `TestEvolvingInterface`

**函数:** `setup_method`, `test_parse_yaml_rule`, `test_parse_json_rule`, `test_parse_simple_condition`, `test_validate_rule_syntax`, `setup_method`, `test_add_rule`, `test_evaluate_rule`, `test_get_statistics`, `setup_method` ... (+14 more)

---

### `FLY-2_法则层.Tests.test_integration`

FLY-2 法·法则层 - 集成测试

**类:** `TestRuleEngine`, `TestConflictResolver`, `TestSecurityEnforcer`, `TestInterfaces`

**函数:** `setUp`, `test_rule_parsing_yaml`, `test_rule_validation`, `test_rule_execution`, `setUp`, `test_priority_calculation`, `test_resource_allocation`, `test_deadlock_detection`, `setUp`, `test_permission_check` ... (+2 more)

---

### `FLY-3_趋势层.Convolv.emergent_detection`

涌现检测 (Emergent Detection)

检测涌现模式和异常信号。

**类:** `EmergenceLevel`, `EmergentPattern`, `EmergenceSignal`, `EmergentDetector`

**函数:** `__init__`, `detect`, `_update_historical_data`, `_detect_convergence`, `_detect_acceleration`, `_detect_phase_change`, `_cv_to_level`, `_update_pattern`, `get_active_patterns`, `get_emergence_alert`

---

### `FLY-3_趋势层.Convolv.trend_convolv`

趋势卷积 (Trend Convolv)

将多个维度的趋势进行卷积运算，生成涌现模式。

**类:** `ConvolvConfig`, `ConvolvResult`, `TrendVector`, `TrendConvolv`

**函数:** `__init__`, `convolve`, `_to_vector`, `_cross_dimension_convolution`, `_triple_dimension_convolution`, `_intra_dimension_convolution`, `_calculate_interaction`, `_calculate_similarity`, `_calculate_confidence`, `get_pattern` ... (+2 more)

---

### `FLY-3_趋势层.Core.PredictionEngine.prediction_engine`

预测引擎 (Prediction Engine)

提供趋势预测能力:
- 时序预测
- 趋势外推
- 置信区间

**类:** `PredictionModel`, `PredictionHorizon`, `Prediction`, `TimeSeriesPoint`, `PredictionEngine`

**函数:** `__init__`, `predict`, `_linear_regression`, `_exponential_smoothing`, `_moving_average`, `_weighted_moving_average`, `_simple_trend`, `_calculate_confidence`, `_determine_trend`, `_get_accuracy` ... (+2 more)

---

### `FLY-3_趋势层.Core.TrendAnalyzer.behavior_analyzer`

行为趋势分析器 (Behavior Analyzer)

分析用户/智能体行为趋势:
- 使用模式
- 性能趋势
- 交互模式

**类:** `BehaviorEvent`, `BehaviorPattern`, `BehaviorAnalyzer`

**函数:** `__init__`, `record_event`, `analyze_agent_behavior`, `_calculate_regularity`, `_analyze_performance`, `analyze_all_agents`, `detect_anomalous_behavior`, `get_usage_trends`, `get_success_rate_trend`

---

### `FLY-3_趋势层.Core.TrendAnalyzer.market_trend_analyzer`

市场趋势分析器 (Market Trend Analyzer)

分析市场数据趋势:
- 价格/量趋势
- 市场份额变化
- 竞争格局变化

**类:** `MarketDataPoint`, `MarketMetric`, `MarketTrendAnalyzer`

**函数:** `__init__`, `add_data`, `add_batch_data`, `analyze_symbol`, `analyze_all`, `_determine_trend`, `_calculate_volatility`, `_calculate_score`, `_calculate_confidence`, `get_metrics` ... (+2 more)

---

### `FLY-3_趋势层.Core.TrendAnalyzer.tech_trend_analyzer`

技术趋势分析器 (Tech Trend Analyzer)

专门分析技术领域趋势:
- 技术关键词提取
- 技术栈趋势
- 新兴技术识别

**类:** `TechKeyword`, `TechKeywordExtractor`, `TechTrendAnalyzer`

**函数:** `__init__`, `_build_keyword_index`, `extract_from_text`, `get_trending_keywords`, `__init__`, `analyze`, `_determine_trend_type`, `_calculate_score`, `_calculate_confidence`, `_calculate_velocity` ... (+4 more)

---

### `FLY-3_趋势层.Core.TrendAnalyzer.trend_analyzer`

趋势分析器核心 (Trend Analyzer)

提供趋势识别的通用框架:
- 趋势数据模型
- 趋势聚合
- 趋势评分

**类:** `TrendType`, `TrendSource`, `Trend`, `TrendAnalysis`, `TrendAggregator`, `TrendScorer`, `TrendAnalyzer`

**函数:** `is_significant`, `get_lifespan`, `__init__`, `aggregate_trends`, `_merge_trends`, `calculate_score`, `calculate_confidence`, `__init__`, `add_analyzer`, `analyze` ... (+5 more)

---

### `S1_Evolution.Phase1_Fix.comment_checker`

代码注释检查器

检查代码注释率，确保符合规范(<15%)

**类:** `CommentStats`, `CommentChecker`

**函数:** `__init__`, `check_file`, `_check_debug_comment`, `check_directory`, `_generate_summary`, `generate_report`

---

### `S1_Evolution.Phase1_Fix.config_validator`

配置文件验证器

检测YAML/JSON配置中的重复键和其他问题

**类:** `ValidationIssue`, `ValidationResult`, `ConfigValidator`

**函数:** `__init__`, `validate_file`, `_validate_yaml`, `_validate_json`, `_detect_duplicate_keys_yaml`, `_detect_duplicate_keys_json`, `validate_directory`, `generate_report`

---

### `S1_Evolution.Phase1_Fix.handoff_bridge`

HandoffBridge - 智能体交接桥接模块

负责智能体之间的任务交接和状态传递
修复版本: v1.1 (S1进化)

**类:** `HandoffState`, `HandoffPriority`, `HandoffContext`, `HandoffResult`, `HandoffBridge`

**函数:** `is_expired`, `time_remaining`, `is_successful`, `__init__`, `initiate_handoff`, `confirm_handoff`, `complete_handoff`, `fail_handoff`, `cancel_handoff`, `_handle_timeout` ... (+6 more)

---

### `S1_Evolution.Phase1_Fix.test_handoff_bridge`

HandoffBridge边界测试用例

测试各种边界条件和异常场景
修复版本: v1.1 (S1进化)

**类:** `TestHandoffBridgeBasic`, `TestHandoffBridgeBoundary`, `TestHandoffBridgeTimeout`, `TestHandoffBridgeConcurrency`, `TestHandoffBridgePriority`, `TestHandoffBridgeMetadata`, `TestHandoffBridgeStats`, `TestHandoffBridgeHistory`, `TestHandoffBridgeQuery`

**函数:** `setup_method`, `test_initiate_basic_handoff`, `test_confirm_handoff`, `test_complete_handoff`, `setup_method`, `test_empty_source_agent_id`, `test_empty_target_agent_id`, `test_same_source_and_target`, `test_empty_task_data`, `test_none_task_data` ... (+25 more)

---

### `S1_Evolution.Phase2_Interface.evolve_engine_client`

EvolveEngine接口客户端

提供与EvolveEngine进化引擎的通信接口

**类:** `EvolutionState`, `CapabilityType`, `Capability`, `EvolutionRequest`, `EvolutionResult`, `EvolveEngineClient`

**函数:** `__init__`, `get_cache`, `clear_cache`

---

### `S1_Evolution.Phase2_Interface.run_phase2_tests`

Phase 2: 接口测试运行器
独立运行接口测试，不依赖SwarmFly核心模块

**类:** `EvolutionState`, `CapabilityType`, `Capability`, `EvolutionRequest`, `EvolutionResult`, `EvolveEngineClient`, `ToolStatus`, `ExecutionStatus`, `Tool`, `ToolExecution`, `UsageMetrics`, `ZenLoopClient`, `TestEvolveEngine`, `TestZenLoop`, `TestInterfaceIntegration`

**函数:** `__init__`, `get_cache`, `success_rate`, `__init__`, `setUp`, `test_client_initialization`, `test_sync_capability_bidirectional`, `test_request_capability_evolution`, `test_report_execution_result`, `test_subscribe_evolution_events` ... (+11 more)

---

### `S1_Evolution.Phase2_Interface.test_evolve_engine`

EvolveEngine接口测试用例

**类:** `TestEvolveEngineBasic`, `TestCapabilitySync`, `TestEvolutionRequest`, `TestExecutionResult`, `TestEventSubscription`, `TestCapability`, `TestEvolutionRequestModel`, `TestEvolutionResultModel`

**函数:** `setup_method`, `test_client_initialization`, `test_get_agent_evolution_status`, `setup_method`, `test_sync_capability_bidirectional`, `test_capability_cache`, `setup_method`, `test_request_capability_evolution`, `test_evolution_request_with_callback`, `setup_method` ... (+10 more)

---

### `S1_Evolution.Phase2_Interface.test_zenloop`

ZenLoop接口测试用例

**类:** `TestZenLoopBasic`, `TestToolRegistration`, `TestToolDiscovery`, `TestToolExecution`, `TestToolMonitoring`, `TestToolRelease`, `TestTool`, `TestToolExecutionModel`, `TestUsageMetrics`

**函数:** `setup_method`, `test_client_initialization`, `setup_method`, `test_register_tool_basic`, `test_register_tool_with_full_params`, `test_register_multiple_tools`, `setup_method`, `test_discover_all_tools`, `test_discover_by_category`, `test_discover_by_query` ... (+16 more)

---

### `S1_Evolution.Phase2_Interface.zenloop_client`

ZenLoop工具循环引擎接口客户端

提供与ZenLoop工具中心的通信接口

**类:** `ToolStatus`, `ExecutionStatus`, `Tool`, `ToolExecution`, `UsageMetrics`, `ZenLoopClient`

**函数:** `success_rate`, `__init__`

---

### `S1_Evolution.Phase3_Integration.run_phase3_tests`

Phase 3: 框架整合测试

测试整合组件的功能

**类:** `TestConfigManager`, `TestLifecycleManager`, `TestMetricsExporter`, `TestMainController`, `TestSwarmFlyAdapter`, `TestComponentIntegration`

**函数:** `setUp`, `test_load_default_config`, `test_get_config_item`, `test_get_nested_config`, `test_get_default_value`, `setUp`, `test_register_component`, `test_register_with_dependencies`, `test_get_component_state`, `test_get_component_state_not_found` ... (+19 more)

---

### `S1_Evolution.Phase3_Integration.swarmfly_integration`

SwarmFly框架整合 - Phase 3

整合SwarmFly到智能体主框架，实现统一管理

**类:** `ComponentState`, `ComponentType`, `ComponentInfo`, `LifecycleHook`, `ConfigManager`, `LifecycleManager`, `UnifiedLogger`, `MetricsExporter`, `MainController`, `SwarmFlyAdapter`

**函数:** `__init__`, `_get_default_config_path`, `_get_default_config`, `_validate_config`, `get`, `get_all`, `reload`, `on_config_change`, `__init__`, `register_component` ... (+28 more)

---

### `S1_Evolution.Phase4_Test.run_phase4_tests`

Phase 4: 测试验证
> **执行周期**: Week 6 (2026-06-03 ~ 2026-06-08)
> **状态**: 🚧 执行中

包含:
- 单元测试 (Unit Tests)
- 集成测试 (Integration Tests)
- 性能测试 (Performance Tests)
- E2E测试 (End-to-End Tests)
- 安全测试 (Security Te

**类:** `EvolutionState`, `CapabilityType`, `Capability`, `EvolutionRequest`, `ToolStatus`, `ExecutionStatus`, `Tool`, `ToolExecution`, `UsageMetrics`, `EvolveEngineClient`, `ZenLoopClient`, `ComponentState`, `ComponentType`, `ComponentInfo`, `LifecycleManager`, `TestUnitSuite`, `TestEvolveEngineIntegration`, `TestZenLoopIntegration`, `TestEndToEnd`, `TestPerformance`, `TestSecurity`, `TestLifecycle`

**函数:** `__init__`, `__init__`, `__init__`, `register_component`, `get_uptime`, `state`, `test_evolution_state_enum`, `test_capability_type_enum`, `test_tool_status_enum`, `test_execution_status_enum` ... (+26 more)

---

### `collaboration.conflict_resolver`

冲突解决器

处理多 Agent 协作中的资源冲突和决策冲突

**类:** `ConflictType`, `ResolutionStrategy`, `Conflict`, `ResolutionResult`, `ConflictResolver`

**函数:** `is_resolved`, `to_dict`, `finish`, `duration`, `to_dict`, `__init__`, `set_agent_weight`, `get_agent_weight`, `register_conflict`, `resolve` ... (+13 more)

---

### `collaboration.consensus`

共识机制

实现多 Agent 决策的共识算法

**类:** `ConsensusProtocol`, `Vote`, `ConsensusResult`, `ConsensusMechanism`, `ConsensusRound`, `QuorumConsensus`, `WeightedConsensus`, `UnanimousConsensus`

**函数:** `to_dict`, `finish`, `total_votes`, `agreement_rate`, `to_dict`, `__init__`, `propose`, `vote`, `check_decision`, `get_round` ... (+15 more)

---

### `collaboration.engine`

协作引擎核心

整合任务分发、负载均衡、共识和冲突解决的统一协作引擎

**类:** `CollaborationConfig`, `TaskResult`, `CollaborationEngine`

**函数:** `duration`, `to_dict`, `__init__`, `_init_consensus`, `_setup_internal_callbacks`, `register_agent`, `unregister_agent`, `get_registered_agents`, `submit_task`, `dispatch_next_task` ... (+16 more)

---

### `collaboration.load_balancer`

负载均衡器

管理 Agent 的负载并进行智能任务分配

**类:** `LoadMetric`, `BalancingStrategy`, `AgentLoad`, `LoadBalancer`

**函数:** `total_load`, `normalized_load`, `get_metric`, `to_dict`, `__post_init__`, `agent_count`, `overloaded_agents`, `underloaded_agents`, `register_agent`, `unregister_agent` ... (+14 more)

---

### `collaboration.task_dispatcher`

任务分发器

负责任务的创建、分配和跟踪

**类:** `TaskPriority`, `TaskStatus`, `DispatchStrategy`, `Task`, `TaskDispatcher`

**函数:** `is_completed`, `can_retry`, `get_duration`, `to_dict`, `__post_init__`, `pending_count`, `assigned_count`, `register_agent`, `unregister_agent`, `get_available_agents` ... (+15 more)

---

### `core`

SwarmFly 核心入口

SwarmFly 层统一入口，整合生命周期、协作引擎、内存池和团队模块

**类:** `SwarmFlyConfig`, `SwarmFly`

**函数:** `__init__`, `_init_lifecycle`, `_init_collaboration`, `_init_memory`, `_init_teams`, `register_agent`, `unregister_agent`, `get_registered_agents`, `get_agent_state`, `transition_agent_state` ... (+15 more)

---

### `core.controller`

SwarmFly Controller - 智能体集群主控制器

整合所有FLY层，提供统一的智能体集群管理接口

**类:** `SwarmFlyController`

**函数:** `__init__`, `register_agent`, `unregister_agent`, `get_agent`, `list_agents`, `update_agent_status`, `submit_task`, `dispatch_task`, `complete_task`, `fail_task` ... (+22 more)

---

### `core.fly_layers`

SwarmFly - 智能体集群协同控制器

FLY层架构:
- FLY-0: 主智能体层（任务理解/分派/验收）
- FLY-1: 使命层（愿景/目标设定）
- FLY-2: 法则层（规则/约束）
- FLY-3: 趋势层（市场/技术趋势）
- FLY-4: 技能层（能力/技能）
- FLY-5: 工具层（工具/资源）

**类:** `FLYLevel`, `TaskStatus`, `AgentRole`, `FLYLayer`, `FLY0Master`, `FLY1Mission`, `FLY2Law`, `FLY3Trend`, `FLY4Skill`, `FLY5Tool`

**函数:** `__init__`, `get_state`, `update_state`, `add_listener`, `_notify_listeners`, `__init__`, `submit_task`, `dispatch_task`, `complete_task`, `fail_task` ... (+35 more)

---

### `implementation.shared.base`

FLY深度实现 - 共享基础类定义

**类:** `SwarmFlyError`, `ValidationError`, `ConfigurationError`, `ResourceError`, `BaseModel`, `EnumSerializer`

**函数:** `__init__`, `__init__`, `__init__`, `__init__`, `__init__`, `to_dict`, `to_json`, `from_dict`, `update`, `__repr__` ... (+1 more)

---

### `implementation.shared.events`

FLY深度实现 - 事件总线

**类:** `EventType`, `Event`, `EventBus`

**函数:** `__str__`, `__init__`, `subscribe`, `subscribe_async`, `unsubscribe`, `publish_sync`, `get_history`, `clear_history`

---

### `implementation.shared.logging`

FLY深度实现 - 日志模块

**类:** `LogLevel`, `SwarmFlyFormatter`, `SwarmFlyLogger`

**函数:** `format`, `__init__`, `_setup_handlers`, `debug`, `info`, `warning`, `error`, `critical`, `get_logger`

---

### `implementation.shared.types`

FLY深度实现 - 类型定义

**类:** `Priority`, `MessageType`, `ResourceType`, `TaskStatus`, `AgentState`, `Realm`, `EnlightenmentLevel`, `ResourceRequest`, `ResourceAllocation`, `ExecutionResult`, `ValidationResult`, `Conflict`, `Resolution`

**函数:** `name_cn`, `level`, `name_cn`, `level`

---

### `layers.collaboration`

AgentCollaboration - 智能体协作框架

提供任务分发、结果聚合和冲突解决机制

**类:** `ConflictResolutionStrategy`, `TaskDistributionStrategy`, `TaskDistributor`, `ResultAggregator`, `ConflictResolver`, `AgentCollaborationFramework`

**函数:** `__init__`, `distribute`, `_distribute_random`, `_distribute_round_robin`, `_distribute_least_loaded`, `_distribute_capability_match`, `_distribute_affinity_based`, `update_load`, `__init__`, `aggregate` ... (+19 more)

---

### `lifecycle.agent_lifecycle`

Agent 生命周期状态机

定义 Agent 的完整生命周期状态和状态转换

**类:** `AgentState`, `LifecycleTransition`, `LifecycleCallbacks`, `AgentLifecycle`

**函数:** `__init__`, `state`, `is_active`, `is_terminal`, `can_transition_to`, `transition_history`, `created_at`, `last_updated`, `error`, `register_callback` ... (+15 more)

---

### `lifecycle.exceptions`

生命周期异常定义

**类:** `LifecycleError`, `InvalidTransitionError`, `StateError`, `TransitionError`, `StateManagerError`, `CallbackError`

**函数:** `__init__`, `__init__`

---

### `lifecycle.state_manager`

状态管理器

管理多个 Agent 的状态，提供批量操作和状态查询功能

**类:** `StateTransitionResult`, `StateManager`

**函数:** `__init__`, `agent_count`, `active_agents`, `transition_history`, `register_agent`, `unregister_agent`, `get_agent`, `get_state`, `transition`, `batch_transition` ... (+11 more)

---

### `lifecycle.transitions`

状态转换规则定义和验证器

**类:** `TransitionType`, `TransitionRule`, `TransitionRules`, `TransitionValidator`

**函数:** `can_transition`, `__init__`, `add_rule`, `remove_rule`, `get_rules_for_state`, `get_target_states`, `_build_transition_map`, `rules`, `__init__`, `_build_map` ... (+2 more)

---

### `memory.coherence`

缓存一致性

实现缓存一致性协议（MESI 等）

**类:** `CoherenceProtocol`, `CacheLineState`, `CacheLine`, `InvalidationResult`, `CacheCoherence`

**函数:** `is_valid`, `is_modified`, `is_shared`, `is_exclusive`, `to_dict`, `__init__`, `read`, `write`, `_mesi_write`, `_msi_write` ... (+13 more)

---

### `memory.lock_manager`

锁管理器

提供读写锁、公平锁等多种锁机制

**类:** `LockType`, `Lock`, `LockAcquisitionResult`, `ReadLock`, `WriteLock`, `FairLock`, `LockManager`

**函数:** `holder_count`, `is_exclusive`, `add_holder`, `remove_holder`, `to_dict`, `duration`, `__init__`, `__enter__`, `__exit__`, `__init__` ... (+23 more)

---

### `memory.segment`

内存段管理

管理共享内存池中的内存段

**类:** `SegmentType`, `SegmentAccess`, `MemorySegment`, `SegmentManager`

**函数:** `size`, `can_read`, `can_write`, `is_accessible_by`, `read`, `write`, `acquire_read_lock`, `acquire_write_lock`, `release_lock`, `mark_clean` ... (+16 more)

---

### `memory.shared_pool`

共享内存池核心

提供多 Agent 共享内存的统一管理

**类:** `MemoryPoolConfig`, `PoolStats`, `SharedMemoryPool`

**函数:** `__init__`, `register_agent`, `unregister_agent`, `get_registered_agents`, `create_segment`, `get_segment`, `delete_segment`, `read_with_lock`, `write_with_lock`, `update_with_lock` ... (+12 more)

---

### `memory.sync_protocol`

同步协议

定义内存同步的消息格式和操作类型

**类:** `SyncOperation`, `SyncState`, `SyncMessage`, `SyncProtocol`

**函数:** `is_broadcast`, `to_dict`, `__init__`, `register_peer`, `unregister_peer`, `get_peers`, `create_message`, `send_message`, `receive_message`, `acknowledge_message` ... (+11 more)

---

### `team.builder`

团队构建器

提供团队创建、配置和管理的统一接口

**类:** `TeamStatus`, `TeamConfig`, `BuildResult`, `Team`, `TeamBuilder`

**函数:** `is_active`, `member_count`, `to_dict`, `__init__`, `create_team`, `_validate_config`, `get_team`, `get_all_teams`, `dissolve_team`, `add_member` ... (+5 more)

---

### `team.formation`

编队管理

管理团队的阵型和位置

**类:** `FormationType`, `Position`, `Formation`, `FormationManager`

**函数:** `coordinates`, `distance_to`, `is_adjacent_to`, `to_dict`, `size`, `filled_positions`, `is_full`, `available_positions`, `assign`, `unassign` ... (+14 more)

---

### `team.membership`

成员管理

管理团队成员和成员关系

**类:** `MembershipStatus`, `Member`, `MembershipRequest`, `MembershipManager`

**函数:** `is_active`, `success_rate`, `performance_score`, `update_activity`, `record_task_completion`, `to_dict`, `approve`, `reject`, `to_dict`, `__init__` ... (+16 more)

---

### `team.roles`

角色定义

定义 Agent 的角色类型和角色能力

**类:** `AgentRole`, `RoleCapability`, `RoleDefinition`, `RoleRegistry`

**函数:** `has_capability`, `get_capability`, `to_dict`, `__init__`, `_register_default_roles`, `register`, `get_role`, `get_all_roles`, `get_roles_by_priority`, `check_role_constraints` ... (+1 more)

---

### `team.sub_agent_manager`

SubAgentManager - 子智能体管理模块

管理所有子智能体的生命周期、状态和交互

**类:** `SubAgentStatus`, `SubAgentType`, `SubAgent`, `SubAgentManager`, `ExecutorSubAgent`, `ObserverSubAgent`, `CoordinatorSubAgent`, `SpecialistSubAgent`

**函数:** `__init__`, `set_status`, `execute_task`, `_execute`, `_update_metrics`, `get_state`, `terminate`, `__init__`, `_register_default_factories`, `create_agent` ... (+14 more)

---

### `team.team_collaboration`

TeamCollaboration - 团队协作模块

管理团队内部的协作模式、任务分配和结果聚合

**类:** `CollaborationMode`, `TeamRole`, `Team`, `TeamCollaborationManager`

**函数:** `__init__`, `add_member`, `remove_member`, `get_member`, `list_members`, `assign_task`, `_assign_to_member`, `complete_task`, `fail_task`, `collaborate` ... (+20 more)

---

### `team.team_protocol`

团队协议

定义团队成员间的通信协议

**类:** `MessageType`, `ProtocolMessage`, `TeamProtocol`

**函数:** `is_broadcast`, `is_expired`, `acknowledge`, `mark_processed`, `to_dict`, `__init__`, `send_message`, `receive_message`, `process_inbox`, `acknowledge_message` ... (+13 more)

---

### `tests.M8_test_integration`

SwarmFly M8 集成测试套件
FLY-2/3/5 三层协同验证

执行方式: python test_m8_integration.py

**类:** `TestStatus`, `TestCase`, `TestSuite`, `FLY2TestSuite`, `FLY3TestSuite`, `FLY5TestSuite`, `SyncTestSuite`, `M8IntegrationTestRunner`

**函数:** `add_case`, `get_summary`, `__init__`, `_setup_cases`, `__init__`, `_setup_cases`, `__init__`, `_setup_cases`, `callback`, `__init__` ... (+4 more)

---

### `tests.test_collaboration`

协作引擎模块单元测试

**类:** `TestTask`, `TestTaskDispatcher`, `TestLoadBalancer`, `TestConsensus`, `TestConflictResolver`, `TestCollaborationEngine`

**函数:** `test_task_creation`, `test_task_is_completed`, `test_task_can_retry`, `test_dispatcher_creation`, `test_register_agent`, `test_submit_task`, `test_dispatch_task`, `test_complete_task`, `test_fail_task`, `test_priority_ordering` ... (+21 more)

---

### `tests.test_lifecycle`

生命周期模块单元测试

**类:** `TestAgentState`, `TestAgentLifecycle`, `TestTransitionRules`, `TestTransitionValidator`, `TestStateManager`, `TestExceptions`

**函数:** `test_state_values`, `test_state_count`, `test_lifecycle_creation`, `test_initial_state`, `test_valid_transitions`, `test_invalid_transition`, `test_state_history`, `test_callback_registration`, `on_state_change`, `test_to_dict` ... (+20 more)

---

### `tests.test_memory`

内存池模块单元测试

**类:** `TestMemorySegment`, `TestSegmentManager`, `TestLockManager`, `TestSyncProtocol`, `TestCacheCoherence`, `TestSharedMemoryPool`

**函数:** `test_segment_creation`, `test_read_write`, `test_read_only`, `test_version_control`, `test_access_tracking`, `test_manager_creation`, `test_create_segment`, `test_delete_segment`, `test_get_segments_by_type`, `test_manager_creation` ... (+23 more)

---

### `tests.test_swarmfly`

阶段三测试套件 - FLY层深化测试

**类:** `TestFLY0Master`, `TestFLY1Mission`, `TestFLY2Law`, `TestFLY3Trend`, `TestFLY4Skill`, `TestFLY5Tool`, `TestSwarmFlyController`, `TestSubAgentManager`, `TestTeamCollaborationManager`, `TestAgentCollaborationFramework`, `TestResultAggregator`

**函数:** `setUp`, `test_submit_task`, `test_dispatch_task`, `test_complete_task`, `test_fail_task`, `test_get_stats`, `setUp`, `test_get_mission`, `test_get_values`, `test_align_agent` ... (+33 more)

---

### `tests.test_team`

团队模块单元测试

**类:** `TestAgentRole`, `TestRoleDefinition`, `TestRoleRegistry`, `TestPosition`, `TestFormation`, `TestFormationManager`, `TestMember`, `TestMembershipManager`, `TestTeamProtocol`, `TestTeamBuilder`, `TestTeam`

**函数:** `test_role_values`, `test_role_count`, `test_role_definition_creation`, `test_has_capability`, `test_registry_creation`, `test_get_role`, `test_check_constraints`, `test_global_registry`, `test_position_creation`, `test_distance_calculation` ... (+25 more)

---

### `tests.week5_integration.test_integration`

FLY-2/3/5 Week 5 集成测试
End-to-End Integration Tests for FLY-2/3/5

**类:** `TestMetrics`, `IntegrationTestSuite`, `TestFly2Fly3Integration`, `TestFly3Fly5Integration`, `TestFly2Fly5Integration`, `TestFullChainIntegration`, `TestPerformance`, `TestCircuitBreaker`, `TestRollbackMechanism`

**函数:** `__init__`, `record_metric`, `get_summary`, `setup_method`, `test_rule_triggers_trend_analysis`, `test_trend_prediction_triggers_rule_update`, `setup_method`, `test_trend_alert_triggers_tool_call`, `setup_method`, `test_rule_execution_triggers_notification` ... (+13 more)

---

