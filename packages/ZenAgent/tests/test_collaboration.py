import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from collaboration.protocols import ProtocolType, MessagePriority
from collaboration.negotiator import CollaborationNegotiator
from collaboration.task_router import TaskRouter, RouteStrategy

class TestCollaboration:
    """协作测试"""
    
    def test_negotiator_creation(self):
        """测试协商器创建"""
        negotiator = CollaborationNegotiator()
        assert negotiator is not None
    
    def test_router_creation(self):
        """测试路由器创建"""
        router = TaskRouter()
        assert router is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
