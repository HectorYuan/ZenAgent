# 智能体Context传递规范

> 
> **状态**: ✅ 已批准入库
**版本**: v1.0
> **创建时间**: 2026-04-15
> **状态**: 已生效
> **核心思路**: 建立主智能体↔子智能体之间的context传递协议，实现"上下文是智能体协作的隐形脊梁"

---

## 一、概述

### 1.1 设计原则

> **上下文是智能体协作的隐形脊梁**
> - 主智能体→子智能体：传递enlightenment_context + task_context
> - 子智能体→主智能体：返回task_result + enlightenment_insight
> - context传递通过文件实现，确保完整性和可追溯性

### 1.2 架构图

```
【智能体集群 × Context传递】

┌───────────────────────────────────────────────────────────────────────────┐
│                         【主智能体】觉悟协调者                              │
│                                                                            │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                  │
│  │ 理解任务     │ →   │ 生成context │ →   │ 分配任务     │                  │
│  │ (会话输入)   │     │ (快照)      │     │ (带context) │                  │
│  └─────────────┘     └─────────────┘     └─────────────┘                  │
│         │                  │                  │                            │
│         │                  │                  │                            │
│         ▼                  ▼                  ▼                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    context传递文件                                   │  │
│  │  ├── enlightenment_context.json (觉悟上下文)                        │  │
│  │  ├── task_context.json (任务上下文)                                  │  │
│  │  └── agent_instruction.json (智能体指令)                             │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                      │
└────────────────────────────────────┼────────────────────────────────────┘
                                     │
                                     │ sessions_spawn
                                     │ context文件传递
                                     │
                                     ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         【子智能体】悟道执行者                              │
│                                                                            │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                  │
│  │ 读取context │ →   │ 理解完整背景 │ →   │ 执行任务     │                  │
│  │ (文件)       │     │ (悟道)       │     │ (证道)       │                  │
│  └─────────────┘     └─────────────┘     └─────────────┘                  │
│         │                  │                  │                            │
│         │                  │                  │                            │
│         ▼                  ▼                  ▼                            │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                  │
│  │ 证道执行     │ →   │ 沉淀洞察    │ →   │ 生成result  │                  │
│  │ (带context)  │     │ (经验教训)  │     │ (归档)       │                  │
│  └─────────────┘     └─────────────┘     └─────────────┘                  │
│                                                                            │
└───────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ 返回result文件
                                     │ sessions_result
                                     │
                                     ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         【主智能体】归档整合者                              │
│                                                                            │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                  │
│  │ 读取result  │ →   │ 更新任务状态 │ →   │ 触发回传     │                  │
│  │ (文件)       │     │ (TASK-Q)    │     │ (context)    │                  │
│  └─────────────┘     └─────────────┘     └─────────────┘                  │
│                                                                            │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 二、传递文件规范

### 2.1 文件列表

| 文件名 | 方向 | 用途 | 格式 |
|-------|------|------|------|
| `enlightenment_context.json` | 主→子 | 觉悟上下文 | JSON |
| `task_context.json` | 主→子 | 任务上下文 | JSON |
| `agent_instruction.json` | 主→子 | 智能体指令 | JSON |
| `task_result.json` | 子→主 | 任务结果 | JSON |
| `enlightenment_insight.json` | 子→主 | 觉悟洞察 | JSON |

### 2.2 文件存储位置

```
System/.shared_state/agent_context/
├── {session_id}/
│   ├── enlightenment_context.json
│   ├── task_context.json
│   ├── agent_instruction.json
│   ├── task_result.json (子智能体创建)
│   └── enlightenment_insight.json (子智能体创建)
```

---

## 三、enlightenment_context.json

### 3.1 结构定义

```json
{
  "enlightenment_id": "en_001",
  "type": "knowledge_trigger",
  "trigger": {
    "source": "knowledge_library",
    "file": "上下文共享强化方案.md",
    "reason": "新增方案入库"
  },
  "intent": {
    "why": "理解上下文共享与zen_enlightenment的融合点",
    "goal": "设计融合方案",
    "expected_outcome": "觉悟指数3→4"
  },
  "axiom_refs": ["axiom_003", "axiom_context_continuity"],
  "related_experiences": ["en_005", "en_012"],
  "lane": "NORMAL-P",
  "enlightenment_stage": "定境",
  "timestamp": "20260415T193000"
}
```

### 3.2 字段说明

| 字段 | 必填 | 说明 |
|-----|------|------|
| enlightenment_id | 是 | 觉悟ID，唯一标识 |
| type | 是 | 觉悟类型（knowledge_trigger/pattern_recognition/system_optimization） |
| trigger.source | 是 | 触发来源 |
| trigger.file | 否 | 触发文件 |
| trigger.reason | 是 | 触发原因 |
| intent.why | 是 | 为什么学 |
| intent.goal | 是 | 学习目标 |
| intent.expected_outcome | 是 | 预期结果 |
| axiom_refs | 否 | 引用的公理 |
| related_experiences | 否 | 相关历史经验 |
| lane | 是 | 对应的觉悟车道 |
| enlightenment_stage | 是 | 当前觉悟阶段（缘起/定境/慧照/证道/默化） |

---

## 四、task_context.json

### 4.1 结构定义

```json
{
  "task_id": "task_001",
  "description": "优化上下文传递机制",
  "source": {
    "from": "环节4: 目标→任务",
    "goal_id": "goal_001",
    "goal_name": "提升系统能力"
  },
  "context_chain": {
    "planning_intent": "ctx_01_xxx",
    "solution_decision": "ctx_02_xxx",
    "project_phase": "ctx_03_xxx",
    "goal_decomposition": "ctx_04_xxx"
  },
  "reasoning": "因为当前五环节之间缺乏显式上下文传递...",
  "axiom_refs": ["axiom_003", "axiom_007"],
  "constraints": ["不影响现有功能", "向后兼容"],
  "expected_outcome": "五环节上下文传递自动化率≥80%",
  "lane": "NORMAL-P",
  "priority": 2,
  "deadline": "2026-04-24",
  "enlightenment_ref": "en_001"
}
```

### 4.2 字段说明

| 字段 | 必填 | 说明 |
|-----|------|------|
| task_id | 是 | 任务ID |
| description | 是 | 任务描述 |
| source.from | 是 | 来源环节 |
| source.goal_id | 否 | 来源目标 |
| source.goal_name | 否 | 目标名称 |
| context_chain | 是 | 完整context链 |
| reasoning | 是 | 决策原因 |
| axiom_refs | 否 | 引用公理 |
| constraints | 否 | 约束条件 |
| expected_outcome | 是 | 预期结果 |
| lane | 是 | 分配车道 |
| priority | 是 | 优先级 |
| deadline | 否 | 截止时间 |
| enlightenment_ref | 否 | 关联觉悟ID |

---

## 五、agent_instruction.json

### 5.1 结构定义

```json
{
  "instruction_id": "inst_001",
  "task_id": "task_001",
  "agent_role": "创作者",
  "agent_capabilities": ["文档创作", "格式规范"],
  "task_description": "创建五环节context生成规范文档",
  "execution_steps": [
    "1. 读取背景文档了解context设计原则",
    "2. 按规范创建文档结构",
    "3. 生成5种context类型模板",
    "4. 保存到指定路径"
  ],
  "output_requirements": {
    "path": "Knowledge/L4-Implementation/",
    "filename": "五环节context生成规范.md",
    "format": "Markdown",
    "validation": ["格式规范检查", "内容完整性检查"]
  },
  "rollback_plan": "如果失败，保留已创建的部分文档",
  "callback_event": "task_completed",
  "context_files": [
    "enlightenment_context.json",
    "task_context.json"
  ],
  "created_at": "20260415T120000"
}
```

### 5.2 字段说明

| 字段 | 必填 | 说明 |
|-----|------|------|
| instruction_id | 是 | 指令ID |
| task_id | 是 | 关联任务ID |
| agent_role | 是 | 子智能体角色 |
| agent_capabilities | 否 | 子智能体能力要求 |
| task_description | 是 | 任务描述 |
| execution_steps | 是 | 执行步骤 |
| output_requirements | 是 | 输出要求 |
| output_requirements.path | 是 | 输出路径 |
| output_requirements.filename | 是 | 文件名 |
| output_requirements.format | 是 | 格式 |
| output_requirements.validation | 否 | 验证清单 |
| rollback_plan | 否 | 回滚计划 |
| callback_event | 是 | 回调事件 |
| context_files | 是 | 使用的context文件 |

---

## 六、task_result.json（子智能体创建）

### 6.1 结构定义

```json
{
  "result_id": "result_001",
  "task_id": "task_001",
  "status": "completed",
  "outputs": {
    "files_created": [
      {
        "path": "Knowledge/L4-Implementation/五环节context生成规范.md",
        "size": 15000,
        "checksum": "xxx"
      }
    ],
    "data_updated": [
      {
        "file": "SESSION-INDEX.json",
        "change": "添加context_relay字段"
      }
    ]
  },
  "execution": {
    "started_at": "20260415T120000",
    "completed_at": "20260415T121500",
    "duration_seconds": 90,
    "steps_executed": ["步骤1", "步骤2", "步骤3"]
  },
  "verification": {
    "self_check": "passed",
    "validation_results": [
      {"check": "格式规范", "status": "passed"},
      {"check": "内容完整", "status": "passed"}
    ]
  },
  "created_at": "20260415T121500"
}
```

### 6.2 字段说明

| 字段 | 必填 | 说明 |
|-----|------|------|
| result_id | 是 | 结果ID |
| task_id | 是 | 关联任务ID |
| status | 是 | 执行状态（completed/failed/partially_completed） |
| outputs.files_created | 否 | 创建的文件列表 |
| outputs.data_updated | 否 | 更新的数据列表 |
| execution.started_at | 是 | 开始时间 |
| execution.completed_at | 是 | 完成时间 |
| execution.duration_seconds | 是 | 执行时长 |
| execution.steps_executed | 是 | 执行的步骤 |
| verification.self_check | 是 | 自检结果 |
| verification.validation_results | 否 | 验证结果列表 |

---

## 七、enlightenment_insight.json（子智能体创建）

### 7.1 结构定义

```json
{
  "insight_id": "insight_001",
  "enlightenment_id": "en_001",
  "task_id": "task_001",
  "enlightenment_stage": "慧照",
  "insights": {
    "new_understanding": "context传递需要显式设计才能自动化",
    "pattern_discovered": "五环节间传递需要统一的context结构",
    "improvement_suggestion": "建议增加context版本管理机制"
  },
  "lessons_learned": [
    "觉悟触发时生成context快照很重要",
    "证道验证时归档到task_results"
  ],
  "context_enhancement": {
    "improved_fields": ["context_chain"],
    "new_fields_added": ["enlightenment_ref"],
    "deprecated_fields": []
  },
  "related_enlightenments": ["en_005", "en_012"],
  "timestamp": "20260415T121500"
}
```

### 7.2 字段说明

| 字段 | 必填 | 说明 |
|-----|------|------|
| insight_id | 是 | 洞察ID |
| enlightenment_id | 是 | 关联觉悟ID |
| task_id | 是 | 关联任务ID |
| enlightenment_stage | 是 | 觉悟阶段（缘起/定境/慧照/证道/默化） |
| insights.new_understanding | 是 | 新理解 |
| insights.pattern_discovered | 否 | 发现的模式 |
| insights.improvement_suggestion | 否 | 改进建议 |
| lessons_learned | 是 | 经验教训 |
| context_enhancement | 是 | context增强建议 |
| related_enlightenments | 否 | 相关觉悟 |

---

## 八、传递流程

### 8.1 主→子传递流程

```
1. 主智能体创建任务
   └── 生成 task_context.json

