"""
HiTL 单元测试
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from htl.policy import ApprovalPolicy, RiskLevel


class TestApprovalPolicy:
    """ApprovalPolicy 测试"""
    
    def setup_method(self):
        self.policy = ApprovalPolicy()
    
    def test_policy_initialization(self):
        """测试策略初始化"""
        assert self.policy is not None
        assert hasattr(self.policy, "_rules")
    
    def test_risk_thresholds(self):
        """测试风险阈值"""
        assert self.policy._risk_thresholds is not None
        assert RiskLevel.LOW in self.policy._risk_thresholds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
