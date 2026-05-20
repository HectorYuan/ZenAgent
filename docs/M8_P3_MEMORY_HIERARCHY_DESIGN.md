# M8 P3: 记忆分层架构增强 设计方案

**日期**: 2026-05-21
**状态**: 设计中
**版本**: v2.0（五轮专家评审优化已整合）
**设计依据**: [E2E_OPTIMIZATION_DESIGN §模块9](../E2E_OPTIMIZATION_DESIGN.md)

---

## 一、方案定位

在现有 `MemoryHierarchy` + `MemoryScorer` 基础上，构建**四层存储 + 两个横切子系统 + 统一管线**的完整记忆架构。

---

## 二、四层存储架构

| 层级 | 对标设计 | 数据结构 | 容量 | 延迟 | 职责 |
|------|----------|----------|------|------|------|
| **L1 热** | 工作记忆 | deque (FIFO) | 20 条 | <0.1ms | 当前会话即时上下文 |
| **L2 温** | 情景记忆 | dict + PluggableBackend | 1000 条 | <1ms | 跨会话情景记忆 |
| **L3 语义** | 语义记忆 | SemanticKnowledgeBase (SPO 三元组 + 向量索引) | 无限制 | <5ms | 结构化知识提取与检索 |
| **L4 归档** | 档案记忆 | 压缩摘要 + JSON 文件 | 无限制 | <30s | 长期历史归档 |

## 三、知识表示模型（专家 #1：知识图谱）

### 3.1 SPO 三元组 + 来源追踪

```python
@dataclass
class KnowledgeTriple:
    subject: str          # 主体
    predicate: str        # 谓词
    object: str           # 客体
    confidence: float     # 0-1
    sources: list[str]    # 来源记忆 ID（可追溯）
    first_seen: float     # 首次提取时间
    last_seen: float      # 最后确认时间
    seen_count: int       # 被确认次数

class SemanticKnowledgeBase:
    _triples: dict[str, KnowledgeTriple]  # key = "s:p:o"
    _entity_index: dict[str, set[str]]     # entity → triple keys

    def upsert(triple)     # 同一事实自动合并 seen_count++
    def detect_conflict()  # 同 (s,p) 不同 object → 标记待验证
    def semantic_search(query, top_k)  # 向量相似度检索
```

## 四、检索系统（专家 #4：检索性能）

### 4.1 检索意图分流 + 并行执行

```python
class RetrieveIntent(Enum):
    RECENT_CONTEXT = "recent"        # 仅 L1+L2
    SEMANTIC_KNOWLEDGE = "semantic"  # 仅 L3
    HISTORICAL = "historical"        # 仅 L4
    FULL_STACK = "full"              # 四层并行

class MemoryRetriever:
    async def retrieve(query, intent):
        if intent == FULL_STACK:
            # 并行执行，延迟 = max(L1,L2,L3,L4) 而非 sum
            results = await asyncio.gather(
                search_l1(query), search_l2(query),
                search_l3(query), search_l4(query)
            )
            return merge(*results)
        else:
            # 按意图分流到对应层级
```

### 4.2 三路加权融合召回

```
score = sim * 0.5 + time_decay * 0.3 + importance * 0.2
```
- sim: Jaccard/余弦相似度
- time_decay: e^(-λt) 遗忘曲线
- importance: MemoryScorer 重要性评分

---

## 五、知识提取管道（专家 #3/#5：LLM 成本 + 数据一致性）

### 5.1 分层摘要策略

| 级别 | 触发 | 方法 | 成本 |
|------|------|------|------|
| 快速摘要 | 每次 L1→L2 降级 | 规则提取字段 (topic, entities, outcome) | $0 |
| 批量摘要 | L2 累计 50 条待处理 | 一次 LLM 调用生成汇总段落 | ~$0.002 |
| 深度摘要 | L2 累计 500 条 | LLM 生成结构化叙事 | ~$0.01 |

### 5.2 统一 ConsolidationPipeline

```
所有降级操作经过统一管线:

L1 entry → [过期?] → 丢弃
         → [重要?] → ConsolidationPipeline.process(entry)
                          │
                          ├─ 1. 实体识别 + 关系抽取
                          ├─ 2. SPO 三元组提取 → L3 语义库 (upsert + sources)
                          ├─ 3. 累积归档缓冲区 → 达到阈值 → 批量压缩 → L4
                          └─ 4. 标记 L2 entry 为 processed

去重保证: 每条记忆只进管线一次，通过 sources 字段追溯
```

### 5.3 KnowledgeExtractor

```
L2 中待处理的记忆
    │
    ▼
┌─────────────────┐
│ 1. 实体识别      │ → 提取人名、术语、概念
│ 2. 关系抽取      │ → 识别关联 (is_a, has_property, related_to)
│ 3. 事实提取      │ → 从对话中提取声明性事实
│ 4. 置信度更新    │ → 重复出现 → seen_count++
│ 5. 冲突检测      │ → 同 (s,p) 不同 object → 标记待验证
│ 6. 写入语义库    │ → SemanticKnowledgeBase.upsert()
└─────────────────┘
```

### 5.4 ArchivalManager