2. 主智能体检查是否觉悟任务
   └── 如果是 → 生成 enlightenment_context.json

3. 主智能体生成指令
   └── 生成 agent_instruction.json

4. 主智能体打包context文件
   └── 存储到 System/.shared_state/agent_context/{session_id}/

5. 主智能体调用 sessions_spawn
   └── 在任务描述中说明使用哪些context文件

6. 子智能体启动时读取context文件
   └── 读取 enlightenment_context.json（如存在）
   └── 读取 task_context.json
   └── 读取 agent_instruction.json
```

### 8.2 子→主返回流程

```
1. 子智能体执行任务
   └── 按 agent_instruction.json 执行

2. 子智能体生成执行结果
   └── 生成 task_result.json

3. 子智能体判断是否有觉悟收获
   └── 如果有 → 生成 enlightenment_insight.json

4. 子智能体存储结果文件
   └── 存储到 System/.shared_state/agent_context/{session_id}/

5. 子智能体完成任务
   └── 返回 task_id, status, result_summary

6. 主智能体读取结果文件
   └── 读取 task_result.json
   └── 读取 enlightenment_insight.json（如存在）

7. 主智能体更新状态
   └── 更新 TASK-QUEUE.json
   └── 更新 MEMORY.md pending_contexts
   └── 触发 context 回传
