# SwarmFly API 版本策略

> **文档版本**: v1.0
> **更新日期**: 2026-04-24
> **适用范围**: SwarmFly 所有对外API接口

---

## 一、版本策略概述

### 1.1 版本策略原则

1. **向前兼容**: API v{N} 至少维护到 v{N+1} 发布后6个月
2. **语义化版本**: 主版本号.次版本号.修订号 (MAJOR.MINOR.PATCH)
3. **灰度发布**: 新版本先小比例流量验证，再全量推送
4. **优雅降级**: 旧版本客户端可继续使用，直到明确废弃通知

### 1.2 版本生命周期

```
废弃期 (6个月) → 维护期 (12个月) → 当前稳定版 → 未来版本
     ↓               ↓              ↓            ↓
  不再接受新请求   仅修复Bug      全面支持      规划中
```

---

## 二、版本路由设计

### 2.1 URL版本方案

```python
# API版本路由配置
API_VERSION_ROUTES = {
    # 稳定版本
    "v1": {
        "status": "deprecated",  # 即将废弃
        "sunset_date": "2026-12-31",
        "migration_guide": "/docs/migration/v1-to-v2",
        "rate_limit": "1000/min"
    },
    "v2": {
        "status": "current",  # 当前稳定版
        "release_date": "2026-01-01",
        "rate_limit": "5000/min",
        "features": ["趋势预测", "涌现检测", "自适应"]
    },
    "v3": {
        "status": "beta",  # Beta测试版
        "release_date": "2026-06-01",
        "beta_end_date": "2026-09-01",
        "rate_limit": "100/min"
    }
}
```

### 2.2 请求示例

```http
# 使用v2版本
GET /api/v2/rules HTTP/1.1
Host: api.swarmfly.example.com
Authorization: Bearer {token}

# 使用v3 Beta版本
GET /api/v3/rules HTTP/1.1
Host: api.swarmfly.example.com
X-API-Key: {beta_key}
```

### 2.3 版本响应头

```http
HTTP/1.1 200 OK
Content-Type: application/json
API-Version: v2
API-Status: current
API-Sunset-Date: 2026-12-31
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4999
```

---

## 三、接口契约管理

### 3.1 接口变更类型

| 变更类型 | MAJOR | MINOR | PATCH | 示例 |
|----------|-------|-------|-------|------|
| 新增API | - | ✓ | - | 新增 `/v2/batch-predict` |
| 新增可选参数 | - | ✓ | - | `GET /rules?tag=` |
| 新增响应字段 | - | ✓ | - | 返回值增加 `metadata` |
| 修改参数名 | ✓ | - | - | `user_id` → `owner_id` |
| 删除端点 | ✓ | - | - | 删除 `/v1/legacy` |
| 修改返回值结构 | ✓ | - | - | 数组 → 分页对象 |
| Bug修复 | - | - | ✓ | 修正字段类型 |

### 3.2 向后兼容示例

```python
# ✅ 兼容变更: 添加新的可选字段
class RuleResponseV2:
    """V2版本响应"""
    rule_id: str
    name: str
    status: str
    # V1已有字段保持不变
    
    # V2新增可选字段
    tags: Optional[List[str]] = None
    metadata: Optional[Dict] = None

# ❌ 不兼容变更: 修改字段类型
# 旧: age: int
# 新: age: str  # 不允许!
```

### 3.3 接口契约定义

```python
# 接口契约模板
INTERFACE_CONTRACT_TEMPLATE = """
## {endpoint_name}

### 基本信息
- **版本**: {version}
- **路径**: {path}
- **方法**: {method}
- **状态**: {status}

### 请求参数
| 参数名 | 类型 | 必填 | 说明 | 起始版本 |
|--------|------|------|------|----------|
{request_params}

### 响应参数
| 参数名 | 类型 | 说明 | 起始版本 |
|--------|------|------|----------|
{response_params}

### 错误码
| 错误码 | HTTP状态 | 说明 | 起始版本 |
|--------|----------|------|----------|
{error_codes}

### 变更历史
{change_history}
"""
```

---

## 四、版本迁移指南

### 4.1 v1 到 v2 迁移

```python
# V1 旧代码
response = requests.get("/api/v1/rules", params={"page": 1})

# V2 新代码
response = requests.get(
    "/api/v2/rules",
    params={
        "page": 1,
        "page_size": 20,
        "include_metadata": True  # 新参数
    }
)

# V2 响应结构变更
# 旧: {"rules": [...], "total": 100}
# 新: {"data": {"rules": [...]}, "pagination": {...}}
```

