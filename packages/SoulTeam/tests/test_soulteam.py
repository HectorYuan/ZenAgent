import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from memory.meta_soul import MetaSoul
from learning.learner import SelfLearner
from reflection.reflector import Reflector
from personality.personality import Personality

class TestSoulTeam:
    """SoulTeam层测试"""
    
    def test_metasoul_creation(self):
        """测试MetaSoul创建"""
        soul = MetaSoul()
        assert soul is not None
    
    def test_learner_creation(self):
        """测试学习器创建"""
        learner = SelfLearner(soul_id="test_soul")
        assert learner is not None
    
    def test_reflector_creation(self):
        """测试反思器创建"""
        reflector = Reflector()
        assert reflector is not None
    
    def test_personality_creation(self):
        """测试人格创建"""
        personality = Personality()
        assert personality is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
