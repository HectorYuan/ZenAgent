"""
key_manager.py 单元测试

覆盖 KeyInfo、KeyRotationPolicy、KeyManager 的核心功能
"""

import base64
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta

from packages.Runtime.security.key_manager import (
    KeyInfo,
    KeyManager,
    KeyRotationPolicy,
    KeyStatus,
    KeyType,
    generate_random_key,
    get_default_key_manager,
)


# ---------------------------------------------------------------------------
# KeyInfo 测试
# ---------------------------------------------------------------------------

class TestKeyInfo:
    """KeyInfo 数据类测试"""

    def setup_method(self):
        self.key_info = KeyInfo(
            key_id="test-key-001",
            key_type=KeyType.SYMMETRIC,
            name="test-key",
            description="测试密钥",
            status=KeyStatus.ACTIVE,
            algorithm="AES-256-GCM",
            key_size=32,
            created_at=datetime(2026, 1, 1),
            expires_at=datetime(2099, 12, 31),
            tags={"production", "api"},
            metadata={"env": "prod"},
            created_by="tester",
        )

    def test_to_dict_from_dict_roundtrip(self):
        """to_dict 和 from_dict 往返序列化后字段一致"""
        d = self.key_info.to_dict()
        restored = KeyInfo.from_dict(d)

        assert restored.key_id == self.key_info.key_id
        assert restored.key_type == KeyType.SYMMETRIC
        assert restored.name == "test-key"
        assert restored.status == KeyStatus.ACTIVE
        assert restored.created_at == self.key_info.created_at
        assert restored.expires_at == self.key_info.expires_at
        assert restored.tags == {"production", "api"}
        assert restored.metadata == {"env": "prod"}
        assert isinstance(restored.allowed_operations, set)

    def test_to_dict_types(self):
        """to_dict 输出中枚举和集合被转为基本类型"""
        d = self.key_info.to_dict()

        assert isinstance(d["key_type"], str)
        assert isinstance(d["status"], str)
        assert isinstance(d["allowed_operations"], list)
        assert isinstance(d["tags"], list)
        assert isinstance(d["created_at"], str)

    def test_from_dict_handles_none_datetime(self):
        """from_dict 对 None 时间戳字段正确处理"""
        d = self.key_info.to_dict()
        d["activated_at"] = None
        d["last_used_at"] = None
        restored = KeyInfo.from_dict(d)

        assert restored.activated_at is None
        assert restored.last_used_at is None

    def test_is_valid_active_not_expired(self):
        """活跃且未过期的密钥 is_valid 为 True"""
        assert self.key_info.is_valid is True

    def test_is_valid_expired(self):
        """过期的密钥 is_valid 为 False"""
        self.key_info.expires_at = datetime(2020, 1, 1)
        assert self.key_info.is_valid is False

    def test_is_valid_revoked(self):
        """已撤销的密钥 is_valid 为 False"""
        self.key_info.status = KeyStatus.REVOKED
        assert self.key_info.is_valid is False

    def test_is_expired_with_future_date(self):
        """未来过期时间 is_expired 为 False"""
        self.key_info.expires_at = datetime(2099, 12, 31)
        assert self.key_info.is_expired is False

    def test_is_expired_with_past_date(self):
        """过去过期时间 is_expired 为 True"""
        self.key_info.expires_at = datetime(2020, 1, 1)
        assert self.key_info.is_expired is True

    def test_is_expired_none(self):
        """无过期时间 is_expired 为 False"""
        self.key_info.expires_at = None
        assert self.key_info.is_expired is False

    def test_age_days(self):
        """age_days 返回自创建以来的天数"""
        self.key_info.created_at = datetime.now() - timedelta(days=10)
        assert self.key_info.age_days >= 10


# ---------------------------------------------------------------------------
# KeyRotationPolicy 测试
# ---------------------------------------------------------------------------

