# Runtime 模块

> 路径: `packages/Runtime/`

## 模块列表

### `audit.audit_trail`

审计轨迹管理

提供审计记录的存储、查询、分析和追踪功能

**类:** `AuditRecordType`, `RecordStatus`, `AuditRecord`, `AuditQuery`, `AuditTrail`

**函数:** `to_dict`, `from_dict`, `is_expired`, `__init__`, `add`, `_compute_checksum`, `_update_indexes`, `_add_to_index`, `_cleanup_old_records`, `get` ... (+12 more)

---

### `audit.compliance`

合规检查模块

提供审计日志的合规性检查、报告生成和违规检测功能

**类:** `ComplianceFramework`, `ComplianceStatus`, `ViolationSeverity`, `ComplianceRule`, `ComplianceViolation`, `ComplianceReport`, `ComplianceChecker`

**函数:** `check`, `_check_threshold`, `_check_pattern`, `_check_time_window`, `_check_required_operation`, `_check_sensitive_access`, `_check_data_retention`, `_check_condition`, `to_dict`, `to_dict` ... (+15 more)

---

### `audit.logger`

审计日志记录器

提供操作审计、敏感操作标记、日志持久化等功能

**类:** `AuditLevel`, `SensitiveOperation`, `AuditEvent`, `AuditLogger`

**函数:** `to_dict`, `from_dict`, `__init__`, `_add_default_handlers`, `console_handler`, `_output_handlers`, `log`, `debug`, `info`, `warning` ... (+12 more)

---

### `buses.event_bus`

事件总线
提供发布/订阅模式的事件通信

**类:** `EventType`, `Event`, `EventBus`

**函数:** `__init__`, `publish`, `_publish_local`, `subscribe`, `get_stats`

---

### `buses.task_queue`

任务队列
基于 Redis Streams 的持久化任务队列

**类:** `TaskPriority`, `Task`, `TaskQueue`

**函数:** `__init__`, `enqueue`, `_enqueue_redis`, `_enqueue_local`, `dequeue`, `_dequeue_redis`, `_dequeue_local`, `ack`, `get_stats`

---

### `buses.tests.test_buses`

Runtime Buses 单元测试

**类:** `TestEventBus`, `TestTaskQueue`, `TestEventBusWithRedis`, `TestTaskQueueWithRedis`

**函数:** `test_creation`, `test_publish_subscribe`, `callback`, `test_stats`, `test_creation`, `test_enqueue_dequeue`, `test_priority`, `test_stats`, `test_with_redis`, `test_with_redis`

---

### `checkpoint.event_store`

事件存储 - Event Store

提供事件溯源的存储和查询能力

**类:** `EventType`, `Event`, `EventStore`

**函数:** `to_dict`, `from_dict`, `__init__`, `append`, `get_events`, `get_event_by_id`, `get_event_stream`, `replay`, `subscribe`, `unsubscribe` ... (+10 more)

---

### `checkpoint.recovery`

恢复机制 - Recovery Manager

提供系统故障恢复和状态重建能力

**类:** `RecoveryStrategy`, `RecoveryPoint`, `RecoveryResult`, `RecoveryManager`

**函数:** `to_dict`, `from_dict`, `to_dict`, `__init__`, `register_state_reducer`, `recover`, `_recover_from_snapshot`, `_recover_from_events`, `_recover_snapshot_then_events`, `_recover_best_effort` ... (+6 more)

---

### `checkpoint.snapshot`

快照管理 - Snapshot Manager

提供状态快照的创建、存储和恢复功能

**类:** `SnapshotType`, `Snapshot`, `SnapshotManager`

**函数:** `to_dict`, `from_dict`, `verify`, `_calculate_checksum`, `__init__`, `create_snapshot`, `get_snapshot`, `get_latest_snapshot`, `get_all_snapshots`, `restore_snapshot` ... (+12 more)

---

### `context_compaction.compressor`

上下文压缩器 - Context Compressor

负责对上下文进行实际压缩操作

**类:** `CompressionLevel`, `CompressionResult`, `Compressor`

**函数:** `to_dict`, `__init__`, `compress`, `_categorize_messages`, `_compress_light`, `_compress_medium`, `_compress_aggressive`, `_compress_adaptive`, `_merge_consecutive_messages`, `_preserve_recent_messages` ... (+5 more)

---

### `context_compaction.manager`

上下文管理器 - Context Manager

管理对话上下文的生命周期，包括自动压缩和清理

**类:** `ContextState`, `ContextConfig`, `ContextStats`, `ContextManager`

**函数:** `to_dict`, `__init__`, `add_message`, `add_messages`, `get_messages`, `get_recent_messages`, `clear`, `compress`, `get_stats`, `get_summary` ... (+11 more)

---

### `context_compaction.summarizer`

摘要提取器 - Message Summarizer

从对话历史中提取关键信息，生成简洁的摘要

**类:** `SummarizerStrategy`, `MessageSummary`, `Summarizer`

