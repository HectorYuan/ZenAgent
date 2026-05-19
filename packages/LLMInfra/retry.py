"""
重试机制工具类

提供指数退避重试、超时控制等通用能力
"""

import asyncio
import logging
from typing import Callable, TypeVar, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryConfig:
    """重试配置"""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retry_exceptions: Optional[Tuple[type, ...]] = None,
    ):
        """
        初始化重试配置

        Args:
            max_attempts: 最大尝试次数
            initial_delay: 初始延迟（秒）
            max_delay: 最大延迟（秒）
            backoff_factor: 退避因子
            jitter: 是否添加随机抖动
            retry_exceptions: 需要重试的异常类型（默认所有异常）
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retry_exceptions = retry_exceptions or (Exception,)

    def calculate_delay(self, attempt: int) -> float:
        """
        计算第 N 次尝试后的延迟

        Args:
            attempt: 当前尝试次数（从 0 开始）

        Returns:
            延迟秒数
        """
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            import random
            delay = delay * (0.5 + random.random())

        return delay

    def should_retry(self, exception: Exception) -> bool:
        """
        判断是否应该重试

        Args:
            exception: 发生的异常

        Returns:
            是否应该重试
        """
        return isinstance(exception, self.retry_exceptions)


async def with_retry(
    func: Callable[..., Any],
    config: Optional[RetryConfig] = None,
    *args,
    **kwargs,
) -> Any:
    """
    带重试机制的异步函数调用

    Args:
        func: 要执行的异步函数
        config: 重试配置
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        函数执行结果

    Raises:
        最后一次尝试的异常（如果所有尝试都失败）
    """
    if config is None:
        config = RetryConfig()

    last_exception: Optional[Exception] = None

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e

            if not config.should_retry(e):
                logger.warning(f"Not retrying exception type: {type(e).__name__}")
                raise

            if attempt < config.max_attempts - 1:
                delay = config.calculate_delay(attempt)
                logger.warning(
                    f"Attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"All {config.max_attempts} attempts failed. Last error: {e}"
                )

    if last_exception:
        raise last_exception
    raise RuntimeError("Retry failed with no exception")


class RetryMixin:
    """重试混合类

    可继承此类为 Provider 添加重试能力
    """

    def __init__(self, retry_config: Optional[RetryConfig] = None):
        self._retry_config = retry_config or RetryConfig()

    async def _execute_with_retry(
        self,
        func: Callable[..., Any],
        *args,
        retry_config: Optional[RetryConfig] = None,
        **kwargs,
    ) -> Any:
        """
        带重试地执行函数

        Args:
            func: 异步函数
            *args: 位置参数
            retry_config: 覆盖默认重试配置
            **kwargs: 关键字参数

        Returns:
            执行结果
        """
        config = retry_config or self._retry_config
        return await with_retry(func, config, *args, **kwargs)


# 预设的常用重试配置

# 快速重试：适合网络波动（3次，1s/2s/4s）
FAST_RETRY = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=4.0,
    backoff_factor=2.0,
)

# 标准重试：适合一般 API 调用（4次，1s/2s/4s/8s）
STANDARD_RETRY = RetryConfig(
    max_attempts=4,
    initial_delay=1.0,
    max_delay=8.0,
    backoff_factor=2.0,
)

# 慢重试：适合复杂/长时任务（5次，2s/4s/8s/16s）
SLOW_RETRY = RetryConfig(
    max_attempts=5,
    initial_delay=2.0,
    max_delay=16.0,
    backoff_factor=2.0,
)

# 仅重试特定网络异常
NETWORK_RETRY_EXCEPTIONS = (
    aiohttp.ClientError if 'aiohttp' in globals() else Exception,
    asyncio.TimeoutError,
    ConnectionError,
)

# 网络专用重试配置
NETWORK_RETRY = RetryConfig(
    max_attempts=4,
    initial_delay=0.5,
    max_delay=5.0,
    backoff_factor=1.5,
    retry_exceptions=NETWORK_RETRY_EXCEPTIONS,
)
