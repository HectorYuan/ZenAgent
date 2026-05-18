"""
异常处理模块
"""


class LLMError(Exception):
    """LLM 基础异常"""
    pass


class ProviderError(LLMError):
    """提供商异常"""
    
    def __init__(self, provider: str, message: str, status_code: int = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")


class RateLimitError(ProviderError):
    """限流异常"""
    
    def __init__(self, provider: str, message: str, retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(provider, message, 429)


class AuthenticationError(ProviderError):
    """认证异常"""
    
    def __init__(self, provider: str, message: str):
        super().__init__(provider, message, 401)


class InvalidRequestError(ProviderError):
    """无效请求异常"""
    
    def __init__(self, provider: str, message: str):
        super().__init__(provider, message, 400)


class ModelNotFoundError(ProviderError):
    """模型未找到异常"""
    
    def __init__(self, provider: str, model: str):
        super().__init__(provider, f"Model '{model}' not found", 404)
        self.model = model


class TimeoutError(ProviderError):
    """超时异常"""
    
    def __init__(self, provider: str, timeout: int):
        super().__init__(provider, f"Request timeout after {timeout}s", 408)
        self.timeout = timeout


class ServiceUnavailableError(ProviderError):
    """服务不可用异常"""
    
    def __init__(self, provider: str, message: str = "Service unavailable"):
        super().__init__(provider, message, 503)


class FallbackError(LLMError):
    """降级异常"""
    
    def __init__(self, original_error: Exception, fallback_success: bool = False):
        self.original_error = original_error
        self.fallback_success = fallback_success
        super().__init__(f"Fallback: {str(original_error)}")