class TestKeyRotationPolicy:
    """KeyRotationPolicy 测试"""

    def setup_method(self):
        self.policy = KeyRotationPolicy(
            policy_id="policy-001",
            name="90天轮换",
            rotation_period_days=90,
            max_usage_count=1000,
            alert_before_expiry_days=7,
            alert_usage_threshold=0.8,
            enabled=True,
        )

    def test_should_rotate_by_age(self):
        """密钥超过轮换周期天数时应轮换"""
        key_info = KeyInfo(
            key_id="k1",
            name="old-key",
            status=KeyStatus.ACTIVE,
            created_at=datetime.now() - timedelta(days=100),
        )
        assert self.policy.should_rotate(key_info) is True

    def test_should_rotate_by_usage_count(self):
        """密钥使用次数达到上限时应轮换"""
        key_info = KeyInfo(
            key_id="k2",
            name="heavy-key",
            status=KeyStatus.ACTIVE,
            use_count=1000,
            created_at=datetime.now(),
        )
        assert self.policy.should_rotate(key_info) is True

    def test_should_rotate_not_needed(self):
        """密钥未超期且使用次数未达上限时不应轮换"""
        key_info = KeyInfo(
            key_id="k3",
            name="fresh-key",
            status=KeyStatus.ACTIVE,
            use_count=10,
            created_at=datetime.now(),
        )
        assert self.policy.should_rotate(key_info) is False

    def test_should_rotate_disabled_policy(self):
        """策略禁用时始终不触发轮换"""
        self.policy.enabled = False
        key_info = KeyInfo(
            key_id="k4",
            name="old-key",
            status=KeyStatus.ACTIVE,
            created_at=datetime.now() - timedelta(days=200),
        )
        assert self.policy.should_rotate(key_info) is False

    def test_should_rotate_by_last_rotated_at(self):
        """基于 last_rotated_at 判断轮换"""
        key_info = KeyInfo(
            key_id="k5",
            name="rotated-key",
            status=KeyStatus.ACTIVE,
            created_at=datetime.now() - timedelta(days=200),
            last_rotated_at=datetime.now() - timedelta(days=95),
        )
        assert self.policy.should_rotate(key_info) is True

    def test_should_alert_near_expiry(self):
        """密钥接近过期时应告警"""
        key_info = KeyInfo(
            key_id="k6",
            name="expiring-key",
            status=KeyStatus.ACTIVE,
            expires_at=datetime.now() + timedelta(days=5),
        )
        should, reason = self.policy.should_alert(key_info)
        assert should is True
        assert "过期" in reason

    def test_should_alert_high_usage(self):
        """密钥使用率超过阈值时应告警"""
        key_info = KeyInfo(
            key_id="k7",
            name="busy-key",
            status=KeyStatus.ACTIVE,
            use_count=850,
        )
        should, reason = self.policy.should_alert(key_info)
        assert should is True
        assert "使用率" in reason

    def test_should_alert_no_alert_needed(self):
        """密钥状态正常时不应告警"""
        key_info = KeyInfo(
            key_id="k8",
            name="normal-key",
            status=KeyStatus.ACTIVE,
            use_count=10,
            expires_at=datetime.now() + timedelta(days=365),
        )
        should, reason = self.policy.should_alert(key_info)
        assert should is False
        assert reason == ""

    def test_should_alert_disabled_policy(self):
        """策略禁用时始终不告警"""
        self.policy.enabled = False
        key_info = KeyInfo(
            key_id="k9",
            name="expiring-key",
            status=KeyStatus.ACTIVE,
            expires_at=datetime.now() + timedelta(days=1),
            use_count=999,
        )
        should, reason = self.policy.should_alert(key_info)
        assert should is False


# ---------------------------------------------------------------------------
# KeyManager 核心功能测试
# ---------------------------------------------------------------------------

