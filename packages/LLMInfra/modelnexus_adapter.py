"""
ModelNexus 适配层

提供 ZenAgent LLMInfra 层与 ModelNexus 的集成接口

实现方式: HTTP API 调用 (OpenAI 兼容协议)，不依赖 ModelNexus 内部模块
优势:
  1. 解耦 - 不需要 ModelNexus 作为子模块运行在同一进程
  2. 稳定 - HTTP API 协议稳定，不受内部代码变更影响
  3. 灵活 - 支持远程 ModelNexus 服务部署
"""

from typing import List, Optional, AsyncIterator, Dict, Any
import logging
import aiohttp
from datetime import datetime

from .core import ChatRequest, LLMResponse, Message
from .config import Settings

logger = logging.getLogger(__name__)


class ModelNexusAdapter:
    """ModelNexus 适配器 - 通过 HTTP API 调用 ModelNexus 服务

    使用 OpenAI 兼容的 HTTP API 协议，不依赖 ModelNexus 内部 Python 模块
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._base_url = settings.providers.get("modelnexus", {}).get("base_url", "http://localhost:8080")
        if isinstance(self._base_url, str) and not self._base_url.endswith("/"):
            self._base_url = self._base_url + "/"
        self._api_key = settings.providers.get("modelnexus", {}).get("api_key", "")
        self._initialized = False
        self._session = None

    async def initialize(self):
        """初始化 ModelNexus 客户端"""
        if self._initialized:
            return

        # 创建 HTTP 会话
        timeout = aiohttp.ClientTimeout(total=120)
        self._session = aiohttp.ClientSession(timeout=timeout)
        self._initialized = True
        logger.info("ModelNexus adapter initialized with HTTP API mode")

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        provider: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        通过 ModelNexus 进行聊天

        Args:
            messages: 消息列表
            model: 模型名称
            provider: 提供商名称 (被忽略，使用 modelnexus)
            use_cache: 是否使用缓存 (被忽略，缓存由 LLMClient 层处理)
            **kwargs: 其他参数 (temperature, max_tokens, top_p, stop, stream)

        Returns:
            LLMResponse
        """
        if not self._initialized:
            await self.initialize()

        request = ChatRequest(
            model=model or "default",
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens"),
            top_p=kwargs.get("top_p"),
            stop=kwargs.get("stop"),
            stream=kwargs.get("stream", False)
        )

        return await self._call_nexus_chat(request)

    async def _call_nexus_chat(self, request: ChatRequest) -> Dict[str, Any]:
        """
        调用 ModelNexus 聊天接口 (HTTP API)

        Args:
            request: 聊天请求

        Returns:
            LLMResponse
        """
        # 构建请求参数
        payload = {
            "model": request.model,
            "messages": [
                {
                    "role": msg.role.value if hasattr(msg.role, "value") else str(msg.role),
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
            "Authorization": f"Bearer {self._api_key}"
        }

        url = f"{self._base_url}chat/completions"

        async with self._session.post(url, headers=headers, json=payload) as response:
            response.raise_for_status()
            result = await response.json()

        # 解析 OpenAI 兼容的响应格式
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        raw_usage = result.get("usage", {})

        # 清理 usage 字典，移除 None 值
        usage = {
            "prompt_tokens": raw_usage.get("prompt_tokens") or 0,
            "completion_tokens": raw_usage.get("completion_tokens") or 0,
            "total_tokens": raw_usage.get("total_tokens") or 0
        }

        return LLMResponse(
            provider="modelnexus",
            model=result.get("model", request.model),
            content=content,
            messages=request.messages,
            usage=usage,
            cost=self._calculate_cost(usage),
            created_at=datetime.now(),
            raw_response=result
        )

    def _calculate_cost(self, usage: Dict[str, int]) -> float:
        """
        计算成本

        Args:
            usage: 使用统计

        Returns:
            成本
        """
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        # 默认价格：$0.0015/1K input, $0.002/1K output
        cost = (prompt_tokens / 1000) * 0.0015 + (completion_tokens / 1000) * 0.002
        return cost

    async def get_available_models(self) -> List[str]:
        """
        获取可用模型列表

        Returns:
            模型列表
        """
        if not self._initialized:
            await self.initialize()

        try:
            headers = {"Authorization": f"Bearer {self._api_key}"}
            url = f"{self._base_url}models"

            async with self._session.get(url, headers=headers) as response:
                response.raise_for_status()
                result = await response.json()

            return [m.get("id", m.get("model", "")) for m in result.get("data", [])]
        except Exception as e:
            logger.warning(f"Failed to list models: {e}")
            return [
                "gpt-3.5-turbo", "gpt-4", "claude-3-sonnet-20240229",
                "claude-3-opus-20240229", "qwen-turbo", "glm-4", "Kimi-K2.5"
            ]

    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            健康状态
        """
        try:
            if not self._session:
                return {
                    "status": "unhealthy",
                    "error": "HTTP session not initialized"
                }

            # 尝试调用模型列表作为健康检查
            headers = {"Authorization": f"Bearer {self._api_key}"}
            url = f"{self._base_url}models"

            async with self._session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    return {"status": "healthy", "api": "reachable"}
                return {
                    "status": "degraded",
                    "error": f"HTTP {response.status}",
                    "api_url": self._base_url
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "api_url": self._base_url
            }

    async def get_cost_stats(self) -> Dict[str, Any]:
        """
        获取成本统计

        Returns:
            成本统计 (当前未实现，返回空字典)
        """
        return {}

    async def shutdown(self):
        """关闭连接"""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("ModelNexus adapter shutdown")


class ModelNexusFallbackAdapter:
    """ModelNexus 后备适配器 - 当 ModelNexus 不可用时使用 Mock 响应

    设计目标:
    1. 主链路失败时提供降级服务
    2. 静默失败，不影响用户体验
    3. 提供 Fallback 标记便于调试
    """

    def __init__(self, fallback_client):
        self.fallback_client = fallback_client
        self._nexus_adapter = None
        self._nexus_available = False

    async def initialize(self):
        """初始化 - 尝试连接 ModelNexus"""
        try:
            from .modelnexus_adapter import ModelNexusAdapter
            self._nexus_adapter = ModelNexusAdapter(Settings())
            await self._nexus_adapter.initialize()

            # 健康检查
            health = await self._nexus_adapter.health_check()
            self._nexus_available = health.get("status") == "healthy"

            if self._nexus_available:
                logger.info("ModelNexus is available")
            else:
                logger.warning("ModelNexus health check failed, using fallback")
        except Exception as e:
            logger.warning(f"ModelNexus not available, using fallback: {e}")
            self._nexus_available = False

    async def chat(self, messages, model=None, provider=None, **kwargs):
        """聊天 - 优先使用 ModelNexus，失败时降级到 Fallback"""
        if self._nexus_available and self._nexus_adapter:
            try:
                return await self._nexus_adapter.chat(messages, model, provider, **kwargs)
            except Exception as e:
                logger.warning(f"ModelNexus failed, falling back: {e}")

        # 使用后备客户端
        return await self.fallback_client.chat(messages, model, provider, **kwargs)

    async def health_check(self):
        """健康检查"""
        if self._nexus_available and self._nexus_adapter:
            return await self._nexus_adapter.health_check()
        return {"status": "degraded", "fallback": True}
