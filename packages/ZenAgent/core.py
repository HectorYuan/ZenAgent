from __future__ import annotations
"""
ZenAgent 核心入口

整合 MCP、Hooks、Awakening、Collaboration 和 LLM 模块的统一入口
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)

# MCP 模块
from .mcp import (
    MCPProtocol,
    MCPMessage,
    MCPRequest,
    MCPResponse,
    MCPSession,
    MCPSessionState,
    MCPSessionManager,
    MCPHandler,
    MCPHandlerRegistry,
    AgentRegistry,
    RegisteredAgent,
    AgentMetadata,
    AgentStatus,
    AgentCapability,
    get_registry,
)

# Hooks 模块
from .hooks import (
    HookManager,
    HookPriority,
    HookEvent,
    LifecycleHook,
    LifecycleEvent,
    LifecycleManager,
    LoggingHook,
    MetricsHook,
    RateLimitHook,
    MonitoringHook,
    get_hook_manager,
    get_logging_hook,
    get_metrics_hook,
    get_rate_limit_hook,
    get_monitoring_hook,
    # 装饰器
    on_create,
    on_start,
    on_message,
    on_response,
    on_error,
    on_shutdown,
)

# Awakening 模块
from .awakening import (
    AwakeningAdapter,
    AwakeningState,
    AwakeningCapability,
    CapabilityRegistry,
    EvolutionEngine,
    EvolutionStage,
    EvolutionEvent,
    get_adapter,
    get_capability_registry,
    get_evolution_engine,
)

# Collaboration 模块
from .collaboration import (
    CollaborationProtocol,
    CollaborationMessage,
    CollaborationRequest,
    CollaborationResponse,
    ProtocolType,
    MessagePriority,
    CollaborationNegotiator,
    NegotiationResult,
    NegotiationStatus,
    TaskRouter,
    TaskRoute,
    RouteStrategy,
    get_router,
    get_negotiator,
)

# LLMInfra 模块 — 优先 packages.LLMInfra（规范路径），避免与 bare LLMInfra 产生双份模块
try:
    from packages.LLMInfra import (
        LLMClient,
        Message,
        MessageRole,
        LLMResponse,
        Settings as LLMSettings,
        ProviderConfig,
        ModelNexusAdapter,
        has_modelnexus,
    )
    _HAS_LLMINFRA = True
except ImportError:
    try:
        from LLMInfra import (
            LLMClient,
            Message,
            MessageRole,
            LLMResponse,
            Settings as LLMSettings,
            ProviderConfig,
            ModelNexusAdapter,
            has_modelnexus,
        )
        _HAS_LLMINFRA = True
    except ImportError:
        _HAS_LLMINFRA = False
        LLMClient = None
        Message = None
        MessageRole = None
        LLMResponse = None
        LLMSettings = None
        ProviderConfig = None
        ModelNexusAdapter = None
        has_modelnexus = None

# MetaSoul 记忆系统 — 优先 packages.MetaSoul（规范路径）
try:
    from packages.MetaSoul.memory import MetaSoul, MemoryType, MemoryImportance
    from packages.MetaSoul.personality import Personality
    _HAS_SOULTEAM = True
except ImportError:
    try:
        from MetaSoul.memory import MetaSoul, MemoryType, MemoryImportance
        from MetaSoul.personality import Personality
        _HAS_SOULTEAM = True
    except ImportError:
        _HAS_SOULTEAM = False
        MetaSoul = None
        MemoryType = None
        MemoryImportance = None
        Personality = None


@dataclass
class ZenAgentConfig:
    """ZenAgent 配置"""
    # Agent 基本信息
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = "ZenAgent"
    agent_type: str = "general"
    
    # MCP 配置
    mcp_protocol_version: str = "1.0.0"
    session_idle_timeout: int = 300
    session_max_lifetime: int = 3600
    
    # Hooks 配置
    enable_logging: bool = True
    enable_metrics: bool = True
    enable_rate_limit: bool = True
    rate_limit_max_per_window: int = 100
    rate_limit_window_seconds: int = 60
    
    # Awakening 配置
    awakening_threshold: float = 0.8
    enable_evolution: bool = True
    
    # Collaboration 配置
    collaboration_timeout: int = 60
    max_collaboration_participants: int = 5
    
    # 功能开关
    enable_mcp: bool = True
    enable_hooks: bool = True
    enable_awakening: bool = True
    enable_collaboration: bool = True

    # LLM 配置
    enable_llm: bool = True
    llm_provider: str = "mock"  # mock, modelnexus, openai, anthropic
    llm_model: str = "default"
    llm_temperature: float = 0.7
    llm_max_tokens: Optional[int] = None
    enable_llm_cache: bool = True

    # 记忆配置
    enable_memory: bool = True
    auto_memory_recording: bool = True  # 自动记录对话到记忆
    memory_type_for_conversation: MemoryType = MemoryType.EPISODIC
    enable_personality_influence: bool = True  # 启用人格影响思考

    # M9a: 经验-记忆闭环
    enable_experience_loop: bool = True


class ZenAgent:
    """
    ZenAgent 核心类
    
    整合所有模块的统一入口
    """
    
    def __init__(self, config: Optional[ZenAgentConfig] = None):
        """
        初始化 ZenAgent
        
        Args:
            config: 配置对象
        """
        self.config = config or ZenAgentConfig()
        
        # MCP 模块
        self._protocol: Optional[MCPProtocol] = None
        self._session_manager: Optional[MCPSessionManager] = None
        self._handler_registry: Optional[MCPHandlerRegistry] = None
        self._agent_registry: Optional[AgentRegistry] = None
        
        # Hooks 模块
        self._hook_manager: Optional[HookManager] = None
        self._lifecycle_manager: Optional[LifecycleManager] = None
        self._logging_hook: Optional[LoggingHook] = None
        self._metrics_hook: Optional[MetricsHook] = None
        self._rate_limit_hook: Optional[RateLimitHook] = None
        self._monitoring_hook: Optional[MonitoringHook] = None
        
        # Awakening 模块
        self._awakening_adapter: Optional[AwakeningAdapter] = None
        self._capability_registry: Optional[CapabilityRegistry] = None
        self._evolution_engine: Optional[EvolutionEngine] = None
        
        # Collaboration 模块
        self._collaboration_protocol: Optional[CollaborationProtocol] = None
        self._negotiator: Optional[CollaborationNegotiator] = None
        self._task_router: Optional[TaskRouter] = None

        # LLM 模块
        self._llm_client: Optional[LLMClient] = None
        self._llm_settings: Optional[LLMSettings] = None
        self._conversation_history: List[Message] = []

        # MetaSoul 模块
        self._meta_soul: Optional[MetaSoul] = None
        self._personality: Optional[Personality] = None

        # M9a: 经验-记忆闭环 (初始化于 __init__ 保证属性始终存在)
        self._experience_loop = None

        # 初始化所有模块
        self._initialize_modules()
    
    def _initialize_modules(self) -> None:
        """初始化所有模块"""
        # MCP 模块
        if self.config.enable_mcp:
            self._protocol = MCPProtocol(version=self.config.mcp_protocol_version)
            self._session_manager = MCPSessionManager()
            self._handler_registry = MCPHandlerRegistry()
            self._agent_registry = get_registry()
        
        # Hooks 模块
        if self.config.enable_hooks:
            self._hook_manager = get_hook_manager()
            self._lifecycle_manager = LifecycleManager(self._hook_manager)
            
            if self.config.enable_logging:
                self._logging_hook = get_logging_hook()
            if self.config.enable_metrics:
                self._metrics_hook = get_metrics_hook()
            if self.config.enable_rate_limit:
                self._rate_limit_hook = get_rate_limit_hook()
            self._monitoring_hook = get_monitoring_hook()
        
        # Awakening 模块
        if self.config.enable_awakening:
            self._awakening_adapter = get_adapter(self.config.agent_id)
            self._capability_registry = get_capability_registry()
            self._evolution_engine = get_evolution_engine()
            
            # 设置适配器的注册表和引擎
            if self._awakening_adapter:
                self._awakening_adapter.set_capability_registry(
                    self._capability_registry
                )
                self._awakening_adapter.set_evolution_engine(
                    self._evolution_engine
                )
                self._awakening_adapter.context.awakening_threshold = (
                    self.config.awakening_threshold
                )
        
        # Collaboration 模块
        if self.config.enable_collaboration:
            self._collaboration_protocol = CollaborationProtocol()
            self._negotiator = get_negotiator()
            self._task_router = get_router()

            # 设置路由器的注册表
            if self._task_router and self._agent_registry:
                self._task_router.set_registry(self._agent_registry)

        # LLM 模块
        if self.config.enable_llm and _HAS_LLMINFRA:
            self._init_llm()

        # MetaSoul 模块
        if self.config.enable_memory and _HAS_SOULTEAM:
            self._init_soul()

    def _init_llm(self) -> None:
        """初始化 LLM 客户端"""
        if not _HAS_LLMINFRA:
            return

        # 创建 LLM 设置
        self._llm_settings = LLMSettings(
            default_provider=self.config.llm_provider,
        )

        # 配置缓存
        self._llm_settings.cache.enabled = self.config.enable_llm_cache

        # 配置 Mock Provider 用于测试
        if self.config.llm_provider == "mock":
            self._llm_settings.providers["mock"] = ProviderConfig(
                api_key="",
                base_url="",
                default_model="mock-model"
            )

        self._llm_client = LLMClient(self._llm_settings)

        # 初始化意图路由器
        from packages.LLMInfra.intent_router import (
            IntentRouter, ChatRequest
        )
        self._intent_router = IntentRouter()
        self._ChatRequest = ChatRequest  # 保存引用供 think() 使用

    def _init_soul(self) -> None:
        """初始化 MetaSoul 记忆和人格系统"""
        if not _HAS_SOULTEAM:
            return

        # 初始化 MetaSoul
        self._meta_soul = MetaSoul(soul_id=self.config.agent_id)

        # 初始化人格系统
        if self.config.enable_personality_influence:
            self._personality = Personality()

        # M9a: 经验-记忆闭环 (初始化为 None，无条件)
        self._experience_loop = None
        if self.config.enable_experience_loop and self.config.enable_memory:
            self._init_experience_loop()

    def _init_experience_loop(self):
        """初始化经验-记忆闭环 (M9a)"""
        try:
            from packages.MetaSoul.experience_loop import ExperienceMemoryLoop
            from packages.MetaSoul.learning.learner import SelfLearner
            from packages.MetaSoul.reflection.reflector import Reflector
            self._experience_loop = ExperienceMemoryLoop(
                soul_id=self.config.agent_id,
                learner=SelfLearner(soul_id=self.config.agent_id),
                reflector=Reflector(),
            )
        except ImportError:
            self._experience_loop = None

    # ====================
    # LLM 访问器和方法
    # ====================

    @property
    def llm_client(self) -> Optional[LLMClient]:
        """获取 LLM 客户端"""
        return self._llm_client

    @property
    def conversation_history(self) -> List[Message]:
        """获取对话历史"""
        return self._conversation_history.copy() if _HAS_LLMINFRA else []

    def clear_conversation(self) -> None:
        """清空对话历史"""
        self._conversation_history.clear()

    async def think(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        use_history: bool = True,
        record_to_memory: bool = True,
        use_router: bool = True,
        **kwargs
    ) -> Any:
        """
        思考 - 使用意图路由调用 LLM

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            use_history: 是否使用对话历史
            record_to_memory: 是否记录到记忆
            use_router: 是否使用意图路由（False 时走原单一路径）
            **kwargs: 其他 LLM 参数

        Returns:
            LLMResponse: LLM 响应
        """
        if not self._llm_client:
            raise RuntimeError("LLM client not initialized. Enable LLM in config first.")

        messages = []

        # 添加系统提示词
        if system_prompt and _HAS_LLMINFRA:
            messages.append(Message(
                role=MessageRole.SYSTEM,
                content=system_prompt
            ))

        # 添加对话历史
        if use_history and self._conversation_history:
            messages.extend(self._conversation_history)

        # 添加当前用户提示
        if _HAS_LLMINFRA:
            messages.append(Message(
                role=MessageRole.USER,
                content=prompt
            ))

        # 应用人格影响（如果启用）
        if self.config.enable_personality_influence and self._personality:
            messages = self._apply_personality_to_messages(messages)

        # 意图路由
        if use_router and self._intent_router:
            classify_result = self._intent_router.classify(messages)
            path = self._intent_router.dispatcher.dispatch(classify_result)

            request = self._ChatRequest(
                model=kwargs.get("model", self.config.llm_model),
                messages=messages,
                temperature=kwargs.get("temperature", self.config.llm_temperature),
                max_tokens=kwargs.get("max_tokens", self.config.llm_max_tokens),
            )

            route_result = await self._intent_router.execute_path(
                path=path,
                request=request,
                fast_executor=self._llm_client.chat_fast,
                deep_executor=self._llm_client.chat_deep,
                rag_executor=self._llm_client.chat_rag,
                tool_executor=self._llm_client.chat_tool,
                fallback_executor=self._llm_client.chat_fallback,
            )

            if not route_result.success:
                logger.warning(
                    f"All paths failed for intent={classify_result.intent.value}, "
                    f"degradation={route_result.degradation_path.value if route_result.degradation_path else 'none'}"
                )
                # 最终 Fallback
                response = await self._llm_client.chat_fallback(request)
            else:
                response = route_result.response

        else:
            # 传统单一路径（无路由）
            response = await self._llm_client.chat(
                messages=messages,
                model=kwargs.get("model", self.config.llm_model),
                temperature=kwargs.get("temperature", self.config.llm_temperature),
                max_tokens=kwargs.get("max_tokens", self.config.llm_max_tokens),
                use_cache=kwargs.get("use_cache", self.config.enable_llm_cache),
            )

        # 更新对话历史
        if use_history and _HAS_LLMINFRA:
            self._conversation_history.append(Message(
                role=MessageRole.USER,
                content=prompt
            ))
            self._conversation_history.append(Message(
                role=MessageRole.ASSISTANT,
                content=response.content
            ))

        # 记录到记忆
        if record_to_memory and self._meta_soul and self.config.auto_memory_recording:
            self._record_to_memory(prompt, response)

        # M9a: 经验-记忆闭环
        if self._experience_loop:
            import asyncio
            asyncio.create_task(
                self._experience_loop.on_interaction_complete(
                    prompt, response,
                    store=self._meta_soul.store_v2 if self._meta_soul else None,
                    personality=self._personality,
                )
            )

        return response

    def _apply_personality_to_messages(self, messages: List[Any]) -> List[Any]:
        """
        应用人格影响到消息（M8 P4 升级版）

        使用 PersonalityMatrix + DynamicAdjuster + PersonalityInjector
        替代旧的生硬参数注入
        """
        if not self._personality or not _HAS_SOULTEAM:
            return messages

        try:
            from packages.MetaSoul.personality import BigFiveTraits
            from packages.MetaSoul.personality.personality_matrix import (
                PersonalityMatrix, DynamicAdjuster, PersonalityInjector
            )
        except ImportError:
            try:
                from MetaSoul.personality import BigFiveTraits
                from MetaSoul.personality.personality_matrix import (
                    PersonalityMatrix, DynamicAdjuster, PersonalityInjector
                )
            except ImportError:
                return messages

        # 获取当前人格值
        traits = {}
        for trait in BigFiveTraits:
            traits[trait.value] = self._personality.get_trait(trait)

        # 懒初始化 M8 P4 组件
        if not hasattr(self, '_personality_matrix'):
            self._personality_matrix = PersonalityMatrix(baseline=traits)
            self._personality_adjuster = DynamicAdjuster(self._personality_matrix)
            self._personality_injector = PersonalityInjector()

        # 提取最后一条用户消息
        last_user_msg = ""
        for msg in reversed(messages):
            if hasattr(msg, 'role') and str(msg.role) == 'user':
                last_user_msg = msg.content if hasattr(msg, 'content') else str(msg)
                break

        # 场景检测 + 动态调整
        scenario = self._personality_adjuster.detect_scenario(last_user_msg)
        self._personality_matrix.set_scenario(scenario)
        self._personality_adjuster.on_new_turn(last_user_msg)

        # 获取场景有效人格
        effective_traits = self._personality_matrix.get_effective_traits()

        # 生成人格画像叙述
        persona_prompt = self._personality_injector.to_system_prompt(
            effective_traits, scenario
        )

        # 注入到消息中（作为额外的 system 消息）
        if _HAS_LLMINFRA:
            persona_msg = Message(
                role=MessageRole.SYSTEM,
                content=persona_prompt
            )
            # 插入到第一条 system 之后
            insert_idx = 0
            for i, m in enumerate(messages):
                if hasattr(m, 'role') and str(m.role) == 'system':
                    insert_idx = i + 1
            messages.insert(insert_idx, persona_msg)

        return messages

    def _record_to_memory(self, prompt: str, response: Any) -> None:
        """记录对话到记忆"""
        if not self._meta_soul or not _HAS_SOULTEAM:
            return

        # 记录用户输入
        self._meta_soul.store_memory(
            content=f"User: {prompt}",
            memory_type=self.config.memory_type_for_conversation,
            metadata={
                "type": "user_input",
                "agent_id": self.config.agent_id,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # 记录助手响应
        self._meta_soul.store_memory(
            content=f"Assistant: {response.content}",
            memory_type=self.config.memory_type_for_conversation,
            metadata={
                "type": "assistant_response",
                "agent_id": self.config.agent_id,
                "timestamp": datetime.now().isoformat(),
                "model": response.model,
                "provider": response.provider,
                "cost": response.cost,
            }
        )

        # 记录工作记忆（当前正在进行的对话）
        self._meta_soul.store_memory(
            content=f"Conversation turn: User asked, Assistant replied.",
            memory_type=MemoryType.WORKING,
            metadata={
                "type": "conversation_turn",
                "agent_id": self.config.agent_id,
            }
        )

    @property
    def intent_router(self):
        """获取意图路由器"""
        return self._intent_router

    # ====================
    # MetaSoul 访问器
    # ====================

    @property
    def memory(self) -> Optional[MetaSoul]:
        """获取记忆系统"""
        return self._meta_soul

    @property
    def personality(self) -> Optional[Personality]:
        """获取人格系统"""
        return self._personality

    def remember(self, content: str, memory_type: Any = None, **metadata) -> str:
        """
        手动存储记忆

        Args:
            content: 记忆内容
            memory_type: 记忆类型
            **metadata: 元数据

        Returns:
            str: 记忆 ID
        """
        if not self._meta_soul:
            raise RuntimeError("Memory system not initialized. Enable memory in config first.")

        return self._meta_soul.store_memory(
            content=content,
            memory_type=memory_type or self.config.memory_type_for_conversation,
            metadata=metadata
        )

    def recall(self, query: str, limit: int = 5, **kwargs) -> List[Any]:
        """
        检索记忆

        Args:
            query: 查询内容
            limit: 返回结果数量
            **kwargs: 其他参数

        Returns:
            List[Any]: 记忆列表
        """
        if not self._meta_soul:
            return []

        return self._meta_soul.retrieve(query=query, limit=limit, **kwargs)

    # ====================
    # MCP 访问器
    # ====================
    
    @property
    def protocol(self) -> Optional[MCPProtocol]:
        """获取 MCP 协议"""
        return self._protocol
    
    @property
    def session_manager(self) -> Optional[MCPSessionManager]:
        """获取会话管理器"""
        return self._session_manager
    
    @property
    def handler_registry(self) -> Optional[MCPHandlerRegistry]:
        """获取处理器注册表"""
        return self._handler_registry
    
    @property
    def agent_registry(self) -> Optional[AgentRegistry]:
        """获取 Agent 注册表"""
        return self._agent_registry
    
    # ====================
    # Hooks 访问器
    # ====================
    
    @property
    def hook_manager(self) -> Optional[HookManager]:
        """获取钩子管理器"""
        return self._hook_manager
    
    @property
    def lifecycle_manager(self) -> Optional[LifecycleManager]:
        """获取生命周期管理器"""
        return self._lifecycle_manager
    
    @property
    def metrics(self) -> Optional[MetricsHook]:
        """获取指标钩子"""
        return self._metrics_hook
    
    # ====================
    # Awakening 访问器
    # ====================
    
    @property
    def awakening(self) -> Optional[AwakeningAdapter]:
        """获取觉醒适配器"""
        return self._awakening_adapter
    
    @property
    def capabilities(self) -> Optional[CapabilityRegistry]:
        """获取能力注册表"""
        return self._capability_registry
    
    @property
    def evolution(self) -> Optional[EvolutionEngine]:
        """获取进化引擎"""
        return self._evolution_engine
    
    # ====================
    # Collaboration 访问器
    # ====================
    
    @property
    def collaboration_protocol(self) -> Optional[CollaborationProtocol]:
        """获取协作协议"""
        return self._collaboration_protocol
    
    @property
    def negotiator(self) -> Optional[CollaborationNegotiator]:
        """获取协商器"""
        return self._negotiator
    
    @property
    def task_router(self) -> Optional[TaskRouter]:
        """获取任务路由器"""
        return self._task_router
    
    # ====================
    # 便捷方法
    # ====================
    
    def register_handler(
        self,
        method: str,
        handler: Callable,
        **kwargs
    ) -> None:
        """
        注册 MCP 处理器
        
        Args:
            method: 方法名
            handler: 处理函数
            **kwargs: 其他参数
        """
        if self._handler_registry:
            self._handler_registry.register(method, handler, **kwargs)
    
    def register_hook(
        self,
        event: LifecycleEvent,
        handler: Callable,
        **kwargs
    ) -> None:
        """
        注册生命周期钩子
        
        Args:
            event: 生命周期事件
            handler: 处理函数
            **kwargs: 其他参数
        """
        if self._hook_manager:
            self._hook_manager.register(event.value, handler, **kwargs)
    
    def register_agent(
        self,
        metadata: AgentMetadata,
        endpoint: Optional[str] = None
    ) -> Optional[RegisteredAgent]:
        """
        注册 Agent
        
        Args:
            metadata: Agent 元数据
            endpoint: 连接端点
            
        Returns:
            Optional[RegisteredAgent]: 注册的 Agent
        """
        if self._agent_registry:
            return self._agent_registry.register(metadata, endpoint)
        return None
    
    async def emit_lifecycle_event(
        self,
        event: LifecycleEvent,
        **data
    ) -> None:
        """
        触发生命周期事件
        
        Args:
            event: 生命周期事件
            **data: 事件数据
        """
        if self._lifecycle_manager:
            await self._hook_manager.trigger(
                event_name=event.value,
                data=data,
                source=self.config.agent_id,
            )
    
    def route_task(
        self,
        task_type: str,
        **kwargs
    ) -> Optional[TaskRoute]:
        """
        路由任务
        
        Args:
            task_type: 任务类型
            **kwargs: 其他参数
            
        Returns:
            Optional[TaskRoute]: 路由结果
        """
        if self._task_router:
            return self._task_router.route(task_type, **kwargs)
        return None
    
    def create_collaboration_request(
        self,
        task_type: str,
        task_description: str,
        **kwargs
    ) -> Optional[CollaborationRequest]:
        """
        创建协作请求
        
        Args:
            task_type: 任务类型
            task_description: 任务描述
            **kwargs: 其他参数
            
        Returns:
            Optional[CollaborationRequest]: 协作请求
        """
        if self._collaboration_protocol:
            return self._collaboration_protocol.create_request(
                requester_id=self.config.agent_id,
                requester_name=self.config.agent_name,
                task_type=task_type,
                task_description=task_description,
                **kwargs
            )
        return None
    
    def get_full_status(self) -> Dict[str, Any]:
        """
        获取完整状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        status = {
            "agent_id": self.config.agent_id,
            "agent_name": self.config.agent_name,
            "agent_type": self.config.agent_type,
            "timestamp": datetime.now().isoformat(),
        }
        
        # MCP 状态
        if self._session_manager:
            status["mcp"] = self._session_manager.get_stats()
        
        # Hooks 状态
        if self._hook_manager:
            status["hooks"] = self._hook_manager.get_stats()
        
        # Metrics 状态
        if self._metrics_hook:
            status["metrics"] = self._metrics_hook.get_summary()
        
        # Awakening 状态
        if self._awakening_adapter:
            status["awakening"] = self._awakening_adapter.get_info()
        
        # Evolution 状态
        if self._evolution_engine:
            status["evolution"] = self._evolution_engine.get_progress(
                self.config.agent_id
            )
        
        # Agent Registry 状态
        if self._agent_registry:
            status["registry"] = self._agent_registry.get_stats()
        
        # Collaboration 状态
        if self._negotiator:
            status["collaboration"] = self._negotiator.get_stats()
        
        if self._task_router:
            status["routing"] = self._task_router.get_stats()

        if self._intent_router:
            status["intent_router"] = self._intent_router.stats

        return status
    
    def reset(self) -> None:
        """重置 ZenAgent"""
        # 重置所有模块
        if self._hook_manager:
            self._hook_manager.reset_once_hooks()
            self._hook_manager.clear_history()
        
        if self._metrics_hook:
            self._metrics_hook.reset()
        
        if self._rate_limit_hook:
            self._rate_limit_hook.reset()
        
        if self._monitoring_hook:
            self._monitoring_hook.clear_alerts()
        
        if self._awakening_adapter:
            self._awakening_adapter.reset()
        
        if self._evolution_engine:
            self._evolution_engine.reset(self.config.agent_id)


# 全局 ZenAgent 实例
_default_agent: Optional[ZenAgent] = None


def get_zenaagent(config: Optional[ZenAgentConfig] = None) -> ZenAgent:
    """
    获取 ZenAgent 实例
    
    Args:
        config: 配置对象
        
    Returns:
        ZenAgent: ZenAgent 实例
    """
    global _default_agent
    if _default_agent is None:
        _default_agent = ZenAgent(config)
    return _default_agent


def create_zenaagent(**kwargs) -> ZenAgent:
    """
    创建新的 ZenAgent 实例
    
    Args:
        **kwargs: 配置参数
        
    Returns:
        ZenAgent: 新的 ZenAgent 实例
    """
    config = ZenAgentConfig(**kwargs)
    return ZenAgent(config)
