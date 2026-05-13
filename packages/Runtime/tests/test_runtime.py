import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from checkpoint.event_store import EventStore
from checkpoint.snapshot import SnapshotManager
from context_compaction.manager import ContextManager
from htl.handler import HTLHandler
from session.session import Session

class TestRuntime:
    """Runtime层测试"""
    
    def test_event_store_creation(self):
        """测试事件存储创建"""
        store = EventStore()
        assert store is not None
    
    def test_snapshot_manager(self):
        """测试快照管理器"""
        manager = SnapshotManager()
        assert manager is not None
    
    def test_context_manager(self):
        """测试上下文管理器"""
        manager = ContextManager()
        assert manager is not None
    
    def test_htl_handler(self):
        """测试HTL处理器"""
        handler = HTLHandler()
        assert handler is not None
    
    def test_session_creation(self):
        """测试会话创建"""
        session = Session()
        assert session is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