```

---

## 九、sessions_spawn 调用规范

### 9.1 任务描述模板

```markdown
## 任务：{任务名称}

### 背景
{任务背景}

### context来源
- enlightenment_context: System/.shared_state/agent_context/{session_id}/enlightenment_context.json
- task_context: System/.shared_state/agent_context/{session_id}/task_context.json

### 执行要求
{执行要求}

### 输出
- 输出路径: {路径}
- 格式: {格式}

### 完成后
1. 生成 task_result.json 到 context目录
2. 如有觉悟收获，生成 enlightenment_insight.json
3. 返回任务ID和执行摘要
```

### 9.2 示例

```markdown
## 任务：创建五环节context生成规范文档

### 背景
用户需要创建上下文共享强化方案的Phase 2产出文档

### context来源
- enlightenment_context: System/.shared_state/agent_context/sub_001/enlightenment_context.json
- task_context: System/.shared_state/agent_context/sub_001/task_context.json

### 执行要求
1. 读取 enlightenment_context.json 了解觉悟目标
2. 读取 task_context.json 了解任务上下文
3. 按照五环节context生成规范创建文档
4. 包含5种context类型模板

### 输出
- 输出路径: Knowledge/L4-Implementation/
- 文件名: 五环节context生成规范.md
- 格式: Markdown