```
L2 容量达到阈值 (800/1000)
    │
    ▼
┌─────────────────┐
│ 1. 选择候选      │ → 最低活跃度的 200 条
│ 2. 规则快速摘要  │ → topic, entities, outcome ($0)
│ 3. LLM 批量摘要  │ → 50条批次生成段落 ($0.002)
│ 4. 写入归档      │ → JSONL 文件 + 索引
│ 5. 从 L2 删除    │ → 释放温层空间
└─────────────────┘
```

---

## 六、数据升温机制（专家 #2：存储架构）

### 6.1 L3/L4 → L1 预热回填

```
L3/L4 被检索命中时:
    ├─ 返回结果
    └─ 异步回填到 L1 (标记 archived_warmup, priority=0.5)
```

### 6.2 L2 活跃度计数器

每条 L2 记忆维护:
- `access_count`: 被检索次数
- `last_access`: 最后访问时间

```
access_count > 3  → 优先保留 (免于淘汰)
access_count = 0 且 >7天 → 优先压缩归档

L3 知识三元组 confidence 衰减:
  last_seen > 30天 → confidence *= 0.9 (知识老化)
  confidence < 0.3 → 移入待验证池
```

---

## 七、整体架构图

```
                    ┌──────────────────────────────┐
                    │       MetaSoul (core)         │
                    │   统一入口 + 检索分流         │
                    └──────────────┬───────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
            ▼                      ▼                      ▼
    ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
    │Hierarchical  │    │Consolidation     │    │MemoryRetriever   │
    │Store         │    │Pipeline          │    │(检索意图分流)    │
    │(四层存储)    │    │(统一写入管线)    │    │(并行+三路加权)   │
    └──────┬───────┘    └────────┬─────────┘    └────────┬─────────┘
           │                    │                       │
    ┌──────┼────────┬──────────┐│                       │
    ▼      ▼        ▼          ▼▼                       │
   L1     L2       L3         L4                        │
  热记忆 温记忆   语义知识   档案归档                    │
  deque  dict+    SPO三元组  JSON文件                    │
  20条   backend  向量索引   摘要索引                    │
           │                                              │
           ▼                                              │
    ┌──────────────┐                                      │
    │Pluggable     │                                      │
    │Backend       │                                      │
    │Mem | Redis   │                                      │
    └──────────────┘                                      │
                                                          │
           ┌──────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────┐
    │Knowledge     │
    │Extractor     │
    │(实体/关系/   │
    │ 事实提取)    │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐      ┌──────────────┐
    │Semantic      │      │Archival      │
    │KnowledgeBase │      │Manager       │
    │(SPO三元组)   │      │(批量压缩)    │
    └──────────────┘      └──────────────┘
```

---

## 八、文件规划

| 文件 | 变更 | 说明 |
|------|------|------|
| `packages/MetaSoul/memory/hierarchical_store.py` | **新建** | HierarchicalStore (L1-L4) + PluggableBackend |
| `packages/MetaSoul/memory/semantic_kb.py` | **新建** | KnowledgeTriple + SemanticKnowledgeBase |
| `packages/MetaSoul/memory/knowledge_extractor.py` | **新建** | KnowledgeExtractor (实体/关系/事实提取) |
| `packages/MetaSoul/memory/archival_manager.py` | **新建** | ArchivalManager (批量压缩归档) |
| `packages/MetaSoul/memory/consolidation.py` | **新建** | ConsolidationPipeline (统一写入管线) |
| `packages/MetaSoul/memory/memory_retriever.py` | **新建** | MemoryRetriever (意图分流 + 三路加权) |
| `packages/MetaSoul/memory/__init__.py` | **修改** | 导出新类 |
| `packages/MetaSoul/core.py` | **修改** | MetaSoul 集成新架构 |
| `packages/MetaSoul/tests/test_memory_hierarchy_v2.py` | **新建** | 全部测试 |

---

## 九、分阶段交付

| 阶段 | 内容 | 预估 | 测试 |
|------|------|------|------|
| Phase 1 | HierarchicalStore L1-L4 存储 + PluggableBackend + MemoryRetriever | 1 天 | 15 |
| Phase 2 | SPO 三元组 + SemanticKnowledgeBase + KnowledgeExtractor | 0.5 天 | 8 |
| Phase 3 | ConsolidationPipeline + ArchivalManager + 集成 MetaSoul | 0.5 天 | 7 |

---

## 十、测试计划

| 测试类 | 内容 | 数量 |
|--------|------|------|
| HierarchicalStore | L1-L4 分层存储/FIFO淘汰/降级检索/后端切换 | 10 |
| SemanticKnowledgeBase | SPO upsert/冲突检测/置信度衰减/来源追溯 | 6 |
| MemoryRetriever | 意图分流/并行检索/FULL_STACK 融合 | 5 |
| KnowledgeExtractor | 实体/关系/事实提取/规则摘要 | 4 |
| ConsolidationPipeline | 统一管线/去重/批量摘要触发 | 4 |
| ArchivalManager | 候选选择/规则摘要/批量归档/容量管理 | 3 |
| 集成 | MetaSoul + 全栈唤醒 | 3 |
