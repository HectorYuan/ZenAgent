# 子智能体运行机制

> 整合自：Knowledge/L4-Implementation/智能体协作/子智能体运行机制.md, Knowledge/L4-Implementation/智能体协作/智能体集群运行机制.md

## 1. 子智能体生命周期

```
┌──────────┐
│  CREATE  │ ← 实例化
└────┬─────┘
     ▼
┌──────────┐
│  INIT    │ ← 技能加载
└────┬─────┘
     ▼
┌──────────┐
│  IDLE    │ ← 等待任务
└────┬─────┘
     ▼
┌──────────┐
│ RUNNING  │ ← 执行任务
└────┬─────┘
     ▼
┌──────────┐
│COMPLETED │ ← 返回结果
└────┬─────┘
     │
     └──→ IDLE (循环) 或 TERMINATE
```

## 2. 子智能体类型

| 类型 | 职责 | 特点 |
|------|------|------|
| Worker | 任务执行 | 被动响应 |
| Analyst | 分析决策 | 主动思考 |
| Coordinator | 协调调度 | 跨团队通信 |
| Specialist | 专业领域 | 深度技能 |

## 3. 任务分派流程

```python
# Master Agent
1. 任务分解 → SubTask[]
2. 能力匹配 → Agent-SubTask 映射
3. 任务下发 → Agent.submit_task()
4. 进度监控 → Agent.get_status()
5. 结果汇总 → Master.complete_task()
```

## 4. 状态管理

### 4.1 状态类型
- `PENDING`: 等待分配
- `ASSIGNED`: 已分配
- `RUNNING`: 执行中
- `WAITING`: 等待资源
- `COMPLETED`: 已完成
- `FAILED`: 执行失败

### 4.2 状态同步
- 实时状态上报
- 超时检测
- 心跳保活

## 5. 集群协同

### 5.1 资源共享
- CPU/内存配额
- 工具访问权限
- 上下文限制

### 5.2 负载均衡
- 任务队列监控
- 动态分配
- 热点规避

---

*来源：Knowledge/L4-Implementation/智能体协作/子智能体运行机制.md*
