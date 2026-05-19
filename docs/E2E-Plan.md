# ZenAgent 端到端测试计划

**版本**: 1.0
**创建日期**: 2026-05-18
**最后更新**: 2026-05-19
**状态**: ✅ 已完成

---

## 项目状态总览

### 全部完成

- ✅ **Runtime (L1)**: 43 tests passed - 运行时层（事件总线、任务队列、上下文管理）
- ✅ **MetaSoul (L3)**: 100+ tests passed - 个体灵魂引擎（记忆、学习、人格、反思）
- ✅ **SwarmFly (L4)**: 153 tests passed - 群体层（生命周期、协作、共享内存、团队）
- ✅ **ZenAgent (L2)**: 11 tests passed - 智能体层（MCP、Hooks、Awakening、Collaboration）
- ✅ **LLMInfra (L0)**: Provider 重试、Token 预算、响应校验 - LLM 基础设施层
- ✅ **Phase 1 E2E**: 27 tests - Agent 创建、任务分发、事件总线
- ✅ **Phase 2 E2E**: 57 tests - 完整任务执行、团队协作、Agent 进化
- ✅ **Phase 3 E2E**: 11 tests - ZenAgent + LLMInfra + MetaSoul 联动
- ✅ **Phase 4 CI/CD**: 149 tests - 分阶段 E2E 流水线
- ✅ **Phase 5 真实 LLM**: 11 pass + 6 skip - ModelNexus 端到端验证
- **总计: 511 passed, 6 skipped, 0 failures**

---

## 一、测试架构设计

### 1.1 五层测试金字塔

