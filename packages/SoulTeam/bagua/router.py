"""
八卦路由引擎 (M10 Phase J)

4 阶段路由: 解析→匹配→相生相克→路径选择
双轨: 功能协作轨(60%) + 五行能量轨(40%)
"""

import time
import math
from typing import Optional
from dataclasses import dataclass, field

from .coordinates import (
    BAGUA_POSITIONS, ENERGY_THRESHOLDS,
    generate_relation, BAGUA_WUXING, WuXing,
)


@dataclass
class BaguaPacket:
    """八卦封包"""
    packet_id: str
    source_bagua: str          # 源卦位
    target_bagua: str          # 目标卦位
    message: dict = field(default_factory=dict)
    ttl: int = 300
    hops: int = 0
    max_hops: int = 3
    created_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl or self.hops >= self.max_hops


class BaguaRouter:
    """
    八卦路由器

    路由权重:
    - shortest_path: 0.3
    - load_balance: 0.2
    - bagua_match: 0.2 (相生加分)
    - phase_optimal: 0.1
    - energy_balance: 0.2
    """

    W_SHORTEST = 0.3
    W_LOAD = 0.2
    W_BAGUA = 0.2
    W_PHASE = 0.1
    W_ENERGY = 0.2

    def __init__(self):
        self._route_table: dict[str, dict[str, float]] = {}  # 8x8 matrix
        self._energy_levels: dict[str, float] = {
            name: 100.0 for name in BAGUA_POSITIONS
        }
        self._build_matrix()

    def _build_matrix(self):
        """构建 8×8 路由矩阵"""
        for src_name, src in BAGUA_POSITIONS.items():
            self._route_table[src_name] = {}
            for dst_name, dst in BAGUA_POSITIONS.items():
                if src_name == dst_name:
                    self._route_table[src_name][dst_name] = 1.0
                    continue
                rel = generate_relation(src, dst)
                base = 0.6
                if rel == "sheng":
                    base = 0.9
                elif rel == "ke":
                    base = 0.3
                self._route_table[src_name][dst_name] = base

    def route(self, packet: BaguaPacket) -> Optional[str]:
        """
        4 阶段路由:
        1. 解析封包
        2. 消息类型匹配
        3. 相生相克决策
        4. 路径选择
        """
        if packet.is_expired():
            return None

        src = packet.source_bagua
        if src not in self._route_table:
            return None

        # 计算每个目标卦位的综合得分
        scores = {}
        for dst_name in self._route_table:
            if dst_name == src:
                continue
            scores[dst_name] = self._score_route(src, dst_name)

        if not scores:
            return None

        # 最高分者为下一跳
        best = max(scores, key=scores.get)
        packet.hops += 1
        return best

    def _score_route(self, src: str, dst: str) -> float:
        matrix_score = self._route_table.get(src, {}).get(dst, 0.5)
        rel = generate_relation(BAGUA_POSITIONS[src], BAGUA_POSITIONS[dst])
        bagua_score = 0.7 if rel == "sheng" else 0.3 if rel == "ke" else 0.5

        # 能量平衡
        src_energy = self._energy_levels.get(src, 100)
        dst_energy = self._energy_levels.get(dst, 100)
        energy_diff = abs(src_energy - dst_energy) / 200
        energy_score = 1.0 - energy_diff

        return (
            matrix_score * self.W_BAGUA +
            0.5 * self.W_SHORTEST +       # 简化: 1-hop
            0.7 * self.W_LOAD +            # 简化: 默认负载
            energy_score * self.W_ENERGY
        )

    def update_energy(self, bagua_name: str, delta: float):
        if bagua_name in self._energy_levels:
            self._energy_levels[bagua_name] = max(0, min(150,
                self._energy_levels[bagua_name] + delta))

    def get_energy_status(self, bagua_name: str) -> str:
        e = self._energy_levels.get(bagua_name, 100)
        if e > 100: return "overflow"
        if e >= 50: return "optimal"
        if e >= 20: return "normal"
        return "low"

    def get_matrix(self) -> dict:
        return dict(self._route_table)

    def get_energies(self) -> dict:
        return dict(self._energy_levels)
