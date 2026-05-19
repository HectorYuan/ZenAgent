"""
ModelNexus Provider - 通过 ModelNexus 网关调用 LLM

特性:
- OpenAI 兼容 HTTP API
- 指数退避重试机制
- 响应空值防护与校验
- 会话管理与资源自动清理
- Fallback 降级机制
"""

from typing import List, Optional, AsyncIterator, Dict, Any
import logging
from datetime import datetime
import aiohttp

from ..core import ChatRequest, LLMResponse, Message
from ..config import Settings
from .base import BaseProvider
from ..retry import RetryConfig, with_retry, STANDARD_RETRY

logger = logging.getLogger(__name__)


class ModelNexusProvider(BaseProvider):
    """ModelNexus 网关 Provider - 支持 OpenAI 兼容 API"""

    def __init__(self, provider_name: str, settings: Settings):
        super().__init__(provider_name, settings)
        self._adapter = None
        self._adapter_initialized = False
        self._config = settings.providers.get(provider_name, None)
        self._session: Optional[aiohttp.ClientSession] = None
        self._retry_config = RetryConfig(
            max_attempts=4,
            initial_delay=1.0,
            max_delay=8.0,
            backoff_factor=2.0,
        )
        # 根据问题类型设置不同的超时
        self._timeouts = {
            "simple": 30,    # 简单问答
            "normal": 60,    # 一般推理
            "complex": 120,  # 复杂问题/长文本生成
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 HTTP 会话（复用连接池）"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeouts["normal"]),
                connector=aiohttp.TCPConnector(limit=100, ttl_dns_cache=300),
            )
        return self._session

    async def _close_session(self):
        """关闭 HTTP 会话，释放资源"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.debug("ModelNexus HTTP session closed")

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
                return await with_retry(
                    self._http_chat,
                    self._retry_config,
                    request=request,
                )
            except Exception as e:
                logger.warning(f"ModelNexus HTTP API failed after retry, trying adapter: {e}")

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

    def _detect_request_complexity(self, request: ChatRequest) -> str:
        """
        检测请求复杂度，用于设置不同的超时

        Args:
            request: 聊天请求

        Returns:
            "simple" | "normal" | "complex"
        """
        total_chars = sum(len(msg.content) for msg in request.messages)

        if total_chars > 2000:
            return "complex"
        elif total_chars > 500:
            return "normal"
        return "simple"

    async def _http_chat(self, request: ChatRequest) -> LLMResponse:
        """通过 HTTP API 调用聊天"""
        if not self._config:
            raise ValueError("ModelNexus provider not configured")

        base_url = self._config.base_url.rstrip('/')
        api_key = self._config.api_key
        model = request.model or self._config.default_model

        # 根据复杂度设置超时
        complexity = self._detect_request_complexity(request)
        timeout_seconds = self._timeouts.get(complexity, self._timeouts["normal"])

        # 构建 OpenAI 兼容的请求格式
        payload = {
            "model": model,
            "messages": [
                {
                    "role": msg.role.value if hasattr(msg.role, 'value') else str(msg.role),
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

        session = await self._get_session()
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)

        async with session.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            result = await response.json()

        # 解析 OpenAI 兼容的响应格式
        choices = result.get("choices", [])
        if not choices:
            logger.warning("API returned empty choices array")
            content = ""
            finish_reason = None
        else:
            content = choices[0].get("message", {}).get("content", "")
            finish_reason = choices[0].get("finish_reason")

        # 空值防护：如果 content 为空或 None，降级处理
        if content is None:
            logger.warning("API returned null content, treating as empty string")
            content = ""

        if not content.strip():
            logger.warning("API returned empty content, using fallback response")
            content = f"[ModelNexus Fallback] Received: {request.messages[-1].content[:50]}..."

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
            raw_response=result,
            finish_reason=finish_reason
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
            raw_response={"fallback": True, "modelnexus": "unavailable"},
            finish_reason="stop"
        )

    def _create_response(
        self,
        content: str,
        messages: List[Message],
        model: str,
        usage: Dict[str, int],
        raw_response: Optional[Dict[str, Any]] = None,
        finish_reason: Optional[str] = None
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
            raw_response=raw_response or {},
            finish_reason=finish_reason
        )

    def _calculate_cost(self, usage: Dict[str, int]) -> float:
        """
        计算成本

        Args:
            usage: 使用统计

        Returns:
            成本 (USD)
        """
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
                logger.warning(f"Embedding via HTTP failed: {e}")

        # 其次尝试 Adapter
        adapter = await self._get_adapter()
        if adapter:
            try:
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

        session = await self._get_session()
        async with session.post(
            f"{base_url}/embeddings",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30),
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
                logger.warning(f"List models via HTTP failed: {e}")

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

        session = await self._get_session()
        async with session.get(
            f"{base_url}/models",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            result = await response.json()

        return [m.get("id", m.get("model", "")) for m in result.get("data", [])]

    def __del__(self):
        """析构函数：确保 HTTP 会话被正确关闭"""
        if self._session and not self._session.closed:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._close_session())
                else:
                    loop.run_until_complete(self._close_session())
            except Exception:
                pass  # 忽略关闭时的异常，避免析构函数报错

    async def close(self):
        """手动关闭 Provider 资源"""
        await self._close_session()
        logger.info("ModelNexusProvider resources released")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出 - 确保资源释放"""
        await self._close_session()
        return False  # 不抑制异常
