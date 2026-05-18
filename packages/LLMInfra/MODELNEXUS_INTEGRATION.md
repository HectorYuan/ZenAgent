# ModelNexus 与 ZenAgent 集成指南

## 概述

ModelNexus 是 ZenAgent 项目的核心大模型网关组件，提供企业级的多模型路由、成本控制、智能降级等功能。通过 Git Submodule 方式集成到 ZenAgent 项目中。

## 集成架构

```
ZenAgent Monorepo
│
├── packages/
│   ├── LLMInfra/          # L0: LLM 基础设施层
│   │   ├── __init__.py   # 支持本地和 ModelNexus 两种模式
│   │   ├── core.py       # 核心客户端
│   │   ├── config.py     # 配置管理
│   │   ├── cache.py      # 缓存模块
│   │   ├── modelnexus_adapter.py  # ModelNexus 适配器
│   │   └── providers/     # 本地 Provider 实现
│   │
│   ├── modelnexus/        # ModelNexus Git Submodule
│   │   ├── api/          # API 端点
│   │   ├── core/         # 核心路由
│   │   ├── cache/        # 缓存模块
│   │   ├── services/     # 服务层
│   │   └── observability/# 可观测性
│   │
│   ├── Runtime/           # L1: 运行时层
│   ├── ZenAgent/          # L2: 智能体层
│   ├── SwarmFly/          # L3: 集群管理层
│   └── SoulTeam/          # L4: 灵魂团队层
```

## ModelNexus 核心功能

### 1. 多模型路由
- 智能选择最优模型
- 意图识别路由
- 成本感知路由
- 负载均衡

### 2. 成本控制
- 实时成本统计
- 批量折扣支持
- 成本告警
- 预算控制

### 3. 智能降级
- 多级降级策略
- 故障自动切换
- 服务可用性保障

### 4. 响应缓存
- Redis 缓存
- 语义缓存
- 多级缓存策略

### 5. 可观测性
- Prometheus 指标
- OpenTelemetry 追踪
- SLO 追踪
- 健康检查

### 6. 安全特性
- Vault 密钥管理
- API 认证
- 内容审核
- 数据脱敏

## 使用方式

### 方式一：直接使用 ModelNexus（推荐）

ModelNexus 作为独立服务运行，ZenAgent 通过 HTTP API 调用：

```bash
# 1. 启动 ModelNexus 服务
cd packages/modelnexus
docker-compose up -d

# 2. 配置环境变量
export MODEL_NEXUS_URL=http://localhost:8008
export MODEL_NEXUS_API_KEY=your-api-key

# 3. 在 ZenAgent 中使用
```

```python
from packages.LLMInfra import ModelNexusAdapter, Settings

async def main():
    settings = Settings()
    adapter = ModelNexusAdapter(settings)
    await adapter.initialize()
    
    messages = [
        {"role": "user", "content": "你好"}
    ]
    
    response = await adapter.chat(messages, model="gpt-3.5-turbo")
    print(response.content)
```

### 方式二：使用本地 Provider

当 ModelNexus 不可用时，使用本地 Provider：

```python
from packages.LLMInfra import LLMClient, Message, MessageRole

async def main():
    client = LLMClient()
    
    messages = [
        Message(role=MessageRole.USER, content="你好")
    ]
    
    response = await client.chat(messages)
    print(response.content)
```

### 方式三：智能切换模式

ModelNexus 可用时优先使用，不可用时自动切换到本地 Provider：

```python
from packages.LLMInfra import (
    ModelNexusFallbackAdapter,
    LLMClient,
    has_modelnexus
)

async def main():
    # 检查 ModelNexus 是否可用
    if has_modelnexus():
        # 使用 ModelNexus 优先模式
        fallback_client = LLMClient()
        adapter = ModelNexusFallbackAdapter(fallback_client)
        await adapter.initialize()
        
        response = await adapter.chat(messages)
    else:
        # 仅使用本地 Provider
        client = LLMClient()
        response = await client.chat(messages)
```

## 配置说明

### ModelNexus 配置

参考 `packages/modelnexus/config/settings.py` 或 `packages/modelnexus/.env.example`

主要配置项：

