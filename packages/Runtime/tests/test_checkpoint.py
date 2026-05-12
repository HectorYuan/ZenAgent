"""
Checkpoint 单元测试
"""

import pytest
import tempfile
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from checkpoint.event_store import EventStore
from checkpoint.snapshot import SnapshotManager, SnapshotType


class TestEventStore:
    """EventStore 测试"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.store = EventStore(self.temp_dir)
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_store_initialization(self):
        """测试存储初始化"""
        assert self.store is not None
        assert self.store.storage_path == self.temp_dir


class TestSnapshotManager:
    """SnapshotManager 测试"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = SnapshotManager(self.temp_dir)
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_manager_initialization(self):
        """测试管理器初始化"""
        assert self.manager is not None
        assert hasattr(self.manager, "_snapshots")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
