"""
Mock Provider - 用于测试的模拟 Provider
"""

from typing import List, Optional, AsyncIterator, Dict, Any
import logging
import uuid
import json

from .base import BaseProvider
from ..core import ChatRequest, LLMResponse, Message
from ..exceptions import ProviderError

logger = logging.getLogger(__name__)


class MockProvider(BaseProvider):
    """模拟 Provider，用于测试"""

    def __init__(self, provider_name: str, settings):
        super().__init__(provider_name, settings)
        self._responses = {
            "default": "This is a mock response from the LLM.",
            "hello": "Hello! How can I help you today?",
            "math": "The answer is 42.",
            "code": "Here's some example code:\n```python\ndef hello():\n    print('Hello, World!')\n```",
        }
        self._delay = 0.0  # 模拟延迟

    def set_responses(self, responses: Dict[str, str]):
        """设置自定义响应"""
        self._responses.update(responses)

    def set_delay(self, delay: float):
        """设置模拟延迟"""
        self._delay = delay

    async def chat(self, request: ChatRequest) -> LLMResponse:
        """
        模拟聊天接口

        Args:
            request: 聊天请求

        Returns:
            LLMResponse
        """
        # 模拟延迟
        if self._delay > 0:
            import asyncio
            await asyncio.sleep(self._delay)

        # 根据请求内容选择响应
        last_message = request.messages[-1] if request.messages else None
        content = last_message.content if last_message else ""

        response_content = self._responses["default"]
        for key, response in self._responses.items():
            if key in content.lower():
                response_content = response
                break

        # 计算 token 使用量（模拟）
        input_tokens = len(content) // 4 if content else 10
        output_tokens = len(response_content) // 4 or 5

        usage = {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }

        return self._create_response(
            content=response_content,
            messages=request.messages,
            model=request.model or "mock-model",
            usage=usage,
            raw_response={"mock": True, "request_id": str(uuid.uuid4())}
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """
        模拟流式聊天接口

        Args:
            request: 聊天请求

        Yields:
            内容片段
        """
        response = await self.chat(request)
        # 按字符流式输出
        for char in response.content:
            if self._delay > 0:
                import asyncio
                await asyncio.sleep(self._delay / len(response.content))
            yield char

    async def embed(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        模拟文本嵌入

        Args:
            text: 文本
            model: 模型名称

        Returns:
            嵌入向量（1536维模拟向量）
        """
        # 生成确定性的模拟向量
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        vector = [(hash_val >> i) & 1 for i in range(1536)]
        # 归一化
        total = sum(vector) or 1
        return [v / total for v in vector]

    async def list_models(self) -> List[str]:
        """
        列出可用模型

        Returns:
            模型列表
        """
        return ["mock-model", "mock-model-large", "mock-model-fast"]
