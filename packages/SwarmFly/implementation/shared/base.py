"""
FLY深度实现 - 共享基础类定义
"""

from datetime import datetime
from typing import Any, Dict, Optional, List
from enum import Enum
import uuid
import json


class SwarmFlyError(Exception):
    """SwarmFly基础异常类"""
    def __init__(self, message: str, code: str = None, details: Dict = None):
        super().__init__(message)
        self.message = message
        self.code = code or "SWARMFLY_ERROR"
        self.details = details or {}
        self.timestamp = datetime.now()


class ValidationError(SwarmFlyError):
    """验证错误"""
    def __init__(self, message: str, field: str = None, details: Dict = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field


class ConfigurationError(SwarmFlyError):
    """配置错误"""
    def __init__(self, message: str, config_key: str = None, details: Dict = None):
        super().__init__(message, "CONFIG_ERROR", details)
        self.config_key = config_key


class ResourceError(SwarmFlyError):
    """资源错误"""
    def __init__(self, message: str, resource_id: str = None, details: Dict = None):
        super().__init__(message, "RESOURCE_ERROR", details)
        self.resource_id = resource_id


class BaseModel:
    """基础数据模型类"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', str(uuid.uuid4()))
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.metadata = kwargs.get('metadata', {})
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, Enum):
                result[key] = value.value
            elif not key.startswith('_'):
                result[key] = value
        return result
    
    def to_json(self) -> str:
        """转换为JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BaseModel':
        """从字典创建"""
        return cls(**data)
    
    def update(self, **kwargs):
        """更新字段"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id})"


class EnumSerializer(json.JSONEncoder):
    """Enum序列化器"""
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
