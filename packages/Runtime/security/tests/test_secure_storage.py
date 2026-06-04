"""
secure_storage 单元测试

覆盖 SecureStorage MEMORY 模式、批量操作、语法糖、VaultBackend
"""

import pytest
import time

from packages.Runtime.security.secure_storage import (
    SecureStorage,
    StorageBackend,
    StorageConfig,
    VaultBackend,
)
from packages.Runtime.security.encryption import (
    EncryptionManager,
    EncryptionType,
    EncryptedData,
)


# ---------------------------------------------------------------------------
# SecureStorage — MEMORY 模式
# ---------------------------------------------------------------------------

class TestSecureStorageMemory:
    """MEMORY 模式下的基本 CRUD 操作"""

    def setup_method(self):
        """每个测试前创建 MEMORY 模式的 SecureStorage"""
        config = StorageConfig(backend=StorageBackend.MEMORY)
        self.storage = SecureStorage(config=config)

    def teardown_method(self):
        """每个测试后清空存储"""
        self.storage.clear()

    # 1. store + retrieve 基本存取
    def test_store_and_retrieve(self):
        """存储字符串后能正确取回"""
        self.storage.store("greeting", "hello world")
        assert self.storage.retrieve("greeting") == "hello world"

    # 2. store dict (JSON 序列化)
    def test_store_retrieve_dict(self):
        """存储 dict 后取回内容一致"""
        data = {"name": "zen", "level": 5}
        self.storage.store("config", data)
        assert self.storage.retrieve("config") == data

    # 3. retrieve 不存在的键返回 default
    def test_retrieve_default(self):
        """取回不存在的键时返回默认值"""
        assert self.storage.retrieve("missing") is None
        assert self.storage.retrieve("missing", default="fallback") == "fallback"

    # 4. delete
    def test_delete_existing(self):
        """删除已存在的键返回 True，之后不存在"""
        self.storage.store("temp", 42)
        assert self.storage.delete("temp") is True
        assert self.storage.retrieve("temp") is None

    def test_delete_nonexistent(self):
        """删除不存在的键返回 False"""
        assert self.storage.delete("ghost") is False

    # 5. exists
    def test_exists(self):
        """exists 对已存储 / 未存储的键返回正确布尔值"""
        self.storage.store("a", 1)
        assert self.storage.exists("a") is True
        assert self.storage.exists("b") is False

    # 6. list_keys
    def test_list_keys(self):
        """list_keys 返回所有已存储的键"""
        self.storage.store("x", 1)
        self.storage.store("y", 2)
        self.storage.store("z", 3)
        keys = self.storage.list_keys()
        assert set(keys) == {"x", "y", "z"}

    # 7. get_metadata
    def test_get_metadata(self):
        """存储时附带的元数据可通过 get_metadata 取回"""
        meta = {"source": "test", "priority": 1}
        self.storage.store("doc", "content", metadata=meta)
        assert self.storage.get_metadata("doc") == meta

    def test_get_metadata_nonexistent(self):
        """取回不存在键的元数据返回 None"""
        assert self.storage.get_metadata("nope") is None

    # 8. clear
    def test_clear(self):
        """clear 清空所有数据和索引"""
        self.storage.store("a", 1)
        self.storage.store("b", 2)
        self.storage.clear()
        assert len(self.storage) == 0
        assert self.storage.list_keys() == []
        assert self.storage.retrieve("a") is None

    # 9. get_size
    def test_get_size(self):
        """get_size 返回存储条目数"""
        assert self.storage.get_size() == 0
        self.storage.store("a", 1)
        self.storage.store("b", 2)
        assert self.storage.get_size() == 2

    # 10. store bytes
    def test_store_retrieve_bytes(self):
        """存储 bytes 类型数据后取回正确字符串"""
        raw = b"\x00\x01\x02binary"
        self.storage.store("raw", raw)
        # bytes 无法 JSON 解码，会走 decode replace 分支
        result = self.storage.retrieve("raw")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# SecureStorage — 批量操作
# ---------------------------------------------------------------------------