### 4.2 迁移自动化工具

```python
class APIVersionMigrationTool:
    """API版本迁移工具"""
    
    def scan_legacy_usage(self, codebase_path: str) -> Dict:
        """扫描代码中的v1 API调用"""
        # 查找所有 /api/v1/ 调用
        pass
    
    def generate_migration_plan(self, usage_report: Dict) -> MigrationPlan:
        """生成迁移计划"""
        # 统计需要修改的位置
        # 评估迁移风险
        # 生成修改建议
        pass
    
    def auto_migrate(self, file_path: str, target_version: str) -> bool:
        """自动迁移单个文件"""
        # 替换URL路径
        # 调整参数结构
        # 更新响应解析逻辑
        pass
```

---

## 五、版本废弃管理

### 5.1 废弃通知流程

```
┌────────────────────────────────────────────────────────────┐
│                    版本废弃流程                              │
└────────────────────────────────────────────────────────────┘

阶段1: 废弃公告 (T-6个月)
├─ 发送废弃通知邮件
├─ 在API文档添加废弃警告
└─ 返回 DeprecationWarning 响应头

阶段2: 维护终止 (T-3个月)
├─ 停止功能更新
├─ 仅修复安全漏洞
└─ 返回 Sunset 响应头

阶段3: 正式关闭 (T-0)
├─ 返回 410 Gone
└─ 重定向到最新版本文档
```

### 5.2 废弃响应示例

```http
HTTP/1.1 200 OK
Warning: 299 - "This API version will be deprecated on 2026-12-31"
API-Deprecation-Date: 2026-12-31
API-Sunset-Date: 2026-12-31
API-Migration-Guide: https://docs.swarmfly.com/migration/v1-v2

# T-0之后
HTTP/1.1 410 Gone
Content-Type: application/json
{
  "error": {
    "code": "API_VERSION_DEPRECATED",
    "message": "API v1 has been deprecated as of 2026-12-31",
    "migration_url": "https://docs.swarmfly.com/migration/v1-v2",
    "current_version": "v2"
  }
}
```

---

## 六、版本回滚策略

### 6.1 回滚触发条件

#### 6.1.1 自动触发条件

| 指标类型 | 阈值 | 时间窗口 | 连续触发次数 |
|---------|------|---------|-------------|
| API错误率 | > 5% | 5分钟 | 3次 |
| API错误率（严重） | > 15% | 1分钟 | 1次 |
| P99响应时间 | > 2000ms | 5分钟 | 3次 |
| P95响应时间 | > 1000ms | 5分钟 | 5次 |
| HTTP 5xx错误率 | > 10% | 5分钟 | 2次 |
| 可用性 | < 99.0% | 10分钟 | 1次 |

#### 6.1.2 手动触发条件

- 出现数据一致性问题
- 核心功能不可用
- 安全漏洞或合规问题
- 业务重大损失风险

#### 6.1.3 监控配置示例

```python
# 回滚触发配置
ROLLBACK_TRIGGER_CONFIG = {
    "auto_rollback": {
        "enabled": True,
        "evaluation_interval": 60,  # 秒
        "conditions": {
            "error_rate": {
                "threshold": 0.05,
                "window": 300,
                "consecutive": 3,
                "severity": "high"
            },
            "response_time_p99": {
                "threshold": 2000,
                "window": 300,
                "consecutive": 3,
                "severity": "medium"
            },
            "http_5xx_rate": {
                "threshold": 0.10,
                "window": 300,
                "consecutive": 2,
                "severity": "critical"
            }
        }
    },
    "alert_channels": ["slack", "pagerduty", "email"],
    "rollback_notification": True
}
```

### 6.2 回滚操作流程

#### 6.2.1 自动回滚流程

```
┌────────────────────────────────────────────────────────────┐
│                    自动回滚流程                             │
└────────────────────────────────────────────────────────────┘

[1] 监控系统检测异常
         ↓
[2] 触发条件满足 → 发送告警 → 开始自动回滚
         ↓
[3] 记录当前版本快照（用于问题排查）
         ↓
[4] 切换流量到上一稳定版本
   - 灰度流量: 10% → 25% → 50% → 100%
   - 健康检查: 每阶段等待30秒
         ↓
[5] 验证回滚结果
   - 检查错误率是否恢复
   - 检查响应时间是否正常
         ↓
[6] 回滚成功 → 发送通知 → 进入问题排查
   或
   回滚失败 → 升级告警 → 人工介入
```

