"""
安全存储模块

提供加密数据的安全存储接口
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Union, Iterator
import json
import os
import threading
import base64
import time

from .encryption import (
    EncryptionManager,
    EncryptionType,
    EncryptedData,
    HybridEncryptor,
)


class StorageBackend(Enum):
    """存储后端"""
    MEMORY = "memory"               # 内存存储
    FILE = "file"                   # 文件存储
    VAULT = "vault"                 # HashiCorp Vault
    ENCRYPTED_FILE = "encrypted_file"  # 加密文件存储


@dataclass
class StorageConfig:
    """存储配置"""
    backend: StorageBackend = StorageBackend.MEMORY
    base_path: str = "./secure_storage"
    encryption_type: EncryptionType = EncryptionType.AES_256_GCM
    key: Optional[bytes] = None
    auto_commit: bool = True
    max_memory_size: int = 10000  # 内存存储最大条目数
    file_extension: str = ".sec"


class SecureStorage:
    """
    安全存储
    
    提供加密数据的安全存储接口
    """
    
    def __init__(
        self,
        config: Optional[StorageConfig] = None,
        encryption_manager: Optional[EncryptionManager] = None,
    ):
        """
        初始化安全存储
        
        Args:
            config: 存储配置
            encryption_manager: 加密管理器
        """
        self.config = config or StorageConfig()
        self.encryption_manager = encryption_manager or EncryptionManager()
        
        # 如果没有密钥，生成一个
        if self.config.key is None:
            self.config.key = os.urandom(32)
        
        # 初始化加密管理器
        self._setup_encryption()
        
        # 存储
        self._memory_store: Dict[str, EncryptedData] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        
        # 索引
        self._keys_index: Dict[str, str] = {}  # name -> key_id
        
        # 锁
        self._lock = threading.RLock()
        
        # 回调
        self._pre_store_callbacks: List[Callable[[str, Any], Any]] = []
        self._post_store_callbacks: List[Callable[[str, EncryptedData], None]] = []
        
        # 初始化存储路径
        if self.config.backend in [
            StorageBackend.FILE,
            StorageBackend.ENCRYPTED_FILE,
        ]:
            os.makedirs(self.config.base_path, exist_ok=True)
    
    def _setup_encryption(self) -> None:
        """设置加密"""
        if self.config.encryption_type == EncryptionType.HYBRID:
            # 混合加密
            hybrid, private_pem, public_pem = HybridEncryptor.generate()
            self.encryption_manager.set_hybrid_encryptor(hybrid)
        else:
            # 对称加密
            self.encryption_manager.set_aes_key(
                self.config.key,
                self.config.encryption_type,
            )
    
    def store(
        self,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
        encrypt: bool = True,
    ) -> str:
        """
        存储数据
        
        Args:
            key: 存储键
            value: 要存储的值
            metadata: 元数据
            encrypt: 是否加密
            
        Returns:
            存储记录 ID
        """
        # 预处理
        for callback in self._pre_store_callbacks:
            value = callback(key, value)
        
        with self._lock:
            # 序列化数据
            if isinstance(value, (dict, list)):
                data_bytes = json.dumps(value, default=str).encode("utf-8")
            elif isinstance(value, str):
                data_bytes = value.encode("utf-8")
            elif isinstance(value, bytes):
                data_bytes = value
            else:
                data_bytes = str(value).encode("utf-8")
            
            # 加密
            if encrypt and self.config.backend != StorageBackend.MEMORY:
                encrypted = self.encryption_manager.encrypt(data_bytes)
            else:
                # 不加密，直接存储
                encrypted = EncryptedData(
                    cipher_text=data_bytes,
                    encryption_type=self.config.encryption_type,
                )
            
            # 存储
            record_id = self._save(key, encrypted, metadata)
            
            # 更新索引
            self._keys_index[key] = record_id
            
            # 后处理
            for callback in self._post_store_callbacks:
                try:
                    callback(key, encrypted)
                except Exception:
                    pass
            
            return record_id
    
    def _save(
        self,
        key: str,
        encrypted_data: EncryptedData,
        metadata: Optional[Dict[str, Any]],
    ) -> str:
        """保存数据"""
        record_id = encrypted_data.cipher_text[:16].hex() if len(encrypted_data.cipher_text) >= 16 else encrypted_data.cipher_text.hex()
        
        if self.config.backend == StorageBackend.MEMORY:
            self._memory_store[record_id] = encrypted_data
            self._metadata[record_id] = {
                "key": key,
                "created_at": time.time(),
                "metadata": metadata or {},
            }
        
        elif self.config.backend == StorageBackend.FILE:
            self._save_to_file(record_id, encrypted_data, metadata)
        
        elif self.config.backend == StorageBackend.ENCRYPTED_FILE:
            self._save_encrypted_file(record_id, encrypted_data, metadata)
        
        return record_id
    
    def _save_to_file(
        self,
        record_id: str,
        encrypted_data: EncryptedData,
        metadata: Optional[Dict[str, Any]],
    ) -> None:
        """保存到文件"""
        # 保存加密数据
        data_path = os.path.join(
            self.config.base_path,
            f"{record_id}{self.config.file_extension}",
        )
        with open(data_path, "wb") as f:
            f.write(encrypted_data.cipher_text)
        
        # 保存元数据
        meta_path = os.path.join(
            self.config.base_path,
            f"{record_id}.meta.json",
        )
        with open(meta_path, "w") as f:
            json.dump({
                "record_id": record_id,
                "encryption_type": encrypted_data.encryption_type.value,
                "metadata": metadata or {},
            }, f)
    
    def _save_encrypted_file(
        self,
        record_id: str,
        encrypted_data: EncryptedData,
        metadata: Optional[Dict[str, Any]],
    ) -> None:
        """保存加密文件"""
        file_path = os.path.join(
            self.config.base_path,
            f"{record_id}{self.config.file_extension}",
        )
        with open(file_path, "w") as f:
            json.dump(encrypted_data.to_dict(), f, indent=2)
    
    def retrieve(
        self,
        key: str,
        default: Any = None,
        decrypt: bool = True,
    ) -> Any:
        """
        获取数据
        
        Args:
            key: 存储键
            default: 默认值
            decrypt: 是否解密
            
        Returns:
            存储的值
        """
        with self._lock:
            record_id = self._keys_index.get(key)
            if record_id is None:
                return default
            
            encrypted_data = self._load(record_id)
            if encrypted_data is None:
                return default
            
            # 解密
            if decrypt and self.config.backend != StorageBackend.MEMORY:
                try:
                    data_bytes = self.encryption_manager.decrypt(encrypted_data)
                except Exception:
                    return default
            else:
                data_bytes = encrypted_data.cipher_text
            
            # 反序列化
            try:
                # 尝试 JSON
                return json.loads(data_bytes.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return data_bytes.decode("utf-8", errors="replace")
    
    def _load(self, record_id: str) -> Optional[EncryptedData]:
        """加载数据"""
        if self.config.backend == StorageBackend.MEMORY:
            return self._memory_store.get(record_id)
        
        elif self.config.backend == StorageBackend.FILE:
            return self._load_from_file(record_id)
        
        elif self.config.backend == StorageBackend.ENCRYPTED_FILE:
            return self._load_encrypted_file(record_id)
        
        return None
    
    def _load_from_file(self, record_id: str) -> Optional[EncryptedData]:
        """从文件加载"""
        data_path = os.path.join(
            self.config.base_path,
            f"{record_id}{self.config.file_extension}",
        )
        
        if not os.path.exists(data_path):
            return None
        
        with open(data_path, "rb") as f:
            cipher_text = f.read()
        
        # 读取元数据获取加密类型
        meta_path = os.path.join(
            self.config.base_path,
            f"{record_id}.meta.json",
        )
        enc_type = self.config.encryption_type
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                meta = json.load(f)
                enc_type = EncryptionType(meta.get("encryption_type", enc_type.value))
        
        return EncryptedData(
            cipher_text=cipher_text,
            encryption_type=enc_type,
        )
    
    def _load_encrypted_file(self, record_id: str) -> Optional[EncryptedData]:
        """加载加密文件"""
        file_path = os.path.join(
            self.config.base_path,
            f"{record_id}{self.config.file_extension}",
        )
        
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, "r") as f:
            return EncryptedData.from_dict(json.load(f))
    
    def delete(self, key: str) -> bool:
        """
        删除数据
        
        Args:
            key: 存储键
            
        Returns:
            是否成功
        """
        with self._lock:
            record_id = self._keys_index.pop(key, None)
            if record_id is None:
                return False
            
            if self.config.backend == StorageBackend.MEMORY:
                self._memory_store.pop(record_id, None)
                self._metadata.pop(record_id, None)
            
            elif self.config.backend in [
                StorageBackend.FILE,
                StorageBackend.ENCRYPTED_FILE,
            ]:
                self._delete_file(record_id)
            
            return True
    
    def _delete_file(self, record_id: str) -> None:
        """删除文件"""
        for ext in [self.config.file_extension, ".meta.json"]:
            path = os.path.join(self.config.base_path, f"{record_id}{ext}")
            if os.path.exists(path):
                os.remove(path)
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return key in self._keys_index
    
    def list_keys(self) -> List[str]:
        """列出所有键"""
        return list(self._keys_index.keys())
    
    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """获取元数据"""
        record_id = self._keys_index.get(key)
        if record_id is None:
            return None
        
        if self.config.backend == StorageBackend.MEMORY:
            return self._metadata.get(record_id, {}).get("metadata")
        
        # 从文件加载
        meta_path = os.path.join(
            self.config.base_path,
            f"{record_id}.meta.json",
        )
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                meta = json.load(f)
                return meta.get("metadata")
        
        return None
    
    def update_metadata(self, key: str, metadata: Dict[str, Any]) -> bool:
        """更新元数据"""
        with self._lock:
            record_id = self._keys_index.get(key)
            if record_id is None:
                return False
            
            if self.config.backend == StorageBackend.MEMORY:
                if record_id in self._metadata:
                    self._metadata[record_id]["metadata"].update(metadata)
            else:
                meta_path = os.path.join(
                    self.config.base_path,
                    f"{record_id}.meta.json",
                )
                if os.path.exists(meta_path):
                    with open(meta_path, "r") as f:
                        meta = json.load(f)
                    meta["metadata"].update(metadata)
                    with open(meta_path, "w") as f:
                        json.dump(meta, f)
            
            return True
    
    def batch_store(
        self,
        items: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        批量存储
        
        Args:
            items: 要存储的键值对
            metadata: 默认元数据
            
        Returns:
            存储记录 ID 列表
        """
        return [self.store(k, v, metadata) for k, v in items.items()]
    
    def batch_retrieve(
        self,
        keys: List[str],
        default: Any = None,
    ) -> Dict[str, Any]:
        """
        批量获取
        
        Args:
            keys: 键列表
            default: 默认值
            
        Returns:
            键值对字典
        """
        return {k: self.retrieve(k, default) for k in keys}
    
    def batch_delete(self, keys: List[str]) -> int:
        """
        批量删除
        
        Args:
            keys: 键列表
            
        Returns:
            删除数量
        """
        return sum(1 for k in keys if self.delete(k))
    
    def on_pre_store(self, callback: Callable[[str, Any], Any]) -> None:
        """注册存储前回调"""
        self._pre_store_callbacks.append(callback)
    
    def on_post_store(self, callback: Callable[[str, EncryptedData], None]) -> None:
        """注册存储后回调"""
        self._post_store_callbacks.append(callback)
    
    def clear(self) -> None:
        """清空存储"""
        with self._lock:
            if self.config.backend == StorageBackend.MEMORY:
                self._memory_store.clear()
                self._metadata.clear()
            
            elif self.config.backend in [
                StorageBackend.FILE,
                StorageBackend.ENCRYPTED_FILE,
            ]:
                import shutil
                for filename in os.listdir(self.config.base_path):
                    path = os.path.join(self.config.base_path, filename)
                    if os.path.isfile(path):
                        os.remove(path)
            
            self._keys_index.clear()
    
    def get_size(self) -> int:
        """获取存储大小"""
        with self._lock:
            if self.config.backend == StorageBackend.MEMORY:
                return len(self._memory_store)
            
            elif self.config.backend in [
                StorageBackend.FILE,
                StorageBackend.ENCRYPTED_FILE,
            ]:
                return len([
                    f for f in os.listdir(self.config.base_path)
                    if os.path.isfile(os.path.join(self.config.base_path, f))
                ])
            
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "backend": self.config.backend.value,
                "total_items": len(self._keys_index),
                "encryption_type": self.config.encryption_type.value,
                "size": self.get_size(),
            }
    
    def __len__(self) -> int:
        return len(self._keys_index)
    
    def __contains__(self, key: str) -> bool:
        return key in self._keys_index
    
    def __getitem__(self, key: str) -> Any:
        value = self.retrieve(key)
        if value is None:
            raise KeyError(key)
        return value
    
    def __setitem__(self, key: str, value: Any) -> None:
        self.store(key, value)
    
    def __delitem__(self, key: str) -> None:
        if not self.delete(key):
            raise KeyError(key)
    
    def __iter__(self) -> Iterator[str]:
        return iter(self._keys_index)


