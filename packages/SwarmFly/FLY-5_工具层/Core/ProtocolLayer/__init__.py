"""
协议层 (Protocol Layer)

提供工具调用协议:
- 调用协议
- 响应协议
- 超时处理
- 重试策略
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import asyncio
import time

logger = logging.getLogger(__name__)


class CallStatus(Enum):
    """调用状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class CallRequest:
    """调用请求"""
    request_id: str
    tool_id: str
    method: str
    parameters: Dict[str, Any]
    timeout: float = 30.0
    retry_enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CallResult:
    """调用结果"""
    request_id: str
    tool_id: str
    status: CallStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RetryStrategy:
    """重试策略"""
    
    def __init__(
        self,
        max_retries: int = 3,
        backoff_multiplier: float = 2.0,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        retryable_errors: Optional[List[str]] = None
    ):
        self.max_retries = max_retries
        self.backoff_multiplier = backoff_multiplier
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.retryable_errors = retryable_errors or [
            'timeout', 'connection', 'unavailable', 'busy'
        ]
    
    def should_retry(self, error: str, retry_count: int) -> bool:
        """判断是否应该重试"""
        if retry_count >= self.max_retries:
            return False
        
        # 检查错误类型
        error_lower = error.lower()
        return any(e in error_lower for e in self.retryable_errors)
    
    def get_delay(self, retry_count: int) -> float:
        """获取重试延迟"""
        delay = self.initial_delay * (self.backoff_multiplier ** retry_count)
        return min(delay, self.max_delay)


