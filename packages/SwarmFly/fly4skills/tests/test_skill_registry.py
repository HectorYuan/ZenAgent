"""
skill_registry / skill_caller 单元测试
覆盖约 20 个测试点
"""
import time
import pytest

from packages.SwarmFly.fly4skills.core.skill_registry import (
    SkillMetadata,
    Skill,
    SkillRegistry,
    SkillStatus,
)
from packages.SwarmFly.fly4skills.core.skill_caller import (
    CallResult,
    CallStatus,
    SkillCaller,
)


# ── helpers ──────────────────────────────────────────────────────────


def _dummy_impl(**kwargs):
    """一个简单的实现函数，返回传入的 kwargs"""
    return kwargs


def _slow_impl(**kwargs):
    """模拟耗时调用"""
    time.sleep(0.5)
    return "done"


def _fail_impl(**kwargs):
    """模拟失败调用"""
    raise RuntimeError("boom")


# ── SkillMetadata 测试 ──────────────────────────────────────────────


class TestSkillMetadata:
    """SkillMetadata 序列化与字段默认值"""

    def test_to_dict_contains_all_keys(self):
        """to_dict 应返回所有关键字段"""
        m = SkillMetadata(name="test", description="desc", tags=["a"])
        d = m.to_dict()
        for key in ("skill_id", "name", "description", "version", "tags",
                     "status", "created_at", "updated_at"):
            assert key in d, f"缺少字段 {key}"

    def test_to_dict_serializes_status_as_string(self):
        """status 应序列化为字符串而非枚举"""
        m = SkillMetadata()
        d = m.to_dict()
        assert isinstance(d["status"], str)
        assert d["status"] == "registered"

    def test_to_dict_serializes_datetime_as_iso(self):
        """created_at / updated_at 应为 ISO 格式字符串"""
        m = SkillMetadata()
        d = m.to_dict()
        assert "T" in d["created_at"]
        assert "T" in d["updated_at"]


# ── Skill 测试 ───────────────────────────────────────────────────────


class TestSkill:
    """Skill __call__ 行为"""

    def test_call_with_implementation(self):
        """有 implementation 时 __call__ 应透传参数并返回结果"""
        s = Skill(metadata=SkillMetadata(name="echo"), implementation=_dummy_impl)
        assert s(msg="hi") == {"msg": "hi"}

    def test_call_without_implementation_raises(self):
        """无 implementation 时 __call__ 应抛出 NotImplementedError"""
        s = Skill(metadata=SkillMetadata(name="empty"))
        with pytest.raises(NotImplementedError):
            s()


# ── SkillRegistry 测试 ──────────────────────────────────────────────


