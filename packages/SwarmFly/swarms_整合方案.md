# SwarmFly × Swarms 框架整合方案

> **版本**: v1.3  
> **日期**: 2026-04-24  
> **状态**: 方案设计（评审通过）

---

## 一、整合定位

### 1.1 核心定位

**swarms 作为 SwarmFly 的「智能路由增强层」**

> **架构约束**：不引入嵌入模型，采用 SkillOrchestra（LLM推理）+ FLY-2 规则引擎混合路由

```
┌─────────────────────────────────────────────────────────────┐
│                    SwarmFly Controller                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ SubAgentMgr │  │ TeamCollab  │  │   Swarms Router     │ │
│  │             │  │             │  │  ┌───────────────┐  │ │
│  │             │  │             │  │  │SkillOrchestra│  │ │
│  │             │  │             │  │  │ HandoffBridge│  │ │
│  │             │  │             │  │  └───────────────┘  │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────────┐
              │     FLY Framework Layers    │
              │  FLY-0 → FLY-1 → FLY-2     │
              └────────────────────────────┘
```

### 1.2 能力映射

| Swarms 组件 | 对应 SwarmFly 能力 | 增强方向 |
|------------|-------------------|----------|
| SkillOrchestra | FLY-4 技能层 | 技能匹配精度从「类型级」→「原子技能级」 |
| Handoff Engine | TeamCollaboration | 从「消息传递」→「上下文完整交接」 |
| HierarchicalSwarm | SubAgentManager | 从「树形管理」→「Worker-Judge 层级评价」 |

> **说明**：不采用 AgentRouter（基于嵌入的语义路由），改用 SkillOrchestra + FLY-2 规则引擎实现路由

---

## 二、整合架构

### 2.1 整体架构图

```
                    ┌──────────────────────────────────────────┐
                    │          SwarmFlyController              │
                    │  ┌──────────────────────────────────┐   │
                    │  │      Swarms Integration Layer     │   │
                    │  │  ┌────────────┐ ┌─────────────┐ │   │
                    │  │  │SkillRouter │ │HandoffBridge │ │   │
                    │  │  └────────────┘ └─────────────┘ │   │
                    │  └──────────────────────────────────┘   │
                    └──────────────────────────────────────────┘
                               │              │
          ┌────────────────────┼──────────────┘
          │                    │
    ┌─────▼─────┐       ┌─────▼────────┐
    │SkillOrchestra│      │HandoffEngine│
    │  (swarms)  │       │  (swarms)   │
    └─────┬─────┘       └──────┬───────┘
          │                    │
          ▼                    ▼
    ┌─────────────────────────────────────────────────────┐
    │              FLY Framework (v3.2)                   │
    │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐   │
    │  │FLY-0/1  │ │FLY-2    │ │FLY-3/4  │ │FLY-5      │   │
    │  │Mission  │ │Rules    │ │Trend/Skill│ │Tools     │   │
    │  └─────────┘ └─────────┘ └─────────┘ └───────────┘   │
    └─────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
Task Input
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│  1. SkillOrchestra.run()                                  │
│     - LLM 推理任务所需的原子技能                            │
│     - 基于 SkillHandbook 评分                             │
│     - 返回: 最高 competence 的 Agent                      │
└────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│  2. FLY-2 规则引擎验证                                     │
│     - 置信度阈值检查: score >= 0.6                         │
│     - 规则匹配兜底: keyword → Agent mapping                │
│     - 资源仲裁器分配                                       │
│     - 权限检查器授权                                       │
└────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│  3. HandoffBridge (if needed)                             │
│     - 上下文打包                                           │
│     - 交接目标 Agent                                       │
│     - 质量反馈回传                                         │
└────────────────────────────────────────────────────────────┘
    │
    ▼
Result Output
```

---

## 三、路由增强方案

### 3.1 SkillOrchestra 增强 TaskDistributor

**现状问题**:
- TaskDistributor 按 Agent 类型路由，精度不足
- 同一类型 Agent 可能有不同的技能擅长

**整合方案**:

```python
from swarms.structs.agent import Agent
from swarms.structs.skill_orchestra import (
    SkillOrchestra,
    SkillHandbook,
    SkillDefinition,
    AgentProfile,
    AgentSkillProfile,
)

class SwarmsTaskRouter:
    """swarms SkillOrchestra 增强的任务路由 - 无嵌入模型版本"""
    
    def __init__(self, agents: List[Agent], skill_handbook=None):
        self.confidence_threshold = 0.6
        
        # SkillOrchestra 配置
        self.orchestra = SkillOrchestra(
            name="SwarmFly-Router",
            agents=agents,
            skill_handbook=skill_handbook,
            max_loops=3,
            model="gpt-4o",
            competence_weight=0.7,
            cost_weight=0.3,
            top_k_agents=3,
        )
        
    def route_task(self, task: str) -> AgentSelectionResult:
        """技能感知的任务路由"""
        # Step 1: SkillOrchestra.run() 执行 LLM 推理路由
        selected_agent = self.orchestra.run(task)
        
        # Step 2: FLY-2 规则引擎验证
        validated = self.fly2_rule_validation(task, selected_agent)
        
        return validated
    
    def fly2_rule_validation(self, task: str, selected_agent) -> AgentSelectionResult:
        """FLY-2 规则引擎兜底逻辑"""
        
        # 获取 SkillOrchestra 返回的评分
        scores = self.orchestra.get_agent_scores(task) if hasattr(self.orchestra, 'get_agent_scores') else {}
        
        # 规则1: 置信度阈值检查
        best_score = max(scores.values()) if scores else 0
        if best_score < self.confidence_threshold:
            # 降级: 使用规则匹配兜底
            return self.rule_based_fallback(task)
        
        # 规则2: 关键词一致性验证（不覆盖 SkillOrchestra 结果）
        rule_agent = self.keyword_rule_match(task)
        if rule_agent and rule_agent.name != selected_agent.name:
            # 记录不一致日志，供后续分析优化
            logger.warning(f"关键词与SkillOrchestra不一致: 关键词->{rule_agent.name}, LLM->{selected_agent.name}")
        
        # 最终返回 SkillOrchestra 结果
        return AgentSelectionResult(
            agent=selected_agent,
            source="skill_orchestra",
            score=best_score
        )
    
    def rule_based_fallback(self, task: str) -> AgentSelectionResult:
        """关键词规则兜底"""
        keyword_map = {
            "python": "CodeExpert",
            "代码": "CodeExpert",
            "write": "CodeExpert",
            "分析": "DataAnalyst",
            "analyze": "DataAnalyst",
            "文档": "TechWriter",
            "report": "TechWriter",
        }
        
        for keyword, agent_name in keyword_map.items():
            if keyword.lower() in task.lower():
                return AgentSelectionResult(
                    agent=self.get_agent_by_name(agent_name),
                    source="rule_keyword_fallback",
                    score=0.5
                )
        
        # 最终降级: 返回默认Agent
        return AgentSelectionResult(
            agent=self.default_agent,
            source="rule_default",
            score=0.3
        )
```

**评分公式**:
```
score = 0.7 × competence_i + 0.3 × normalized_cost_i
```
其中：
- `competence_i`: Agent 在该技能上的能力评分 (0-1)
- `normalized_cost_i`: Agent 执行成本归一化值 (0-1，越低越好)
- 最终得分 0-1，低于 0.6 触发规则兜底

### 3.2 Bridge 组件简化

**架构调整**: 简化为两层 Bridge，删除依赖嵌入模型的 AgentBridge

| Bridge 组件 | 职责 | 依赖 |
|------------|------|------|
| SkillRouter | SkillOrchestra + FLY-2 规则引擎 | LLM API |
| HandoffBridge | 上下文完整交接 | 无外部依赖 |

---

## 四、技能路由增强

### 4.1 技能体系映射

| FLY-4 技能层 | SkillOrchestra 原子技能 |
|-------------|------------------------|
| 代码生成 | `python_coding`, `javascript_coding` |
| 数据分析 | `data_analysis`, `visualization` |
| 文档撰写 | `technical_writing`, `creative_writing` |
| 搜索研究 | `web_search`, `information_retrieval` |

### 4.2 Skill Handbook 初始化