class TestBatchOperations:
    """批量存储、取回、删除"""

    def setup_method(self):
        config = StorageConfig(backend=StorageBackend.MEMORY)
        self.storage = SecureStorage(config=config)

    def teardown_method(self):
        self.storage.clear()

    # 11. batch_store + batch_retrieve
    def test_batch_store_and_retrieve(self):
        """批量存储后批量取回，内容一致"""
        items = {"k1": "v1", "k2": {"a": 1}, "k3": [1, 2, 3]}
        ids = self.storage.batch_store(items)
        assert len(ids) == 3

        result = self.storage.batch_retrieve(["k1", "k2", "k3"])
        assert result["k1"] == "v1"
        assert result["k2"] == {"a": 1}
        assert result["k3"] == [1, 2, 3]

    # 12. batch_retrieve 含不存在键
    def test_batch_retrieve_with_missing(self):
        """批量取回含不存在键时返回默认值"""
        self.storage.store("exists", "yes")
        result = self.storage.batch_retrieve(["exists", "missing"], default="N/A")
        assert result["exists"] == "yes"
        assert result["missing"] == "N/A"

    # 13. batch_delete
    def test_batch_delete(self):
        """批量删除返回成功删除的数量"""
        self.storage.store("a", 1)
        self.storage.store("b", 2)
        self.storage.store("c", 3)
        deleted = self.storage.batch_delete(["a", "b", "ghost"])
        assert deleted == 2
        assert self.storage.exists("a") is False
        assert self.storage.exists("c") is True


# ---------------------------------------------------------------------------
# SecureStorage — __getitem__ / __setitem__ / __delitem__ 语法糖
# ---------------------------------------------------------------------------

class TestItemSyntax:
    """字典风格的 [] 访问语法糖"""

    def setup_method(self):
        config = StorageConfig(backend=StorageBackend.MEMORY)
        self.storage = SecureStorage(config=config)

    def teardown_method(self):
        self.storage.clear()

    # 14. __setitem__ + __getitem__
    def test_setitem_getitem(self):
        """storage[key] = value 存储后 storage[key] 取回"""
        self.storage["answer"] = 42
        assert self.storage["answer"] == 42

    # 15. __getitem__ 不存在的键抛 KeyError
    def test_getitem_key_error(self):
        """取回不存在的键抛出 KeyError"""
        with pytest.raises(KeyError):
            _ = self.storage["nonexistent"]

    # 16. __delitem__
    def test_delitem(self):
        """del storage[key] 删除后取回抛 KeyError"""
        self.storage["temp"] = "gone"
        del self.storage["temp"]
        assert self.storage.exists("temp") is False

    # 17. __delitem__ 不存在的键抛 KeyError
    def test_delitem_key_error(self):
        """删除不存在的键抛出 KeyError"""
        with pytest.raises(KeyError):
            del self.storage["ghost"]

    # __contains__ 和 __len__
    def test_contains_and_len(self):
        """in 运算符和 len() 正常工作"""
        self.storage["a"] = 1
        self.storage["b"] = 2
        assert "a" in self.storage
        assert "c" not in self.storage
        assert len(self.storage) == 2

    # __iter__
    def test_iter(self):
        """迭代存储返回所有键"""
        self.storage["x"] = 1
        self.storage["y"] = 2
        keys = list(self.storage)
        assert set(keys) == {"x", "y"}


# ---------------------------------------------------------------------------
# VaultBackend
# ---------------------------------------------------------------------------

