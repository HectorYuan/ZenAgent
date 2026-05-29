# M11: ModelNexus 提升为 L0 核心服务层 — 架构重构方案

**日期**: 2026-05-24
**版本**: v2.0（6 轮专家评审 · 16 项优化全部采纳）
**严重程度**: 🔴 架构级别

---

## 一、问题诊断

### 1.1 双重建设

L0 层存在两套并行的 LLM 基础设施，功能高度重叠：

| 能力域 | ModelNexus（已建成,未用） | LLMInfra（重复建设,在用） | 重复度 |
|--------|--------------------------|--------------------------|:---:|
| 语义缓存 | `SemanticCache` + `TieredCache` | `CacheManager` + `SemanticCacheLayer` | 90% |
| 分层路由 | `TierRouter` + `ABTestFramework` | `IntentRouter` + `ProviderChain` | 80% |
| 熔断保护 | `CircuitBreaker` | `CircuitBreaker` | 100% |
| 限流控制 | `RateLimiter` | `TokenBucketRateLimiter` | 85% |
| 成本管理 | `CostManager` + `route_with_budget()` | 无对应 | — |
| 可观测性 | `PrometheusExporter` + `SLOTracker` + `AlertManager` | `MetricsCollector`(简化版) | 40% |
| 服务降级 | `DegradationManager` + `FallbackChain` | 无对应 | — |
| 请求批处理 | `RequestBatcher` | 无对应 | — |
| 模型配置 | `ConfigManager` + `models.yaml` | `ProviderConfig`(简化) | 30% |
| 安全防护 | `PromptGuard` + `DataMasking` | `ResponseValidator`(简化) | 20% |

### 1.2 Provider 定位错误

```
❌ ModelNexusProvider = 一个可选的 Provider（与 OpenAI/Mock 平级）
✅ ModelNexusCore    = LLM 调用的唯一入口，Provider 只是下游协议适配器
```

### 1.3 调用链断裂

```
当前: zena → LLMClient → OpenAIProvider ──→ DeepSeek API （绕过全部 ModelNexus）
目标: zena → LLMClient → ModelNexusCore ──→ ProviderAdapter ──→ DeepSeek API
                              │
                              ├─ Cache (L1+L2+L3)
                              ├─ Security (前置检查+后置脱敏)
                              ├─ Route (成本+灰度+熔断)
                              ├─ Observe (Prometheus+SLO+Alert)
                              └─ Degrade (优雅降级)
```

---

## 二、目标架构（6 轮评审整合）

### 2.1 Pipeline 模式（架构专家 #1）

```
                      ┌──────────────────────┐
                      │   ZenAgent / zena     │
                      └──────────┬───────────┘
                                 │
                      ┌──────────▼───────────┐
                      │    LLMClient (不变)   │
                      └──────────┬───────────┘
                                 │
              ┌──────────────────▼──────────────────┐
              │        ModelNexusCore               │
              │                                     │
              │  Pipeline (可插拔管线)              │
              │  ┌─────────────────────────────────┐│
              │  │ SecurityStage (前置检查)        ││  ← 安全专家 #1
              │  │ [CacheRead ‖ RateLimit] (并行)  ││  ← 性能专家 #2
              │  │ RouteStage (TierRouter+AB)      ││  ← 运维专家 #3
              │  │ CircuitBreakStage               ││
              │  │ ProviderStage (纯适配器调用)    ││
              │  │ SecurityStage (后置脱敏)        ││  ← 安全专家 #2
              │  │ QualityStage (校验)             ││
              │  │ [CacheWrite ‖ Cost ‖ Observe]   ││  ← 性能专家 #2
              │  │ AuditStage (审计日志)           ││  ← 安全专家 #3
              │  └─────────────────────────────────┘│
              │                                     │
              │  Components                         │
              │  ┌─────────────────────────────────┐│
              │  │ TieredCache (L1+L2+L3)          ││  ← 性能专家 #1
              │  │ ConfigManager (models.yaml)      ││  ← 架构专家 #3
              │  │ ProviderPool (连接池预热)       ││  ← 性能专家 #3
              │  │ HealthChecker (/health 端点)    ││  ← 运维专家 #2
              │  │ PluginRegistry (自定义 Stage)   ││  ← 扩展专家 #1
              │  └─────────────────────────────────┘│
              └────────────────────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              OpenAICompat  Anthropic    Mock
              (DeepSeek    (DeepSeek    (测试用)
               MIMO Qwen)   Volc Claude)
```

### 2.2 PipelineStage 接口

