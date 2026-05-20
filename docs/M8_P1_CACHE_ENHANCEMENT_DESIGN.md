# M8 P1: 精确匹配缓存增强 + 热点预缓存 设计方案

**日期**: 2026-05-20
**状态**: 设计中
**版本**: v2.0（已整合三轮专家评审优化）
**设计依据**: [E2E_OPTIMIZATION_DESIGN §模块3](../E2E_OPTIMIZATION_DESIGN.md)

---

## 一、方案定位

在现有 `CacheManager` + `MemoryCache` 基础上，增加**热点识别、异步预缓存、智能淘汰**三层增强，最终合并到 `packages/LLMInfra/cache.py`。

**核心目标**：缓存命中率从 <10% 提升至 20-30%，为后续语义缓存 (L2/HNSW) 预留扩展接口。

---

## 二、核心架构

```
                    ┌─────────────────────────────┐
                    │       CacheManager           │
                    │  (精简后的统一入口)           │
                    └──────────┬──────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  HotspotTracker │ │  PreCacheWorker │ │  CacheBackend   │
│  热点识别引擎   │ │  异步预缓存器   │ │  缓存后端        │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                  │                    │
         │  ┌───────────────┼────────────────────┤
         │  │               │                    │
         │  │    ┌──────────┴──────────┐         │
         ▼  ▼    ▼                     ▼         ▼
   ┌──────────────┐  ┌──────────────────────┐  ┌──────────┐
   │ RingBuffer   │  │ EvictionManager      │  │ Redis    │
   │ 环形缓冲区   │  │ 热度加权淘汰管理器   │  │ Memory   │
   └──────────────┘  └──────────────────────┘  └──────────┘
```

---

## 三、核心组件设计

### 3.1 HotspotTracker — 热点识别引擎

**问题**：原方案维护两套独立时间窗口（5min + 30min），存储冗余。

**优化方案（性能专家建议 #1）**：使用**单一环形缓冲区**存储所有命中时间戳，两个窗口共享同一份原始数据。

```python
class RingBuffer:
    """环形缓冲区 — 共享原始命中数据"""
    capacity: int = 10000           # 最大记录数
    _buffer: list[tuple[float, str]]  # [(timestamp, cache_key)]
    _cursor: int = 0                 # 写入游标

    def record(self, key: str):
        """记录一次命中，自动淘汰最旧记录"""

    def count_range(self, since: float) -> int:
        """统计指定时间范围内的命中次数"""

    def stats_range(self, since: float) -> tuple[float, float]:
        """计算指定范围内的均值和标准差"""
```

```python
class HotspotTracker:
    """热点识别引擎"""
    _ring: RingBuffer
    SHORT_WINDOW = 300      # 快速触发窗口 (5min)
    LONG_WINDOW = 1800      # 统计确认窗口 (30min)
    QUICK_THRESHOLD = 3     # 快速触发阈值
    SIGMA_MULTIPLIER = 2.0  # 自适应异常检测倍数
    SYNC_INTERVAL = 30      # 全局计数器同步间隔 (秒)

    class HotLevel(Enum):
        HOT = "hot"      # 持续高频，预缓存 + 延长 TTL
        WARM = "warm"    # 降低热度，仅 L1 缓存
        COLD = "cold"    # 低频查询，正常逻辑

    def record_hit(self, key: str) -> HotLevel:
        """记录命中并返回当前热度等级"""

    def get_hot_keys(self) -> list[str]:
        """获取当前所有 HOT 级别的缓存键"""

    async def _push_to_global(self):
        """异步推送本地计数到全局 Redis (每 SYNC_INTERVAL 秒)"""
```

**热度状态机**：

```
    COLD ────(短窗口 ≥3 次命中)────→ HOT
    HOT ─────(30min 后)────────────→ 检查长窗口统计
                                       │
                        ┌──────────────┼──────────────┐
                        ↓              ↓              ↓
                     频率 ≥ μ+2σ   频率 < μ       μ ≤ 频率 < μ+2σ
                        ↓              ↓              ↓
                       保持 HOT      降级 COLD      降级 WARM

    WARM ────(短窗口再触发)────────→ HOT
    WARM ────(持续 15min 不触发)───→ COLD
```

**关键点**：降级路径保证了资源不会无限占用——HOT 条目的 TTL 延长是有检查周期的，热度冷却后自动恢复标准 TTL。

### 3.2 PreCacheWorker — 异步预缓存器

**工作流程**：

```
热点检测到 HOT
    │
    ▼
┌─────────────────┐
│ 预缓存任务队列   │ ← asyncio.Queue (容量 20)
│ (key, priority) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 异步 Worker      │ → 从队列取任务
│ (后台协程)       │ → 调用 LLM 预计算
└────────┬────────┘ → 结果写入缓存
         │            → 记录预缓存指标
         ▼
┌─────────────────┐
│ 结果写入缓存     │
│ TTL=30min (HOT) │
└─────────────────┘
```

