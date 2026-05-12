# SwarmFly API 文档

> **文档版本**: v1.1
> **更新日期**: 2026-06-08
> **适用范围**: SwarmFly FLY-2/3/5 深度实现

---

## 一、API 概述

### 1.1 接口架构

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                          │
├─────────────────────────────────────────────────────────┤
│  RevolvingInterface  │  EvolvingInterface  │  ConvolvInterface │
│     (FLY-2)           │      (FLY-3)        │     (FLY-3)        │
├─────────────────────────────────────────────────────────┤
│              ToolRegistry (FLY-5)                       │
├─────────────────────────────────────────────────────────┤
│           MessageQueue (FLY-5)                          │
└─────────────────────────────────────────────────────────┘
```

### 1.2 认证方式

所有API请求需要携带认证信息：

```http
Authorization: Bearer <token>
Content-Type: application/json
X-Request-ID: <request_id>
```

---

## 二、规则引擎 API (FLY-2)

### 2.1 规则管理

#### POST /api/v1/rules
创建新规则

**请求体**:
```json
{
  "name": "high_cpu_alert",
  "type": "alert",
  "conditions": [
    {
      "field": "cpu.usage",
      "operator": ">",
      "value": 80
    }
  ],
  "actions": [
    {
      "type": "notify",
      "params": {
        "channel": "slack",
        "message": "CPU usage exceeds 80%"
      }
    }
  ],
  "priority": 100,
  "enabled": true
}
```

**响应**:
```json
{
  "rule_id": "rule_123456",
  "name": "high_cpu_alert",
  "status": "active",
  "created_at": "2026-06-08T10:00:00Z"
}
```

#### GET /api/v1/rules
获取规则列表

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20 |
| type | string | 否 | 规则类型过滤 |
| enabled | bool | 否 | 启用状态过滤 |

**响应**:
```json
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "rules": [...]
}
```

#### GET /api/v1/rules/{rule_id}
获取单个规则详情

#### PUT /api/v1/rules/{rule_id}
更新规则

#### DELETE /api/v1/rules/{rule_id}
删除规则

#### POST /api/v1/rules/{rule_id}/enable
启用规则

#### POST /api/v1/rules/{rule_id}/disable
禁用规则

### 2.2 规则执行

#### POST /api/v1/rules/execute
执行规则

**请求体**:
```json
{
  "rule_id": "rule_123456",
  "context": {
    "cpu": {"usage": 85},
    "memory": {"usage": 60}
  }
}
```

**响应**:
```json
{
  "execution_id": "exec_789",
  "rule_id": "rule_123456",
  "status": "success",
  "actions_executed": [
    {
      "type": "notify",
      "result": "sent"
    }
  ],
  "execution_time_ms": 12.5
}
```

#### POST /api/v1/rules/batch-execute
批量执行规则

**请求体**:
```json
{
  "rule_ids": ["rule_1", "rule_2"],
  "context": {
    "cpu": {"usage": 85}
  },
  "parallel": true
}
```

### 2.3 规则验证

#### POST /api/v1/rules/validate
验证规则语法

**请求体**:
```json
{
  "name": "test_rule",
  "type": "alert",
  "conditions": [...],
  "actions": [...]
}
```

**响应**:
```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    {
      "field": "priority",
      "message": "Priority value is out of typical range"
    }
  ]
}
```

### 2.4 版本管理

#### GET /api/v1/rules/versions
获取规则版本列表

#### POST /api/v1/rules/rollback
回滚到指定版本

**请求体**:
```json
{
  "rule_id": "rule_123456",
  "target_version": "v2"
}
```

---

## 三、预测引擎 API (FLY-3)

### 3.1 预测管理

#### POST /api/v1/predictions
创建预测

**请求体**:
```json
{
  "metric_name": "cpu_usage",
  "model": "linear",
  "horizon": "short",
  "data_points": [
    {"timestamp": "2026-06-01T00:00:00Z", "value": 45.2},
    {"timestamp": "2026-06-02T00:00:00Z", "value": 48.1},
    {"timestamp": "2026-06-03T00:00:00Z", "value": 52.3}
  ]
}
```

**响应**:
```json
{
  "prediction_id": "pred_123",
  "metric_name": "cpu_usage",
  "predicted_value": 58.5,
  "horizon": "short",
  "confidence": 0.85,
  "lower_bound": 52.0,
  "upper_bound": 65.0,
  "trend_direction": "rising",
  "forecast_until": "2026-06-10T00:00:00Z"
}
```

**错误响应** (FLY-3-PR-0001):
```json
{
  "error": {
    "code": "FLY-3-PR-0001",
    "message": "Insufficient data points for metric 'cpu_usage': 3 < 10. Please provide at least 10 historical data points for accurate prediction.",
    "context": {
      "metric_name": "cpu_usage",
      "actual": 3,
      "required": 10
    }
  }
}
```

#### GET /api/v1/predictions
获取预测历史

#### GET /api/v1/predictions/{prediction_id}
获取单个预测详情

### 3.2 模型配置

#### GET /api/v1/models
获取可用预测模型列表

```json
{
  "models": [
    {"name": "linear", "description": "线性回归模型"},
    {"name": "exponential", "description": "指数平滑模型"},
    {"name": "moving_average", "description": "移动平均模型"},
    {"name": "weighted_moving_average", "description": "加权移动平均"},
    {"name": "simple_trend", "description": "简单趋势模型"}
  ]
}
```

#### PUT /api/v1/models/{model_name}/config
更新模型配置

---

## 四、趋势分析 API (FLY-3)

### 4.1 趋势卷积

#### POST /api/v1/convolv
执行趋势卷积

**请求体**:
```json
{
  "tech_trends": [
    {
      "trend_id": "tech_ai",
      "score": 85,
      "velocity": 10,
      "keywords": ["AI", "ML"]
    }
  ],
  "market_trends": [
    {
      "trend_id": "market_cloud",
      "score": 72,
      "velocity": 5
    }
  ],
  "behavior_trends": [
    {
      "trend_id": "behavior_remote",
      "score": 65,
      "velocity": 8
    }
  ]
}
```

**响应**:
```json
{
  "patterns": [
    {
      "pattern_id": "pattern_001",
      "name": "AI-Driven Cloud Transformation",
      "description": "AI技术推动云市场增长",
      "source_trends": ["tech_ai", "market_cloud"],
      "intensity": 0.78,
      "confidence": 0.92
    }
  ]
}
```

**警告响应** (FLY-3-TR-0001):
```json
{
  "patterns": [],
  "warnings": [
    {
      "code": "FLY-3-TR-0001",
      "message": "All trend inputs are empty. No patterns can be generated."
    }
  ]
}
```

### 4.2 涌现检测

#### GET /api/v1/patterns
获取涌现模式列表

#### GET /api/v1/patterns/{pattern_id}
获取模式详情

#### GET /api/v1/patterns/{pattern_id}/impact
获取模式影响分析

---

## 五、消息队列 API (FLY-5)

### 5.1 主题管理

#### POST /api/v1/topics
创建主题

**请求体**:
```json
{
  "name": "events.system",
  "partitions": 6,
  "replication_factor": 3,
  "retention_hours": 168
}
```

#### GET /api/v1/topics
获取主题列表

#### DELETE /api/v1/topics/{topic_name}
删除主题

### 5.2 消息发布

#### POST /api/v1/topics/{topic_name}/publish
发布消息

**请求体**:
```json
{
  "key": "event_001",
  "value": {
    "event_type": "alert",
    "severity": "high",
    "message": "System load high"
  },
  "headers": {
    "source": "monitor"
  }
}
```

**响应**:
```json
{
  "message_id": "msg_123456",
  "partition": 2,
  "offset": 1001,
  "timestamp": "2026-06-08T10:30:00Z"
}
```

### 5.3 消息订阅

#### POST /api/v1/topics/{topic_name}/subscribe
创建订阅

**请求体**:
```json
{
  "subscription_id": "sub_alert_handler",
  "consumer_group": "alert_processors",
  "filter": {
    "event_type": "alert"
  },
  "auto_commit": true
}
```

#### GET /api/v1/topics/{topic_name}/messages
消费消息

### 5.4 RPC 调用

#### POST /api/v1/rpc
发起 RPC 调用

**请求体**:
```json
{
  "service": "rule_engine",
  "method": "evaluate",
  "params": {
    "rule_id": "rule_123",
    "context": {}
  },
  "timeout_ms": 5000
}
```

**响应**:
```json
{
  "request_id": "rpc_789",
  "result": {
    "matched": true,
    "actions": [...]
  },
  "execution_time_ms": 15
}
```

---

## 六、工具注册 API (FLY-5)

### 6.1 工具管理

#### POST /api/v1/tools
注册新工具

**请求体**:
```json
{
  "name": "send_email",
  "version": "1.0.0",
  "description": "发送邮件工具",
  "category": "communication",
  "parameters": [
    {
      "name": "to",
      "type": "string",
      "required": true
    },
    {
      "name": "subject",
      "type": "string",
      "required": true
    },
    {
      "name": "body",
      "type": "string",
      "required": true
    }
  ],
  "handler": "modules.tools.email.send"
}
```

#### GET /api/v1/tools
获取工具列表

#### GET /api/v1/tools/{tool_name}
获取工具详情

#### PUT /api/v1/tools/{tool_name}
更新工具

#### DELETE /api/v1/tools/{tool_name}
注销工具

### 6.2 工具执行

#### POST /api/v1/tools/{tool_name}/execute
执行工具

**请求体**:
```json
{
  "params": {
    "to": "user@example.com",
    "subject": "Alert",
    "body": "CPU usage exceeded threshold"
  },
  "async": false
}
```

---

## 七、监控 API

### 7.1 指标查询

#### GET /api/v1/metrics
查询系统指标

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| metrics | string | 指标名称，多个用逗号分隔 |
| start_time | ISO8601 | 开始时间 |
| end_time | ISO8601 | 结束时间 |
| interval | string | 聚合间隔 |

**响应**:
```json
{
  "metrics": [
    {
      "name": "rule_execution_count",
      "values": [
        {"timestamp": "2026-06-08T10:00:00Z", "value": 1250}
      ]
    }
  ]
}
```

### 7.2 告警规则

#### GET /api/v1/alerts/rules
获取告警规则列表

#### POST /api/v1/alerts/rules
创建告警规则

**请求体**:
```json
{
  "name": "high_error_rate",
  "metric": "error_rate",
  "condition": ">",
  "threshold": 0.05,
  "duration_seconds": 300,
  "severity": "critical",
  "channels": ["slack", "email"]
}
```

#### PUT /api/v1/alerts/rules/{rule_id}
更新告警规则

#### DELETE /api/v1/alerts/rules/{rule_id}
删除告警规则

### 7.3 告警历史

#### GET /api/v1/alerts/history
获取告警历史

---

## 八、错误响应格式

所有错误响应遵循统一格式：

```json
{
  "error": {
    "code": "FLY-XXX-XXXX",
    "message": "错误描述",
    "context": {},
    "trace_id": "abc123"
  }
}
```

详细错误码说明请参考 [错误码说明文档](./错误码说明文档.md)。

---

## 九、速率限制

| API 级别 | 限制 | 窗口 |
|----------|------|------|
| 普通 | 100 请求 | 1 分钟 |
| 高级 | 1000 请求 | 1 分钟 |
| 企业 | 10000 请求 | 1 分钟 |

响应头包含速率限制信息：
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1623158400
```

---

**API 版本**: v1  
**联系支持**: support@swarmsfly.com