### 完成后
1. 生成 task_result.json 到 context目录
2. 返回任务ID和执行摘要
```

---

## 十、验收标准

- [ ] 主→子传递包含完整enlightenment_context（如适用）
- [ ] 主→子传递包含完整task_context
- [ ] 子智能体能读取并使用context文件
- [ ] 子→主返回包含task_result.json
- [ ] 觉悟任务返回包含enlightenment_insight.json
- [ ] context_chain可追溯
- [ ] 文件传递有完整日志记录

---

## 十一、错误处理

### 11.1 context文件缺失

```markdown
错误：enlightenment_context.json 不存在
处理：
1. 记录警告日志
2. 继续执行，但标记 context_incomplete=true
3. 在 result 中说明缺失的 context
```

### 11.2 context文件格式错误

```markdown
错误：JSON 格式解析失败
处理：
1. 记录错误日志
2. 尝试使用默认 context
3. 在 result 中说明错误
```

### 11.3 子智能体执行失败

```markdown
错误：任务执行失败
处理：
1. 生成 error_result.json
2. 包含错误信息和部分成果
3. 返回错误状态给主智能体
4. 主智能体决定是否重试或降级
```

---

## 十二、附录

### 12.1 文件命名规范

| 文件 | 命名格式 | 示例 |
|-----|---------|------|
| enlightenment_context | enlightenment_context.json | enlightenment_context.json |
| task_context | task_context_{task_id}.json | task_context_task001.json |
| agent_instruction | agent_instruction_{task_id}.json | agent_instruction_task001.json |
| task_result | task_result_{task_id}_{timestamp}.json | task_result_task001_20260415.json |
| enlightenment_insight | enlightenment_insight_{en_id}_{timestamp}.json | enlightenment_insight_en001_20260415.json |

### 12.2 状态码

| 状态码 | 含义 | 说明 |
|-------|------|------|
| 0 | completed | 任务完成 |
| 1 | failed | 任务失败 |
| 2 | partially_completed | 部分完成 |
| 3 | context_incomplete | context不完整 |
| 4 | timeout | 执行超时 |

---

## 关联文档

- [知识库管理机制](../L3-Rules/知识库管理机制.md)
- [知识入库规范](../L3-Rules/知识入库规范.md)
