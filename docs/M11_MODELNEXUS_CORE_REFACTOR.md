# M11: ModelNexus 提升为 L0 核心服务层 — 架构重构方案

**日期**: 2026-05-24
**状态**: 设计中
**严重程度**: 🔴 架构级别

---

## 一、问题诊断

### 1.1 双重建设

L0 层存在两套并行的 LLM 基础设施，各自独立开发、功能高度重叠：

| 能力域 | ModelNexus（已建成,未用） | LLMInfra（重复建设,在用） | 重复度 |
|--------|--------------------------|--------------------------|:---:|
| 语义缓存 | `SemanticCache` + `TieredCache` | `CacheManager` + `SemanticCacheLayer` | 90% |
| 分层路由 | `TierRouter` + `ABTestFramework` | `IntentRouter` + `ProviderChain` | 80% |
| 熔断保护 | `CircuitBreaker` | `CircuitBreaker` | 100% |
| 限流控制 | `RateLimiter` | `TokenBucketRateLimiter` | 85% |
| 成本管理 | `CostManager` + `route_with_budget()` | 无对应 | 0% |
| 可观测性 | `PrometheusExporter` + `SLOTracker` + `AlertManager` | `MetricsCollector`(简化版) | 40% |
| 服务降级 | `DegradationManager` + `FallbackChain` | 无对应 | 0% |
| 请求批处理 | `RequestBatcher` | 无对应 | 0% |
| 模型配置 | `ConfigManager` + `models.yaml` | `ProviderConfig`(简化) | 30% |
| 安全防护 | `PromptGuard` + `DataMasking` + `ContentModeration` | `ResponseValidator`(简化) | 20% |

### 1.2 Provider 定位错误

```
当前（错误）:  ModelNexusProvider = 一个可选的 Provider（与 OpenAI/Mock 平级）
正确:          ModelNexusCore = LLM 调用的唯一入口，Provider 只是其下游适配器
```

### 1.3 调用链断裂

```
当前调用链:
  zena → ZenAgent → LLMClient → OpenAIProvider ──→ DeepSeek API
                        (绕过所有 ModelNexus 能力)

ModelNexus Gateway 未被调用:
  - SemanticCache: 缓存命中率 >0% vs 当前 ~10%
  - TierRouter:   成本感知路由 vs 当前固定单 provider
  - ABTestFramework: 模型灰度 vs 无
  - DegradationManager: 优雅降级 vs 无
```

---

## 二、目标架构

### 2.1 新 L0 层次结构

```
                     ┌──────────────────────┐
                     │   ZenAgent / zena     │  ← L2 调用方不变
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │    LLMClient          │  ← 接口不变
                     └──────────┬───────────┘
                                │
              ┌─────────────────┴─────────────────┐
              │     ModelNexusCore (内嵌)          │  ← NEW: L0 真正核心
              │                                    │
              │  ┌──────────────────────────────┐ │
              │  │ CacheLayer (L1+L2)            │ │
              │  │ TierRouter + ABTestFramework  │ │
              │  │ CircuitBreaker (per-provider) │ │
              │  │ RateLimiter                   │ │
              │  │ CostManager                   │ │
              │  │ DegradationManager            │ │
              │  │ SecurityPipeline              │ │
              │  │ Observability                 │ │
              │  └──────────────────────────────┘ │
              │                                    │
              │           ┌────────────────────┐   │
              │           │ ProviderAdapter    │   │
              │           │ (精简为纯适配器)    │   │
              │           └────────┬───────────┘   │
              └────────────────────┼───────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              OpenAICompat    Anthropic      Mock
              (DeepSeek/MIMO  (DeepSeek/Volc (测试用)
               /OpenAI/Qwen)   /Claude)
```

### 2.2 Provider 降级为纯适配器

Provider 不再承担路由、缓存、熔断、限流等职责，退化为纯粹的协议适配器：

```python
class ProviderAdapter(ABC):
    """Provider 纯协议适配器 — 不包含任何业务逻辑"""
    @abstractmethod
    async def chat(self, request: ChatRequest) -> LLMResponse: ...
    @abstractmethod
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]: ...
```

---

## 三、组件合并清单