**设计要点**：
- 单 Worker 协程，避免并发预缓存抢占 LLM 资源
- 队列容量上限 20，满时丢弃最旧任务
- 预缓存结果写入时标记 `precached=True`，区分自然缓存
- 自然命中时检查是否需要触发预缓存（异步，不阻塞请求）

### 3.3 EvictionManager — 热度加权淘汰管理器

**问题**：原方案 TTL 延长和淘汰策略是盲目的，浪费内存。

**优化方案（策略专家建议 #3）**：热度加权淘汰 + 主动降级

```python
class EvictionManager:
    """热度加权缓存淘汰管理器"""
    _max_entries: int = 5000          # 最大缓存条目数
    _eviction_threshold: float = 0.8  # 触发淘汰的内存压力阈值
    _decay_factor: float = 0.95       # 时间衰减因子 (每分钟)

    def compute_score(self, key: str, tracker: HotspotTracker) -> float:
        """
        热度分数 = 频率 × 时间衰减因子
        分数越高越不容易被淘汰
        """

    def maybe_evict(self, backend: CacheBackend, tracker: HotspotTracker):
        """
        当缓存条目超过阈值时淘汰低分条目
        1. 按热度分数排序
        2. 从最低分开始逐个删除
        3. 直到低于安全阈值
        """

    def check_and_downgrade(self, key: str, tracker: HotspotTracker):
        """
        每 5 分钟检查一次热度状态
        - 若已降级 WARM → TTL 恢复为默认值
        - 若已降级 COLD → 下次淘汰优先照顾
        """
```

### 3.4 双层计数器 — 多实例支持

**优化方案（分布式专家建议 #2）**：本地 + 全局双层计数器

```
 实例 A          实例 B          实例 C
┌────────┐     ┌────────┐     ┌────────┐
│RingBuf │     │RingBuf │     │RingBuf │
│(本地)  │     │(本地)  │     │(本地)  │
└───┬────┘     └───┬────┘     └───┬────┘
    │               │               │
    │ 每 30s 异步推 │               │
    ▼               ▼               ▼
┌──────────────────────────────────────────┐
│              Redis (可选)                │
│  ZADD hotkeys:<key> <count>             │
│  ZREVRANGE hotkeys 0 20  # Top-20 热点  │
│  PUBLISH hotspot:changed <key> <level>  │
└──────────────────────────────────────────┘
```

- **本地快速路径**：请求命中 → 本地环形缓冲区记录 → 即时判断热度（< 1ms）
- **全局聚合路径**：每 30s 异步推送本地计数到 Redis → 跨实例聚合排名 → 广播热点标记
- **降级兼容**：Redis 不可用时退化为纯本地模式，不影响核心功能

---

## 四、集成到 LLMClient

```python
class LLMClient:
    # 现有属性保持不变
    cache_manager: CacheManager
    provider_chain: ProviderChain

    # 新增属性
    hotspot_tracker: HotspotTracker
    eviction_manager: EvictionManager
    precache_worker: Optional[PreCacheWorker]

    async def chat(self, ...) -> LLMResponse:
        """现有 chat 方法保持不变，内部增强"""
        # 1. 生成缓存键
        # 2. 精确匹配查询 (L1)
        # 3. 命中 → 记录到 HotspotTracker → 检查是否需要预缓存 → 返回
        # 4. 未命中 → 调用责任链 → 写入缓存 → 返回
```

---

## 五、文件规划

| 文件 | 变更 | 说明 |
|------|------|------|
| `packages/LLMInfra/cache.py` | **重写** | 新增 HotspotTracker, EvictionManager, RingBuffer |
| `packages/LLMInfra/precache.py` | **新建** | PreCacheWorker 异步预缓存器 |
| `packages/LLMInfra/core.py` | **修改** | LLMClient 集成热点追踪和预缓存 |
| `packages/LLMInfra/__init__.py` | **修改** | 导出新类 |
| `packages/LLMInfra/tests/test_cache_enhanced.py` | **新建** | 热点追踪、淘汰策略、预缓存测试 |

---

## 六、测试计划

| 测试类 | 测试项 | 预期数量 |
|--------|--------|----------|
| RingBuffer | 写入/读取/窗口统计/容量溢出 | 6 |
| HotspotTracker | 快速触发/自适应降级/状态转换/HOT键列表 | 10 |
| EvictionManager | 分数计算/淘汰边界/主动降级/空缓存 | 7 |
| PreCacheWorker | 队列入队/预缓存执行/结果验证/队列满 | 6 |
| CacheManager | 命中率统计/缓存键优化/降级兼容 | 5 |
| 集成测试 | LLMClient end-to-end 缓存流 | 4 |

---

## 七、验证方式

```bash
# 运行缓存增强测试
pytest packages/LLMInfra/tests/test_cache_enhanced.py -v

# 运行完整 LLMInfra 回归测试
pytest packages/LLMInfra/tests/ -v

# 覆盖率报告
pytest packages/LLMInfra/ --cov=packages/LLMInfra --cov-report=term-missing
```