```python
class PipelineStage(ABC):
    """管线阶段 — 可插拔，可排序"""
    name: str
    priority: int  # 越小越靠前

    @abstractmethod
    async def process(self, ctx: PipelineContext) -> PipelineContext: ...

    @property
    def can_parallel_with(self) -> set[str]:
        """可与哪些阶段并行执行"""
        return set()
```

### 2.3 三级缓存（性能专家 #1）

| 层级 | 存储 | 命中率 | 延迟 | 失效策略 |
|------|------|--------|------|----------|
| L1 精确 | 内存 hash (RingBuffer) | 10-15% | <0.1ms | TTL + FIFO |
| L2 语义 | HNSW 向量索引 | 30-40% | <5ms | 余弦 >0.92 + TTL |
| L3 版本 | Redis key:model_version | 5-10% | ~1ms | 模型版本变更 |

### 2.4 管线并行化（性能专家 #2）

```
Security ──→ [CacheRead ‖ RateLimit] ──→ Route ──→ CircuitBreak ──→ Provider
                                                                        │
              [CacheWrite ‖ CostRecord ‖ Observe] ←── Quality ←── SecurityPost ←─┘
```

---

## 三、核心 API

```python
class ModelNexusCore:
    def __init__(self, config_path: str = "models.yaml"):
        self.config = ConfigManager(config_path)         # 唯一配置源
        self.cache = TieredCache(...)                    # L1+L2+L3
        self.router = TierRouter(...)                    # 分层路由 + A/B
        self.breaker = CircuitBreaker(...)                # 熔断
        self.limiter = RateLimiter(...)                   # 限流
        self.cost = CostManager(...)                      # 成本
        self.degrader = DegradationManager(...)           # 降级
        self.security = SecurityPipeline(...)             # 安全（前置+后置）
        self.observability = Observability(...)           # Prometheus+SLO+Alert
        self.health = HealthChecker(...)                  # /health 端点
        self.audit = AuditLogger(...)                     # 审计日志
        self.providers: dict[str, ProviderAdapter] = {}   # 运行时注册
        self._pipeline: list[PipelineStage] = []          # 可插拔管线
        self._pool = ProviderPool(...)                    # 连接池预热

    def register_provider(self, name: str, adapter: ProviderAdapter):
        """运行时注册 Provider（架构专家 #2）"""

    def register_stage(self, stage: PipelineStage):
        """注册自定义管线阶段（扩展专家 #1）"""

    def get_stats(self) -> dict:
        """供给 SoulTeam L5 集群监控（扩展专家 #2）"""
        return {
            "providers": {n: p.stats for n, p in self.providers.items()},
            "cache": self.cache.stats,
            "router": self.router.get_stats(),
            "ab_tests": self.router.get_ab_status(),
            "cost": self.cost.summary(),
            "health": self.health.check_all(),
        }
```

---

## 四、组件合并清单（更新版）

| ModelNexus 模块 | 替换 LLMInfra | 新能力 |
|----------------|-------------|--------|
| `TieredCache` | `cache.py` + `semantic_cache_layer.py` | L3 模型版本缓存 |
| `TierRouter` | `intent_router.py` + `provider_chain.py` + `adaptive_load_balancer.py` | 成本路由 + A/B |
| `CircuitBreaker` | `circuit_breaker.py` | 同（去重） |
| `RateLimiter` | `flow_control/rate_limiter.py` | 同（去重） |
| `CostManager` | 无 | **新增** |
| `DegradationManager` | 无 | **新增** |
| `SecurityPipeline` | `response_validator.py` | 前置注入检测 + 后置脱敏 |
| `Observability` | `tracing/metrics.py` | SLO + Alert **新增** |
| `ConfigManager` | `config.py` (Settings) | models.yaml 驱动 |
| `ProviderAdapter` | `providers/` | 精简为纯协议层 |
| `AuditLogger` | 无 | **新增** |
| `HealthChecker` | 无 | **新增** |
| `PluginRegistry` | 无 | **新增** |

**保留不动**: `mixture_of_agents.py` (L4), `quality_pipeline.py` (L2), `token_budget.py` (L2)

---

## 五、迁移策略（渐进式废弃 · 迁移专家 #1）

```python
class LLMClient:
    def __init__(self, settings=None, use_modelnexus_core: bool = None):
        # Phase 1: feature flag, 默认 False
        # Phase 2: 默认 True, 旧代码 deprecated
        # Phase 3: 删除旧代码
        if use_modelnexus_core is None:
            use_modelnexus_core = os.getenv("MODELNEXUS_CORE", "0") == "1"
        ...
```