```
┌─────────────────────────────────────────────────────────────────┐
│                    完全真实 E2E 测试 (Phase 3)                   │
│            ┌─────────────────────────────────────────┐          │
│            │  用户输入 → Agent思考 → 工具调用 → 结果输出  │          │
│            │  ↓ 真实 LLM 调用 ↓ 真实协作 ↓ 真实反馈    │          │
│            └─────────────────────────────────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│                    场景化集成测试 (Phase 2)                       │
│         ┌──────────────┐  ┌──────────────┐  ┌───────────┐     │
│         │  完整任务执行  │  │  多Agent协作  │  │  进化学习  │     │
│         └──────────────┘  └──────────────┘  └───────────┘     │
├─────────────────────────────────────────────────────────────────┤
│                    主线流程测试 (Phase 1)                        │
│    ┌────────────┐  ┌───────────────┐  ┌──────────────────┐    │
│    │ Agent创建  │  │  任务分发协作  │  │  事件总线/队列   │    │
│    └────────────┘  └───────────────┘  └──────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                    单元测试 (已完成)                              │
│    Runtime 43 + SoulTeam 100 + SwarmFly 153 + ZenAgent 11      │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 测试环境配置

| 环境类型 | 说明 | 依赖 | 适用阶段 |
|---------|------|------|---------|
| **Mock 环境** | 所有 LLM 调用使用 Mock，无外部依赖 | Python + pytest | Phase 1, 2 |
| **混合环境** | ModelNexus 网关 + Mock Provider | Python + Redis | Phase 2 |
| **真实环境** | ModelNexus + 真实 LLM Provider | Docker + Redis + API Key | Phase 3 |

---

## 二、Phase 1: 主线流程测试

**目标**: 验证核心工作流程的正确性，不依赖真实 LLM

### 2.1 Agent 创建与初始化流程

**测试文件**: `tests/e2e/test_phase1_agent_lifecycle.py`

| 测试用例 | 优先级 | 状态 | 覆盖模块 |
|---------|--------|------|---------|
| T1.1 Agent 完整注册流程 | P0 | 📋 | MCP Protocol + Registry |
| T1.2 生命周期状态转换 | P0 | 📋 | SwarmFly Lifecycle |
| T1.3 人格系统初始化 | P0 | 📋 | SoulTeam Personality |
| T1.4 记忆系统初始化 | P0 | 📋 | MetaSoul Memory |
| T1.5 Hook 系统正确触发 | P1 | 📋 | ZenAgent Hooks |

**测试流程**:
```
1. 创建 Agent 配置
2. 注册到 MCP Registry
3. 初始化 SoulTeam (人格+记忆)
4. 启动 SwarmFly 生命周期管理
5. 验证所有组件状态正确
6. 优雅关闭 Agent
```

### 2.2 任务分发与协作流程

**测试文件**: `tests/e2e/test_phase1_task_dispatch.py`

| 测试用例 | 优先级 | 状态 | 覆盖模块 |
|---------|--------|------|---------|
| T2.1 单任务创建 → 分发 → 执行 → 完成 | P0 | 📋 | SwarmFly Collaboration |
| T2.2 多 Agent 负载均衡分配 | P0 | 📋 | LoadBalancer |
| T2.3 任务优先级排序 | P1 | 📋 | TaskDispatcher |
| T2.4 任务回调机制验证 | P1 | 📋 | Collaboration Engine |

### 2.3 事件总线与消息队列

**测试文件**: `tests/e2e/test_phase1_event_bus.py`

| 测试用例 | 优先级 | 状态 | 覆盖模块 |
|---------|--------|------|---------|
| T3.1 事件发布 → 订阅 → 接收完整链路 | P0 | 📋 | Runtime EventBus |
| T3.2 RPC 调用请求 → 响应流程 | P0 | 📋 | Runtime MessageQueue |
| T3.3 消息持久化与死信队列 | P1 | 📋 | SwarmFly MessageQueue |

---

## 三、Phase 2: 场景化集成测试

**目标**: 验证关键应用场景的端到端正确性，可使用 Mock LLM

### 3.1 完整任务执行场景

**测试文件**: `tests/e2e/test_phase2_full_task.py`

| 测试用例 | 优先级 | 状态 | 覆盖模块 |
|---------|--------|------|---------|
| T4.1 用户输入 → 任务规划 → 执行 → 结果反馈 | P0 | 📋 | 全链路 |
| T4.2 上下文管理与记忆写入 | P0 | 📋 | Runtime Context + SoulTeam Memory |
| T4.3 Agent 觉醒与能力启用 | P1 | 📋 | ZenAgent Awakening |

### 3.2 多 Agent 团队协作场景

**测试文件**: `tests/e2e/test_phase2_team_collaboration.py`

| 测试用例 | 优先级 | 状态 | 覆盖模块 |
|---------|--------|------|---------|
| T5.1 团队创建 → 角色分配 → 成员加入 | P0 | 📋 | SwarmFly Team Builder |
| T5.2 任务拆解 → 并行执行 → 结果汇总 | P0 | 📋 | SwarmFly Collaboration |
| T5.3 共识决策机制验证 | P1 | 📋 | Consensus Mechanism |
| T5.4 冲突检测与解决 | P1 | 📋 | Conflict Resolver |

### 3.3 Agent 进化与学习场景

**测试文件**: `tests/e2e/test_phase2_evolution.py`

| 测试用例 | 优先级 | 状态 | 覆盖模块 |
|---------|--------|------|---------|
| T6.1 任务反馈 → 自我学习 → 知识更新 | P0 | 📋 | SoulTeam Learning |
| T6.2 行为反思 → 模式识别 → 洞察提取 | P0 | 📋 | SoulTeam Reflection |
| T6.3 人格特质演化 | P1 | 📋 | SoulTeam Personality |

---

## 四、Phase 3: 完全真实 E2E 测试

**目标**: 接入真实大模型，验证完整智能体工作流

### 4.1 ModelNexus 集成方案

#### 集成架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        ZenAgent Monorepo                         │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────────┐  │
│  │ ZenAgent │──▶│ LLMInfra │──▶│Runtime   │──▶│  SwarmFly   │  │
│  │   (L2)   │   │    (L0)  │   │  (L1)    │   │    (L3)     │  │
│  └──────────┘   └─────┬────┘   └──────────┘   └──────┬──────┘  │
│                        │                               │         │
│  ┌─────────────────────▼───────────────────────────────▼─────┐ │
│  │                      ModelNexus Adapter                     │ │
│  │  (HTTP API / 本地导入两种模式)                               │ │
│  └─────────────────────────────┬──────────────────────────────┘ │
└────────────────────────────────│────────────────────────────────┘
                                 │ HTTP :8008
                   ┌─────────────▼─────────────┐
                   │      ModelNexus 网关       │
                   │   - 多模型路由              │
                   │   - 成本控制                │
                   │   - 智能降级                │
                   │   - 响应缓存                │
                   └─────────────┬─────────────┘
                                 │
                   ┌─────────────▼─────────────┐
                   │    真实 LLM Provider       │
                   │  (OpenAI / Anthropic / ...)│
                   └───────────────────────────┘
```