#### 6.2.2 手动回滚流程

```python
# 手动回滚命令示例
class APIVersionRollback:
    """API版本手动回滚"""
    
    async def execute_rollback(
        self,
        target_version: str,
        reason: str,
        initiated_by: str
    ) -> RollbackResult:
        """执行手动回滚"""
        rollback_id = self._generate_rollback_id()
        
        # 1. 创建回滚快照
        snapshot = await self._create_snapshot(rollback_id)
        
        # 2. 验证目标版本可用性
        if not await self._verify_version_available(target_version):
            raise RollbackError(f"Target version {target_version} not available")
        
        # 3. 通知相关团队
        await self._notify_rollback_start(rollback_id, target_version, reason)
        
        # 4. 执行流量切换
        await self._switch_traffic(target_version, gradual=True)
        
        # 5. 验证回滚效果
        health_check = await self._verify_rollback_health()
        
        # 6. 记录回滚日志
        await self._log_rollback_execution(rollback_id, snapshot, health_check)
        
        return RollbackResult(
            rollback_id=rollback_id,
            success=health_check.is_healthy,
            version_switched=target_version,
            duration_seconds=health_check.duration
        )
    
    async def _switch_traffic(
        self,
        target_version: str,
        gradual: bool = True
    ):
        """流量切换"""
        if gradual:
            # 渐进式切换: 10% → 25% → 50% → 100%
            stages = [0.10, 0.25, 0.50, 1.0]
            for stage in stages:
                await self._update_router_weight(target_version, stage)
                await asyncio.sleep(30)  # 每阶段等待30秒
                if not await self._health_check():
                    raise RollbackError(f"Health check failed at {stage*100}%")
        else:
            # 直接切换
            await self._update_router_weight(target_version, 1.0)
```

#### 6.2.3 回滚决策树

```
                    检测到异常
                        │
                        ▼
            ┌─ 严重程度 > 严重阈值? ─┐
            │                       │
           是                        否
            │                        │
            ▼                        ▼
    ┌─ 自动回滚 ─┐          ┌─ 发送告警等待确认 ─┐
    │            │          │                   │
    │  记录日志  │          │  5分钟内无响应? ─┐ │
    │  切换流量  │          │                 │ │
    │  验证结果  │          │ 否              是│
    │  通知团队  │          │                 │ │
    └────────────┘          │  ↓              ↓ │
                            │ 进入自动回滚流程  │
                            └───────────────────┘
```

### 6.3 回滚SLA要求

#### 6.3.1 响应时间要求

| 回滚类型 | 检测到触发条件 | 完成自动回滚 | 总恢复时间(RTO) |
|---------|---------------|-------------|----------------|
| P0 - 严重故障 | < 1分钟 | < 5分钟 | < 10分钟 |
| P1 - 高优先级 | < 3分钟 | < 10分钟 | < 30分钟 |
| P2 - 中优先级 | < 5分钟 | < 30分钟 | < 60分钟 |
| P3 - 低优先级 | 人工判断 | 手动执行 | 人工评估 |

#### 6.3.2 SLA保证机制

```python
# SLA保证配置
SLA_CONFIG = {
    "p0_critical": {
        "detection_window": 60,  # 秒
        "auto_rollback_window": 300,  # 秒
        "max_rto": 600,  # 秒
        "escalation": "immediate",
        "required_approvers": 0  # 无需审批
    },
    "p1_high": {
        "detection_window": 180,
        "auto_rollback_window": 600,
        "max_rto": 1800,
        "escalation": "5min",
        "required_approvers": 1
    },
    "p2_medium": {
        "detection_window": 300,
        "auto_rollback_window": 1800,
        "max_rto": 3600,
        "escalation": "15min",
        "required_approvers": 2
    }
}

# 监控SLA达成率
ROLLBACK_SLA_METRICS = {
    "detection_time_p99": 45,      # 秒
    "rollback_time_p95": 180,       # 秒
    "total_recovery_p99": 420,      # 秒
    "rollback_success_rate": 0.998,
    "false_positive_rate": 0.001
}
```

### 6.4 数据回滚处理

#### 6.4.1 数据一致性保证

