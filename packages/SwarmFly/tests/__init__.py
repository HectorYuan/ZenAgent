"""
SwarmFly 单元测试

测试 SwarmFly 层的各个模块
"""

import pytest
import sys
import os

# 添加 packages 目录到 path
PACKAGES_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PACKAGES_DIR)