class TestVaultBackend:
    """VaultBackend 模拟 Vault 的 CRUD 和 list 操作"""

    def setup_method(self):
        self.vault = VaultBackend(address="http://localhost:8200", token="test-token")

    # 18. write + read
    def test_write_and_read(self):
        """写入后读取返回含 data 和 metadata 的结构"""
        data = {"secret": "my-secret-value"}
        assert self.vault.write("secret/data/myapp", data) is True

        result = self.vault.read("secret/data/myapp")
        assert result is not None
        assert result["data"] == data
        assert "created_time" in result["metadata"]

    # 19. read 不存在的路径
    def test_read_nonexistent(self):
        """读取不存在的路径返回 None"""
        assert self.vault.read("secret/data/missing") is None

    # 20. delete
    def test_delete_existing(self):
        """删除已存在的路径返回 True"""
        self.vault.write("secret/data/to-delete", {"k": "v"})
        assert self.vault.delete("secret/data/to-delete") is True
        assert self.vault.read("secret/data/to-delete") is None

    def test_delete_nonexistent(self):
        """删除不存在的路径返回 False"""
        assert self.vault.delete("secret/data/ghost") is False

    # 21. list
    def test_list(self):
        """list 返回指定路径下的直接子键"""
        self.vault.write("secret/data/app1/config", {"a": 1})
        self.vault.write("secret/data/app1/creds", {"b": 2})
        self.vault.write("secret/data/app2/config", {"c": 3})

        keys = self.vault.list("secret/data/app1")
        assert set(keys) == {"config", "creds"}

    def test_list_empty(self):
        """list 无匹配路径时返回空列表"""
        assert self.vault.list("secret/data/empty") == []

    # 22. enable_secrets_engine / create_policy / enable_auth_method
    def test_utility_methods(self):
        """辅助方法 enable_secrets_engine / create_policy / enable_auth_method 均返回 True"""
        assert self.vault.enable_secrets_engine("kv", "secret/") is True
        assert self.vault.create_policy("test-policy", ["read", "write"]) is True
        assert self.vault.enable_auth_method("token") is True


# ---------------------------------------------------------------------------
# SecureStorage — callbacks
# ---------------------------------------------------------------------------

class TestCallbacks:
    """存储前后回调机制"""

    def setup_method(self):
        config = StorageConfig(backend=StorageBackend.MEMORY)
        self.storage = SecureStorage(config=config)

    def teardown_method(self):
        self.storage.clear()

    def test_pre_store_callback(self):
        """pre_store 回调可修改待存储的值"""
        self.storage.on_pre_store(lambda k, v: v.upper() if isinstance(v, str) else v)
        self.storage.store("key", "hello")
        assert self.storage.retrieve("key") == "HELLO"

    def test_post_store_callback(self):
        """post_store 回调在存储后被调用"""
        called = {}

        def on_post(key, enc_data):
            called["key"] = key
            called["called"] = True

        self.storage.on_post_store(on_post)
        self.storage.store("test", "value")
        assert called.get("called") is True
        assert called.get("key") == "test"


# ---------------------------------------------------------------------------
# SecureStorage — get_statistics
# ---------------------------------------------------------------------------

class TestStatistics:
    """统计信息"""

    def setup_method(self):
        config = StorageConfig(backend=StorageBackend.MEMORY)
        self.storage = SecureStorage(config=config)

    def teardown_method(self):
        self.storage.clear()

    def test_get_statistics(self):
        """get_statistics 返回正确结构"""
        self.storage.store("a", 1)
        self.storage.store("b", 2)
        stats = self.storage.get_statistics()
        assert stats["backend"] == "memory"
        assert stats["total_items"] == 2
        assert stats["encryption_type"] == EncryptionType.AES_256_GCM.value
        assert stats["size"] == 2


# ---------------------------------------------------------------------------
# SecureStorage — store with encrypt=False (显式)
# ---------------------------------------------------------------------------

class TestStoreEncryptFlag:
    """显式 encrypt 参数对 MEMORY 模式的影响"""

    def setup_method(self):
        config = StorageConfig(backend=StorageBackend.MEMORY)
        self.storage = SecureStorage(config=config)

    def teardown_method(self):
        self.storage.clear()

    def test_store_encrypt_false(self):
        """MEMORY 模式下 encrypt=False 也能正常存取"""
        self.storage.store("plain", "clear-text", encrypt=False)
        assert self.storage.retrieve("plain") == "clear-text"

    def test_store_list_value(self):
        """存储 list 类型后取回一致"""
        data = [1, "two", 3.0]
        self.storage.store("lst", data)
        assert self.storage.retrieve("lst") == data

    def test_store_numeric_value(self):
        """存储数值类型"""
        self.storage.store("num", 12345)
        assert self.storage.retrieve("num") == 12345
