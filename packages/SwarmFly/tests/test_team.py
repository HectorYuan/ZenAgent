"""
团队模块单元测试
"""

import pytest
import sys
import os

PACKAGES_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PACKAGES_DIR)

from SwarmFly.team import (
    TeamBuilder,
    Team,
    TeamConfig,
    AgentRole,
    RoleDefinition,
    RoleCapability,
    RoleRegistry,
    get_role_registry,
    Formation,
    FormationType,
    Position,
    FormationManager,
    Member,
    MembershipStatus,
    MembershipRequest,
    MembershipManager,
    TeamProtocol,
    MessageType,
    ProtocolMessage,
)


class TestAgentRole:
    """Agent 角色测试"""
    
    def test_role_values(self):
        """测试角色值"""
        assert AgentRole.LEADER.value == "leader"
        assert AgentRole.COORDINATOR.value == "coordinator"
        assert AgentRole.WORKER.value == "worker"
        assert AgentRole.SPECIALIST.value == "specialist"
        assert AgentRole.OBSERVER.value == "observer"
    
    def test_role_count(self):
        """测试角色数量"""
        assert len(AgentRole) >= 5


class TestRoleDefinition:
    """角色定义测试"""
    
    def test_role_definition_creation(self):
        """测试角色定义创建"""
        role = RoleDefinition(
            role=AgentRole.LEADER,
            name="Team Leader",
            description="The team leader",
            capabilities=[
                RoleCapability("decision", "Decision making"),
                RoleCapability("delegation", "Task delegation"),
            ],
            max_count=1,
            priority=10,
        )
        
        assert role.role == AgentRole.LEADER
        assert role.name == "Team Leader"
        assert len(role.capabilities) == 2
    
    def test_has_capability(self):
        """测试能力检查"""
        role = RoleDefinition(
            role=AgentRole.LEADER,
            name="Leader",
            description="",
            capabilities=[RoleCapability("decision", "Decision making")],
        )
        
        assert role.has_capability("decision") is True
        assert role.has_capability("unknown") is False


class TestRoleRegistry:
    """角色注册表测试"""
    
    def test_registry_creation(self):
        """测试注册表创建"""
        registry = RoleRegistry()
        
        roles = registry.get_all_roles()
        assert len(roles) > 0
    
    def test_get_role(self):
        """测试获取角色"""
        registry = RoleRegistry()
        
        leader = registry.get_role(AgentRole.LEADER)
        
        assert leader is not None
        assert leader.role == AgentRole.LEADER
    
    def test_check_constraints(self):
        """测试约束检查"""
        registry = RoleRegistry()
        
        # Leader 最多 1 个
        result = registry.check_role_constraints(AgentRole.LEADER, 0)
        assert result is True
        
        result = registry.check_role_constraints(AgentRole.LEADER, 1)
        assert result is False
    
    def test_global_registry(self):
        """测试全局注册表"""
        registry = get_role_registry()
        
        assert registry is not None
        assert len(registry.get_all_roles()) > 0


class TestPosition:
    """位置测试"""
    
    def test_position_creation(self):
        """测试位置创建"""
        pos = Position(
            position_id="pos-1",
            name="Leader Position",
            x=0, y=0, z=0,
        )
        
        assert pos.position_id == "pos-1"
        assert pos.coordinates == (0, 0, 0)
    
    def test_distance_calculation(self):
        """测试距离计算"""
        pos1 = Position(position_id="p1", name="P1", x=0, y=0, z=0)
        pos2 = Position(position_id="p2", name="P2", x=3, y=4, z=0)
        
        distance = pos1.distance_to(pos2)
        
        assert abs(distance - 5.0) < 0.001  # 3-4-5 三角形


