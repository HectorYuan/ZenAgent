"""
密钥管理模块

提供密钥的生成、存储、轮换和生命周期管理
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Set, Tuple, Union
import hashlib
import os
import threading
import uuid
import json

# 尝试导入加密库
try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class KeyType(Enum):
    """密钥类型"""
    SYMMETRIC = "symmetric"          # 对称密钥 (AES)
    ASYMMETRIC_PRIVATE = "asymmetric_private"  # 非对称私钥
    ASYMMETRIC_PUBLIC = "asymmetric_public"    # 非对称公钥
    MASTER = "master"               # 主密钥
    DATA_ENCRYPTION = "data_encryption"        # 数据加密密钥 (DEK)
    KEY_ENCRYPTION = "key_encryption"          # 密钥加密密钥 (KEK)


class KeyStatus(Enum):
    """密钥状态"""
    ACTIVE = "active"               # 活跃
    ENABLED = "enabled"             # 启用
    DISABLED = "disabled"            # 禁用
    EXPIRED = "expired"              # 过期
    REVOKED = "revoked"              # 撤销
    DESTROYED = "destroyed"          # 已销毁


@dataclass
class KeyInfo:
    """
    密钥信息
    
    存储密钥的元数据
    """
    key_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    key_type: KeyType = KeyType.SYMMETRIC
    name: str = ""
    description: str = ""
    
    # 密钥材料 (不存储实际密钥，只存储引用或哈希)
    key_fingerprint: Optional[str] = None  # 密钥指纹
    encrypted_key_ref: Optional[str] = None  # 加密密钥引用
    
    # 状态
    status: KeyStatus = KeyStatus.ACTIVE
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    activated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    last_rotated_at: Optional[datetime] = None
    
    # 使用统计
    use_count: int = 0
    encryption_count: int = 0
    decryption_count: int = 0
    
    # 安全设置
    algorithm: str = "AES-256-GCM"
    key_size: int = 32  # 字节
    
    # 权限
    allowed_operations: Set[str] = field(default_factory=lambda: {"encrypt", "decrypt"})
    allowed_users: Set[str] = field(default_factory=set)  # 用户 ID
    allowed_roles: Set[str] = field(default_factory=set)
    
    # 关联
    parent_key_id: Optional[str] = None
    child_key_ids: List[str] = field(default_factory=list)
    version: int = 1
    
    # 元数据
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 审计
    created_by: str = "system"
    rotation_policy_id: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        """检查密钥是否有效"""
        return (
            self.status in (KeyStatus.ACTIVE, KeyStatus.ENABLED)
            and not self.is_expired
        )
    
    @property
    def is_expired(self) -> bool:
        """检查密钥是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    @property
    def age_days(self) -> int:
        """密钥使用天数"""
        return (datetime.now() - self.created_at).days
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "key_id": self.key_id,
            "key_type": self.key_type.value,
            "name": self.name,
            "description": self.description,
            "key_fingerprint": self.key_fingerprint,
            "encrypted_key_ref": self.encrypted_key_ref,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "last_rotated_at": self.last_rotated_at.isoformat() if self.last_rotated_at else None,
            "use_count": self.use_count,
            "encryption_count": self.encryption_count,
            "decryption_count": self.decryption_count,
            "algorithm": self.algorithm,
            "key_size": self.key_size,
            "allowed_operations": list(self.allowed_operations),
            "allowed_users": list(self.allowed_users),
            "allowed_roles": list(self.allowed_roles),
            "parent_key_id": self.parent_key_id,
            "child_key_ids": self.child_key_ids,
            "version": self.version,
            "tags": list(self.tags),
            "metadata": self.metadata,
            "created_by": self.created_by,
            "rotation_policy_id": self.rotation_policy_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KeyInfo":
        """从字典创建"""
        data = data.copy()
        if "key_type" in data:
            data["key_type"] = KeyType(data["key_type"])
        if "status" in data:
            data["status"] = KeyStatus(data["status"])
        for dt_field in ["created_at", "activated_at", "expires_at", "last_used_at", "last_rotated_at"]:
            if data.get(dt_field) and isinstance(data[dt_field], str):
                data[dt_field] = datetime.fromisoformat(data[dt_field])
        if "allowed_operations" in data:
            data["allowed_operations"] = set(data["allowed_operations"])
        if "allowed_users" in data:
            data["allowed_users"] = set(data["allowed_users"])
        if "allowed_roles" in data:
            data["allowed_roles"] = set(data["allowed_roles"])
        if "tags" in data:
            data["tags"] = set(data["tags"])
        return cls(**data)


