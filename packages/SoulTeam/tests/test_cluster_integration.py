"""集群集成测试 (M10 Phase W)"""
import pytest
from packages.SoulTeam.protocol import ClusterMessage, MessageType, TaskStatus, Baton
from packages.SoulTeam.registry import AgentRegistry, AgentCategory
from packages.SoulTeam.router import FourDimensionRouter

class TestProtocol:
    def test_task_request(self):
        msg = ClusterMessage.task_request("m", "SUB-1.1", {"t":"x"})
        assert msg.msg_type == MessageType.TASK_REQUEST
        assert msg.sender_id == "m"
        assert msg.correlation_id
    def test_json_roundtrip(self):
        msg = ClusterMessage.task_request("m", "s", {"t":"x"})
        j = msg.to_json()
        m2 = ClusterMessage.from_json(j)
        assert m2.correlation_id == msg.correlation_id
    def test_baton(self):
        b = Baton(zone="A")
        b.pass_to("B", "SUB-2.1")
        assert b.zone == "B"
        assert b.round_count == 1

class TestRegistry:
    def test_16_agents(self):
        reg = AgentRegistry()
        assert len(reg.all_agents) == 16
    def test_4_teams(self):
        reg = AgentRegistry()
        assert len(reg.all_teams) == 4
        assert len(reg.get_team_members("TEAM-INVEST")) == 4
    def test_by_category(self):
        reg = AgentRegistry()
        assert len(reg.get_by_category(AgentCategory.BUSINESS)) == 4
        assert len(reg.get_by_category(AgentCategory.MANAGEMENT)) == 3
        assert len(reg.get_by_category(AgentCategory.PROFESSIONAL)) == 9

class TestRouter:
    def test_route_invest(self):
        router = FourDimensionRouter(AgentRegistry())
        results = router.route(["invest", "strategy"], team_id="TEAM-INVEST")
        assert len(results) >= 1
        assert results[0][0].agent_id == "SUB-1.1"
    def test_score_range(self):
        router = FourDimensionRouter(AgentRegistry())
        agent = AgentRegistry().get("SUB-3.1")
        s = router.score(agent, ["architecture"])
        assert 0 <= s <= 1
