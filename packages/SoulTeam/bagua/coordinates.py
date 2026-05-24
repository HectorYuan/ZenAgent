"""
八卦坐标系 (M10 Phase I)

8 卦位坐标 + 五行相生相克 + 能量阈值
"""

import math
from enum import Enum
from dataclasses import dataclass


class WuXing(str, Enum):
    JIN = "金"
    SHUI = "水"
    MU = "木"
    HUO = "火"
    TU = "土"


# 相生: 金→水→木→火→土→金
WUXING_CYCLE = {
    WuXing.JIN: WuXing.SHUI,
    WuXing.SHUI: WuXing.MU,
    WuXing.MU: WuXing.HUO,
    WuXing.HUO: WuXing.TU,
    WuXing.TU: WuXing.JIN,
}

# 相克: 金克木, 木克土, 土克水, 水克火, 火克金
WUXING_COUNTER = {
    WuXing.JIN: WuXing.MU,
    WuXing.MU: WuXing.TU,
    WuXing.TU: WuXing.SHUI,
    WuXing.SHUI: WuXing.HUO,
    WuXing.HUO: WuXing.JIN,
}


# 八卦→五行映射
BAGUA_WUXING = {
    "乾☰": WuXing.JIN, "兑☱": WuXing.JIN,
    "坎☵": WuXing.SHUI,
    "震☳": WuXing.MU, "巽☴": WuXing.MU,
    "離☲": WuXing.HUO,
    "坤☷": WuXing.TU, "艮☶": WuXing.TU,
}


@dataclass
class BaguaCoord:
    """八卦坐标"""
    name: str             # "乾☰"
    degree: float         # 0-360
    wx: WuXing           # 五行
    vector: tuple[float, float]  # 单位向量
    energy: float = 100.0

    def __post_init__(self):
        rad = math.radians(self.degree)
        self.vector = (math.cos(rad), math.sin(rad))


# 8 卦位标准坐标
BAGUA_POSITIONS = {
    "乾☰": BaguaCoord("乾☰", 0, WuXing.JIN, (0, 0), 100),
    "兌☱": BaguaCoord("兌☱", 45, WuXing.JIN, (0, 0), 100),
    "離☲": BaguaCoord("離☲", 90, WuXing.HUO, (0, 0), 100),
    "震☳": BaguaCoord("震☳", 135, WuXing.MU, (0, 0), 100),
    "巽☴": BaguaCoord("巽☴", 180, WuXing.MU, (0, 0), 100),
    "坎☵": BaguaCoord("坎☵", 225, WuXing.SHUI, (0, 0), 100),
    "艮☶": BaguaCoord("艮☶", 270, WuXing.TU, (0, 0), 100),
    "坤☷": BaguaCoord("坤☷", 315, WuXing.TU, (0, 0), 100),
}

# 能量阈值
ENERGY_THRESHOLDS = {
    "overflow": 100,     # > 100: 过载
    "optimal": 50,       # 50-100: 最优
    "normal": 20,        # 20-50: 正常
    "low": 20,           # < 20: 低能
}


def generate_relation(from_pos: BaguaCoord, to_pos: BaguaCoord) -> str:
    """判断两卦位关系: 相生/相克/中性"""
    from_wx = BAGUA_WUXING.get(from_pos.name)
    to_wx = BAGUA_WUXING.get(to_pos.name)
    if not from_wx or not to_wx:
        return "neutral"
    if WUXING_CYCLE.get(from_wx) == to_wx:
        return "sheng"  # 相生
    if WUXING_COUNTER.get(from_wx) == to_wx:
        return "ke"     # 相克
    return "neutral"