class VaultBackend:
    """
    Vault 后端 (模拟)
    
    提供与 HashiCorp Vault 类似接口的模拟实现
    """
    
    def __init__(self, address: str = "http://localhost:8200", token: Optional[str] = None):
        """
        初始化 Vault 后端
        
        Args:
            address: Vault 地址
            token: 访问令牌
        """
        self.address = address
        self.token = token
        self._storage: Dict[str, Dict[str, Any]] = {}
        self._policies: Dict[str, List[str]] = {}
    
    def write(self, path: str, data: Dict[str, Any]) -> bool:
        """写入数据"""
        self._storage[path] = {
            "data": data,
            "metadata": {
                "created_time": time.time(),
            },
        }
        return True
    
    def read(self, path: str) -> Optional[Dict[str, Any]]:
        """读取数据"""
        return self._storage.get(path)
    
    def delete(self, path: str) -> bool:
        """删除数据"""
        return self._storage.pop(path, None) is not None
    
    def list(self, path: str) -> List[str]:
        """列出路径下的键"""
        prefix = path.rstrip("/") + "/"
        return [
            k[len(prefix):].split("/")[0]
            for k in self._storage.keys()
            if k.startswith(prefix)
        ]
    
    def enable_secrets_engine(self, engine_type: str, path: str) -> bool:
        """启用 secrets 引擎"""
        return True
    
    def create_policy(self, name: str, policy: List[str]) -> bool:
        """创建策略"""
        self._policies[name] = policy
        return True
    
    def enable_auth_method(self, method_type: str) -> bool:
        """启用认证方法"""
        return True


# 全局存储实例
_default_storage: Optional[SecureStorage] = None
_storage_lock = threading.Lock()


def get_default_storage() -> SecureStorage:
    """获取默认安全存储"""
    global _default_storage
    with _storage_lock:
        if _default_storage is None:
            _default_storage = SecureStorage()
        return _default_storage


def set_default_storage(storage: SecureStorage) -> None:
    """设置默认安全存储"""
    global _default_storage
    with _storage_lock:
        _default_storage = storage