#### 集成模式选择

| 模式 | 说明 | 适用场景 | 配置 |
|-----|------|---------|------|
| **模式 A: 本地导入** | 直接 import modelnexus 包 | 单机构建、测试 | 最简单 |
| **模式 B: HTTP API** | ModelNexus 独立服务，HTTP 调用 | 生产部署、分布式 | Docker 启动 |
| **模式 C: Fallback** | ModelNexus + 本地 Provider 双模式 | 高可用场景 | 自动切换 |

**推荐**: Phase 3 初期采用 **模式 A (本地导入)** + Mock Provider，验证集成后再接入真实 API Key。

### 4.2 真实 E2E 测试用例

**测试文件**: `tests/e2e/test_phase3_real_llm.py`

| 测试用例 | 优先级 | 状态 | 说明 |
|---------|--------|------|------|
| T7.1 ModelNexus 健康检查与连接 | P0 | 📋 | 验证网关可用 |
| T7.2 真实 LLM 调用完整链路 | P0 | 📋 | 用户输入 → LLM → 响应输出 |
| T7.3 多轮对话上下文保持 | P0 | 📋 | 验证记忆正确传递 |
| T7.4 工具调用端到端 | P1 | 📋 | LLM 决定调用工具 → 执行 → 返回结果 |
| T7.5 多 Agent 带 LLM 协作 | P1 | 📋 | 真实 LLM 驱动的团队协作 |

### 4.3 测试环境准备

#### 步骤 1: 环境配置

```bash
# 1. 切换到 neo 分支或合并 LLMInfra 代码
git checkout neo  # 或合并到 main

# 2. 安装 ModelNexus 依赖
cd /root/DevSpace/modelnexus
pip install -r requirements.txt

# 3. 启动 Redis (用于缓存和事件总线)
docker run -d -p 6379:6379 redis:7-alpine

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填入真实 API Key (如果需要真实 LLM)
# OPENAI_API_KEY=sk-xxx
# ANTHROPIC_API_KEY=sk-ant-xxx
```

#### 步骤 2: ModelNexus 服务启动

```bash
# 方式一: 本地直接启动
cd /root/DevSpace/modelnexus
python main.py

# 方式二: Docker 启动 (推荐)
cd /root/DevSpace/modelnexus
docker-compose up -d

# 验证服务
curl http://localhost:8008/health
```

#### 步骤 3: ZenAgent 集成验证

```python
# 测试脚本: scripts/test_modelnexus_integration.py
import asyncio
from packages.LLMInfra import (
    ModelNexusAdapter,
    Settings,
    Message,
    MessageRole
)

async def test_connection():
    """测试 ModelNexus 连接"""
    settings = Settings()
    adapter = ModelNexusAdapter(settings)
    
    try:
        await adapter.initialize()
        print("✅ ModelNexus 连接成功")
        
        # 测试简单调用 (使用 Mock 或真实 LLM)
        messages = [
            Message(role=MessageRole.USER, content="你好，简单自我介绍")
        ]
        
        response = await adapter.chat(messages)
        print(f"✅ LLM 调用成功: {response.content[:50]}...")
        print(f"   模型: {response.model}, 成本: ${response.cost:.6f}")
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_connection())
```