| 阶段 | 内容 | 风险 | 预估 |
|------|------|------|------|
| **Phase 1** | ModelNexusCore 实现 + feature flag 并存 | 低 | 2d |
| **Phase 2** | 默认 Core, 旧代码 deprecated, 全量回归 | 中 | 1d |
| **Phase 3** | 删除重复模块, Provider 精简, CLI/TUI 验证 | 中 | 1d |
| **Phase 4** | 插件系统 + SoulTeam 集成 + A/B CLI 参数 | 低 | 1d |
| | **合计** | | **5d** |

---

## 六、Provider 精简（纯协议适配器）

```python
class ProviderAdapter(ABC):
    """纯协议适配器 — 不包含业务逻辑"""
    name: str
    models: list[str]

    @abstractmethod
    async def chat(self, request: ChatRequest) -> LLMResponse: ...
    @abstractmethod
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]: ...

class OpenAICompatibleAdapter(ProviderAdapter):
    """支持: DeepSeek/MIMO/Qwen/OpenAI/GitHub Models..."""
```

---

## 七、CLI/TUI 增强（扩展专家 #3）

```bash
./zena chat "Hello"
# 每次调用自动经过 ModelNexusCore 管线

./zena chat "Hello" --ab-group B
# A/B 实验分组

./zena status
# 新增显示: 缓存命中率 / Provider 健康 / A/B 状态 / SLO
# L0 ModelNexusCore  │ cache:67.3% route:fast A/B:group-A slo:99.8%

./zena tui  # Infra 屏幕 (按5) 显示管线实时状态
```

---

## 八、验证

```bash
# 每阶段完成后验证
MODELNEXUS_CORE=1 ./zena chat "Hello"          # Phase 1: feature flag
./zena status | grep -A5 "ModelNexusCore"       # Phase 2: 默认启用
pytest packages/LLMInfra/tests/ packages/modelnexus/tests/ -q   # 全量回归
```

---

## 九、实施记录 (v3.0)

**日期**: 2026-05-26
**状态**: Phase 2+3 完成，ModelNexusCore 已成为唯一路径

### 9.1 已完成的变更

| 变更 | 说明 |
|------|------|
| 删除 `MODELNEXUS_CORE` 特性开关 | `LLMClient.chat()` 无条件走 `_core.chat()`，legacy ~60 行代码已删除 |
| 集中化配置 | `providers.yaml` + `modelnexus_core_config.py` 作为单一起源 |
| SecureKeyManager 扩展 | 新增 6 个 key definitions (deepseek/mimo/anthropic/volc/zhipu/ernie) |
| FileKeyProvider | 开发环境从 `config/secret_keys.yaml` 读取密钥（Vault → File → EnvVar 降级链）|
| TokenBudgetStage | 管线新增 priority=20 token budget 阶段（截断 + 意图分配）|
| Adapter 简化 | 删除 `_detect_*()` ~80 行 + `_env_lock`副作用注入 |
| Settings 委托 | `_load_providers_from_env()` → `_load_providers_from_core_config()` |
| neo_model.yaml | 移除硬编码 api_key，替换为 `secure_key_name` 引用 |

### 9.2 当前架构

```
zena CLI / TUI → ZenaDataAdapter
                    │
                    ▼
              ZenAgentConfig
                    │
                    ▼
              LLMClient ──(唯一路径)──→ ModelNexusCore
                                           │
              ┌────────────────────────────┤
              │  9-Stage Pipeline          │
              │  Security → CacheRead     │
              │  → TokenBudget → RateLimit │
              │  → Route → Provider       │
              │  → Quality → CacheWrite   │
              │  → Observe                │
              └────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   OpenAICompat  Anthropic   Mock
   (DeepSeek    (DeepSeek
    MiMo Qwen)   Volc)

配置来源:
  providers.yaml     → Provider 元数据（base_url, model, key 映射）
  secret_keys.yaml   → API Key（开发环境, gitignored）
  Vault              → API Key（生产环境）
  SecureKeyManager   → 统一密钥获取（Vault → File → EnvVar）
```

### 9.3 密钥管理

```
SecureKeyManager.get_key("deepseek_api_key")
  → Vault (生产): secret/neo_model/llm/deepseek_api_key
  → File (开发): config/secret_keys.yaml
  → EnvVar (降级): DEEPSEEK_ANTHROPIC_AUTH_TOKEN
```

### 9.4 验证结果

```bash
pytest packages/LLMInfra/tests/ packages/ZenAgent/tests/ \
      packages/Runtime/tests/ packages/MetaSoul/tests/ -q
# 415 passed, 0 failures

python3 tests/e2e/test_real_e2e.py --scene 1
# ✓ 4/4 steps passed (real DeepSeek v4 Pro LLM call)
```
