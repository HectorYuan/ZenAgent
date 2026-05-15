"""
LLMInfra 使用示例
"""

import asyncio
import os
from dotenv import load_dotenv

from .core import LLMClient, Message, MessageRole
from .config import Settings
from .exceptions import ProviderError, RateLimitError


async def basic_chat_example():
    """基础聊天示例"""
    print("=== 基础聊天示例 ===")
    
    client = LLMClient()
    
    messages = [
        Message(role=MessageRole.SYSTEM, content="你是一个有用的助手"),
        Message(role=MessageRole.USER, content="你好，请介绍一下你自己")
    ]
    
    try:
        response = await client.chat(messages)
        print(f"Response: {response.content}")
        print(f"Model: {response.model}")
        print(f"Cost: ${response.cost:.6f}")
        print(f"Usage: {response.usage}")
    except Exception as e:
        print(f"Error: {e}")


async def multiple_providers_example():
    """多提供商示例"""
    print("\n=== 多提供商示例 ===")
    
    client = LLMClient()
    
    # 获取可用模型
    models = await client.get_available_models()
    print(f"Available models: {models}")
    
    messages = [
        Message(role=MessageRole.USER, content="用一句话介绍 Python")
    ]
    
    # 尝试使用不同提供商
    for provider in ["openai", "qianwen", "zhipu"]:
        try:
            print(f"\nTrying {provider}...")
            response = await client.chat(messages, provider=provider)
            print(f"{provider} response: {response.content[:50]}...")
        except Exception as e:
            print(f"{provider} failed: {e}")


async def streaming_example():
    """流式输出示例"""
    print("\n=== 流式输出示例 ===")
    
    client = LLMClient()
    
    messages = [
        Message(role=MessageRole.USER, content="讲一个关于 AI 的小故事")
    ]
    
    try:
        print("Response: ", end="", flush=True)
        async for chunk in client.chat_stream(messages):
            print(chunk, end="", flush=True)
        print()
    except Exception as e:
        print(f"\nError: {e}")


async def embed_example():
    """嵌入向量示例"""
    print("\n=== 嵌入向量示例 ===")
    
    client = LLMClient()
    
    text = "Hello, world!"
    
    try:
        embedding = await client.embed(text)
        print(f"Text: {text}")
        print(f"Embedding length: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")
    except Exception as e:
        print(f"Error: {e}")


async def main():
    """主函数"""
    # 加载环境变量
    load_dotenv()
    
    # 运行示例
    await basic_chat_example()
    await multiple_providers_example()
    await streaming_example()
    await embed_example()


if __name__ == "__main__":
    asyncio.run(main())
