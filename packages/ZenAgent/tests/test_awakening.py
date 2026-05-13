import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from awakening.adapter import AwakeningAdapter, AwakeningState
from awakening.capabilities import AwakeningCapability
from awakening.evolution import EvolutionStage

class TestAwakeningAdapter:
    """Awakening适配器测试"""
    
    def test_adapter_creation(self):
        """测试适配器创建"""
        adapter = AwakeningAdapter()
        assert adapter is not None
        assert hasattr(adapter, 'state')
    
    def test_adapter_has_capability(self):
        """测试能力检查"""
        adapter = AwakeningAdapter()
        # 应该有has_capability方法
        assert hasattr(adapter, 'has_capability')
    
    def test_adapter_awaken(self):
        """测试觉醒方法"""
        adapter = AwakeningAdapter()
        # awaken方法存在
        assert hasattr(adapter, 'awaken')
        # 调用它不应该报错
        adapter.awaken()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