**函数:** `__init__`, `to_dict`, `from_dict`, `__init__`, `summarize`, `_truncate_summarize`, `_extract_key_points`, `_abstractive_summarize`, `_hybrid_summarize`, `_messages_to_text` ... (+4 more)

---

### `htl.approval_flow`

审批流程 - Approval Flow

管理审批请求的创建、流转和结果处理

**类:** `ApprovalStatus`, `ApprovalPriority`, `ApprovalRequest`, `ApprovalResult`, `ApprovalFlow`

**函数:** `to_dict`, `from_dict`, `is_pending`, `is_completed`, `is_expired`, `to_dict`, `__init__`, `create_request`, `approve`, `reject` ... (+12 more)

---

### `htl.handler`

HiTL 处理器 - HTL Handler

整合审批流程和策略，提供完整的人工审批功能

**类:** `HTLOperationMode`, `HTLConfig`, `HTLOperation`, `HTLHandler`

**函数:** `__init__`, `register_operation_handler`, `register_callback`, `process`, `_process_sync`, `_process_async`, `handle_approval_result`, `_execute_operation`, `_complete_operation`, `check_pending_operations` ... (+6 more)

---

### `htl.policy`

审批策略 - Approval Policy

定义和管理审批策略，包括敏感操作识别和风险评估

**类:** `RiskLevel`, `OperationCategory`, `ApprovalRule`, `RiskAssessment`, `ApprovalPolicy`, `PolicyEngine`

**函数:** `matches`, `to_dict`, `__init__`, `_initialize_default_rules`, `add_rule`, `remove_rule`, `get_rule`, `get_matching_rules`, `get_rules_by_category`, `set_default_risk_level` ... (+10 more)

---

### `runtime`

Runtime 层统一入口 - Runtime Core

整合 Context Manager、Checkpoint Manager、HTL Manager 和 Session Manager
提供完整的 Runtime 功能支持

**类:** `RuntimeConfig`, `Runtime`

**函数:** `__init__`, `_init_context_manager`, `_init_checkpoint_manager`, `_init_htl_manager`, `_init_session_manager`, `add_message`, `get_context`, `compress_context`, `get_context_stats`, `save_checkpoint` ... (+17 more)

---

### `security.encryption`

加密工具模块

提供 AES、RSA 和混合加密实现

**类:** `EncryptionType`, `EncryptedData`, `AESEncryptor`, `RSAEncryptor`, `HybridEncryptor`, `EncryptionManager`

**函数:** `is_valid`, `to_dict`, `from_dict`, `to_base64`, `from_base64`, `__init__`, `encrypt`, `_encrypt_gcm`, `_encrypt_cbc`, `decrypt` ... (+24 more)

---

### `security.key_manager`

密钥管理模块

提供密钥的生成、存储、轮换和生命周期管理

**类:** `KeyType`, `KeyStatus`, `KeyInfo`, `KeyRotationPolicy`, `KeyManager`

**函数:** `is_valid`, `is_expired`, `age_days`, `to_dict`, `from_dict`, `should_rotate`, `should_alert`, `__init__`, `generate_key`, `_compute_fingerprint` ... (+25 more)

---

### `security.secure_storage`

安全存储模块

提供加密数据的安全存储接口

**类:** `StorageBackend`, `StorageConfig`, `SecureStorage`, `VaultBackend`

**函数:** `__init__`, `_setup_encryption`, `store`, `_save`, `_save_to_file`, `_save_encrypted_file`, `retrieve`, `_load`, `_load_from_file`, `_load_encrypted_file` ... (+28 more)

---

### `session.session`

会话状态机 - Session State Machine

管理会话生命周期和状态转换

**类:** `SessionState`, `SessionEvent`, `StateTransition`, `Session`, `SessionManager`

**函数:** `__init__`, `created_at`, `updated_at`, `last_activity_at`, `is_active`, `is_terminal`, `send_event`, `start`, `resume`, `pause` ... (+27 more)

---

### `tests.test_checkpoint`

Checkpoint 单元测试

**类:** `TestEventStore`, `TestSnapshotManager`

**函数:** `setup_method`, `teardown_method`, `test_store_initialization`, `setup_method`, `teardown_method`, `test_manager_initialization`

---

### `tests.test_context_compaction`

Context Compaction 单元测试

**类:** `TestContextManager`

**函数:** `setup_method`, `test_add_message`, `test_get_messages`, `test_compression_stats`, `test_clear`

---

### `tests.test_htl`

HiTL 单元测试

**类:** `TestApprovalPolicy`

**函数:** `setup_method`, `test_policy_initialization`, `test_risk_thresholds`

---

### `tests.test_runtime`

Runtime层测试

**类:** `TestRuntime`

**函数:** `test_event_store_creation`, `test_snapshot_manager`, `test_context_manager`, `test_htl_handler`, `test_session_creation`

---

### `tests.test_session`

Session 单元测试

**类:** `TestSession`

**函数:** `setup_method`, `test_initial_state`, `test_start_session`, `test_pause_resume`, `test_complete_session`, `test_terminate_session`, `test_is_active`

---

