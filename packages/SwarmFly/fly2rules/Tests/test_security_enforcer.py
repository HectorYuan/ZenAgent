"""
安全执行模块单元测试

覆盖 PermissionChecker / AuditLogger / EncryptionHandler 三个组件。
"""

import pytest
from datetime import datetime, timedelta

from packages.SwarmFly.fly2rules.Core.SecurityEnforcer.permission_checker import (
    PermissionChecker, Permission, PermissionContext, PermissionCheckResult,
    Role, User,
)
from packages.SwarmFly.fly2rules.Core.SecurityEnforcer.audit_logger import (
    AuditLogger, AuditEventType, AuditLevel, AuditEvent,
)
from packages.SwarmFly.fly2rules.Core.SecurityEnforcer.encryption_handler import (
    EncryptionHandler, EncryptionConfig, EncryptionAlgorithm, EncryptedData,
)


# ================================================================
#  PermissionChecker 测试
# ================================================================

class TestPermissionChecker:
    """PermissionChecker 权限检查器测试"""

    def setup_method(self):
        self.checker = PermissionChecker()

    def _make_context(self, user_id="u1", roles=None, permissions=Permission.NONE):
        """快速构建权限上下文"""
        user = self.checker.create_user(
            user_id=user_id,
            name="test_user",
            roles=roles or [],
            permissions=permissions,
        )
        return PermissionContext(user=user, resource_type="rule", action="read")

    def test_grant_role_permission(self):
        """分配角色后权限检查通过"""
        ctx = self._make_context(roles=["reader"])
        result = self.checker.check_permission(ctx, Permission.READ)
        assert result.allowed is True

    def test_deny_insufficient_permission(self):
        """缺少权限时拒绝"""
        ctx = self._make_context(roles=["reader"])
        result = self.checker.check_permission(ctx, Permission.WRITE)
        assert result.allowed is False
        assert "denied" in result.reason.lower() or "insufficient" in result.reason.lower()

    def test_revoke_role(self):
        """撤销角色后权限丢失"""
        user = self.checker.create_user("u2", "user2", roles=["operator"])
        self.checker.revoke_role("u2", "operator")
        ctx = PermissionContext(user=user, resource_type="rule")
        result = self.checker.check_permission(ctx, Permission.WRITE)
        assert result.allowed is False

    def test_admin_has_all_permissions(self):
        """admin 角色拥有所有权限"""
        ctx = self._make_context(roles=["admin"])
        for perm in (Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.DELETE):
            result = self.checker.check_permission(ctx, perm)
            assert result.allowed is True

    def test_direct_permissions(self):
        """直接权限生效"""
        ctx = self._make_context(permissions=Permission.READ | Permission.WRITE)
        assert self.checker.check_permission(ctx, Permission.READ).allowed is True
        assert self.checker.check_permission(ctx, Permission.WRITE).allowed is True
        assert self.checker.check_permission(ctx, Permission.DELETE).allowed is False

    def test_inactive_user_denied(self):
        """非活跃用户被拒绝"""
        user = self.checker.create_user("u3", "inactive", roles=["admin"])
        user.is_active = False
        ctx = PermissionContext(user=user, resource_type="rule")
        result = self.checker.check_permission(ctx, Permission.READ)
        assert result.allowed is False

    def test_check_multiple_permissions(self):
        """多权限检查"""
        ctx = self._make_context(roles=["operator"])
        result = self.checker.check_multiple_permissions(
            ctx, {Permission.READ, Permission.WRITE}
        )
        assert result.allowed is True

    def test_check_multiple_permissions_partial_fail(self):
        """多权限检查中部分缺失"""
        ctx = self._make_context(roles=["reader"])
        result = self.checker.check_multiple_permissions(
            ctx, {Permission.READ, Permission.DELETE}
        )
        assert result.allowed is False
        assert Permission.DELETE in result.missing_permissions

    def test_stats_tracking(self):
        """统计信息正确"""
        ctx = self._make_context(roles=["reader"])
        self.checker.check_permission(ctx, Permission.READ)
        stats = self.checker.get_stats()
        assert stats["total_checks"] >= 1
        assert stats["allowed_checks"] >= 1


# ================================================================
#  AuditLogger 测试
# ================================================================

