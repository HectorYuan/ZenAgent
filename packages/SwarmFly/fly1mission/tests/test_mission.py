"""
fly1mission 使命层单元测试

覆盖 Mission、MissionAligner、AlignmentReport 的核心逻辑
"""

import pytest
import sys
import os

# 确保能从项目根目录导入 packages 模块
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from packages.SwarmFly.fly1mission.core.mission import (
    Mission, MissionStatus, ValueSystem,
)
from packages.SwarmFly.fly1mission.core.mission_aligner import (
    MissionAligner, AlignmentReport,
)


# ──────────────────────────────────────────────
# Mission 测试
# ──────────────────────────────────────────────

class TestMissionPostInit:
    """Mission.__post_init__ 默认值测试"""

    def setup_method(self):
        """每个测试前创建默认 Mission"""
        self.mission = Mission(mission_id="test-001")

    def test_default_vision(self):
        """未指定 vision 时应自动填充"""
        assert self.mission.vision != ""
        assert "成为高效、协作、自我进化的智能体协作网络" in self.mission.vision

    def test_default_goals(self):
        """未指定 goals 时应自动填充 3 个默认目标"""
        assert len(self.mission.goals) == 3
        assert "优化智能体间协作效率" in self.mission.goals

    def test_default_principles(self):
        """未指定 principles 时应自动填充 3 个默认原则"""
        assert len(self.mission.principles) == 3
        assert "透明沟通" in self.mission.principles

    def test_custom_values_preserved(self):
        """指定自定义值时不应被 __post_init__ 覆盖"""
        m = Mission(
            mission_id="custom",
            vision="自定义愿景",
            goals=["目标A"],
            principles=["原则X"],
        )
        assert m.vision == "自定义愿景"
        assert m.goals == ["目标A"]
        assert m.principles == ["原则X"]

    def test_default_status_active(self):
        """默认状态应为 ACTIVE"""
        assert self.mission.status == MissionStatus.ACTIVE

    def test_default_values_count(self):
        """默认价值体系应包含 3 个核心价值"""
        assert len(self.mission.values) == 3
        names = {v.name for v in self.mission.values}
        assert names == {"用户中心", "效率优先", "持续进化"}


class TestMissionAlignWithMission:
    """Mission.align_with_mission 对齐计算测试"""

    def setup_method(self):
        self.mission = Mission(mission_id="align-test")

    def test_full_alignment(self):
        """完全对齐应返回 100 分"""
        all_values = ["用户中心", "效率优先", "持续进化"]
        score = self.mission.align_with_mission(all_values)
        assert score == 100.0

    def test_partial_alignment(self):
        """部分对齐应返回对应比例分数（2/3 ≈ 66.67）"""
        score = self.mission.align_with_mission(["用户中心", "效率优先"])
        assert score == pytest.approx(66.67, abs=0.1)

    def test_zero_alignment(self):
        """完全偏离应返回 0 分"""
        score = self.mission.align_with_mission(["无关价值A", "无关价值B"])
        assert score == 0.0

    def test_alignment_updates_score_and_timestamp(self):
        """对齐后应更新 alignment_score 和 last_aligned_at"""
        assert self.mission.last_aligned_at is None
        self.mission.align_with_mission(["用户中心"])
        assert self.mission.alignment_score == pytest.approx(33.33, abs=0.1)
        assert self.mission.last_aligned_at is not None