class TimeoutHandler:
    """超时处理器"""
    
    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout
        self.active_calls: Dict[str, asyncio.Task] = {}
    
    async def call_with_timeout(
        self,
        coro: Callable,
        timeout: float,
        request_id: str
    ) -> Any:
        """带超时的调用"""
        try:
            result = await asyncio.wait_for(coro, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            # 取消任务
            if request_id in self.active_calls:
                self.active_calls[request_id].cancel()
            raise TimeoutError(f"Call {request_id} timed out after {timeout}s")
    
    def cancel(self, request_id: str):
        """取消调用"""
        if request_id in self.active_calls:
            self.active_calls[request_id].cancel()


class ToolCallProtocol:
    """
    工具调用协议
    
    提供标准化的工具调用流程:
    1. 参数验证
    2. 权限检查
    3. 资源分配
    4. 执行调用
    5. 超时处理
    6. 重试机制
    7. 结果返回
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 组件
        self.retry_strategy = RetryStrategy(
            max_retries=self.config.get('max_retries', 3),
            backoff_multiplier=self.config.get('backoff_multiplier', 2.0),
            initial_delay=self.config.get('initial_delay', 1.0)
        )
        
        self.timeout_handler = TimeoutHandler(
            default_timeout=self.config.get('default_timeout', 30.0)
        )
        
        # 工具执行器(需要外部注入)
        self.tool_executor: Optional[Callable] = None
        
        # 钩子
        self.pre_call_hooks: List[Callable] = []
        self.post_call_hooks: List[Callable] = []
        
        # 统计
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'timeouts': 0,
            'retries': 0
        }
    
    def set_executor(self, executor: Callable):
        """设置执行器"""
        self.tool_executor = executor
    
    async def call(
        self,
        tool_id: str,
        method: str,
        parameters: Dict[str, Any],
        timeout: Optional[float] = None,
        retry: bool = True
    ) -> CallResult:
        """
        执行工具调用
        
        Args:
            tool_id: 工具ID
            method: 方法名
            parameters: 参数
            timeout: 超时时间
            retry: 是否启用重试
            
        Returns:
            CallResult: 调用结果
        """
        request_id = f"{tool_id}:{method}:{int(time.time() * 1000)}"
        timeout = timeout or self.config.get('default_timeout', 30.0)
        
        self.stats['total_calls'] += 1
        
        # 创建请求
        request = CallRequest(
            request_id=request_id,
            tool_id=tool_id,
            method=method,
            parameters=parameters,
            timeout=timeout,
            retry_enabled=retry
        )
        
        # 执行前置钩子
        for hook in self.pre_call_hooks:
            try:
                await hook(request)
            except Exception as e:
                logger.error(f"Pre-call hook error: {e}")
        
        # 执行调用(带重试)
        result = await self._execute_with_retry(request)
        
        # 执行后置钩子
        for hook in self.post_call_hooks:
            try:
                await hook(request, result)
            except Exception as e:
                logger.error(f"Post-call hook error: {e}")
        
        return result
    
    async def _execute_with_retry(self, request: CallRequest) -> CallResult:
        """带重试的执行"""
        retry_count = 0
        last_error = None
        
        while retry_count <= self.retry_strategy.max_retries:
            start_time = time.time()
            
            try:
                # 执行调用
                result = await self.timeout_handler.call_with_timeout(
                    self._execute_call(request),
                    request.timeout,
                    request.request_id
                )
                
                execution_time = (time.time() - start_time) * 1000
                
                call_result = CallResult(
                    request_id=request.request_id,
                    tool_id=request.tool_id,
                    status=CallStatus.SUCCESS,
                    result=result,
                    execution_time_ms=execution_time,
                    retry_count=retry_count
                )
                
                self.stats['successful_calls'] += 1
                if retry_count > 0:
                    self.stats['retries'] += retry_count
                
                return call_result
                
            except TimeoutError as e:
                execution_time = (time.time() - start_time) * 1000
                last_error = str(e)
                
                self.stats['timeouts'] += 1
                
                call_result = CallResult(
                    request_id=request.request_id,
                    tool_id=request.tool_id,
                    status=CallStatus.TIMEOUT,
                    error=last_error,
                    execution_time_ms=execution_time,
                    retry_count=retry_count
                )
                
                # 检查是否重试
                if request.retry_enabled and self.retry_strategy.should_retry('timeout', retry_count):
                    retry_count += 1
                    delay = self.retry_strategy.get_delay(retry_count)
                    await asyncio.sleep(delay)
                    continue
                
                self.stats['failed_calls'] += 1
                return call_result
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                last_error = str(e)
                
                call_result = CallResult(
                    request_id=request.request_id,
                    tool_id=request.tool_id,
                    status=CallStatus.FAILED,
                    error=last_error,
                    execution_time_ms=execution_time,
                    retry_count=retry_count
                )
                
                # 检查是否重试
                if request.retry_enabled and self.retry_strategy.should_retry(last_error, retry_count):
                    retry_count += 1
                    delay = self.retry_strategy.get_delay(retry_count)
                    await asyncio.sleep(delay)
                    continue
                
                self.stats['failed_calls'] += 1
                return call_result
        
        # 达到最大重试次数
        return CallResult(
            request_id=request.request_id,
            tool_id=request.tool_id,
            status=CallStatus.FAILED,
            error=f"Max retries exceeded: {last_error}",
            retry_count=retry_count
        )
    
    async def _execute_call(self, request: CallRequest) -> Any:
        """执行调用"""
        if self.tool_executor:
            return await self.tool_executor(
                request.tool_id,
                request.method,
                request.parameters
            )
        
        # 默认实现: 返回模拟结果
        await asyncio.sleep(0.1)
        return {'status': 'success', 'data': request.parameters}
    
    async def batch_call(
        self,
        calls: List[Dict[str, Any]],
        max_parallel: int = 5
    ) -> List[CallResult]:
        """批量调用"""
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def call_with_limit(call_spec: Dict):
            async with semaphore:
                return await self.call(
                    tool_id=call_spec['tool_id'],
                    method=call_spec['method'],
                    parameters=call_spec.get('parameters', {}),
                    timeout=call_spec.get('timeout'),
                    retry=call_spec.get('retry', True)
                )
        
        tasks = [call_with_limit(c) for c in calls]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def add_pre_hook(self, hook: Callable):
        """添加前置钩子"""
        self.pre_call_hooks.append(hook)
    
    def add_post_hook(self, hook: Callable):
        """添加后置钩子"""
        self.post_call_hooks.append(hook)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        success_rate = 0.0
        if self.stats['total_calls'] > 0:
            success_rate = self.stats['successful_calls'] / self.stats['total_calls']
        
        return {
            **self.stats,
            'success_rate': success_rate
        }