| ModelNexus 模块 | 替换的 LLMInfra 模块 | 保留/废弃 |
|----------------|---------------------|-----------|
| `SemanticCache` | `cache.py` (CacheManager) | 废弃，ModelNexus 替代 |
| `TieredCache` | `semantic_cache_layer.py` | 废弃 |
| `TierRouter` | `intent_router.py` (IntentRouter) | 合并，TierRouter 吸收 IntentRouter |
| `ABTestFramework` | 无 | 保留，提升到核心层 |
| `CircuitBreaker` | `circuit_breaker.py` | 保留 ModelNexus 版，删除重复 |
| `RateLimiter` | `flow_control/rate_limiter.py` | 保留 ModelNexus 版 |
| `CostManager` | 无 | 保留 |
| `DegradationManager` | 无 | 保留 |
| `PromptGuard` | `response_validator.py` | 合并，留 ModelNexus 版 |
| `DataMasking` | 无 | 保留 |
| `PrometheusExporter` | `tracing/metrics.py` | 保留 ModelNexus 版 |
| `ConfigManager` | `config.py` (Settings/ProviderConfig) | 合并 |
| `ProviderAdapter` | `providers/` 目录 | 精简为纯协议适配器 |
| — | `provider_chain.py` | 废弃（TierRouter 替代） |
| — | `adaptive_load_balancer.py` | 废弃（TierRouter 替代） |
| — | `mixture_of_agents.py` | 独立保留，L4 能力 |
| — | `quality_pipeline.py` | 独立保留，L2 能力 |

---

## 四、新 API

```python
class ModelNexusCore:
    """L0 LLM 基础设施核心 — 调用的唯一入口"""

    def __init__(self, config: ModelNexusConfig):
        self.cache = SemanticCache(...)          # L1+L2 缓存
        self.router = TierRouter(...)            # 分层路由 + A/B
        self.breaker = CircuitBreaker(...)        # 熔断保护
        self.limiter = RateLimiter(...)           # 限流控制
        self.cost = CostManager(...)              # 成本管理
        self.degrader = DegradationManager(...)   # 服务降级
        self.security = SecurityPipeline(...)      # 安全防护
        self.observability = Observability(...)    # 可观测性
        self.providers: dict[str, ProviderAdapter] = {}  # 纯适配器

    async def chat(self, request: ChatRequest) -> LLMResponse:
        """唯一入口 — 所有 LLM 调用经过此方法"""
        with self.observability.span("llm.chat"):
            # 1. 安全检查
            self.security.check(request)
            # 2. 缓存查询 (L1 精确 → L2 语义)
            cached = await self.cache.get(request)
            if cached: return cached
            # 3. 限流检查
            await self.limiter.acquire()
            # 4. 路由选择 (成本 + 灰度 + 熔断)
            provider_name, model = self.router.route(request)
            # 5. 熔断保护
            async with self.breaker.protect(provider_name):
                response = await self.providers[provider_name].chat(request)
            # 6. 质量校验
            self.security.validate(response)
            # 7. 写入缓存
            await self.cache.set(request, response)
            # 8. 成本记录
            self.cost.record(response)
            return response
```

---

## 五、Provider 精简

```python
# 删除 LLMInfra/providers/ 中的业务逻辑
# 每个 Provider 仅保留: chat() + chat_stream() + 协议转换

class OpenAICompatibleAdapter(ProviderAdapter):
    """OpenAI 兼容协议适配器 (DeepSeek/MIMO/Qwen/OpenAI...)"""
    def __init__(self, name, base_url, api_key, model):
        self._name = name
        self._url = f"{base_url}/chat/completions"
        self._key = api_key
        self._model = model

    async def chat(self, request: ChatRequest) -> LLMResponse:
        payload = self._to_openai_format(request)
        async with aiohttp.post(self._url, json=payload, headers=...) as resp:
            return self._from_openai_format(await resp.json())
```

---

## 六、迁移阶段

| 阶段 | 内容 | 风险 | 预估 |
|------|------|------|------|
| **Phase 1** | 提取 ModelNexusCore 类 + 内嵌启动 | 低 — 新代码 | 2d |
| **Phase 2** | LLMClient 改为调用 ModelNexusCore | 中 — 接口适配 | 1d |
| **Phase 3** | 删除 LLMInfra 中重复模块 | 中 — 需验证无遗漏 | 1d |
| **Phase 4** | 精简 Provider 为纯适配器 | 低 — 仅删除 | 0.5d |
| **Phase 5** | CLI/TUI 验证 + 全量回归 | 低 — 验证 | 0.5d |
| | **合计** | | **5d** |

---

## 七、影响分析

| 组件 | 影响 | 处理 |
|------|------|------|
| `LLMClient` | API 不变，内部调用链改为 ModelNexusCore | 透明迁移 |
| `ZenaDataAdapter` | 不再需要手动注入 env var | 删除 `_detect_available_provider()` |
| `ProviderFactory` | 改为注册 ProviderAdapter | 简化为 dict |
| `ProviderChain` | 废弃 | 由 TierRouter 替代 |
| `./zena chat` | 自动获得缓存/路由/A/B/降级等所有能力 | 无感升级 |

---

## 八、验证

```bash
# Phase 完成后逐阶段验证
./zena chat "Hello"            # 确保调用链正常
./zena status                  # 确认 modelnexus 核心状态
pytest packages/LLMInfra/tests/ -q
```