class TestMissionToDict:
    """Mission.to_dict 序列化测试"""

    def setup_method(self):
        self.mission = Mission(mission_id="dict-test")

    def test_to_dict_keys(self):
        """序列化结果应包含所有必要字段"""
        d = self.mission.to_dict()
        expected_keys = {
            "mission_id", "core_mission", "status",
            "values", "alignment_score", "last_aligned_at",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_status_value(self):
        """status 应序列化为字符串值"""
        d = self.mission.to_dict()
        assert d["status"] == "active"

    def test_to_dict_values_structure(self):
        """values 应序列化为包含 name 和 weight 的字典列表"""
        d = self.mission.to_dict()
        assert len(d["values"]) == 3
        assert all("name" in v and "weight" in v for v in d["values"])

    def test_to_dict_last_aligned_at_none(self):
        """未对齐时 last_aligned_at 应为 None"""
        d = self.mission.to_dict()
        assert d["last_aligned_at"] is None


# ──────────────────────────────────────────────
# MissionAligner 测试
# ──────────────────────────────────────────────

class TestMissionAlignerAlignAgent:
    """MissionAligner.align_agent 对齐测试"""

    def setup_method(self):
        self.aligner = MissionAligner(Mission(mission_id="aligner-test"))

    def test_full_alignment_report(self):
        """完全对齐时报告应无偏离且分数为 100"""
        report = self.aligner.align_agent(
            "agent-1", ["用户中心", "效率优先", "持续进化"]
        )
        assert report.alignment_score == 100.0
        assert len(report.deviations) == 0

    def test_partial_alignment_report(self):
        """部分对齐时应检测到缺失价值"""
        report = self.aligner.align_agent("agent-2", ["用户中心"])
        assert report.alignment_score == pytest.approx(33.33, abs=0.1)
        assert any("缺少价值" in d for d in report.deviations)

    def test_full_deviation_report(self):
        """完全偏离时分数应为 0 且有偏离记录"""
        report = self.aligner.align_agent("agent-3", ["无关价值"])
        assert report.alignment_score == 0.0
        assert len(report.deviations) > 0

    def test_mission_mismatch_deviation(self):
        """使命描述不一致时应记录偏离"""
        report = self.aligner.align_agent(
            "agent-4",
            ["用户中心", "效率优先", "持续进化"],
            agent_mission="完全不同的使命",
        )
        assert any("使命描述偏离" in d for d in report.deviations)
        assert any("更新使命描述" in r for r in report.recommendations)

    def test_extra_values_recommendation(self):
        """包含额外价值时应给出移除建议"""
        report = self.aligner.align_agent(
            "agent-5",
            ["用户中心", "效率优先", "持续进化", "额外价值"],
        )
        assert any("可考虑移除" in r for r in report.recommendations)


class TestMissionAlignerQuery:
    """MissionAligner 查询方法测试"""

    def setup_method(self):
        self.aligner = MissionAligner(Mission(mission_id="query-test"))
        # 注册不同对齐度的智能体
        self.aligner.align_agent("high", ["用户中心", "效率优先", "持续进化"])
        self.aligner.align_agent("mid", ["用户中心", "效率优先"])
        self.aligner.align_agent("low", ["无关价值"])

    def test_check_alignment_existing(self):
        """查询已注册智能体应返回对应分数"""
        score = self.aligner.check_alignment("high")
        assert score == 100.0

    def test_check_alignment_missing(self):
        """查询未注册智能体应返回 None"""
        assert self.aligner.check_alignment("nonexistent") is None

    def test_get_all_aligned(self):
        """get_all_aligned 应返回分数 >= 阈值的智能体"""
        aligned = self.aligner.get_all_aligned(threshold=80.0)
        assert "high" in aligned
        assert "low" not in aligned

    def test_get_all_deviated(self):
        """get_all_deviated 应返回分数 < 阈值的智能体"""
        deviated = self.aligner.get_all_deviated(threshold=80.0)
        assert "low" in deviated
        assert "high" not in deviated

    def test_get_alignment_rate(self):
        """对齐率应为对齐智能体占总数的百分比"""
        # high=100, mid≈66.7, low=0 → 1/3 ≈ 33.33%
        rate = self.aligner.get_alignment_rate()
        assert rate == pytest.approx(33.33, abs=0.1)

    def test_get_alignment_rate_empty(self):
        """无智能体时对齐率应为 100%"""
        empty_aligner = MissionAligner()
        assert empty_aligner.get_alignment_rate() == 100.0


# ──────────────────────────────────────────────
# AlignmentReport 测试
# ──────────────────────────────────────────────

class TestAlignmentReport:
    """AlignmentReport.is_aligned 阈值判断测试"""

    def test_is_aligned_above_threshold(self):
        """分数高于阈值时应返回 True"""
        report = AlignmentReport(
            agent_id="a1", mission_id="m1", alignment_score=90.0
        )
        assert report.is_aligned(threshold=80.0) is True

    def test_is_aligned_below_threshold(self):
        """分数低于阈值时应返回 False"""
        report = AlignmentReport(
            agent_id="a2", mission_id="m1", alignment_score=50.0
        )
        assert report.is_aligned(threshold=80.0) is False

    def test_is_aligned_at_exact_threshold(self):
        """分数恰好等于阈值时应返回 True"""
        report = AlignmentReport(
            agent_id="a3", mission_id="m1", alignment_score=80.0
        )
        assert report.is_aligned(threshold=80.0) is True
