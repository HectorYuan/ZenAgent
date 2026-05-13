"""
生命周期异常定义
"""


class LifecycleError(Exception):
    """生命周期基础异常"""
    pass


class InvalidTransitionError(LifecycleError):
    """无效状态转换异常"""
    
    def __init__(self, from_state: str, to_state: str, reason: str = ""):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        msg = f"Invalid transition from '{from_state}' to '{to_state}'"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class StateError(LifecycleError):
    """状态相关异常"""
    pass


class TransitionError(LifecycleError):
    """状态转换执行异常"""
    
    def __init__(self, state: str, action: str, reason: str = ""):
        self.state = state
        self.action = action
        self.reason = reason
        msg = f"Failed to perform '{action}' in state '{state}'"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class StateManagerError(LifecycleError):
    """状态管理器异常"""
    pass


class CallbackError(LifecycleError):
    """回调执行异常"""
    pass