@dataclass
class KeyRotationPolicy:
    """密钥轮换策略"""
    policy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    
    # 轮换条件
    rotation_period_days: int = 90           # 轮换周期 (天)
    max_usage_count: int = 0                  # 最大使用次数 (0 = 无限制)
    auto_rotate: bool = True                  # 是否自动轮换
    
    # 兼容性设置
    grace_period_days: int = 30               # 宽限期 (旧密钥仍可用于解密)
    keep_versions: int = 3                    # 保留的旧版本数量
    
    # 告警设置
    alert_before_expiry_days: int = 7         # 过期前告警天数
    alert_usage_threshold: float = 0.8        # 使用率告警阈值
    
    # 状态
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    def should_rotate(self, key_info: KeyInfo) -> bool:
        """检查是否应该轮换密钥"""
        if not self.enabled:
            return False
        
        # 检查使用次数
        if self.max_usage_count > 0:
            if key_info.use_count >= self.max_usage_count:
                return True
        
        # 检查时间
        if key_info.last_rotated_at:
            days_since_rotation = (datetime.now() - key_info.last_rotated_at).days
        else:
            days_since_rotation = key_info.age_days
        
        if days_since_rotation >= self.rotation_period_days:
            return True
        
        return False
    
    def should_alert(self, key_info: KeyInfo) -> Tuple[bool, str]:
        """检查是否应该告警"""
        if not self.enabled:
            return False, ""
        
        # 过期告警
        if key_info.expires_at:
            days_to_expiry = (key_info.expires_at - datetime.now()).days
            if 0 < days_to_expiry <= self.alert_before_expiry_days:
                return True, f"密钥将在 {days_to_expiry} 天后过期"
        
        # 使用率告警
        if self.max_usage_count > 0:
            usage_ratio = key_info.use_count / self.max_usage_count
            if usage_ratio >= self.alert_usage_threshold:
                return True, f"密钥使用率已达 {usage_ratio*100:.1f}%"
        
        return False, ""