class TestFormation:
    """编队测试"""
    
    def test_formation_creation(self):
        """测试编队创建"""
        formation = Formation(
            formation_id="test-formation",
            name="Test Formation",
            formation_type=FormationType.HIERARCHICAL,
        )
        
        assert formation.formation_id == "test-formation"
        assert formation.size == 0
    
    def test_assign_position(self):
        """测试位置分配"""
        formation = Formation(
            formation_id="test",
            name="Test",
            formation_type=FormationType.FLAT,
        )
        
        pos = Position(position_id="pos-1", name="Pos 1")
        formation.positions["pos-1"] = pos
        
        result = formation.assign("pos-1", "agent-1")
        
        assert result is True
        assert formation.assignments["pos-1"] == "agent-1"
    
    def test_get_adjacent_agents(self):
        """测试获取相邻 Agent"""
        formation = Formation(
            formation_id="test",
            name="Test",
            formation_type=FormationType.HIERARCHICAL,
        )
        
        # 手动创建简单结构
        p1 = Position(position_id="p1", name="P1")
        p1.connected_positions = {"p2"}
        p2 = Position(position_id="p2", name="P2")
        p2.connected_positions = {"p1", "p3"}
        p3 = Position(position_id="p3", name="P3")
        p3.connected_positions = {"p2"}
        
        formation.positions = {"p1": p1, "p2": p2, "p3": p3}
        formation.assign("p1", "agent-1")
        formation.assign("p2", "agent-2")
        formation.assign("p3", "agent-3")
        
        adjacent = formation.get_adjacent_agents("agent-1")
        assert "agent-2" in adjacent


class TestFormationManager:
    """编队管理器测试"""
    
    def test_manager_creation(self):
        """测试管理器创建"""
        manager = FormationManager()
        
        formations = manager.get_all_formations()
        assert len(formations) > 0
    
    def test_get_formation(self):
        """测试获取编队"""
        manager = FormationManager()
        
        formation = manager.get_formation("hierarchical")
        
        assert formation is not None
        assert formation.formation_type == FormationType.HIERARCHICAL


class TestMember:
    """成员测试"""
    
    def test_member_creation(self):
        """测试成员创建"""
        member = Member(
            member_id="m-1",
            agent_id="agent-1",
            team_id="team-1",
            role="worker",
            status=MembershipStatus.ACTIVE,
        )
        
        assert member.member_id == "m-1"
        assert member.agent_id == "agent-1"
        assert member.is_active is True
    
    def test_success_rate(self):
        """测试成功率"""
        member = Member(
            member_id="m-1",
            agent_id="agent-1",
            team_id="team-1",
        )
        
        member.record_task_completion(success=True)
        member.record_task_completion(success=True)
        member.record_task_completion(success=False)
        
        assert member.tasks_completed == 2
        assert member.tasks_failed == 1
        assert abs(member.success_rate - 0.666) < 0.01


class TestMembershipManager:
    """成员管理器测试"""
    
    def test_manager_creation(self):
        """测试管理器创建"""
        manager = MembershipManager(team_id="team-1")
        
        assert manager.team_id == "team-1"
        assert manager.member_count == 0
    
    def test_add_member(self):
        """测试添加成员"""
        manager = MembershipManager(team_id="team-1")
        
        member = manager.add_member(
            agent_id="agent-1",
            role="worker",
        )
        
        assert member is not None
        assert manager.member_count == 1
    
    def test_remove_member(self):
        """测试移除成员"""
        manager = MembershipManager(team_id="team-1")
        manager.add_member(agent_id="agent-1")
        
        result = manager.remove_member("agent-1")
        
        assert result is True
        assert manager.member_count == 0
    
    def test_create_request(self):
        """测试创建请求"""
        manager = MembershipManager(team_id="team-1")
        
        request = manager.create_request(
            agent_id="agent-1",
            requested_role="worker",
            reason="I want to join",
        )
        
        assert request is not None
        assert request.status == MembershipStatus.PENDING
    
    def test_process_request(self):
        """测试处理请求"""
        manager = MembershipManager(team_id="team-1")
        
        request = manager.create_request(
            agent_id="agent-1",
            requested_role="worker",
        )
        
        result = manager.process_request(request.request_id, approved=True)
        
        assert result is True
        assert manager.member_count == 1


