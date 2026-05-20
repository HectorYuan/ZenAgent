# M8 P2: 意图分类 + Fast/Deep 路径分流 设计方案

**日期**: 2026-05-21
**状态**: 设计中
**版本**: v2.0（已整合三轮专家评审优化）
**设计依据**: [E2E_OPTIMIZATION_DESIGN §模块6](../E2E_OPTIMIZATION_DESIGN.md)

---

## 一、方案定位

在现有 `IntentClassifier` (4 分类/纯关键词) 基础上，升级为**三级联分类器 + 五路径分流 + 级联退化**的统一路由系统。

**核心目标**：
- 简单请求走 FastPath（缓存优先 + 小模型兜底），延迟 < 50ms
- 复杂请求走 DeepPath（大模型 + CoT），质量优先
- 分类延迟不增加端到端开销（L2 并行化）

---

## 二、整体架构

```
                        ┌──────────────────┐
                        │   ZenAgent.think()│
                        │   新增 intent arg │
                        └────────┬─────────┘
                                 │
                                 ▼
                ┌────────────────────────────┐
                │      IntentRouter          │
                │  统一意图路由入口           │
                └───────────┬────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────┐ ┌──────────────┐ ┌──────────────┐
│ L1 规则分类器   │ │ L2 LLM精分类 │ │ L3 Emb分类   │
│ (增强版)        │ │ (并行触发)   │ │ (离线训练)   │
│ 0.1ms · $0     │ │ 100ms · $0   │ │ 5ms · $0     │
│ 始终执行        │ │ 低置信时执行 │ │ 标注≥500启用 │
└────────┬────────┘ └──────┬───────┘ └──────┬───────┘
         │                │                │
         └────────────────┼────────────────┘
                          │ 分类结果
                          ▼
         ┌────────────────────────────────┐
         │        PathDispatcher          │
         │     五路径分流决策             │
         └───────────┬────────────────────┘
                     │
    ┌───────┬────────┼────────┬──────────┐
    ▼       ▼        ▼        ▼          ▼
FastPath  RAGPath  ToolPath  DeepPath  FallbackPath
(缓存→小 (知识库) (工具调 (大模型+  (兜底响应)
 模型)            用)     CoT)
```

---

## 三、核心组件

### 3.1 IntentRouter — 统一路由入口

```python
class IntentRouter:
    """意图路由器 — 三级联分类 + 路径分流"""

    def __init__(self):
        # L1: 规则快速分类（始终执行）
        self.l1_classifier = L1RuleClassifier()

        # L2: LLM 精分类器（低置信度时触发，并行化）
        self.l2_classifier: Optional[L2LLMClassifier] = None

        # L3: Embedding 分类器（标注 ≥500 条启用）
        self.l3_classifier: Optional[L3EmbeddingClassifier] = None

        # 标注数据池
        self._annotation_pool: list[AnnotationRecord] = []

        # 分发器
        self.dispatcher = PathDispatcher()

    async def route(self, request: ChatRequest) -> RouteResult:
        """
        路由入口:
        1. L1 分类 → 高置信度直接分流
        2. L1 低置信度 → L2 并行执行（不阻塞默认路径）
        3. L3 已启用 → L1 后直接走 L3（skip L2）
        """
```

### 3.2 三级分类器

#### L1 — 规则快速分类（增强版）

| 改进项 | 原版 | 增强版 |
|--------|------|--------|
| 分类数量 | 4 类 | 6 类 + RAG + TOOL |
| 置信度 | 固定 1.0 | 基于覆盖度的置信度评分 |
| 模式匹配 | 无 | 代码模式/工具调用模式/检索模式 |
| 长度启发 | 简单的 >2000 判断 | 分位数动态阈值 |

**置信度计算**：
```
置信度 = 关键词命中数 / 该类别关键词总数 × 0.6
       + 长度匹配度 × 0.3
       + 模式匹配加 × 0.1
```

**6 类意图**：

| 意图 | 典型触发 | 建议路径 |
|------|----------|----------|
| SIMPLE_QA | "是什么"、"怎么"、"定义" | FastPath |
| KNOWLEDGE_RETRIEVAL | "wiki"、"百度百科"、长尾事实 | RAGPath |
| TOOL_CALLING | 含代码、含 API 调用模式 | ToolPath |
| GENERAL_REASONING | "分析"、"总结"、中等复杂度 | FastPath(缓存) → DeepPath |
| COMPLEX_REASONING | "设计系统"、"权衡"、多步骤 | DeepPath |
| CREATIVE_WRITING | "写一篇"、"创作"、长文本生成 | DeepPath |

#### L2 — LLM 精分类（并行化）

**关键设计（延迟专家建议 #1）**：L2 不与主路径串行。

```python
async def route(request):
    # L1 分类
    l1_result = l1_classifier.classify(request)

    if l1_result.confidence >= 0.85:
        return dispatcher.dispatch(l1_result.intent, request)

    # 低置信度：L2 并行执行 + 默认路径同时启动
    default_path = DeepPath  # 安全默认
    l2_task = asyncio.create_task(l2_classifier.classify(request))
    default_task = asyncio.create_task(default_path.execute(request))

    # L2 有 30ms 超时窗口
    done, pending = await asyncio.wait(
        [l2_task, default_task],
        timeout=0.03  # 30ms 超时
    )

    if l2_task in done and l2_task.result():
        # L2 返回且可追上：检查是否需要切换路径
        intent = l2_task.result().intent
        if intent != default_path.intent:
            default_task.cancel()
            return dispatcher.dispatch(intent, request)
    # L2 超时或默认路径已完成：不等待
    return await default_task
```

#### L3 — Embedding 分类（离线训练）

