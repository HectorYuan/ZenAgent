# ZenAgent 技术债全景报告

**日期**: 2026-05-23
**扫描方法**: 双 Agent 并行 (TODO/占位/测试覆盖 + 代码质量/安全/结构)

---

## 🔴 CRITICAL (2)

| # | 文件:行 | 问题 |
|---|---------|------|
| 1 | `modelnexus/services/lmservice/config.py:130` | **硬编码 API Key**: Volcengine `ark-6e42...-cce8c` 已在 git 中暴露 |
| 2 | `packages/ZenAgent/core.py:446` | **logger 未定义**: `logger.warning()` 调用但无 `import logging`，运行时 NameError |

---

## 🟡 HIGH (9)

| # | 文件 | 问题 |
|---|------|------|
| 1-3 | `modelnexus/main.py`, `main_v3.py`, `config/settings.py` | **CORS 通配符** `allow_origins=["*"]` |
| 4 | `modelnexus/api/v1/tier_router.py:135` | **Pydantic v1 API**: `.dict()` → `.model_dump()` |
| 5 | `packages/SwarmFly/__init__.py:92-93` | **TrendConvolv/EmergentDetector 未导入**, SwarmFlyCore 构造时 NameError |
| 6 | `packages/SwarmFly/__init__.py:63-68` | **pass + 死 docstring**, SwarmFlyCore 重复初始化父类组件 |
| 7 | `modelnexus/services/lmservice/core.py` | **22+ 处 DEBUG print** 残留，每次 import 污染 stdout |
| 8 | `modelnexus/services/lmservice/health_checker.py:163` | **`.model_dump()` 用在 dataclass 上** (非 Pydantic), AttributeError |
| 9 | `modelnexus/core/context_aware_router.py:267` | ContextAwareRouter 使用占位成功率，非真实监控数据 |

---

## 🟠 MEDIUM (14)

### 运行时问题

| # | 文件 | 问题 |
|---|------|------|
| 1 | `LLMInfra/core.py:397-408` | `chat_rag()` / `chat_tool()` 两个路径为 stub (raise RuntimeError) |
| 2 | `LLMInfra/retry.py:190` | aiohttp 检测 `globals()` 逻辑永远为 False，回退到裸 `Exception` |
| 3 | `SwarmFly/zenloop_client.py:167-302` | 3 个方法只有 mock_mode，真实 API 调用 `NotImplementedError` |
| 4-8 | 5 个文件含 `sys.path.insert(0, ...)` | zenloop_client, handoff_bridge, summarizer, htl_handler, main_v3 |
| 9 | `modelnexus/main.py:131,158` | `from System.core.discovery...` 导入不存在的外部包，死代码 |
| 10 | `Runtime/runtime.py:59` | `from packages.SwarmFly` 依赖 sys.path 配置，SwarmFly 集成常静默失效 |

### 测试覆盖缺口 (>30 模块无测试)

| 层 | 无测试模块 |
|----|-----------|
| L0 | `config.py`, `exceptions.py`, `modelnexus_adapter.py`, `precache.py`, `providers/*` (5个) |
| L1 | `security/*` (encryption, key_manager, secure_storage) |
| L2 | `fly1mission`, `fly3trends`, `fly4skills`, `fly5tools`, `handoff_bridge`, `zenloop_client`, `management/*` |
| L3 | `ZenAgent/core.py`, `collaboration/*`, `mcp/*`, `zena/*` |
| L4 | MetaSoul: `reflection/*`, `memory/store/index/forgetting/semantic_kb/knowledge_extractor/consolidation/archival_manager`; modelnexus: `security/*`, `events/*`, `injectors/*` |

### 代码结构

| # | 文件 | 问题 |
|---|------|------|
| 11 | `MetaSoul/tests/__init__.py:5-8` | `import *` 通配符 |
| 12 | `ZenAgent/tests/`, `config/guardrails/` | 缺少 `__init__.py` |
| 13 | `SwarmFly/memory/lock_manager.py` | `time.sleep()` 在 sync 代码中阻塞 async 调用 |
| 14 | `zena/core/adapter.py:47-79` | 运行时 `os.environ` 修改，非线程安全 |

---

## 🔵 LOW (11)

| # | 问题 |
|---|------|
| 1 | `pyproject.toml` 无上界版本、缺 `aiohttp`/`pyjwt`/`textual` 显式依赖、无 mypy/ruff |
| 2 | `LLMInfra/cache.py` CacheBackend 未继承 ABC/@abstractmethod |
| 3 | `Runtime/context_compaction/summarizer.py` 仅支持中文关键词提取 |
| 4 | `SwarmFly/执行记录生成.py` 硬编码路径的开发脚本残留 |
| 5 | `SwarmFly/fly2rules/Tests/test_integration.py` 测试收集错误 |
| 6 | `modelnexus/observability/prometheus_exporter.py` 等 3 文件含 `raise NotImplementedError` stub |
| 7 | 全项目 0 处 `from __future__ import annotations` — 增加循环导入风险 |
| 8 | modelnexus 30+ 文件含 "Phase X" 标记，迭代痕迹未清理 |
| 9 | 5 个空 `__init__.py` (ZenAgent, MetaSoul, widgets, screens, packages) |
| 10 | `tests/e2e/test_real_llm.py` 6 个 skipif (预期行为, 需 API key) |
| 11 | `LLMInfra/providers/openai_provider.py:51` Pydantic v2 弃用警告 |

---

## 📊 统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 2 |
| HIGH | 9 |
| MEDIUM | 14 |
| LOW | 11 |
| **合计** | **36** |

| 层 | HIGH+CRIT |
|----|-----------|
| L0 LLMInfra | 0 |
| L1 Runtime | 0 |
| L2 SwarmFly | 2 |
| L3 ZenAgent | 1 |
| L4 modelnexus | 8 |

---

## 建议修复优先级

1. **立即**: 移除硬编码 API Key + 修复 logger NameError
2. **本周**: CORS 配置 + Pydantic `.dict()` + SwarmFlyCore 导入修复 + lmservice print 清理
3. **本月**: 补充 security/providers/zena CLI 测试覆盖
4. **M9**: 拆分大文件, 清理延迟导入, 补充 pyproject.toml, 清理 Phase 标记