class TestTeamProtocol:
    """团队协议测试"""
    
    def test_protocol_creation(self):
        """测试协议创建"""
        protocol = TeamProtocol(team_id="team-1", node_id="node-1")
        
        assert protocol.team_id == "team-1"
        assert protocol.node_id == "node-1"
    
    def test_send_message(self):
        """测试发送消息"""
        protocol = TeamProtocol(team_id="team-1", node_id="node-1")
        
        msg = protocol.send_message(
            message_type=MessageType.TASK_ASSIGN,
            content={"task_id": "t-1"},
            target_id="agent-1",
        )
        
        assert msg is not None
        assert msg.message_type == MessageType.TASK_ASSIGN
        assert msg.target_id == "agent-1"
    
    def test_receive_message(self):
        """测试接收消息"""
        protocol = TeamProtocol(team_id="team-1", node_id="node-1")
        
        msg = ProtocolMessage(
            message_type=MessageType.TASK_ASSIGN,
            sender_id="leader-1",
            target_id="node-1",
            content={"task_id": "t-1"},
        )
        
        result = protocol.receive_message(msg)
        
        assert result is True
        assert protocol.get_inbox_count() == 1
    
    def test_subscribe(self):
        """测试订阅"""
        protocol = TeamProtocol(team_id="team-1", node_id="node-1")
        
        received = []
        
        def on_task_assign(msg):
            received.append(msg)
        
        protocol.subscribe(MessageType.TASK_ASSIGN, on_task_assign)
        
        msg = ProtocolMessage(
            message_type=MessageType.TASK_ASSIGN,
            sender_id="sender",
            target_id="node-1",
        )
        protocol.receive_message(msg)
        
        assert len(received) == 1


class TestTeamBuilder:
    """团队构建器测试"""
    
    def test_builder_creation(self):
        """测试构建器创建"""
        builder = TeamBuilder()
        
        assert builder.role_registry is not None
        assert builder.formation_manager is not None
    
    def test_create_team(self):
        """测试创建团队"""
        builder = TeamBuilder()
        
        config = TeamConfig(
            name="Test Team",
            description="A test team",
        )
        
        result = builder.create_team(config)
        
        assert result.success is True
        assert result.team is not None
        assert result.team.name == "Test Team"
    
    def test_add_member_to_team(self):
        """测试添加成员到团队"""
        builder = TeamBuilder()
        
        config = TeamConfig(name="Team")
        result = builder.create_team(config)
        
        team = result.team
        member = builder.add_member(team.team_id, "agent-1", role="worker")
        
        assert member is not None
        assert member.role == "worker"
    
    def test_remove_member_from_team(self):
        """测试从团队移除成员"""
        builder = TeamBuilder()
        
        config = TeamConfig(name="Team")
        result = builder.create_team(config)
        
        team = result.team
        builder.add_member(team.team_id, "agent-1")
        
        result = builder.remove_member(team.team_id, "agent-1")
        
        assert result is True
    
    def test_get_team_status(self):
        """测试获取团队状态"""
        builder = TeamBuilder()
        
        config = TeamConfig(name="Team")
        result = builder.create_team(config)
        
        team = result.team
        builder.add_member(team.team_id, "agent-1")
        
        status = builder.get_team_status(team.team_id)
        
        assert status is not None
        assert status["name"] == "Team"
        assert status["member_count"] == 1
    
    def test_dissolve_team(self):
        """测试解散团队"""
        builder = TeamBuilder()
        
        config = TeamConfig(name="Team")
        result = builder.create_team(config)
        
        team = result.team
        team_id = team.team_id
        
        result = builder.dissolve_team(team_id)
        
        assert result is True
        assert builder.get_team(team_id) is None


class TestTeam:
    """团队测试"""
    
    def test_team_creation(self):
        """测试团队创建"""
        team = Team(
            team_id="team-1",
            name="Test Team",
        )
        
        assert team.team_id == "team-1"
        assert team.name == "Test Team"
    
    def test_team_status(self):
        """测试团队状态"""
        from SwarmFly.team import TeamStatus
        
        team = Team(
            team_id="team-1",
            name="Test",
            status=TeamStatus.ACTIVE,
        )
        
        assert team.is_active is True