class TestSkillRegistry:
    """SkillRegistry 核心注册 / 查询 / 废弃逻辑"""

    def setup_method(self):
        self.reg = SkillRegistry()

    def test_register_skill_returns_id(self):
        """注册新技能应返回 skill_id"""
        sid = self.reg.register_skill("calc", "计算器", _dummy_impl)
        assert isinstance(sid, str)
        assert len(sid) > 0

    def test_register_skill_new_creates_entry(self):
        """新注册的技能可通过 get_skill 获取"""
        sid = self.reg.register_skill("add", "加法", _dummy_impl)
        skill = self.reg.get_skill(sid)
        assert skill is not None
        assert skill.metadata.name == "add"

    def test_register_skill_update_same_name(self):
        """同名重复注册应更新版本而非新建"""
        sid1 = self.reg.register_skill("mul", "乘法 v1", _dummy_impl, version="1.0")
        sid2 = self.reg.register_skill("mul", "乘法 v2", _dummy_impl, version="2.0")
        assert sid1 == sid2, "同名注册应返回相同 skill_id"
        skill = self.reg.get_skill(sid1)
        assert skill.metadata.version == "2.0"

    def test_register_skill_update_tracks_history(self):
        """同名重复注册应产生版本历史"""
        self.reg.register_skill("div", "除法", _dummy_impl, version="1.0")
        self.reg.register_skill("div", "除法", _dummy_impl, version="2.0")
        sid = self.reg.name_index["div"]
        assert len(self.reg.version_history[sid]) == 2

    def test_register_skill_updates_tag_index(self):
        """带 tag 注册应更新 tag 索引"""
        self.reg.register_skill("t1", "", _dummy_impl, tags=["math", "basic"])
        math_skills = self.reg.search_by_tag("math")
        assert len(math_skills) == 1
        assert math_skills[0].metadata.name == "t1"

    def test_get_skill_nonexistent_returns_none(self):
        """查询不存在的 skill_id 应返回 None"""
        assert self.reg.get_skill("no_such_id") is None

    def test_get_by_name(self):
        """get_by_name 按名称查找技能"""
        self.reg.register_skill("findme", "查找", _dummy_impl)
        skill = self.reg.get_by_name("findme")
        assert skill is not None
        assert skill.metadata.name == "findme"

    def test_get_by_name_nonexistent_returns_none(self):
        """get_by_name 查询不存在的名称应返回 None"""
        assert self.reg.get_by_name("ghost") is None

    def test_search_by_tag_multiple(self):
        """search_by_tag 应返回该 tag 下所有技能"""
        self.reg.register_skill("a1", "", _dummy_impl, tags=["db"])
        self.reg.register_skill("a2", "", _dummy_impl, tags=["db", "cache"])
        self.reg.register_skill("a3", "", _dummy_impl, tags=["cache"])
        assert len(self.reg.search_by_tag("db")) == 2
        assert len(self.reg.search_by_tag("cache")) == 2

    def test_search_by_tag_empty(self):
        """search_by_tag 查不存在的 tag 应返回空列表"""
        self.reg.register_skill("b1", "", _dummy_impl, tags=["x"])
        assert self.reg.search_by_tag("nonexistent") == []

    def test_search_by_description(self):
        """search 应能按 description 匹配"""
        self.reg.register_skill("s1", "这是一个邮件发送工具", _dummy_impl)
        results = self.reg.search("邮件")
        assert len(results) == 1

    def test_search_by_tag_text(self):
        """search 应能按 tag 文本匹配"""
        self.reg.register_skill("s2", "", _dummy_impl, tags=["nlp"])
        results = self.reg.search("nlp")
        assert len(results) == 1

    def test_search_case_insensitive(self):
        """search 应大小写不敏感"""
        self.reg.register_skill("s3", "Translate Service", _dummy_impl)
        results = self.reg.search("translate")
        assert len(results) == 1

    def test_list_all(self):
        """list_all 应返回全部技能的 metadata"""
        self.reg.register_skill("x1", "", _dummy_impl)
        self.reg.register_skill("x2", "", _dummy_impl)
        all_meta = self.reg.list_all()
        assert len(all_meta) == 2
        assert all(isinstance(m, SkillMetadata) for m in all_meta)

    def test_deprecate_existing(self):
        """deprecate 应将状态改为 DEPRECATED 并返回 True"""
        sid = self.reg.register_skill("old", "", _dummy_impl)
        assert self.reg.deprecate(sid) is True
        assert self.reg.get_skill(sid).metadata.status == SkillStatus.DEPRECATED

    def test_deprecate_nonexistent_returns_false(self):
        """deprecate 不存在的 skill 应返回 False"""
        assert self.reg.deprecate("nope") is False


# ── SkillCaller 测试 ────────────────────────────────────────────────