class TestKeyManager:
    """KeyManager 密钥管理器测试"""

    def setup_method(self):
        self.manager = KeyManager()

    # --- 生成 / 查询 ---

    def test_generate_key_basic(self):
        """生成密钥后可正确查询到"""
        key_info = self.manager.generate_key(name="api-key")

        assert key_info.name == "api-key"
        assert key_info.key_type == KeyType.SYMMETRIC
        assert key_info.key_fingerprint is not None
        assert key_info.status == KeyStatus.ACTIVE
        assert key_info.activated_at is not None
        assert key_info.key_id in self.manager

    def test_generate_key_with_expiry(self):
        """生成带过期时间的密钥"""
        key_info = self.manager.generate_key(
            name="temp-key",
            expires_in_days=30,
        )
        assert key_info.expires_at is not None
        assert key_info.expires_at > datetime.now()

    def test_generate_key_custom_algorithm_key_size(self):
        """自定义算法和密钥大小"""
        key_info = self.manager.generate_key(
            name="custom-key",
            algorithm="AES-128-GCM",
        )
        assert key_info.algorithm == "AES-128-GCM"
        assert key_info.key_size == 16

    def test_generate_key_with_tags_metadata(self):
        """生成带标签和元数据的密钥"""
        key_info = self.manager.generate_key(
            name="tagged-key",
            tags={"prod", "critical"},
            metadata={"owner": "team-a"},
        )
        assert "prod" in key_info.tags
        assert key_info.metadata["owner"] == "team-a"

    def test_get_key(self):
        """通过 key_id 获取密钥"""
        key_info = self.manager.generate_key(name="lookup-key")
        result = self.manager.get_key(key_info.key_id)

        assert result is not None
        assert result.key_id == key_info.key_id

    def test_get_key_not_found(self):
        """查询不存在的 key_id 返回 None"""
        assert self.manager.get_key("nonexistent") is None

    def test_get_key_by_name(self):
        """通过名称获取密钥"""
        self.manager.generate_key(name="named-key")
        result = self.manager.get_key_by_name("named-key")

        assert result is not None
        assert result.name == "named-key"

    def test_get_key_by_name_not_found(self):
        """查询不存在的名称返回 None"""
        assert self.manager.get_key_by_name("no-such-key") is None

    def test_get_key_by_fingerprint(self):
        """通过指纹获取密钥"""
        key_info = self.manager.generate_key(name="fp-key")
        result = self.manager.get_key_by_fingerprint(key_info.key_fingerprint)

        assert result is not None
        assert result.key_id == key_info.key_id

    def test_get_key_by_fingerprint_not_found(self):
        """查询不存在的指纹返回 None"""
        assert self.manager.get_key_by_fingerprint("deadbeef") is None

    def test_list_keys_all(self):
        """list_keys 返回所有密钥"""
        self.manager.generate_key(name="k1")
        self.manager.generate_key(name="k2")
        self.manager.generate_key(name="k3")

        keys = self.manager.list_keys()
        assert len(keys) == 3

    def test_list_keys_filter_by_type(self):
        """按类型过滤密钥"""
        self.manager.generate_key(name="sym", key_type=KeyType.SYMMETRIC)
        self.manager.generate_key(name="pub", key_type=KeyType.ASYMMETRIC_PUBLIC)

        sym_keys = self.manager.list_keys(key_type=KeyType.SYMMETRIC)
        assert len(sym_keys) == 1
        assert sym_keys[0].name == "sym"

    def test_list_keys_filter_by_status(self):
        """按状态过滤密钥"""
        k1 = self.manager.generate_key(name="active-key")
        self.manager.generate_key(name="another-key")
        self.manager.revoke_key(k1.key_id)

        active = self.manager.list_keys(status=KeyStatus.ACTIVE)
        revoked = self.manager.list_keys(status=KeyStatus.REVOKED)
        assert len(active) == 1
        assert len(revoked) == 1

    def test_list_keys_filter_by_tags(self):
        """按标签过滤密钥（子集匹配）"""
        self.manager.generate_key(name="a", tags={"prod", "api"})
        self.manager.generate_key(name="b", tags={"prod"})
        self.manager.generate_key(name="c", tags={"dev"})

        result = self.manager.list_keys(tags={"prod"})
        assert len(result) == 2

    def test_list_keys_include_data(self):
        """list_keys include_data=True 返回 (KeyInfo, bytes) 元组"""
        self.manager.generate_key(name="data-key")
        result = self.manager.list_keys(include_data=True)

        assert len(result) == 1
        info, data = result[0]
        assert isinstance(info, KeyInfo)
        assert isinstance(data, bytes)
        assert len(data) > 0

    # --- 更新 / 使用记录 ---

    def test_update_key_status(self):
        """更新密钥状态"""
        key_info = self.manager.generate_key(name="upd-key")
        ok = self.manager.update_key(key_info.key_id, status=KeyStatus.DISABLED)

        assert ok is True
        updated = self.manager.get_key(key_info.key_id)
        assert updated.status == KeyStatus.DISABLED

    def test_update_key_tags_and_metadata(self):
        """更新密钥标签和元数据"""
        key_info = self.manager.generate_key(name="meta-key")
        ok = self.manager.update_key(
            key_info.key_id,
            tags={"new-tag"},
            metadata={"extra": "value"},
        )

        assert ok is True
        updated = self.manager.get_key(key_info.key_id)
        assert "new-tag" in updated.tags
        assert updated.metadata["extra"] == "value"

    def test_update_key_not_found(self):
        """更新不存在的密钥返回 False"""
        assert self.manager.update_key("nonexistent", status=KeyStatus.DISABLED) is False

    def test_record_usage_encrypt(self):
        """记录加密操作"""
        key_info = self.manager.generate_key(name="usage-key")
        ok = self.manager.record_usage(key_info.key_id, operation="encrypt")

        assert ok is True
        updated = self.manager.get_key(key_info.key_id)
        assert updated.use_count == 1
        assert updated.encryption_count == 1
        assert updated.decryption_count == 0
        assert updated.last_used_at is not None

    def test_record_usage_decrypt(self):
        """记录解密操作"""
        key_info = self.manager.generate_key(name="dec-key")
        self.manager.record_usage(key_info.key_id, operation="decrypt")

        updated = self.manager.get_key(key_info.key_id)
        assert updated.use_count == 1
        assert updated.decryption_count == 1
        assert updated.encryption_count == 0

    def test_record_usage_not_found(self):
        """对不存在的密钥记录使用返回 False"""
        assert self.manager.record_usage("nonexistent") is False

    # --- 轮换 ---

    def test_rotate_key_generates_new(self):
        """轮换密钥生成新密钥并建立关联"""
        old = self.manager.generate_key(name="rot-key")
        new = self.manager.rotate_key(old.key_id)

        assert new is not None
        assert new.key_id != old.key_id
        assert new.parent_key_id == old.key_id
        assert new.version == old.version + 1
        assert new.last_rotated_at is not None

        # 旧密钥子列表更新
        old_refetched = self.manager.get_key(old.key_id)
        assert new.key_id in old_refetched.child_key_ids

    def test_rotate_key_not_found(self):
        """轮换不存在的密钥返回 None"""
        assert self.manager.rotate_key("nonexistent") is None

    def test_rotate_key_with_policy_grace_period(self):
        """有策略宽限期时旧密钥设置过期时间"""
        policy = KeyRotationPolicy(
            name="grace",
            grace_period_days=30,
            rotation_period_days=1,
        )
        self.manager.add_policy(policy)

        old = self.manager.generate_key(
            name="grace-key",
            policy_id=policy.policy_id,
        )
        # 使策略触发轮换
        old.created_at = datetime.now() - timedelta(days=100)
        new = self.manager.rotate_key(old.key_id)

        assert new is not None
        old_refetched = self.manager.get_key(old.key_id)
        assert old_refetched.expires_at is not None

    def test_rotate_key_preserve_old_false(self):
        """preserve_old=False 时旧密钥被撤销"""
        old = self.manager.generate_key(name="no-preserve")
        new = self.manager.rotate_key(old.key_id, preserve_old=False)

        assert new is not None
        old_refetched = self.manager.get_key(old.key_id)
        assert old_refetched.status == KeyStatus.REVOKED

    # --- 撤销 / 销毁 ---

    def test_revoke_key(self):
        """撤销密钥"""
        key_info = self.manager.generate_key(name="revoke-key")
        ok = self.manager.revoke_key(key_info.key_id)

        assert ok is True
        revoked = self.manager.get_key(key_info.key_id)
        assert revoked.status == KeyStatus.REVOKED

    def test_revoke_key_not_found(self):
        """撤销不存在的密钥返回 False"""
        assert self.manager.revoke_key("nonexistent") is False

    def test_destroy_key(self):
        """销毁密钥清除数据并更新状态"""
        key_info = self.manager.generate_key(name="destroy-key")
        ok = self.manager.destroy_key(key_info.key_id)

        assert ok is True
        destroyed = self.manager.get_key(key_info.key_id)
        assert destroyed.status == KeyStatus.DESTROYED
        assert self.manager.get_key_data(key_info.key_id) is None

    def test_destroy_key_not_found(self):
        """销毁不存在的密钥返回 False"""
        assert self.manager.destroy_key("nonexistent") is False

    # --- 策略 / 轮换检查 ---

    def test_add_policy_and_get(self):
        """添加策略后可查询"""
        policy = KeyRotationPolicy(name="quarterly")
        pid = self.manager.add_policy(policy)

        assert self.manager.get_policy(pid) is policy

    def test_check_rotation_needed_expired_key(self):
        """过期密钥出现在轮换检查结果中"""
        key_info = self.manager.generate_key(name="expired")
        key_info.expires_at = datetime.now() - timedelta(days=1)

        results = self.manager.check_rotation_needed()
        reasons = [r for _, r in results]
        assert "密钥已过期" in reasons

    def test_check_rotation_needed_policy_trigger(self):
        """策略触发的密钥出现在轮换检查结果中"""
        policy = KeyRotationPolicy(
            name="strict",
            rotation_period_days=1,
        )
        self.manager.add_policy(policy)

        self.manager.generate_key(
            name="old-key",
            policy_id=policy.policy_id,
        )
        # generate_key 的 created_at 为 now，rotation_period_days=1，
        # should_rotate 用 age_days 判断，age_days=0 < 1 所以不触发。
        # 需要设置 last_rotated_at 为过去时间。
        keys = self.manager.list_keys()
        keys[0].last_rotated_at = datetime.now() - timedelta(days=5)

        results = self.manager.check_rotation_needed()
        reasons = [r for _, r in results]
        assert "轮换策略触发" in reasons

    def test_check_rotation_needed_skips_inactive(self):
        """非活跃密钥不参与轮换检查"""
        policy = KeyRotationPolicy(name="p", rotation_period_days=1)
        self.manager.add_policy(policy)

        key_info = self.manager.generate_key(
            name="disabled-key",
            policy_id=policy.policy_id,
        )
        self.manager.revoke_key(key_info.key_id)

        results = self.manager.check_rotation_needed()
        assert len(results) == 0

    # --- 统计 ---

    def test_get_statistics(self):
        """统计数据正确"""
        self.manager.generate_key(name="s1", key_type=KeyType.SYMMETRIC)
        self.manager.generate_key(name="s2", key_type=KeyType.ASYMMETRIC_PUBLIC)
        self.manager.record_usage(
            self.manager.get_key_by_name("s1").key_id,
            operation="encrypt",
        )

        stats = self.manager.get_statistics()

        assert stats["total_keys"] == 2
        assert stats["total_usage"] == 1
        assert stats["policies"] == 0
        assert "symmetric" in stats["by_type"]
        assert "asymmetric_public" in stats["by_type"]
        assert "active" in stats["by_status"]

    def test_len_and_contains(self):
        """__len__ 和 __contains__ 魔术方法"""
        assert len(self.manager) == 0

        key_info = self.manager.generate_key(name="len-key")
        assert len(self.manager) == 1
        assert key_info.key_id in self.manager
        assert "nonexistent" not in self.manager

    # --- 回调 ---

    def test_on_rotation_callback(self):
        """轮换回调在轮换时被调用"""
        called_with = []

        def on_rot(old, new):
            called_with.append((old.key_id, new.key_id))

        self.manager.on_rotation(on_rot)

        old = self.manager.generate_key(name="cb-key")
        self.manager.rotate_key(old.key_id)

        assert len(called_with) == 1
        assert called_with[0][0] == old.key_id

    # --- get_key_data ---

    def test_get_key_data(self):
        """get_key_data 返回原始密钥字节"""
        key_info = self.manager.generate_key(name="raw-key")
        data = self.manager.get_key_data(key_info.key_id)

        assert isinstance(data, bytes)
        assert len(data) == 32  # AES-256 = 32 bytes

    def test_get_key_data_not_found(self):
        """get_key_data 对不存在的 key_id 返回 None"""
        assert self.manager.get_key_data("nonexistent") is None