```python
from swarms.structs.agent import Agent
from swarms.structs.skill_orchestra import (
    SkillOrchestra,
    SkillHandbook,
    SkillDefinition,
    AgentProfile,
    AgentSkillProfile,
)

def build_fly4_skill_handbook(agents: List[Agent]) -> SkillHandbook:
    """从 FLY-4 技能定义构建 Skill Handbook"""
    
    # 1. 收集 FLY-4 技能定义
    fly4_skills = load_fly4_skill_definitions()
    
    # 2. 转换为 SkillDefinition
    skill_defs = [
        SkillDefinition(
            name=skill.id,
            description=skill.description,
            category=skill.category
        ) for skill in fly4_skills
    ]
    
    # 3. 为每个 Agent 构建 AgentProfile
    agent_profiles = [
        AgentProfile(
            agent_name=agent.name,
            skill_profiles=[
                AgentSkillProfile(
                    skill_name=skill.id,
                    competence=skill.competence,  # 从 FLY-4 获取
                    cost=skill.estimated_cost,
                ) for skill in agent.capabilities
            ]
        ) for agent in agents
    ]
    
    # 4. 构建 SkillHandbook
    return SkillHandbook(
        skills=skill_defs,
        agent_profiles=agent_profiles
    )
```

---

## 五、Handoff 机制整合

### 5.1 整合定位

**SwarmFly TeamCollaboration + Swarms Handoff = 完整交接**

```
现有 SwarmFly:
┌─────────────┐     Message      ┌─────────────┐
│  Agent A    │ ──────────────▶ │  Agent B    │
└─────────────┘                 └─────────────┘
      │                                ▲
      │         context_variables     │
      └────────────────────────────────┘
              (部分上下文丢失)

整合后 Swarms:
┌─────────────┐    Handoff     ┌─────────────┐
│  Agent A    │ ══════════════▶ │  Agent B    │
└─────────────┘  (完整上下文)    └─────────────┘
      │                                ▲
      │         execution_history      │
      │         intermediate_results    │
      └────────────────────────────────┘
              (完整上下文保留)
```

### 5.2 Handoff 接口设计

```python
from swarms.structs.agent import Agent

class HandoffBridge:
    """SwarmFly ↔ Swarms Handoff 桥接"""
    
    def __init__(self, fly_controller: SwarmFlyController):
        self.controller = fly_controller
        
    def create_transfer_function(self, from_agent: Agent, target_agent: Agent):
        """创建交接函数"""
        def transfer_to(context_variables: dict):
            # 打包完整上下文
            ctx = {
                **context_variables,
                "handoff_from": from_agent.name,
                "execution_history": self.controller.get_history(),
                "intermediate_results": self.controller.get_results(),
                "session_state": self.controller.get_state()
            }
            # 返回目标 Agent 实例
            return target_agent
        return transfer_to
    
    def enable_bidirectional_handoff(self, agents: List[Agent]):
        """启用双向交接"""
        triage_agent = self.controller.get_triage_agent()
        for agent in agents:
            # 添加返回主控的交接函数
            agent.functions.append(
                self.create_transfer_function(agent, triage_agent)
            )
```

### 5.3 交接场景

| 场景 | 触发条件 | 交接目标 |
|-----|---------|---------|
| 技能不匹配 | SkillOrchestra 返回 confidence < 0.6 | 专家 Agent |
| 边界溢出 | 任务超出当前 Agent 权限 | 权限更高的 Agent |
| 协作需求 | 任务需要多 Agent 协作 | TeamLeader Agent |
| 异常恢复 | 执行失败重试 | 回退到基础 Agent |

---

## 六、整合步骤

### Phase 1: 基础集成 (P0)

**目标**: 最小可用整合，SkillOrchestra 接入

| 步骤 | 内容 | 产出 |
|-----|------|-----|
| 1.1 | 安装 swarms 包 | `pip install swarms` |
| 1.2 | 创建 SwarmsBridge 基类 | `swarms_bridge.py` |
| 1.3 | 集成 SkillOrchestra | `SkillOrchestra` → TaskDistributor |
| 1.4 | 技能 Handbook 初始化 | 从 FLY-4 生成 handbook |
| 1.5 | 基础路由测试 | 单元测试用例 |

**验收标准**:

| 指标 | 目标值 | 判定标准 | 测试方法 |
|-----|--------|---------|---------|
| 路由正确率 | >= 85% | 路由Agent与专家预设Agent一致 | 100条测试任务，人工标注预期Agent后验证 |
| 响应延迟 | P95 < 3s | 单次路由耗时P95分位 | 统计100次路由的P95延迟 |
| 置信度阈值 | score >= 0.6 | 低于阈值触发规则兜底 | 注入低置信度任务验证触发 |
| 规则兜底 | 100% 触发 | 无技能匹配时走fallback | 测试未定义技能的fallback |