---

## 五、测试执行计划

### 5.1 执行顺序

```
第 1 周: Phase 1 主线流程
  ├── Day 1-2: T1 Agent 生命周期
  ├── Day 3-4: T2 任务分发
  └── Day 5-7: T3 事件总线 + 修复

第 2 周: Phase 2 场景集成
  ├── Day 8-10: T4 完整任务
  ├── Day 11-13: T5 团队协作
  └── Day 14: T6 进化学习

第 3 周: Phase 3 真实 LLM
  ├── Day 15-17: ModelNexus 集成
  ├── Day 18-20: 真实 E2E 测试
  └── Day 21: 性能与稳定性验证
```

### 5.2 验收标准

| 阶段 | 通过标准 |
|-----|---------|
| **Phase 1** | 所有 P0 测试 100% 通过，P1 ≥ 90% |
| **Phase 2** | 所有 P0 测试 100% 通过，P1 ≥ 85% |
| **Phase 3** | ModelNexus 连接成功，真实 LLM 调用成功 ≥ 95% |

### 5.3 测试命令

```bash
# 运行所有 E2E 测试
pytest tests/e2e/ -v

# 运行指定阶段
pytest tests/e2e/test_phase1_*.py -v
pytest tests/e2e/test_phase2_*.py -v
pytest tests/e2e/test_phase3_*.py -v  # 需要 ModelNexus

# 运行带真实 LLM 标记的测试
pytest tests/e2e/ -v -m real_llm  # 需要 API Key

# 生成覆盖率报告
pytest tests/e2e/ --cov=packages --cov-report=html
```

---

## 六、ModelNexus 接入详细方案

### 6.1 当前状态分析

**neo 分支已有的内容**:
1. ✅ `packages/LLMInfra/__init__.py` - LLMInfra 入口
2. ✅ `packages/LLMInfra/modelnexus_adapter.py` - ModelNexus 适配器
3. ✅ `packages/LLMInfra/core.py` - 核心数据模型
4. ✅ `packages/LLMInfra/providers/` - Provider 工厂

**缺失的内容**:
1. ❌ `packages/modelnexus/` - ModelNexus 源码作为 submodule
2. ❌ ZenAgent 层与 LLMInfra 的集成代码
3. ❌ 真实 E2E 测试用例

### 6.2 接入步骤

#### Step 1: 合并 neo 分支到 main

```bash
# 切换到 main 分支
git checkout main

# 合并 neo 分支
git merge neo --no-ff -m "Merge neo branch: LLMInfra + ModelNexus integration"

# 解决冲突 (如果有)
# git mergetool
```

#### Step 2: 添加 ModelNexus 为 Submodule

```bash
# 添加为 git submodule
git submodule add /root/DevSpace/modelnexus packages/modelnexus

# 初始化
git submodule init
git submodule update

# 验证
ls packages/modelnexus/
```

#### Step 3: 完善 LLMInfra 集成

**文件**: `packages/ZenAgent/core/agent.py`

```python
from packages.LLMInfra import (
    ModelNexusAdapter,
    Settings,
    Message,
    MessageRole
)

class ZenAgent:
    """增强版 ZenAgent - 集成 ModelNexus"""
    
    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self._llm_settings = Settings()
        self._llm = ModelNexusAdapter(self._llm_settings)
        self._initialized = False
    
    async def initialize(self):
        """初始化 Agent"""
        # 1. 初始化 LLM
        await self._llm.initialize()
        
        # 2. 初始化 SoulTeam
        # ...
        
        # 3. 注册到 SwarmFly
        # ...
        
        self._initialized = True
    
    async def think(self, user_input: str) -> str:
        """思考 - 真实 LLM 调用"""
        messages = [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt),
            Message(role=MessageRole.USER, content=user_input)
        ]
        
        response = await self._llm.chat(
            messages=messages,
            model="gpt-3.5-turbo",
            temperature=0.7
        )
        
        # 写入记忆
        await self._memory.store(
            content=user_input,
            response=response.content,
            metadata={"type": "user_interaction"}
        )
        
        return response.content
```

