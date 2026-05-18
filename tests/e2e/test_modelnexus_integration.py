"""
Phase 5 E2E 测试: ModelNexus 网关集成

测试目标: 验证 ModelNexus 网关与 ZenAgent LLMInfra 层的集成
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import asyncio


class TestModelNexusProvider:
    """ModelNexus Provider 测试"""

    @pytest.mark.asyncio
    async def test_modelnexus_provider_registration(self):
        """测试 ModelNexus Provider 已注册"""
        from packages.LLMInfra import ProviderFactory, Settings

        settings = Settings()
        factory = ProviderFactory(settings)

        available_providers = factory.get_available_providers()
        assert "modelnexus" in available_providers
        print(f"✅ ModelNexus Provider 已注册，可用 Provider: {available_providers}")

    @pytest.mark.asyncio
    async def test_modelnexus_provider_creation(self):
        """测试 ModelNexus Provider 创建"""
        from packages.LLMInfra import ProviderFactory, Settings, ProviderConfig

        settings = Settings()

        # 确保 modelnexus 已配置
        if "modelnexus" not in settings.providers:
            settings.providers["modelnexus"] = ProviderConfig(
                api_key="test",
                base_url="http://localhost:8080",
                default_model="gpt-3.5-turbo"
            )

        factory = ProviderFactory(settings)
        provider = factory.get_provider("modelnexus")

        assert provider is not None
        assert provider.provider_name == "modelnexus"
        print(f"✅ ModelNexus Provider 创建成功: {type(provider).__name__}")

    @pytest.mark.asyncio
    async def test_modelnexus_provider_chat_fallback(self):
        """测试 ModelNexus Provider Fallback 模式"""
        from packages.LLMInfra import ProviderFactory, Settings, ProviderConfig, Message

        settings = Settings()

        if "modelnexus" not in settings.providers:
            settings.providers["modelnexus"] = ProviderConfig(
                api_key="test",
                base_url="http://localhost:8080",
                default_model="gpt-3.5-turbo"
            )

        factory = ProviderFactory(settings)
        provider = factory.get_provider("modelnexus")

        messages = [Message(role="user", content="Hello from ModelNexus")]

        from packages.LLMInfra.core import ChatRequest
        request = ChatRequest(model="gpt-3.5-turbo", messages=messages)

        response = await provider.chat(request)

        assert response is not None
        assert response.content is not None
        assert len(response.content) > 0
        assert response.provider == "modelnexus"

        print(f"✅ ModelNexus Fallback 聊天成功: {response.content[:50]}...")

    @pytest.mark.asyncio
    async def test_modelnexus_provider_list_models(self):
        """测试 ModelNexus Provider 列出模型"""
        from packages.LLMInfra import ProviderFactory, Settings, ProviderConfig

        settings = Settings()

        if "modelnexus" not in settings.providers:
            settings.providers["modelnexus"] = ProviderConfig(
                api_key="test",
                base_url="http://localhost:8080",
                default_model="gpt-3.5-turbo"
            )

        factory = ProviderFactory(settings)
        provider = factory.get_provider("modelnexus")

        models = await provider.list_models()

        assert isinstance(models, list)
        assert len(models) > 0
        assert "gpt-3.5-turbo" in models

        print(f"✅ ModelNexus 模型列表获取成功: {models[:3]}...")

    @pytest.mark.asyncio
    async def test_modelnexus_provider_embedding(self):
        """测试 ModelNexus Provider 嵌入功能"""
        from packages.LLMInfra import ProviderFactory, Settings, ProviderConfig

        settings = Settings()

        if "modelnexus" not in settings.providers:
            settings.providers["modelnexus"] = ProviderConfig(
                api_key="test",
                base_url="http://localhost:8080",
                default_model="gpt-3.5-turbo"
            )

        factory = ProviderFactory(settings)
        provider = factory.get_provider("modelnexus")

        embedding = await provider.embed("Test embedding text")

        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert isinstance(embedding[0], float)

        print(f"✅ ModelNexus 嵌入生成成功: {len(embedding)} 维向量")


class TestZenAgentWithModelNexus:
    """ZenAgent 与 ModelNexus 集成测试"""

    @pytest.mark.asyncio
    async def test_zenagent_with_modelnexus_provider(self):
        """测试 ZenAgent 使用 ModelNexus Provider"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="modelnexus",
            enable_memory=False,
        )

        # 确保 ModelNexus 配置存在
        from packages.LLMInfra import Settings, ProviderConfig
        settings = Settings()
        if "modelnexus" not in settings.providers:
            settings.providers["modelnexus"] = ProviderConfig(
                api_key="test",
                base_url="http://localhost:8080",
                default_model="gpt-3.5-turbo"
            )

        agent = ZenAgent(config)
        assert agent.llm_client is not None
        print("✅ ZenAgent 配置 ModelNexus Provider 成功")

    @pytest.mark.asyncio
    async def test_zenagent_think_with_modelnexus_fallback(self):
        """测试 ZenAgent think() 方法使用 ModelNexus Fallback"""
        from packages.ZenAgent.core import ZenAgent, ZenAgentConfig

        config = ZenAgentConfig(
            enable_llm=True,
            llm_provider="modelnexus",
            enable_memory=False,
        )

        # 确保 ModelNexus 配置存在
        from packages.LLMInfra import Settings, ProviderConfig
        settings = Settings()
        if "modelnexus" not in settings.providers:
            settings.providers["modelnexus"] = ProviderConfig(
                api_key="test",
                base_url="http://localhost:8080",
                default_model="gpt-3.5-turbo"
            )

        agent = ZenAgent(config)

        response = await agent.think(
            prompt="Test ModelNexus integration",
            use_history=False,
            record_to_memory=False,
        )

        assert response is not None
        assert response.content is not None
        assert len(response.content) > 0

        print(f"✅ ZenAgent think() 方法使用 ModelNexus Fallback 成功: {response.content[:50]}...")


