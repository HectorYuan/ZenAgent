"""
测试重试机制
"""

import pytest
import asyncio
from typing import Dict, Any

from ..retry import (
    RetryConfig,
    with_retry,
    RetryMixin,
    FAST_RETRY,
    STANDARD_RETRY,
    SLOW_RETRY,
    NETWORK_RETRY,
)


class TestRetryConfig:
    """测试重试配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.backoff_factor == 2.0

    def test_calculate_delay(self):
        """测试延迟计算"""
        config = RetryConfig(initial_delay=1.0, backoff_factor=2.0, jitter=False)

        # 指数退避: 1s, 2s, 4s...
        assert config.calculate_delay(0) == 1.0
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 4.0

    def test_max_delay(self):
        """测试最大延迟限制"""
        config = RetryConfig(initial_delay=1.0, max_delay=3.0, backoff_factor=2.0, jitter=False)

        # 应该被截断到 max_delay
        assert config.calculate_delay(0) == 1.0
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 3.0  # 本应 4s，被截断到 3s

    def test_jitter(self):
        """测试抖动添加"""
        config = RetryConfig(initial_delay=1.0, jitter=True)

        # 带抖动的延迟应该在 0.5-1.5 倍范围内
        delays = [config.calculate_delay(0) for _ in range(100)]
        assert all(0.5 <= d <= 1.5 for d in delays)
        # 确保不是所有延迟都相同（有随机性）
        assert len(set(delays)) > 1

    def test_should_retry(self):
        """测试应该重试的判断"""
        config = RetryConfig(retry_exceptions=(ValueError,))

        assert config.should_retry(ValueError()) is True
        assert config.should_retry(TypeError()) is False


@pytest.mark.asyncio
class TestWithRetry:
    """测试 with_retry 函数"""

    async def test_success_on_first_try(self):
        """测试第一次就成功"""
        call_count = 0

        async def succeed():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await with_retry(succeed, FAST_RETRY)
        assert result == "success"
        assert call_count == 1

    async def test_retry_and_success(self):
        """测试重试几次后成功"""
        call_count = 0

        async def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Try again")
            return "success"

        result = await with_retry(fail_twice, RetryConfig(max_attempts=3, initial_delay=0.01))
        assert result == "success"
        assert call_count == 3

    async def test_all_attempts_fail(self):
        """测试所有尝试都失败"""
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fail")

        with pytest.raises(ValueError, match="Always fail"):
            await with_retry(always_fail, RetryConfig(max_attempts=3, initial_delay=0.01))

        assert call_count == 3

    async def test_no_retry_on_other_exception(self):
        """测试不在重试列表中的异常不重试"""
        call_count = 0

        async def type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Not in retry list")

        config = RetryConfig(max_attempts=3, initial_delay=0.01, retry_exceptions=(ValueError,))

        with pytest.raises(TypeError, match="Not in retry list"):
            await with_retry(type_error, config)

        assert call_count == 1  # 不应该重试

    async def test_with_args_and_kwargs(self):
        """测试带参数的函数"""

        async def add(a: int, b: int) -> int:
            return a + b

        result = await with_retry(add, FAST_RETRY, 2, 3)
        assert result == 5

    async def test_preset_configs(self):
        """测试预设配置"""
        for config in [FAST_RETRY, STANDARD_RETRY, SLOW_RETRY, NETWORK_RETRY]:
            call_count = 0

            async def succeed():
                nonlocal call_count
                call_count += 1
                return "ok"

            result = await with_retry(succeed, config)
            assert result == "ok"
            assert call_count == 1


@pytest.mark.asyncio
class TestRetryMixin:
    """测试 RetryMixin 混合类"""

    class TestService(RetryMixin):
        """测试服务类"""

        def __init__(self):
            super().__init__(RetryConfig(max_attempts=3, initial_delay=0.01))
            self.call_count = 0

        async def operation(self):
            self.call_count += 1
            if self.call_count < 2:
                raise ValueError("Not yet")
            return "done"

    async def test_mixin_inheritance(self):
        """测试混合类继承"""
        service = self.TestService()

        result = await service._execute_with_retry(service.operation)
        assert result == "done"
        assert service.call_count == 2

    async def test_mixin_override_config(self):
        """测试覆盖重试配置"""
        service = self.TestService()
        service.call_count = 0

        custom_config = RetryConfig(max_attempts=5, initial_delay=0.01)

        async def fail_three_times():
            service.call_count += 1
            if service.call_count < 4:
                raise ValueError("Try again")
            return "done"

        result = await service._execute_with_retry(fail_three_times, retry_config=custom_config)
        assert result == "done"
        assert service.call_count == 4


@pytest.mark.asyncio
class TestNetworkRetry:
    """测试网络相关重试"""

    async def test_network_retry_timeout(self):
        """测试超时异常会被重试"""
        call_count = 0

        async def timeout_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncio.TimeoutError("Timeout")
            return "success"

        result = await with_retry(timeout_once, NETWORK_RETRY)
        assert result == "success"
        assert call_count == 2


class TestRetryDocExamples:
    """测试文档中的示例"""

    def test_preset_configs_exist(self):
        """测试所有预设配置都存在"""
        configs = [FAST_RETRY, STANDARD_RETRY, SLOW_RETRY, NETWORK_RETRY]
        for config in configs:
            assert isinstance(config, RetryConfig)
            assert config.max_attempts >= 1

    def test_retry_config_attributes(self):
        """测试配置属性"""
        config = NETWORK_RETRY
        assert hasattr(config, 'max_attempts')
        assert hasattr(config, 'initial_delay')
        assert hasattr(config, 'max_delay')
        assert hasattr(config, 'backoff_factor')
