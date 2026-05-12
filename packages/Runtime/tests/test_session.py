"""
Session 单元测试
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from session.session import Session, SessionState, SessionEvent


class TestSession:
    """Session 测试"""
    
    def setup_method(self):
        self.session = Session(user_id="user-1")
    
    def test_initial_state(self):
        """测试初始状态"""
        assert self.session.state == SessionState.INITIAL
    
    def test_start_session(self):
        """测试启动会话"""
        self.session.start()
        assert self.session.state == SessionState.ACTIVE
    
    def test_pause_resume(self):
        """测试暂停恢复"""
        self.session.start()
        self.session.pause()
        assert self.session.state == SessionState.SUSPENDED
        self.session.resume()
        assert self.session.state == SessionState.ACTIVE
    
    def test_complete_session(self):
        """测试完成会话"""
        self.session.start()
        self.session.complete()
        assert self.session.state == SessionState.COMPLETED
    
    def test_terminate_session(self):
        """测试终止会话"""
        self.session.start()
        self.session.terminate()
        assert self.session.state == SessionState.TERMINATED
    
    def test_is_active(self):
        """测试活跃状态"""
        assert self.session.is_active == False
        self.session.start()
        assert self.session.is_active == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
