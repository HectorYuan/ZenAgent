import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from hooks.hook_manager import HookManager, HookPriority

class TestHookManager:
    """钩子管理器测试"""
    
    def test_manager_creation(self):
        """测试管理器创建"""
        manager = HookManager()
        assert manager is not None
    
    def test_manager_has_register(self):
        """测试注册方法存在"""
        manager = HookManager()
        assert hasattr(manager, 'register')
    
    def test_manager_has_trigger(self):
        """测试触发方法存在"""
        manager = HookManager()
        assert hasattr(manager, 'trigger')

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
