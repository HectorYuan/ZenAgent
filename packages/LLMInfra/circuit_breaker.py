"""
熔断器模块

设计依据: E2E_OPTIMIZATION_DESIGN §模块5 - 熔断保护与降级开关

三级熔断状态: 关闭(CLOSED) → 打开(OPEN) → 半开(HALF_OPEN)
触发条件: 连续失败达到阈值 或 错误率超过阈值
"""

import asyncio
import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"        # 正常: 所有请求通过
    OPEN = "open"            # 熔断: 所有请求被拒绝
    HALF_OPEN = "half_open"  # 半开: 允许少量试探请求


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5              # 连续失败触发熔断
    error_rate_threshold: float = 0.3       # 错误率阈值 (30%)
    timeout_rate_threshold: float = 0.5     # 超时率阈值 (50%)
    recovery_timeout: float = 30.0          # 半开恢复等待时间（秒）
    half_open_max_calls: int = 3            # 半开状态最大试探次数
    window_size: int = 20                   # 错误率计算窗口大小


@dataclass
class CircuitBreakerStats:
    """熔断器统计"""
    total_calls: int = 0
    success_calls: int = 0
    failure_calls: int = 0
    timeout_calls: int = 0
    rejected_calls: int = 0
    state_transitions: int = 0
    last_state_change: float = 0.0
    consecutive_failures: int = 0


class CircuitBreakerOpenError(Exception):
    """熔断器打开异常"""
    pass


class CircuitBreaker:
    """
    熔断器

    保护下游服务免受级联故障：
    - CLOSED: 正常状态，监控错误率
    - OPEN: 熔断状态，快速失败
    - HALF_OPEN: 试探状态，允许少量请求
    """

    def __init__(self, name: str = "default", config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()

        # 滑动窗口记录（最近 N 次调用的结果）
        self._window: list[bool] = []  # True=成功, False=失败
        self._open_since: float = 0.0
        self._half_open_calls: int = 0

    @property
    def state(self) -> CircuitState:
        """当前状态"""
        return self._state

    def _transition_to(self, new_state: CircuitState):
        """状态转换"""
        if self._state == new_state:
            return
        old_state = self._state
        self._state = new_state
        self._stats.state_transitions += 1
        self._stats.last_state_change = time.monotonic()
        logger.info(f"CircuitBreaker '{self.name}': {old_state.value} -> {new_state.value}")

        if new_state == CircuitState.OPEN:
            self._open_since = time.monotonic()
            self._half_open_calls = 0

    def _record_result(self, success: bool, is_timeout: bool = False):
        """记录调用结果"""
        self._stats.total_calls += 1

        if success:
            self._stats.success_calls += 1
            self._stats.consecutive_failures = 0
            self._window.append(True)
        else:
            self._stats.failure_calls += 1
            self._stats.consecutive_failures += 1
            self._window.append(False)
            if is_timeout:
                self._stats.timeout_calls += 1

        # 维持窗口大小
        if len(self._window) > self._config.window_size:
            self._window = self._window[-self._config.window_size:]

    def _check_state(self):
        """检查并更新状态"""
        if self._state == CircuitState.CLOSED:
            self._check_closed_state()
        elif self._state == CircuitState.OPEN:
            self._check_open_state()
        # HALF_OPEN 状态由 call() 方法管理

    def _check_closed_state(self):
        """检查是否应从 CLOSED 转为 OPEN"""
        # 连续失败检查
        if self._stats.consecutive_failures >= self._config.failure_threshold:
            self._transition_to(CircuitState.OPEN)
            return

        # 错误率检查（窗口满时才计算）
        if len(self._window) >= self._config.window_size:
            error_rate = self._window.count(False) / len(self._window)
            if error_rate >= self._config.error_rate_threshold:
                self._transition_to(CircuitState.OPEN)
                return

            # 超时率检查
            if self._stats.timeout_calls > 0:
                timeout_rate = self._stats.timeout_calls / self._stats.total_calls
                if timeout_rate >= self._config.timeout_rate_threshold:
                    self._transition_to(CircuitState.OPEN)

    def _check_open_state(self):
        """检查是否应从 OPEN 转为 HALF_OPEN"""
        elapsed = time.monotonic() - self._open_since
        if elapsed >= self._config.recovery_timeout:
            self._transition_to(CircuitState.HALF_OPEN)

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过熔断器调用函数

        Args:
            func: 要调用的异步函数
            *args, **kwargs: 函数参数

        Returns:
            函数返回值

        Raises:
            CircuitBreakerOpenError: 熔断器打开时
        """
        async with self._lock:
            self._check_state()

            if self._state == CircuitState.OPEN:
                self._stats.rejected_calls += 1
                raise CircuitBreakerOpenError(
                    f"CircuitBreaker '{self.name}' is OPEN. "
                    f"Recovery in {self._recovery_remaining():.1f}s"
                )

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self._config.half_open_max_calls:
                    self._stats.rejected_calls += 1
                    raise CircuitBreakerOpenError(
                        f"CircuitBreaker '{self.name}' is HALF_OPEN, max probes reached"
                    )
                self._half_open_calls += 1

        # 在锁外执行实际调用
        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                self._record_result(True)
                if self._state == CircuitState.HALF_OPEN:
                    # 半开状态下成功，关闭熔断器
                    self._transition_to(CircuitState.CLOSED)
                    self._window.clear()
                else:
                    self._check_state()
            return result
        except Exception as e:
            is_timeout = "timeout" in type(e).__name__.lower() or "TimeoutError" in type(e).__name__
            async with self._lock:
                self._record_result(False, is_timeout)
                if self._state == CircuitState.HALF_OPEN:
                    # 半开状态下失败，重新打开熔断器
                    self._transition_to(CircuitState.OPEN)
                else:
                    self._check_state()
            raise

    def record_success(self):
        """手动记录成功"""
        self._record_result(True)
        self._check_state()

    def record_failure(self, is_timeout: bool = False):
        """手动记录失败"""
        self._record_result(False, is_timeout)
        self._check_state()

    def _recovery_remaining(self) -> float:
        """剩余恢复时间"""
        elapsed = time.monotonic() - self._open_since
        return max(0.0, self._config.recovery_timeout - elapsed)

    def get_state(self) -> CircuitState:
        """获取当前状态"""
        return self._state

    def get_stats(self) -> dict:
        """获取统计信息"""
        error_rate = 0.0
        if self._window:
            error_rate = self._window.count(False) / len(self._window)

        return {
            "name": self.name,
            "state": self._state.value,
            "total_calls": self._stats.total_calls,
            "success_calls": self._stats.success_calls,
            "failure_calls": self._stats.failure_calls,
            "timeout_calls": self._stats.timeout_calls,
            "rejected_calls": self._stats.rejected_calls,
            "consecutive_failures": self._stats.consecutive_failures,
            "error_rate": round(error_rate, 4),
            "state_transitions": self._stats.state_transitions,
            "recovery_remaining": round(self._recovery_remaining(), 1),
        }

    def reset(self):
        """重置熔断器"""
        self._state = CircuitState.CLOSED
        self._stats = CircuitBreakerStats()
        self._window.clear()
        self._open_since = 0.0
        self._half_open_calls = 0