**触发条件**（标注专家建议 #2）：可信标注样本 ≥ 500 条。

**标注质量控制**：
```
标注记录 → 待验证池
  ├─ L1 + L2 分类一致 → 升级为可信标注
  ├─ L1 + L2 不一致 → 保留在待验证池
  └─ 人工抽查 → 升级为可信标注

可信标注 ≥ 500 条 → 训练 L3
L3 启用后 → 对比 L2 vs L3 差异 → 差异样本回灌待验证池
```

### 3.3 PathDispatcher — 五路径分流

| 路径 | 触发意图 | 执行策略 | 延迟目标 |
|------|----------|----------|----------|
| **FastPath** | SIMPLE_QA, GENERAL | 缓存优先 → 小模型(如 gpt-3.5) → 升级 DeepPath | <50ms (缓存), <1s (小模型) |
| **RAGPath** | KNOWLEDGE_RETRIEVAL | 向量检索知识库 → 拼接上下文 → LLM 生成 | <2s |
| **ToolPath** | TOOL_CALLING | 解析工具调用 → 执行 → 结果注入 → LLM 生成 | <3s |
| **DeepPath** | COMPLEX, CREATIVE | 大模型(如 gpt-4) + Chain-of-Thought | <10s |
| **FallbackPath** | 所有路径失败 | Mock 响应 / 预置回答 | <100ms |

### 3.4 路径级联退化（策略专家建议 #3）

```
FastPath
  ├─ 缓存命中 → 直接返回 (<1ms)
  ├─ 缓存未命中 → ProviderChain 小模型 (30s 超时)
  │   ├─ 成功 → 返回 + 异步写入缓存
  │   └─ 失败 → 升级到 DeepPath
  └─ 升级到 DeepPath

DeepPath
  ├─ 成功 → 返回
  └─ 失败 → 降级到 FallbackPath

RAGPath
  ├─ 知识库命中 → 拼接返回
  ├─ 知识库未命中 → 降级到 DeepPath
  └─ 降级到 FallbackPath

ToolPath
  ├─ 工具执行成功 → 返回
  └─ 工具失败 → 降级到 DeepPath
```

---

## 四、LLMClient 增强

```python
class LLMClient:
    # 现有属性和方法保持不变

    async def chat_fast(self, request: ChatRequest) -> LLMResponse:
        """FastPath: 缓存优先 → 小模型"""
        # 先查缓存
        # 缓存未命中 → ProviderChain 小模型
        # 失败 → raise 由路由层接住升级到 DeepPath

    async def chat_deep(self, request: ChatRequest) -> LLMResponse:
        """DeepPath: 大模型 + CoT"""
        # 使用 ProviderChain 大模型
        # 自动添加 CoT 提示词
        # 失败 → 降级到 Fallback

    async def chat_rag(self, request: ChatRequest) -> LLMResponse:
        """RAGPath: 知识库检索增强"""
        # 1. 从请求提取检索 query
        # 2. 调用知识库检索
        # 3. 拼接检索结果到上下文
        # 4. LLM 生成
        # 未命中 → 降级到 DeepPath

    async def chat_fallback(self, request: ChatRequest) -> LLMResponse:
        """FallbackPath: 兜底响应"""
        # Mock 响应 / 模板回答 / 错误提示
```

---

## 五、文件规划

| 文件 | 变更 | 说明 |
|------|------|------|
| `packages/LLMInfra/intent_router.py` | **新建** | IntentRouter + L1/L2 分类器 + PathDispatcher |
| `packages/LLMInfra/embedding_classifier.py` | **新建** | L3 Embedding 分类器 + 标注池管理 |
| `packages/LLMInfra/token_budget.py` | **修改** | 增强 IntentClassifier → L1RuleClassifier |
| `packages/LLMInfra/core.py` | **修改** | LLMClient 新增 chat_fast/chat_deep/chat_rag/chat_fallback |
| `packages/ZenAgent/core.py` | **修改** | ZenAgent.think() 集成 IntentRouter |
| `packages/LLMInfra/__init__.py` | **修改** | 导出新类 |
| `packages/LLMInfra/tests/test_intent_router.py` | **新建** | 分类器 + 路由 + 路径退化测试 |

---

## 六、分阶段交付

| 阶段 | 内容 | 预估 | 依赖 |
|------|------|------|------|
| Phase 1 | L1 增强分类器 + 五路径分发 + 级联退化 + FastPath/DeepPath 实现 | 1.5 天 | 现有 IntentClassifier |
| Phase 2 | L2 LLM 精分类 + 并行化 + 标注反馈收集 | 0.5 天 | Phase 1 |
| Phase 3 | L3 Embedding 分类 + 标注池质量控制 + 自动启用 | 0.5 天 | Phase 2 标注数据积累 |

---

## 七、测试计划

| 测试类 | 内容 | 预期数量 |
|--------|------|----------|
| L1RuleClassifier | 6 类分类/置信度计算/模式匹配/边缘 case | 12 |
| PathDispatcher | 五路径选择/级联退化/多路径 fallback | 8 |
| IntentRouter | 端到端路由/并行执行/超时机制 | 6 |
| LLMClient 新方法 | FastPath/DeepPath/FallbackPath | 6 |
| 集成测试 | ZenAgent.think() 分流验证 | 4 |

---

## 八、验证方式

```bash
# 运行意图路由测试
pytest packages/LLMInfra/tests/test_intent_router.py -v

# 运行 LLMInfra 全量回归
pytest packages/LLMInfra/tests/ -v

# 运行 ZenAgent 回归
pytest packages/ZenAgent/tests/ -v

# 覆盖率
pytest packages/LLMInfra/ --cov=packages/LLMInfra --cov-report=term-missing
```