**回滚策略**:
- Phase 1 失败 → 回退到原有 TaskDistributor
- Feature Flag 控制: `SWARMFLY_SKILL_ORCHESTRA_ENABLED=false`

**测试用例设计**:

```python
def test_skill_orchestra_routing():
    """测试 SkillOrchestra 路由正确性"""
    router = SwarmsTaskRouter(agents=[code_agent, writer_agent, analyst_agent])
    
    # 场景1: 代码任务
    result = router.route_task("Write a Python function to parse JSON")
    assert result.agent.name == "CodeExpert"
    assert result.score >= 0.6
    
    # 场景2: 文档任务
    result = router.route_task("Generate a technical documentation")
    assert result.agent.name == "TechWriter"
    
    # 场景3: 低于阈值时的兜底
    result = router.route_task("Unknown task type xyz")
    assert result.source in ["rule_keyword_fallback", "rule_default"]

def test_confidence_threshold():
    """测试置信度阈值触发"""
    router = SwarmsTaskRouter(agents=low_confidence_agents)
    
    result = router.route_task("Complex ambiguous task")
    # 低于0.6时应触发规则兜底
    if result.score < 0.6:
        assert result.source in ["rule_keyword", "rule_keyword_fallback"]
```

### Phase 2: Handoff 机制 (P1)

**目标**: 完整上下文交接

| 步骤 | 内容 | 产出 |
|-----|------|-----|
| 2.1 | HandoffBridge 实现 | Swarms Handoff API |
| 2.2 | 上下文打包器 | 完整状态序列化 |
| 2.3 | 交接触发器 | 自动/手动切换 |
| 2.4 | 交接审计 | 记录交接日志 |

**验收标准**:

| 指标 | 目标值 | 判定标准 | 测试方法 |
|-----|--------|---------|---------|
| 上下文完整率 | 100% | 交接后Agent可访问全部历史状态 | 验证handoff_context包含history/results/state |
| 交接延迟 | < 500ms | 上下文打包+传输耗时 | 测量10次交接取平均 |
| 交接日志 | 100% 记录 | 每次交接产生审计记录 | 检查审计表记录数与交接次数一致 |

**回滚策略**:
- Phase 2 失败 → 禁用 HandoffBridge，回退到消息传递
- Feature Flag: `SWARMFLY_HANDOFF_BRIDGE_ENABLED=false`

### Phase 3: 层级 Swarm (P2)

**目标**: HierarchicalSwarm 深度集成

| 步骤 | 内容 | 产出 |
|-----|------|-----|
| 3.1 | Worker-Judge 架构 | 替换 SubAgentManager |
| 3.2 | 并行执行 | ThreadPoolExecutor |
| 3.3 | 评价体系 | 五维评分报告 |

**验收标准**:

| 指标 | 目标值 | 判定标准 | 测试方法 |
|-----|--------|---------|---------|
| Judge 评分准确率 | >= 80% | Judge评分与人工评审一致性 | 随机抽取20个任务对比评分 |
| 并行效率 | 提升 >= 30% | 并行vs串行时间差/串行时间 | 对比串行/并行执行时间 |
| Worker 正确执行率 | >= 95% | Worker执行无异常/超时 | 统计100次任务执行成功率 |

**回滚策略**:
- Phase 3 失败 → 回退到原 SubAgentManager
- Feature Flag: `SWARMFLY_HIERARCHICAL_SWARM_ENABLED=false`

---

## 七、优先级与风险

### 7.1 优先级矩阵

| 功能 | 价值 | 难度 | 优先级 | 嵌入依赖 |
|-----|------|------|--------|---------|
| SkillOrchestra 路由 | 高 | 中 | **P0** | ❌ 无 |
| Handoff 机制 | 中 | 中 | P1 | ❌ 无 |
| HierarchicalSwarm | 中 | 高 | P2 | ❌ 无 |

### 7.2 风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|-----|------|------|---------|
| LLM 路由幻觉 | 高 | 中 | 规则引擎兜底 + 置信度阈值(0.6) |
| 上下文膨胀 | 中 | 高 | 交接时智能压缩 + 关键信息提取 |
| 技能定义不一致 | 中 | 中 | Handbook 标准化 + 版本管理 |
| swarms 版本兼容 | 低 | 低 | 锁定版本 + 接口抽象层 |

### 7.3 依赖关系

```
Phase 1 (SkillOrchestra) ──┐
                           │
Phase 2 (Handoff) ────────┤
                           │
Phase 3 (HierarchicalSwarm)─┘
```

