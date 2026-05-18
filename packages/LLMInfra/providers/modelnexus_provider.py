"""
ModelNexus Provider - 通过 ModelNexus 网关调用 LLM
"""

from typing import List, Optional, AsyncIterator, Dict, Any
import logging
from datetime import datetime
import aiohttp

from ..core import ChatRequest, LLMResponse, Message
from ..config import Settings
from .base import BaseProvider

logger = logging.getLogger(__name__)


class ModelNexusProvider(BaseProvider):
    """ModelNexus 网关 Provider - 支持 OpenAI 兼容 API"""

    def __init__(self, provider_name: str, settings: Settings):
        super().__init__(provider_name, settings)
        self._adapter = None
        self._adapter_initialized = False
        self._config = settings.providers.get(provider_name, None)

    async def _get_adapter(self):
        """获取或初始化 ModelNexus Adapter（子模块集成方式）"""
        if not self._adapter_initialized:
            try:
                from ..modelnexus_adapter import ModelNexusAdapter
                self._adapter = ModelNexusAdapter(self.settings)
                await self._adapter.initialize()
                self._adapter_initialized = True
            except Exception as e:
                logger.warning(f"ModelNexus adapter not available: {e}")
                self._adapter = None
                self._adapter_initialized = True
        return self._adapter

    async def chat(self, request: ChatRequest) -> LLMResponse:
        """
        通过 ModelNexus 进行聊天

        Args:
            request: 聊天请求

        Returns:
            LLMResponse
        """
        # 首先尝试使用 HTTP API 调用（如果配置了 base_url）
        if self._config and self._config.base_url:
            try:
                return await self._http_chat(request)
            except Exception as e:
                logger.warning(f"ModelNexus HTTP API failed, trying adapter: {e}")

        # 其次尝试使用 Adapter
        adapter = await self._get_adapter()
        if adapter:
            try:
                return await adapter.chat(
                    messages=request.messages,
                    model=request.model,
                    provider=self.provider_name,
                    use_cache=self.settings.cache.enabled,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    top_p=request.top_p,
                )
            except Exception as e:
                logger.warning(f"ModelNexus adapter chat failed, using fallback: {e}")

        # 如果都不可用，使用 Mock 响应
        return await self._mock_chat_response(request)

    async def _http_chat(self, request: ChatRequest) -> LLMResponse:
        """通过 HTTP API 调用聊天"""
        if not self._config:
            raise ValueError("ModelNexus provider not configured")

        base_url = self._config.base_url.rstrip('/')
        api_key = self._config.api_key
        model = request.model or self._config.default_model

        # 构建 OpenAI 兼容的请求格式
        payload = {
            "model": model,
            "messages": [
                {
                    "role": msg.role.value if hasattr(msg.role, 'value') else msg.role,
                    "content": msg.content
                }
                for msg in request.messages
            ],
            "temperature": request.temperature if request.temperature is not None else 0.7,
        }

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.top_p:
            payload["top_p"] = request.top_p
        if request.stop:
            payload["stop"] = request.stop
        if request.stream:
            payload["stream"] = request.stream

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                result = await response.json()

        # 解析 OpenAI 兼容的响应格式
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        raw_usage = result.get("usage", {})

        # 清理 usage 字典，移除 None 值并确保都是整数
        usage = {
            "prompt_tokens": raw_usage.get("prompt_tokens") or 0,
            "completion_tokens": raw_usage.get("completion_tokens") or 0,
            "total_tokens": raw_usage.get("total_tokens") or 0
        }

        return self._create_response(
            content=content,
            messages=request.messages,
            model=result.get("model", model),
            usage=usage,
            raw_response=result
        )

    async def _mock_chat_response(self, request: ChatRequest) -> LLMResponse:
        """模拟响应（当 ModelNexus 不可用时）"""
        last_message = request.messages[-1].content if request.messages else ""
        content = f"[ModelNexus Fallback] Received: {last_message[:50]}..."

        usage = {
            "prompt_tokens": len(last_message) // 4,
            "completion_tokens": len(content) // 4,
            "total_tokens": (len(last_message) + len(content)) // 4
        }

        return self._create_response(
            content=content,
            messages=request.messages,
            model=request.model or "modelnexus-fallback",
            usage=usage,
            raw_response={"fallback": True, "modelnexus": "unavailable"}
        )

    def _create_response(
        self,
        content: str,
        messages: List[Message],
        model: str,
        usage: Dict[str, int],
        raw_response: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """创建 LLMResponse 对象"""
        return LLMResponse(
            provider=self.provider_name,
            model=model,
            content=content,
            messages=messages,
            usage=usage,
            cost=self._calculate_cost(usage),
            created_at=datetime.now(),
            raw_response=raw_response or {}
        )

    def _calculate_cost(self, usage: Dict[str, int]) -> float:
        """计算成本"""
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        # 默认价格：$0.0015/1K input, $0.002/1K output
        cost = (prompt_tokens / 1000) * 0.0015 + (completion_tokens / 1000) * 0.002
        return cost

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """
        流式聊天

        Args:
            request: 聊天请求

        Yields:
            内容片段
        """
        response = await self.chat(request)
        # 简单的流式模拟
        chunk_size = 10
        for i in range(0, len(response.content), chunk_size):
            yield response.content[i:i + chunk_size]

    async def embed(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        文本嵌入

        Args:
            text: 文本
            model: 模型名称

        Returns:
            嵌入向量
        """
        # 首先尝试 HTTP API
        if self._config and self._config.base_url:
            try:
                return await self._http_embed(text, model)
            except Exception as e:
                logger.warning(f"ModelNexus HTTP embedding failed: {e}")

        # 其次尝试 Adapter
        adapter = await self._get_adapter()
        if adapter:
            try:
                # 尝试使用 adapter 的嵌入功能
                from modelnexus.api.v1.embeddings import create_embedding
                result = await create_embedding({"model": model or "text-embedding-ada-002", "input": text})
                return result.get("data", [{}])[0].get("embedding", [])
            except Exception as e:
                logger.warning(f"Embedding via ModelNexus failed: {e}")

        # 模拟嵌入向量
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        vector = [(hash_val >> i) & 1 for i in range(1536)]
        total = sum(vector) or 1
        return [v / total for v in vector]

    async def _http_embed(self, text: str, model: Optional[str] = None) -> List[float]:
        """通过 HTTP API 获取嵌入"""
        if not self._config:
            raise ValueError("ModelNexus provider not configured")

        base_url = self._config.base_url.rstrip('/')
        api_key = self._config.api_key
        embed_model = model or "text-embedding-ada-002"

        payload = {
            "model": embed_model,
            "input": text
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{base_url}/embeddings",
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                result = await response.json()

        return result.get("data", [{}])[0].get("embedding", [])

    async def list_models(self) -> List[str]:
        """
        列出可用模型

        Returns:
            模型列表
        """
        # 首先尝试 HTTP API
        if self._config and self._config.base_url:
            try:
                return await self._http_list_models()
            except Exception as e:
                logger.warning(f"ModelNexus HTTP list models failed: {e}")

        # 其次尝试 Adapter
        adapter = await self._get_adapter()
        if adapter:
            return await adapter.get_available_models()

        # 默认模型列表
        return [
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo-preview",
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
            "qwen-turbo",
            "glm-4",
            "Kimi-K2.5"
        ]

    async def _http_list_models(self) -> List[str]:
        """通过 HTTP API 获取模型列表"""
        if not self._config:
            raise ValueError("ModelNexus provider not configured")

        base_url = self._config.base_url.rstrip('/')
        api_key = self._config.api_key

        headers = {
            "Authorization": f"Bearer {api_key}"
        }

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                f"{base_url}/models",
                headers=headers
            ) as response:
                response.raise_for_status()
                result = await response.json()

        return [m.get("id", m.get("model", "")) for m in result.get("data", [])]