class TestAuditLogger:
    """AuditLogger 审计日志测试"""

    def setup_method(self):
        self.logger = AuditLogger()

    def test_log_event(self):
        """记录审计事件"""
        event = self.logger.log(
            event_type=AuditEventType.USER_LOGIN,
            action="用户登录",
            user_id="u1",
        )
        assert isinstance(event, AuditEvent)
        assert event.user_id == "u1"

    def test_query_by_user_id(self):
        """按用户 ID 查询事件"""
        self.logger.log(AuditEventType.USER_LOGIN, "登录", user_id="u1")
        self.logger.log(AuditEventType.USER_LOGOUT, "登出", user_id="u1")
        self.logger.log(AuditEventType.USER_LOGIN, "登录", user_id="u2")
        results = self.logger.query(user_id="u1")
        assert len(results) == 2

    def test_query_by_event_type(self):
        """按事件类型查询"""
        self.logger.log(AuditEventType.RULE_CREATE, "创建规则", user_id="u1")
        self.logger.log(AuditEventType.RULE_DELETE, "删除规则", user_id="u1")
        results = self.logger.query(event_types=[AuditEventType.RULE_CREATE])
        assert len(results) == 1

    def test_query_by_level(self):
        """按级别过滤"""
        self.logger.log(AuditEventType.SYSTEM_ERROR, "系统错误", level=AuditLevel.ERROR)
        self.logger.log(AuditEventType.USER_LOGIN, "登录", level=AuditLevel.INFO)
        results = self.logger.query(level=AuditLevel.ERROR)
        assert all(e.level.value >= AuditLevel.ERROR.value for e in results)

    def test_query_pagination(self):
        """分页查询"""
        for i in range(10):
            self.logger.log(AuditEventType.USER_LOGIN, f"登录{i}", user_id="u1")
        page = self.logger.query(user_id="u1", limit=3, offset=0)
        assert len(page) == 3

    def test_stats_tracking(self):
        """统计信息正确"""
        self.logger.log(AuditEventType.USER_LOGIN, "登录")
        self.logger.log(AuditEventType.AUTH_FAILURE, "认证失败", result="failure")
        stats = self.logger.get_statistics()
        assert stats["total_events"] >= 2

    def test_event_to_dict(self):
        """事件转字典"""
        event = self.logger.log(AuditEventType.RULE_CREATE, "创建")
        d = event.to_dict()
        assert "event_type" in d
        assert "timestamp" in d

    def test_compliance_report(self):
        """生成合规报告"""
        self.logger.log(AuditEventType.PERMISSION_CHECK, "检查权限", user_id="u1")
        self.logger.log(AuditEventType.PERMISSION_DENY, "权限拒绝", user_id="u2")
        report = self.logger.generate_compliance_report(
            start_date=datetime.now() - timedelta(hours=1),
            end_date=datetime.now() + timedelta(hours=1),
        )
        assert "summary" in report
        assert report["summary"]["total_events"] >= 2

    def test_export_events_json(self):
        """导出事件为 JSON"""
        self.logger.log(AuditEventType.USER_LOGIN, "登录")
        exported = self.logger.export_events(format="json")
        assert isinstance(exported, str)
        assert "user.login" in exported


# ================================================================
#  EncryptionHandler 测试
# ================================================================

class TestEncryptionHandler:
    """EncryptionHandler 加密处理器测试"""

    def setup_method(self):
        self.handler = EncryptionHandler()

    def test_encrypt_decrypt_roundtrip(self):
        """加密后解密还原原文"""
        plaintext = "Hello, SwarmFly!"
        encrypted = self.handler.encrypt(plaintext)
        assert isinstance(encrypted, EncryptedData)
        decrypted = self.handler.decrypt(encrypted)
        assert decrypted.decode("utf-8") == plaintext

    def test_encrypt_bytes(self):
        """加密 bytes 类型数据"""
        data = b"\x00\x01\x02\xff"
        encrypted = self.handler.encrypt(data)
        decrypted = self.handler.decrypt(encrypted)
        assert decrypted == data

    def test_different_keys_produce_different_ciphertext(self):
        """不同密钥产生不同密文"""
        key1 = self.handler.key_manager.generate_key(
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            key_id="key_a",
        )
        key2 = self.handler.key_manager.generate_key(
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            key_id="key_b",
        )
        enc1 = self.handler.encrypt("secret", key_id="key_a")
        enc2 = self.handler.encrypt("secret", key_id="key_b")
        assert enc1.ciphertext != enc2.ciphertext

    def test_derive_key(self):
        """密钥派生功能"""
        key, salt = self.handler.derive_key("my_password")
        assert isinstance(key, bytes)
        assert isinstance(salt, bytes)
        assert len(key) > 0

    def test_sign_and_verify(self):
        """HMAC 签名与验证"""
        data = "important message"
        signature = self.handler.sign(data)
        assert self.handler.verify(data, signature) is True

    def test_verify_tampered_data_fails(self):
        """篡改数据后验证失败"""
        data = "original"
        signature = self.handler.sign(data)
        assert self.handler.verify("tampered", signature) is False

    def test_hash_sensitive_data(self):
        """敏感数据哈希"""
        hashed = self.handler.hash_sensitive_data("password123")
        assert "$" in hashed
        assert self.handler.verify_hash("password123", hashed) is True
        assert self.handler.verify_hash("wrong_password", hashed) is False

    def test_secure_envelope_roundtrip(self):
        """安全信封封装与解封"""
        data = {"message": "secret", "value": 42}
        envelope = self.handler.create_secure_envelope(data)
        assert "encrypted" in envelope
        assert "signature" in envelope
        restored = self.handler.open_secure_envelope(envelope)
        assert restored == data

    def test_generate_random_token(self):
        """生成随机令牌"""
        token = self.handler.generate_random_token(32)
        assert isinstance(token, str)
        assert len(token) > 0