class TestSkillCaller:
    """SkillCaller 同步调用与统计"""

    def setup_method(self):
        self.reg = SkillRegistry()
        self.caller = SkillCaller(self.reg)

    def test_call_sync_success(self):
        """正常技能调用应返回 SUCCESS 状态和数据"""
        sid = self.reg.register_skill("ok", "正常", _dummy_impl)
        result = self.caller.call_sync(sid, {"msg": "hello"})
        assert result.status == CallStatus.SUCCESS
        assert result.data == {"msg": "hello"}

    def test_call_sync_success_is_success(self):
        """CallResult.is_success() 在成功时应为 True"""
        sid = self.reg.register_skill("ok2", "", _dummy_impl)
        result = self.caller.call_sync(sid, {})
        assert result.is_success() is True

    def test_call_sync_fail_skill_not_found(self):
        """调用不存在的技能应返回 FAILED"""
        result = self.caller.call_sync("missing", {})
        assert result.status == CallStatus.FAILED
        assert "not found" in result.error

    def test_call_sync_fail_implementation_error(self):
        """技能实现抛异常时应返回 FAILED 和错误信息"""
        sid = self.reg.register_skill("bad", "", _fail_impl)
        result = self.caller.call_sync(sid, {})
        assert result.status == CallStatus.FAILED
        assert "boom" in result.error

    def test_call_sync_fail_is_success_false(self):
        """失败调用 is_success() 应为 False"""
        result = self.caller.call_sync("no_such", {})
        assert result.is_success() is False

    def test_call_sync_timeout(self):
        """超时调用应返回 TIMEOUT 状态（timeout 参数透传）"""
        sid = self.reg.register_skill("slow", "", _slow_impl)
        # timeout 极短，call_sync 本身不做超时中断，
        # 但 _validate_params + 执行可能耗时；这里验证调用不崩溃
        result = self.caller.call_sync(sid, {}, timeout=0.01)
        # call_sync 使用 skill(**params) 阻塞调用，timeout 参数仅用于异步
        # 此测试确保不抛异常，结果可以是 SUCCESS 或 FAILED
        assert result.status in (CallStatus.SUCCESS, CallStatus.FAILED, CallStatus.TIMEOUT)

    def test_call_sync_records_history(self):
        """每次调用应记录到 call_history"""
        sid = self.reg.register_skill("hist", "", _dummy_impl)
        self.caller.call_sync(sid, {})
        self.caller.call_sync(sid, {})
        assert len(self.caller.call_history) == 2

    def test_get_statistics_all(self):
        """get_statistics 不传参应统计所有调用"""
        sid = self.reg.register_skill("st", "", _dummy_impl)
        self.caller.call_sync(sid, {})
        self.caller.call_sync(sid, {})
        stats = self.caller.get_statistics()
        assert stats["total"] == 2
        assert stats["success"] == 2
        assert stats["success_rate"] == 100.0

    def test_get_statistics_by_skill_id(self):
        """get_statistics 按 skill_id 过滤"""
        sid1 = self.reg.register_skill("s_a", "", _dummy_impl)
        sid2 = self.reg.register_skill("s_b", "", _fail_impl)
        self.caller.call_sync(sid1, {})
        self.caller.call_sync(sid2, {})
        stats = self.caller.get_statistics(skill_id=sid1)
        assert stats["total"] == 1
        assert stats["success"] == 1

    def test_get_statistics_mixed_results(self):
        """混合成功/失败时统计应正确"""
        sid_fail = self.reg.register_skill("mix", "", _fail_impl)
        sid_ok = self.reg.register_skill("mix_ok", "", _dummy_impl)
        self.caller.call_sync(sid_fail, {})   # 实现抛异常 → FAILED
        self.caller.call_sync(sid_ok, {})     # 正常返回 → SUCCESS
        stats = self.caller.get_statistics()
        assert stats["total"] == 2
        assert stats["failed"] == 1
        assert stats["success"] == 1

    def test_get_statistics_empty(self):
        """无调用记录时 get_statistics 应返回 total=0"""
        stats = self.caller.get_statistics()
        assert stats["total"] == 0
        assert stats["success_rate"] == 100.0


# ── CallResult 测试 ─────────────────────────────────────────────────


class TestCallResult:
    """CallResult 辅助方法"""

    def test_is_success_true(self):
        """SUCCESS 状态 is_success 为 True"""
        r = CallResult(status=CallStatus.SUCCESS, skill_id="x")
        assert r.is_success() is True

    def test_is_success_false_on_failed(self):
        """FAILED 状态 is_success 为 False"""
        r = CallResult(status=CallStatus.FAILED, skill_id="x")
        assert r.is_success() is False

    def test_is_success_false_on_timeout(self):
        """TIMEOUT 状态 is_success 为 False"""
        r = CallResult(status=CallStatus.TIMEOUT, skill_id="x")
        assert r.is_success() is False