> **注意**: 各 Phase 可独立回退，通过 Feature Flag 控制

---

## 八、接口规范

### 8.1 SwarmsBridge 接口

```python
class SwarmsBridge(ABC):
    """swarms 集成基类"""
    
    @abstractmethod
    def initialize(self) -> None:
        """初始化 swarms 组件"""
        pass
    
    @abstractmethod
    def route_task(self, task: str, context: dict) -> AgentSelectionResult:
        """任务路由 - SkillOrchestra + FLY-2 规则引擎"""
        pass
    
    @abstractmethod
    def execute_handoff(self, from_agent: Agent, to_agent: Agent, 
                        context: dict) -> HandoffResult:
        """执行交接"""
        pass
    
    @abstractmethod
    def get_routing_stats(self) -> RoutingStats:
        """获取路由统计"""
        pass
    
    @abstractmethod
    def set_confidence_threshold(self, threshold: float) -> None:
        """设置置信度阈值"""
        pass
```

### 8.2 配置 schema

```yaml
# swarms_config.yaml
swarms:
  version: ">=1.0.0"
  
  skill_orchestra:
    enabled: true
    model: "gpt-4o"
    max_loops: 3
    competence_weight: 0.7
    cost_weight: 0.3
    confidence_threshold: 0.6
    rule_fallback_enabled: true
    
  handoff:
    enabled: true
    context_compression: true
    max_context_tokens: 8000
    
  hierarchical_swarm:
    enabled: false
    judge_enabled: true
    parallel_workers: 4
```

---

## 九、结论

### 9.1 整合价值

| 维度 | 现状 | 整合后 |
|-----|------|--------|
| 技能匹配精度 | Agent 类型级 | 原子技能级 |
| 路由策略 | 纯规则 | LLM推理 + 规则混合 + 置信度阈值 |
| 交接质量 | 部分上下文 | 完整上下文 |
| 执行评价 | 无 | 五维 Judge 评分（Phase 3） |

### 9.2 实施建议

1. **优先 Phase 1**: SkillOrchestra 投入产出比最高
2. **保持 FLY 完整性**: swarms 作为增强而非替代
3. **渐进式落地**: 每 Phase 独立可用、独立回退
4. **监控路由质量**: 建立 routing metrics 基线
5. **避免嵌入依赖**: 坚持 SkillOrchestra + 规则引擎方案

---

## 附录：修复清单

### v1.2 → v1.3 修复记录

| 问题 | 位置 | 问题描述 | 修复内容 |
|-----|------|---------|---------|
| 1 | 第400行 | 测试用例标题残留FIX标记 | 删除 `[FIX-4]` |
| 2 | 第606行 | 附录FIX-8日期未同步 | 附录日期已同步为 2026-04-24 |
| 3 | 第3.1节 | 关键词规则会覆盖SkillOrchestra结果 | 改为一致性验证日志，不覆盖主路由 |
| 4 | 第219行 | 评分公式除以权重和(1.0)无意义 | 简化为直接加权求和，明确参数定义 |

### 完整修复清单

| 修复编号 | 位置 | 问题 | 修复内容 |
|---------|------|------|---------|
| FIX-1 | 全文档 | SkillOrchestra API 错误 | 使用 `run()` 替代 `infer_task_skills()` |
| FIX-2 | 第140/292/354行 | Import 语句错误 | `from swarm import` → `from swarms.structs.agent import Agent` |
| FIX-3 | 第3.1节 | 置信度阈值缺失 | 添加 `confidence_threshold=0.6` 及规则引擎兜底逻辑 |
| FIX-4 | 第六章 | Phase 验收标准缺失 | 添加验收指标、测试方法、测试用例 |
| FIX-5 | 第二章 | Bridge 组件冗余 | 删除 AgentBridge，简化为 SkillRouter + HandoffBridge |
| FIX-6 | 第八章 | 嵌入模型配置残留 | 注释掉 AgentRouter 配置，标注不使用嵌入模型 |
| FIX-7 | 第六章 | 回滚计划缺失 | 为每个 Phase 添加 Feature Flag 和降级策略 |
| FIX-8 | 文档头部 | 日期错误 | 更新为 2026-04-24 |

---

**文档状态**: ✅ 方案评审通过  
**版本**: v1.3  
**下一步**: Phase 1 详细设计与实现