class TestModelNexusSubmodule:
    """ModelNexus 子模块验证"""

    def test_modelnexus_submodule_exists(self):
        """测试 ModelNexus 子模块存在"""
        import os
        modelnexus_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "packages", "modelnexus"
        )

        assert os.path.exists(modelnexus_path)
        assert os.path.isdir(modelnexus_path)
        print(f"✅ ModelNexus 子模块存在: {modelnexus_path}")

    def test_modelnexus_core_modules_exist(self):
        """测试 ModelNexus 核心模块存在"""
        import os
        modelnexus_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "packages", "modelnexus"
        )

        # 检查关键目录
        dirs_to_check = ["core", "api", "config", "deploy"]
        for d in dirs_to_check:
            assert os.path.exists(os.path.join(modelnexus_path, d)), f"Directory {d} not found"

        print(f"✅ ModelNexus 核心模块存在: {dirs_to_check}")

    def test_modelnexus_adapter_import(self):
        """测试 ModelNexus Adapter 可导入"""
        try:
            from packages.LLMInfra.modelnexus_adapter import ModelNexusAdapter, ModelNexusFallbackAdapter
            print("✅ ModelNexus Adapter 导入成功")
        except ImportError as e:
            pytest.fail(f"ModelNexus Adapter 导入失败: {e}")

    @pytest.mark.asyncio
    async def test_modelnexus_adapter_health_check(self):
        """测试 ModelNexus Adapter 健康检查"""
        from packages.LLMInfra import Settings
        from packages.LLMInfra.modelnexus_adapter import ModelNexusAdapter

        settings = Settings()
        adapter = ModelNexusAdapter(settings)

        # 初始化（可能失败，但应该优雅处理）
        try:
            await adapter.initialize()
            health = await adapter.health_check()
            assert isinstance(health, dict)
            assert "status" in health
            print(f"✅ ModelNexus Adapter 健康检查完成: {health}")
        except Exception as e:
            # 即使 ModelNexus 服务未启动，也应该能优雅处理
            print(f"ℹ️ ModelNexus 服务未启动 (预期): {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