# ---------------------------------------------------------------------------
# 磁盘持久化测试
# ---------------------------------------------------------------------------

class TestKeyManagerPersistence:
    """磁盘持久化测试（使用 tempfile）"""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_from_disk(self):
        """从磁盘加载已有密钥数据"""
        key_id = "persist-key-001"
        key_data = os.urandom(32)
        fingerprint = hashlib.sha256(key_data).hexdigest()[:16]

        # 写入元数据
        meta = {
            "key_id": key_id,
            "key_type": "symmetric",
            "name": "persist-key",
            "description": "",
            "key_fingerprint": fingerprint,
            "encrypted_key_ref": None,
            "status": "active",
            "created_at": datetime(2026, 1, 1).isoformat(),
            "activated_at": None,
            "expires_at": None,
            "last_used_at": None,
            "last_rotated_at": None,
            "use_count": 0,
            "encryption_count": 0,
            "decryption_count": 0,
            "algorithm": "AES-256-GCM",
            "key_size": 32,
            "allowed_operations": ["encrypt", "decrypt"],
            "allowed_users": [],
            "allowed_roles": [],
            "parent_key_id": None,
            "child_key_ids": [],
            "version": 1,
            "tags": [],
            "metadata": {},
            "created_by": "system",
            "rotation_policy_id": None,
        }
        meta_path = os.path.join(self.tmpdir, f"{key_id}.meta.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f)

        # 写入密钥数据
        data_path = os.path.join(self.tmpdir, f"{key_id}.key")
        with open(data_path, "wb") as f:
            f.write(base64.b64encode(key_data))

        # 加载
        manager = KeyManager(storage_path=self.tmpdir)

        loaded = manager.get_key(key_id)
        assert loaded is not None
        assert loaded.name == "persist-key"
        assert loaded.key_fingerprint == fingerprint
        assert loaded.status == KeyStatus.ACTIVE

        loaded_data = manager.get_key_data(key_id)
        assert loaded_data == key_data

        # 索引验证
        assert manager.get_key_by_name("persist-key") is not None
        assert manager.get_key_by_fingerprint(fingerprint) is not None

    def test_save_and_reload_roundtrip(self):
        """generate_key 保存后重新加载一致"""
        # 生成密钥并持久化
        mgr1 = KeyManager(storage_path=self.tmpdir)
        orig = mgr1.generate_key(name="roundtrip-key", tags={"test"})

        # 新管理器加载
        mgr2 = KeyManager(storage_path=self.tmpdir)
        loaded = mgr2.get_key(orig.key_id)

        assert loaded is not None
        assert loaded.name == "roundtrip-key"
        assert loaded.tags == {"test"}

        loaded_data = mgr2.get_key_data(orig.key_id)
        assert loaded_data == mgr1.get_key_data(orig.key_id)

    def test_empty_storage_path_loads_nothing(self):
        """空目录不加载任何密钥"""
        manager = KeyManager(storage_path=self.tmpdir)
        assert len(manager) == 0

    def test_nonexistent_storage_path(self):
        """不存在的 storage_path 不报错"""
        manager = KeyManager(storage_path="/tmp/nonexistent_zkm_test_dir")
        assert len(manager) == 0


# ---------------------------------------------------------------------------
# 独立函数测试
# ---------------------------------------------------------------------------

class TestModuleFunctions:
    """模块级函数测试"""

    def test_generate_random_key_default(self):
        """generate_random_key 默认生成 32 字节"""
        key = generate_random_key()
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_generate_random_key_custom_size(self):
        """generate_random_key 自定义大小"""
        key = generate_random_key(key_size=64)
        assert len(key) == 64

    def test_get_default_key_manager_singleton(self):
        """get_default_key_manager 返回单例"""
        # 重置全局实例以确保干净状态
        import packages.Runtime.security.key_manager as km_mod
        with km_mod._key_manager_lock:
            km_mod._default_key_manager = None

        mgr1 = get_default_key_manager()
        mgr2 = get_default_key_manager()
        assert mgr1 is mgr2

        # 恢复
        with km_mod._key_manager_lock:
            km_mod._default_key_manager = None