```bash
# 服务配置
MODEL_NEXUS_PORT=8008
MNX_REDIS_HOST=localhost
MNX_REDIS_PORT=6379

# 安全配置
MNX_VAULT_ENABLED=false
MNX_API_KEY=your-api-key

# 路由配置
MNX_DEFAULT_MODEL=gpt-3.5-turbo
MNX_ENABLE_INTENT_ROUTING=true

# 缓存配置
MNX_CACHE_ENABLED=true
MNX_CACHE_TTL=3600

# 限流配置
MNX_RATE_LIMIT_ENABLED=true
MNX_RATE_LIMIT_PER_MINUTE=60
```

### ZenAgent LLMInfra 配置

参考 `packages/LLMInfra/config.py`

```python
from packages.LLMInfra.config import Settings

settings = Settings()

# 配置 ModelNexus 网关地址
settings.modelnexus_url = "http://localhost:8008"

# 配置本地 Provider 作为后备
settings.providers["openai"] = {
    "api_key": os.getenv("OPENAI_API_KEY"),
    "base_url": "https://api.openai.com/v1"
}
```

## API 端点

ModelNexus 提供以下主要 API 端点：

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/health/detailed` | GET | 详细健康状态 |
| `/api/v1/chat/completions` | POST | 聊天完成 |
| `/api/v1/completions` | POST | 文本补全 |
| `/api/v1/embeddings` | POST | 文本嵌入 |
| `/api/v1/models` | GET | 模型列表 |
| `/api/v1/cost/stats` | GET | 成本统计 |
| `/api/v1/usage` | GET | 使用统计 |
| `/metrics` | GET | Prometheus 指标 |

## 与 SwarmFly 集成

在 SwarmFly 智能体中使用 ModelNexus：

```python
from packages.LLMInfra import ModelNexusAdapter, Message, MessageRole
from packages.SwarmFly.core import Agent

class ZenAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.llm = ModelNexusAdapter(Settings())
    
    async def think(self, user_message: str) -> str:
        messages = [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt),
            Message(role=MessageRole.USER, content=user_message)
        ]
        
        response = await self.llm.chat(messages)
        return response.content
    
    async def initialize(self):
        await self.llm.initialize()
    
    async def shutdown(self):
        await self.llm.shutdown()
```

## 开发指南

### 本地开发

```bash
# 1. 克隆 ModelNexus（如果作为 submodule）
cd packages/modelnexus
git checkout main
git pull origin main

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动 ModelNexus
python main.py

# 4. 运行测试
pytest tests/ -v
```

### 运行测试

```bash
# ModelNexus 单元测试
cd packages/modelnexus
pytest tests/test_unit.py -v

# ZenAgent LLMInfra 测试
cd packages/LLMInfra
pytest test_basic.py -v

# 集成测试
pytest tests/test_integration.py -v
```

### 贡献代码

1. **ModelNexus 代码修改**：
   ```bash
   cd packages/modelnexus
   # 在 submodule 中进行修改
   git checkout -b feature/your-feature
   git commit -m "Your changes"
   git push origin feature/your-feature
   ```

2. **提交到 ZenAgent 主仓库**：
   ```bash
   cd packages/modelnexus
   git add .
   cd ../../
   git commit -m "Update ModelNexus submodule"
   ```

## 更新 ModelNexus

```bash
# 进入 submodule 目录
cd packages/modelnexus

# 查看远程更新
git fetch origin

# 切换到最新版本
git checkout main
git pull origin main

# 返回主仓库
cd ../..

# 提交 submodule 更新
git add packages/modelnexus
git commit -m "Update ModelNexus to latest version"
```

## 常见问题

### Q: 如何禁用 ModelNexus？
A: 不启动 ModelNexus 服务，LLMInfra 会自动使用本地 Provider。

### Q: 如何切换 Provider？
A: 设置 `MODEL_NEXUS_ENABLED=false` 环境变量，或直接使用 `LLMClient`。

### Q: ModelNexus 和本地 Provider 如何选择？
A: 
- 生产环境：推荐使用 ModelNexus（更多企业级特性）
- 开发环境：使用本地 Provider（更快启动）
- 高可用场景：使用 `ModelNexusFallbackAdapter`（自动切换）

### Q: 如何监控 ModelNexus？
A: 访问 `http://localhost:8008/metrics` 获取 Prometheus 指标。

## 许可证

ModelNexus 采用 MIT License，详见 `packages/modelnexus/LICENSE`。

## 参考链接

- [ModelNexus 官方文档](packages/modelnexus/README.md)
- [ModelNexus 部署指南](packages/modelnexus/docs/DEPLOYMENT.md)
- [ZenAgent 架构文档](../docs/ARCHITECTURE.md)
