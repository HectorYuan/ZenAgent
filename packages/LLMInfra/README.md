# LLMInfra - ZenAgent 大模型网关层

LLMInfra 是 ZenAgent 项目的 L0 层，提供统一的大模型调用接口、多提供商管理、缓存、限流和成本控制功能。

## 功能特性

- **多提供商支持**: OpenAI、通义千问、智谱AI、文心一言等
- **统一接口**: 所有提供商使用相同的调用方式
- **缓存机制**: 支持内存和 Redis 缓存
- **限流控制**: 请求级和 Token 级限流
- **成本统计**: 实时计算 API 调用成本
- **流式输出**: 支持流式响应
- **文本嵌入**: 支持文本向量化

## 安装

```bash
# 安装依赖
cd /workspace
pip install -e .
```

## 快速开始

### 1. 配置环境变量

复制 `.env.example` 为 `.env` 并配置 API 密钥:

```bash
cp .env.example .env
# 编辑 .env，填入你的 API 密钥
```

### 2. 基本使用

```python
import asyncio
from packages.LLMInfra import LLMClient, Message, MessageRole

async def main():
    client = LLMClient()
    
    messages = [
        Message(role=MessageRole.SYSTEM, content="你是一个有用的助手"),
        Message(role=MessageRole.USER, content="你好")
    ]
    
    response = await client.chat(messages)
    print(response.content)

asyncio.run(main())
```

### 3. 指定提供商

```python
# 使用通义千问
response = await client.chat(messages, provider="qianwen")

# 使用智谱AI
response = await client.chat(messages, provider="zhipu")

# 指定模型
response = await client.chat(messages, model="gpt-4")
```

### 4. 流式输出

```python
async for chunk in client.chat_stream(messages):
    print(chunk, end="", flush=True)
```

### 5. 文本嵌入

```python
embedding = await client.embed("Hello, world!")
print(embedding)
```

## 目录结构

```
LLMInfra/
├── __init__.py          # 模块入口
├── core.py              # 核心客户端和数据模型
├── config.py            # 配置管理
├── exceptions.py        # 异常定义
├── cache.py             # 缓存模块
├── providers/           # 提供商实现
│   ├── __init__.py
│   ├── base.py          # Provider 基类
│   ├── openai_provider.py  # OpenAI 兼容实现
│   └── factory.py       # Provider 工厂
├── example.py           # 使用示例
└── README.md            # 本文档
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| OPENAI_API_KEY | OpenAI API 密钥 | - |
| OPENAI_BASE_URL | OpenAI API 地址 | https://api.openai.com/v1 |
| QIANWEN_API_KEY | 通义千问 API 密钥 | - |
| ZHIPU_API_KEY | 智谱 AI API 密钥 | - |
| ERNIE_API_KEY | 文心一言 API 密钥 | - |
| LLM_CACHE_ENABLED | 是否启用缓存 | true |
| LLM_CACHE_TYPE | 缓存类型 (redis/memory) | redis |
| LLM_CACHE_TTL | 缓存过期时间 (秒) | 3600 |
| LLM_RATE_LIMIT_ENABLED | 是否启用限流 | true |
| LLM_RATE_LIMIT_REQUESTS_PER_MINUTE | 每分钟请求限制 | 60 |
| LLM_RATE_LIMIT_TOKENS_PER_MINUTE | 每分钟 Token 限制 | 90000 |

### 代码配置

```python
from packages.LLMInfra.config import Settings, ProviderConfig

settings = Settings()

# 添加自定义 Provider 配置
settings.providers["custom"] = ProviderConfig(
    api_key="your-key",
    base_url="https://api.custom.com/v1",
    default_model="custom-model"
)

client = LLMClient(settings)
```

## 扩展开发

### 添加新的 Provider

1. 继承 `BaseProvider` 类
2. 实现抽象方法
3. 注册到工厂

```python
from packages.LLMInfra.providers import BaseProvider

class CustomProvider(BaseProvider):
    async def chat(self, request):
        # 实现聊天逻辑
        pass
    
    async def chat_stream(self, request):
        # 实现流式聊天
        pass
    
    async def embed(self, text, model=None):
        # 实现嵌入逻辑
        pass
    
    async def list_models(self):
        # 实现模型列表
        pass

# 注册到工厂
client.provider_factory.register_provider("custom", CustomProvider)
```

## 与 SwarmFly 集成

在 SwarmFly 中使用 LLMInfra:

```python
from packages.LLMInfra import LLMClient, Message, MessageRole
from packages.SwarmFly import Swarm

class MyAgent:
    def __init__(self):
        self.llm = LLMClient()
    
    async def think(self, messages):
        response = await self.llm.chat(messages)
        return response.content
```

## 许可证

MIT License
