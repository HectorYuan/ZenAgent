"""八卦路由测试 (M10 Phase Y)"""
import pytest
from packages.SoulTeam.bagua import BaguaRouter, BaguaPacket, BAGUA_POSITIONS, WUXING_CYCLE, WUXING_COUNTER
from packages.SoulTeam.bagua.coordinates import generate_relation, WuXing

class TestBaguaCoordinates:
    def test_8_positions(self): assert len(BAGUA_POSITIONS) == 8
    def test_wuxing_cycle(self):
        assert WUXING_CYCLE[WuXing.JIN] == WuXing.SHUI
        assert WUXING_CYCLE[WuXing.SHUI] == WuXing.MU
    def test_wuxing_counter(self):
        assert WUXING_COUNTER[WuXing.JIN] == WuXing.MU

class TestBaguaRouter:
    def test_matrix_size(self):
        r = BaguaRouter()
        m = r.get_matrix()
        assert len(m) == 8
    def test_route(self):
        r = BaguaRouter()
        keys = list(BAGUA_POSITIONS.keys())
        pkt = BaguaPacket('p1', keys[0], '', message={})
        next_hop = r.route(pkt)
        assert next_hop is not None or pkt.hops == 0
    def test_energy(self):
        r = BaguaRouter()
        r.update_energy('乾☰', -50)
        assert r.get_energy_status('乾☰') == 'optimal'
    def test_generate_relation(self):
        qian = BAGUA_POSITIONS['乾☰']
        kan = BAGUA_POSITIONS['坎☵']
        rel = generate_relation(qian, kan)
        assert rel in ('sheng', 'ke', 'neutral')
