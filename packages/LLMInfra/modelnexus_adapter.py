"""
ModelNexus 适配层

提供 ZenAgent LLMInfra 层与 ModelNexus 的集成接口
"""

from typing import List, Optional, AsyncIterator, Dict, Any
import logging
from datetime import datetime

from .core import ChatRequest, LLMResponse, Message
from .config import Settings

logger = logging.getLogger(__name__)


class ModelNexusAdapter:
    """ModelNexus 适配器 - ZenAgent 与 ModelNexus 之间的桥梁"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        self._initialized = False
    
    async def initialize(self):
        """初始化 ModelNexus 客户端"""
        if self._initialized:
            return
        
        try:
            from modelnexus.services.model_service import get_model_service
            self._client = get_model_service()
            self._initialized = True
            logger.info("ModelNexus adapter initialized")
        except Exception as e:
            logger.error(f"Failed to initialize ModelNexus adapter: {e}")
            raise
    
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
            provider: 提供商名称
            use_cache: 是否使用缓存
            **kwargs: 其他参数
        
        Returns:
            LLMResponse
        """
        if not self._initialized:
            await self.initialize()
        
        request = ChatRequest(
            model=model or "gpt-3.5-turbo",
            messages=messages,
            **kwargs
        )
        
        try:
            # 调用 ModelNexus API
            response_data = await self._call_nexus_chat(request)
            
            return LLMResponse(
                provider=response_data.get("provider", "modelnexus"),
                model=response_data.get("model", request.model),
                content=response_data.get("content", ""),
                messages=messages,
                usage=response_data.get("usage", {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }),
                cost=response_data.get("cost", 0.0),
                created_at=datetime.now(),
                raw_response=response_data
            )
        
        except Exception as e:
            logger.error(f"ModelNexus chat failed: {e}")
            raise
    
    async def _call_nexus_chat(self, request: ChatRequest) -> Dict[str, Any]:
        """
        调用 ModelNexus 聊天接口
        
        Args:
            request: 聊天请求
        
        Returns:
            响应数据
        """
        from modelnexus.api.v1.chat import chat_completion
        
        # 转换消息格式
        nexus_messages = [
            {
                "role": msg.role.value,
                "content": msg.content
            }
            for msg in request.messages
        ]
        
        # 构建请求参数
        params = {
            "model": request.model,
            "messages": nexus_messages,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
        
        if request.max_tokens:
            params["max_tokens"] = request.max_tokens
        if request.stop:
            params["stop"] = request.stop
        
        # 调用 ModelNexus
        result = await chat_completion(params)
        
        return {
            "provider": "modelnexus",
            "model": result.get("model", request.model),
            "content": result.get("choices", [{}])[0].get("message", {}).get("content", ""),
            "usage": result.get("usage", {}),
            "cost": self._calculate_cost(result.get("usage", {}))
        }
    
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
            from modelnexus.api.v1.models import list_models
            models = await list_models()
            return [m.get("id", m.get("model", "")) for m in models]
        except Exception as e:
            logger.warning(f"Failed to list models: {e}")
            return ["gpt-3.5-turbo", "gpt-4", "claude-2"]
    
    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态
        """
        try:
            from modelnexus.observability.health_checker import get_health_checker
            checker = get_health_checker()
            result = await checker.check()
            return result
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def get_cost_stats(self) -> Dict[str, Any]:
        """
        获取成本统计
        
        Returns:
            成本统计
        """
        try:
            from modelnexus.api.v1.cost import get_cost_stats
            return await get_cost_stats()
        except Exception as e:
            logger.warning(f"Failed to get cost stats: {e}")
            return {}
    
    async def shutdown(self):
        """关闭连接"""
        if self._client:
            try:
                from modelnexus.services.model_service import shutdown_model_service
                await shutdown_model_service()
                logger.info("ModelNexus adapter shutdown")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")


class ModelNexusFallbackAdapter:
    """ModelNexus 后备适配器 - 当 ModelNexus 不可用时使用"""
    
    def __init__(self, fallback_client):
        self.fallback_client = fallback_client
        self._nexus_adapter = None
        self._nexus_available = False
    
    async def initialize(self):
        """初始化"""
        try:
            from .modelnexus_adapter import ModelNexusAdapter
            self._nexus_adapter = ModelNexusAdapter(Settings())
            await self._nexus_adapter.initialize()
            self._nexus_available = True
            logger.info("ModelNexus is available")
        except Exception as e:
            logger.warning(f"ModelNexus not available, using fallback: {e}")
            self._nexus_available = False
    
    async def chat(self, messages, model=None, provider=None, **kwargs):
        """聊天"""
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
