"""
Convolv趋势卷积模块

提供趋势卷积和涌现检测功能。
"""

from .trend_convolv import TrendConvolv, ConvolvResult, ConvolvConfig
from .emergent_detection import EmergentDetector, EmergentPattern

__all__ = [
    'TrendConvolv',
    'ConvolvResult',
    'ConvolvConfig',
    'EmergentDetector',
    'EmergentPattern'
]