class KeyManager:
    """
    密钥管理器
    
    提供密钥的集中管理和生命周期控制
    """
    
    def __init__(
        self,
        master_key: Optional[bytes] = None,
        storage_path: Optional[str] = None,
    ):
        """
        初始化密钥管理器
        
        Args:
            master_key: 主密钥 (用于加密存储)
            storage_path: 存储路径
        """
        self.master_key = master_key
        self.storage_path = storage_path
        
        # 密钥存储
        self._keys: Dict[str, KeyInfo] = {}
        self._key_data: Dict[str, bytes] = {}  # 实际密钥数据
        self._policies: Dict[str, KeyRotationPolicy] = {}
        
        # 索引
        self._by_type: Dict[KeyType, Set[str]] = {}
        self._by_status: Dict[KeyStatus, Set[str]] = {}
        self._by_name: Dict[str, str] = {}
        self._by_fingerprint: Dict[str, str] = {}
        
        # 锁
        self._lock = threading.RLock()
        
        # 回调
        self._rotation_callbacks: List[Callable[[KeyInfo, KeyInfo], None]] = []
        self._expiry_callbacks: List[Callable[[KeyInfo], None]] = []
        
        # 加载已有密钥
        if storage_path:
            self._load_from_disk()
    
    def generate_key(
        self,
        name: str,
        key_type: KeyType = KeyType.SYMMETRIC,
        algorithm: str = "AES-256-GCM",
        key_size: Optional[int] = None,
        expires_in_days: Optional[int] = None,
        tags: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        policy_id: Optional[str] = None,
        created_by: str = "system",
    ) -> KeyInfo:
        """
        生成新密钥
        
        Args:
            name: 密钥名称
            key_type: 密钥类型
            algorithm: 算法
            key_size: 密钥大小 (字节)
            expires_in_days: 过期天数
            tags: 标签
            metadata: 元数据
            policy_id: 轮换策略 ID
            created_by: 创建者
            
        Returns:
            密钥信息
        """
        # 确定密钥大小
        if key_size is None:
            if "256" in algorithm:
                key_size = 32
            elif "192" in algorithm:
                key_size = 24
            elif "128" in algorithm:
                key_size = 16
            else:
                key_size = 32
        
        # 生成密钥数据
        key_data = os.urandom(key_size)
        
        # 创建密钥信息
        key_info = KeyInfo(
            key_type=key_type,
            name=name,
            description=metadata.get("description", "") if metadata else "",
            key_fingerprint=self._compute_fingerprint(key_data),
            algorithm=algorithm,
            key_size=key_size,
            expires_at=datetime.now() + timedelta(days=expires_in_days) if expires_in_days else None,
            tags=tags or set(),
            metadata=metadata or {},
            rotation_policy_id=policy_id,
            created_by=created_by,
            activated_at=datetime.now(),
        )
        
        with self._lock:
            # 存储密钥
            self._keys[key_info.key_id] = key_info
            self._key_data[key_info.key_id] = key_data
            
            # 更新索引
            self._update_indexes(key_info)
            
            # 保存
            if self.storage_path:
                self._save_to_disk(key_info.key_id)
        
        return key_info
    
    def _compute_fingerprint(self, key_data: bytes) -> str:
        """计算密钥指纹"""
        return hashlib.sha256(key_data).hexdigest()[:16]
    
    def _update_indexes(self, key_info: KeyInfo) -> None:
        """更新索引"""
        # 按类型索引
        if key_info.key_type not in self._by_type:
            self._by_type[key_info.key_type] = set()
        self._by_type[key_info.key_type].add(key_info.key_id)
        
        # 按状态索引
        if key_info.status not in self._by_status:
            self._by_status[key_info.status] = set()
        self._by_status[key_info.status].add(key_info.key_id)
        
        # 按名称索引
        self._by_name[key_info.name] = key_info.key_id
        
        # 按指纹索引
        if key_info.key_fingerprint:
            self._by_fingerprint[key_info.key_fingerprint] = key_info.key_id
    
    def _remove_from_indexes(self, key_id: str) -> None:
        """从索引中移除"""
        key_info = self._keys.get(key_id)
        if key_info is None:
            return
        
        # 从类型索引移除
        if key_info.key_type in self._by_type:
            self._by_type[key_info.key_type].discard(key_id)
        
        # 从状态索引移除
        if key_info.status in self._by_status:
            self._by_status[key_info.status].discard(key_id)
        
        # 从名称索引移除
        self._by_name.pop(key_info.name, None)
        
        # 从指纹索引移除
        if key_info.key_fingerprint:
            self._by_fingerprint.pop(key_info.key_fingerprint, None)
    
    def get_key(self, key_id: str) -> Optional[KeyInfo]:
        """获取密钥信息"""
        return self._keys.get(key_id)
    
    def get_key_data(self, key_id: str) -> Optional[bytes]:
        """获取密钥数据"""
        return self._key_data.get(key_id)
    
    def get_key_by_name(self, name: str) -> Optional[KeyInfo]:
        """通过名称获取密钥"""
        key_id = self._by_name.get(name)
        return self._keys.get(key_id) if key_id else None
    
    def get_key_by_fingerprint(self, fingerprint: str) -> Optional[KeyInfo]:
        """通过指纹获取密钥"""
        key_id = self._by_fingerprint.get(fingerprint)
        return self._keys.get(key_id) if key_id else None
    
    def list_keys(
        self,
        key_type: Optional[KeyType] = None,
        status: Optional[KeyStatus] = None,
        tags: Optional[Set[str]] = None,
        include_data: bool = False,
    ) -> List[Union[KeyInfo, Tuple[KeyInfo, bytes]]]:
        """列出密钥"""
        with self._lock:
            keys = list(self._keys.values())
        
        # 过滤
        if key_type:
            keys = [k for k in keys if k.key_type == key_type]
        if status:
            keys = [k for k in keys if k.status == status]
        if tags:
            keys = [k for k in keys if tags.issubset(k.tags)]
        
        if include_data:
            return [(k, self._key_data.get(k.key_id, b"")) for k in keys]
        return keys
    
    def update_key(
        self,
        key_id: str,
        status: Optional[KeyStatus] = None,
        tags: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """更新密钥信息"""
        with self._lock:
            key_info = self._keys.get(key_id)
            if key_info is None:
                return False
            
            old_status = key_info.status
            
            if status is not None:
                key_info.status = status
                self._by_status[old_status].discard(key_id)
                if status not in self._by_status:
                    self._by_status[status] = set()
                self._by_status[status].add(key_id)
            
            if tags is not None:
                key_info.tags = tags
            
            if metadata is not None:
                key_info.metadata.update(metadata)
            
            return True
    
    def record_usage(self, key_id: str, operation: str = "encrypt") -> bool:
        """记录密钥使用"""
        with self._lock:
            key_info = self._keys.get(key_id)
            if key_info is None:
                return False
            
            key_info.use_count += 1
            key_info.last_used_at = datetime.now()
            
            if operation == "encrypt":
                key_info.encryption_count += 1
            elif operation == "decrypt":
                key_info.decryption_count += 1
            
            return True
    
    def rotate_key(
        self,
        key_id: str,
        new_key_id: Optional[str] = None,
        preserve_old: bool = True,
    ) -> Optional[KeyInfo]:
        """
        轮换密钥
        
        Args:
            key_id: 要轮换的密钥 ID
            new_key_id: 新密钥 ID (已有密钥)
            preserve_old: 是否保留旧密钥
            
        Returns:
            新密钥信息
        """
        with self._lock:
            old_key = self._keys.get(key_id)
            if old_key is None:
                return None
            
            # 生成新密钥
            if new_key_id is None:
                new_key = self.generate_key(
                    name=old_key.name,
                    key_type=old_key.key_type,
                    algorithm=old_key.algorithm,
                    key_size=old_key.key_size,
                    tags=old_key.tags,
                    metadata=old_key.metadata,
                    policy_id=old_key.rotation_policy_id,
                    created_by=old_key.created_by,
                )
            else:
                new_key = self._keys.get(new_key_id)
                if new_key is None:
                    return None
            
            # 更新关联
            new_key.parent_key_id = key_id
            old_key.child_key_ids.append(new_key.key_id)
            new_key.version = old_key.version + 1
            new_key.last_rotated_at = datetime.now()
            
            # 禁用旧密钥（如果保留宽限期）
            policy = self._policies.get(old_key.rotation_policy_id)
            if policy and policy.grace_period_days > 0:
                old_key.expires_at = datetime.now() + timedelta(days=policy.grace_period_days)
            elif not preserve_old:
                old_key.status = KeyStatus.REVOKED
            
            # 触发回调
            for callback in self._rotation_callbacks:
                try:
                    callback(old_key, new_key)
                except Exception:
                    pass
            
            return new_key
    
    def revoke_key(self, key_id: str) -> bool:
        """撤销密钥"""
        return self.update_key(key_id, status=KeyStatus.REVOKED)
    
    def destroy_key(self, key_id: str) -> bool:
        """
        销毁密钥
        
        Args:
            key_id: 密钥 ID
            
        Returns:
            是否成功
        """
        with self._lock:
            key_info = self._keys.get(key_id)
            if key_info is None:
                return False
            
            # 从索引移除
            self._remove_from_indexes(key_id)
            
            # 删除密钥数据
            self._key_data.pop(key_id, None)
            
            # 更新状态
            key_info.status = KeyStatus.DESTROYED
            
            return True
    
    def add_policy(self, policy: KeyRotationPolicy) -> str:
        """添加轮换策略"""
        self._policies[policy.policy_id] = policy
        return policy.policy_id
    
    def get_policy(self, policy_id: str) -> Optional[KeyRotationPolicy]:
        """获取轮换策略"""
        return self._policies.get(policy_id)
    
    def check_rotation_needed(self) -> List[Tuple[KeyInfo, str]]:
        """检查需要轮换的密钥"""
        result = []
        
        for key_info in self._keys.values():
            if key_info.status not in (KeyStatus.ACTIVE, KeyStatus.ENABLED):
                continue
            
            # 检查过期
            if key_info.is_expired:
                result.append((key_info, "密钥已过期"))
                continue
            
            # 检查策略
            if key_info.rotation_policy_id:
                policy = self._policies.get(key_info.rotation_policy_id)
                if policy:
                    should, reason = policy.should_alert(key_info)
                    if should:
                        result.append((key_info, reason))
                    
                    if policy.should_rotate(key_info):
                        result.append((key_info, "轮换策略触发"))
        
        return result
    
    def on_rotation(self, callback: Callable[[KeyInfo, KeyInfo], None]) -> None:
        """注册轮换回调"""
        self._rotation_callbacks.append(callback)
    
    def on_expiry(self, callback: Callable[[KeyInfo], None]) -> None:
        """注册过期回调"""
        self._expiry_callbacks.append(callback)
    
    def _save_to_disk(self, key_id: str) -> None:
        """保存密钥到磁盘"""
        if not self.storage_path:
            return
        
        import os
        os.makedirs(self.storage_path, exist_ok=True)
        
        key_info = self._keys.get(key_id)
        key_data = self._key_data.get(key_id)
        
        if key_info and key_data:
            # 保存元数据
            meta_path = os.path.join(self.storage_path, f"{key_id}.meta.json")
            with open(meta_path, "w") as f:
                json.dump(key_info.to_dict(), f)
            
            # 保存密钥数据 (加密)
            if self.master_key:
                from ..audit import get_default_logger
                logger = get_default_logger()
                encrypted_data = EncryptedData.from_base64(
                    self._encrypt_for_storage(key_data)
                )
                key_data = encrypted_data.to_base64().encode()
            else:
                key_data = base64.b64encode(key_data)
            
            data_path = os.path.join(self.storage_path, f"{key_id}.key")
            with open(data_path, "wb") as f:
                f.write(key_data if isinstance(key_data, bytes) else key_data.encode())
    
    def _load_from_disk(self) -> None:
        """从磁盘加载密钥"""
        if not self.storage_path:
            return
        
        import os
        import base64
        
        if not os.path.exists(self.storage_path):
            return
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith(".meta.json"):
                key_id = filename[:-9]  # 移除 .meta.json
                meta_path = os.path.join(self.storage_path, filename)
                
                with open(meta_path, "r") as f:
                    key_info = KeyInfo.from_dict(json.load(f))
                
                # 加载密钥数据
                data_path = os.path.join(self.storage_path, f"{key_id}.key")
                if os.path.exists(data_path):
                    with open(data_path, "rb") as f:
                        key_data = f.read()
                    
                    # 解密
                    if self.master_key:
                        encrypted_data = EncryptedData.from_base64(key_data.decode())
                        key_data = self._decrypt_from_storage(encrypted_data)
                    else:
                        key_data = base64.b64decode(key_data)
                    
                    self._key_data[key_id] = key_data
                
                self._keys[key_id] = key_info
                self._update_indexes(key_info)
    
    def _encrypt_for_storage(self, key_data: bytes) -> str:
        """加密密钥用于存储"""
        # 简化实现，实际应使用专门的加密逻辑
        from .encryption import AESEncryptor, EncryptionType, EncryptedData
        encryptor = AESEncryptor(self.master_key[:32], EncryptionType.AES_256_GCM)
        return encryptor.encrypt(key_data).to_base64()
    
    def _decrypt_from_storage(self, encrypted_data: 'EncryptedData') -> bytes:
        """从存储解密密钥"""
        from .encryption import AESEncryptor, EncryptedData
        encryptor = AESEncryptor(self.master_key[:32], EncryptionType.AES_256_GCM)
        return encryptor.decrypt(encrypted_data)
    
    def export_public_keys(self) -> Dict[str, Dict[str, Any]]:
        """导出公钥信息"""
        result = {}
        for key_info in self._keys.values():
            if key_info.key_type == KeyType.ASYMMETRIC_PUBLIC:
                result[key_info.key_id] = {
                    "key_id": key_info.key_id,
                    "name": key_info.name,
                    "algorithm": key_info.algorithm,
                    "fingerprint": key_info.key_fingerprint,
                }
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_keys": len(self._keys),
                "by_type": {
                    kt.value: len(ids) for kt, ids in self._by_type.items()
                },
                "by_status": {
                    ks.value: len(ids) for ks, ids in self._by_status.items()
                },
                "total_usage": sum(k.use_count for k in self._keys.values()),
                "policies": len(self._policies),
            }
    
    def __len__(self) -> int:
        return len(self._keys)
    
    def __contains__(self, key_id: str) -> bool:
        return key_id in self._keys


# 全局密钥管理器实例
_default_key_manager: Optional[KeyManager] = None
_key_manager_lock = threading.Lock()


def get_default_key_manager() -> KeyManager:
    """获取默认密钥管理器"""
    global _default_key_manager
    with _key_manager_lock:
        if _default_key_manager is None:
            _default_key_manager = KeyManager()
        return _default_key_manager


def generate_random_key(key_size: int = 32) -> bytes:
    """生成随机密钥"""
    return os.urandom(key_size)
