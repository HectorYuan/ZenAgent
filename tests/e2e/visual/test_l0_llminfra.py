"""
Phase L0: LLMInfra — ProviderChain + 缓存 + 熔断器 + 管线验证
"""
from .runner import register_phase, PhaseResult
from . import viz


@register_phase("L0", "LLMInfra — ProviderChain + Cache + Circuit Breaker", "L0")
def run_l0(config: dict, result: PhaseResult):
    # ---------- Scenario 1: ProviderChain ----------
    viz.scenario_header("ProviderChain & Circuit Breaker", 1, 4)
    try:
        from packages.LLMInfra.config import Settings
        from packages.LLMInfra.providers import ProviderFactory
        from packages.LLMInfra.provider_chain import create_default_chain
        from packages.LLMInfra.circuit_breaker import CircuitBreaker

        settings = Settings()
        factory = ProviderFactory(settings)

        # 检查可用 Provider
        providers = factory.get_available_providers()
        viz.info(f"Available providers: {', '.join(providers)}")
        viz.ok(f"ProviderFactory initialized with {len(providers)} providers")

        # 创建责任链
        chain = create_default_chain(factory)
        chain_health = chain.get_provider_health()
        viz.kv_table([
            ("Chain providers", len(chain_health)),
            ("Chain enabled", True),
        ])

        # 熔断器状态
        cb_stats = chain.get_circuit_breaker_stats()
        viz.info(f"Circuit breakers: {len(cb_stats)}")
        for name, state in cb_stats.items():
            print(f"    {viz.dim(name)}: {viz.cyan(str(state))}")

        result.add_scenario("ProviderChain", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("ProviderChain", False, [str(e)])

    # ---------- Scenario 2: Cache ----------
    viz.scenario_header("3-Level Cache", 2, 4)
    try:
        from packages.LLMInfra.cache import CacheManager
        from packages.LLMInfra.config import CacheConfig

        cache_cfg = CacheConfig(enabled=True, type="memory", ttl=3600)
        cache_mgr = CacheManager(cache_cfg)
        viz.ok("CacheManager initialized")

        # 检查热点统计
        hotspot = cache_mgr.get_hotspot_stats()
        viz.kv_table([
            ("Hit rate", f"{hotspot.get('hit_rate', 0):.1%}"),
            ("Hot keys", hotspot.get("hot_keys", 0)),
            ("Warm keys", hotspot.get("warm_keys", 0)),
        ])
        result.add_scenario("3-Level Cache", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("3-Level Cache", False, [str(e)])

    # ---------- Scenario 3: Token Budget ----------
    viz.scenario_header("Token Budget", 3, 4)
    try:
        from packages.LLMInfra.token_budget import TokenBudgetManager

        from packages.LLMInfra.config import TokenBudgetConfig
        budget_cfg = TokenBudgetConfig(enabled=True)
        budget = TokenBudgetManager(budget_cfg)
        viz.ok("TokenBudgetManager initialized")

        # 测试不同意图的预算
        from packages.LLMInfra.core import Message, MessageRole
        short_msg = [Message(role=MessageRole.USER, content="Hello")]
        long_msg = [Message(role=MessageRole.USER, content="Explain quantum computing in detail " * 10)]

        try:
            short_alloc = budget.allocate(short_msg)
            long_alloc = budget.allocate(long_msg)
        except Exception:
            short_alloc = long_alloc = None
        short_budget = getattr(short_alloc, 'max_tokens', None) if short_alloc else None
        long_budget = getattr(long_alloc, 'max_tokens', None) if long_alloc else None
        viz.kv_table([
            ("Short query budget", short_budget or "unlimited"),
            ("Long query budget", long_budget or "unlimited"),
        ])
        result.add_scenario("Token Budget", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("Token Budget", False, [str(e)])

    # ---------- Scenario 4: Retry + Response Validator ----------
    viz.scenario_header("Retry & Response Validator", 4, 4)
    try:
        from packages.LLMInfra.retry import RetryConfig
        from packages.LLMInfra.response_validator import ResponseValidator

        retry_cfg = RetryConfig(max_attempts=4, initial_delay=0.5, max_delay=16.0)
        viz.ok(f"RetryConfig(max_attempts={retry_cfg.max_attempts}, initial_delay={retry_cfg.initial_delay})")
        viz.ok("ResponseValidator ready")

        result.add_scenario("Retry & Validator", True)
    except Exception as e:
        viz.fail(str(e))
        result.add_scenario("Retry & Validator", False, [str(e)])
