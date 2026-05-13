"""
Context Compaction 单元测试
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.Runtime.context_compaction.manager import ContextManager, ContextConfig, CompressionLevel


class TestContextManager:
    """ContextManager 测试"""
    
    def setup_method(self):
        self.manager = ContextManager(
            config=ContextConfig(
                max_tokens=80000,
                auto_compress=True,
                compression_level=CompressionLevel.MEDIUM
            )
        )
    
    def test_add_message(self):
        """测试添加消息"""
        msg = {"role": "user", "content": "Hello"}
        stats = self.manager.add_message(msg)
        assert stats is not None
    
    def test_get_messages(self):
        """测试获取消息"""
        self.manager.add_message({"role": "user", "content": "Test"})
        messages = self.manager.get_messages()
        assert len(messages) >= 1
    
    def test_compression_stats(self):
        """测试压缩统计"""
        stats = self.manager.get_stats()
        assert hasattr(stats, "current_tokens")
        assert hasattr(stats, "message_count")
    
    def test_clear(self):
        """测试清空"""
        self.manager.add_message({"role": "user", "content": "Test"})
        self.manager.clear()
        assert len(self.manager.get_messages()) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