#### Step 4: 本地开发优化

为了避免每次都需要真实 API Key，提供 Mock Provider：

**文件**: `packages/LLMInfra/providers/mock_provider.py`

```python
from .base import BaseProvider, LLMResponse
import time
import random

class MockProvider(BaseProvider):
    """Mock Provider - 用于开发和测试"""
    
    async def chat(self, messages, **kwargs):
        """模拟聊天响应"""
        # 模拟延迟
        time.sleep(0.1)
        
        # 生成模拟响应
        user_message = messages[-1].content if messages else ""
        
        mock_content = f"[Mock LLM Response] 收到你的消息: '{user_message[:30]}...'"
        
        return LLMResponse(
            provider="mock",
            model=kwargs.get("model", "mock-model"),
            content=mock_content,
            messages=messages,
            usage={
                "prompt_tokens": random.randint(50, 200),
                "completion_tokens": random.randint(20, 100),
                "total_tokens": random.randint(70, 300)
            },
            cost=0.0
        )
```

### 6.3 CI/CD 集成

**GitHub Actions 配置**: `.github/workflows/e2e-tests.yml`

```yaml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  e2e-phase1-2:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Start Redis
        uses: shogo82148/actions-setup-redis@v1
        with:
          redis-version: '7'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run Phase 1 & 2 E2E Tests
        run: pytest tests/e2e/test_phase1_*.py tests/e2e/test_phase2_*.py -v

  e2e-phase3:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: true
      
      - name: Set up Python
        uses: actions/setup-python@v5
      
      - name: Start ModelNexus services
        run: |
          cd packages/modelnexus
          docker-compose up -d
      
      - name: Wait for services
        run: |
          for i in {1..30}; do
            if curl -s http://localhost:8008/health > /dev/null; then
              echo "ModelNexus is ready!"
              exit 0
            fi
            sleep 1
          done
          echo "Timeout waiting for ModelNexus"
          exit 1
      
      - name: Run Phase 3 E2E Tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: pytest tests/e2e/test_phase3_*.py -v -m real_llm
```

---

## 七、风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|-----|------|------|---------|
| ModelNexus 依赖复杂，难以在 CI 运行 | 高 | 中 | 使用 Mock Provider 进行大部分测试，真实 LLM 仅在 main 分支触发 |
| 真实 API Key 成本高 | 中 | 高 | 限制测试调用次数，使用低成本模型，缓存响应 |
| 网络不稳定导致测试 flaky | 中 | 中 | 增加重试机制，设置合理超时，Mock 模式作为 fallback |
| LLM 响应非确定性 | 高 | 高 | 对 LLM 输出做结构化验证而非精确匹配，使用提示词约束输出格式 |

---

## 八、附录

### 8.1 相关文档

| 文档 | 职责 |
| ---- | ---- |
| [Mission.md](./Mission.md) | 框架使命与六层架构定义（顶层文档） |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 系统架构文档 |
| [ROADMAP.md](./ROADMAP.md) | 项目路线图与进度追踪 |
| [E2E_OPTIMIZATION_DESIGN.md](./E2E_OPTIMIZATION_DESIGN.md) | 13 个优化模块详细设计 |
| [API.md](./API.md) | API 使用手册 |
| [packages/LLMInfra/MODELNEXUS_INTEGRATION.md](../packages/LLMInfra/MODELNEXUS_INTEGRATION.md) | ModelNexus 集成指南 |
| [design/agent-collaboration/](./design/agent-collaboration/) | 多智能体协作设计文档，详见 [Mission.md §七](./Mission.md#七设计文档索引) |

### 8.2 参考测试

- `tests/e2e/test_full_flow.py` - 现有 E2E 测试
- `packages/*/tests/` - 各模块单元测试
- `tests/integration/` - 集成测试

---

**文档维护人**: ZenAgent Team  
**下次评审**: 2026-05-25