```python
# 数据回滚策略
class DataRollbackStrategy:
    """数据回滚策略"""
    
    # 数据状态分类
    DATA_CATEGORIES = {
        "immutable": {
            # 不可变数据：不支持回滚
            "audit_logs": {"rollback_support": False},
            "metrics_data": {"rollback_support": False},
            "execution_history": {"rollback_support": False}
        },
        "critical": {
            # 关键数据：支持精确回滚
            "user_rules": {
                "rollback_support": True,
                "retention_days": 90,
                "backup_frequency": "hourly"
            },
            "system_config": {
                "rollback_support": True,
                "retention_days": 180,
                "backup_frequency": "realtime"
            }
        },
        "operational": {
            # 操作数据：支持最终一致性回滚
            "cache_data": {
                "rollback_support": True,
                "strategy": "invalidate",
                "recovery": "rebuild"
            },
            "derived_metrics": {
                "rollback_support": True,
                "strategy": "recalculate",
                "recovery": "async_rebuild"
            }
        }
    }
    
    async def execute_data_rollback(
        self,
        scope: DataRollbackScope,
        target_time: datetime,
        dry_run: bool = True
    ) -> DataRollbackResult:
        """执行数据回滚"""
        # 1. 评估数据影响范围
        affected_data = await self._assess_affected_data(scope, target_time)
        
        # 2. 验证回滚可行性
        feasibility = await self._verify_rollback_feasibility(affected_data)
        
        # 3. 准备回滚计划
        rollback_plan = self._generate_rollback_plan(affected_data, feasibility)
        
        if dry_run:
            return DataRollbackResult(
                status="dry_run_complete",
                plan=rollback_plan,
                warnings=feasibility.warnings
            )
        
        # 4. 执行回滚
        execution_result = await self._execute_plan(rollback_plan)
        
        # 5. 验证数据一致性
        consistency_check = await self._verify_data_consistency()
        
        return DataRollbackResult(
            status="completed",
            plan=rollback_plan,
            execution=execution_result,
            consistency=consistency_check
        )
```

#### 6.4.2 回滚数据恢复点

```
┌────────────────────────────────────────────────────────────┐
│                    回滚恢复点策略                           │
└────────────────────────────────────────────────────────────┘

时间轴 ──────────────────────────────────────────────────────→

[备份点1]  [备份点2]  [备份点3]  [当前版本]  ← 回滚目标
    ↑                      ↓
    └────── 可以回滚 ─────┘
    
RPO (恢复点目标): 根据数据类型不同
├── 关键配置: 实时同步 → RPO ≈ 0
├── 业务规则: 每小时备份 → RPO ≤ 1小时
└── 监控数据: 每天备份 → RPO ≤ 24小时
```

#### 6.4.3 数据回滚操作矩阵

| 数据类型 | 支持回滚 | 回滚方式 | 回滚窗口 | 注意事项 |
|---------|---------|---------|---------|---------|
| 用户规则配置 | ✅ | 快照恢复 | 90天内 | 需验证关联性 |
| 系统配置 | ✅ | 精确恢复 | 180天内 | 需重启服务 |
| 告警规则 | ✅ | 快照恢复 | 90天内 | 需重新启用 |
| 执行日志 | ❌ | 不可回滚 | - | 保留审计 |
| 性能指标 | ❌ | 不可回滚 | - | 重新计算 |
| 缓存数据 | ✅ | 失效重建 | 实时 | 自动重建 |

---

## 七、SDK版本管理

### 7.1 SDK版本策略

| SDK版本 | 支持API版本 | 生命周期 | 维护状态 |
|---------|------------|----------|----------|
| SDK v1.x | API v1 | 2024-01 ~ 2026-12 | 仅安全修复 |
| SDK v2.x | API v2 | 2026-01 ~ 2028-01 | 全面支持 |
| SDK v3.x | API v3 (Beta) | 2026-06 ~ | Beta测试 |

### 7.2 SDK版本检测

```python
# SDK版本检测示例
from swarmfly import SwarmFlyClient

client = SwarmFlyClient(api_key="xxx")

# 获取客户端版本信息
client_info = client.get_client_info()
# {
#     "sdk_version": "2.5.0",
#     "supported_api_versions": ["v1", "v2"],
#     "recommended_api_version": "v2",
#     "deprecation_warnings": [...]
# }

# 设置API版本
client.set_api_version("v2")  # 默认使用推荐版本
```

---

**文档维护人**: SwarmFly 架构团队
**下次审查日期**: 2026-07-15
