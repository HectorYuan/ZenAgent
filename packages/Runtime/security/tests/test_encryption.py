"""
encryption.py 完整单元测试

覆盖 EncryptedData、AESEncryptor、RSAEncryptor、HybridEncryptor、
EncryptionManager 以及工具函数的全部核心 API。
"""

import base64
import json
import os

import pytest

from packages.Runtime.security.encryption import (
    CRYPTO_AVAILABLE,
    AESEncryptor,
    EncryptedData,
    EncryptionManager,
    EncryptionType,
    HybridEncryptor,
    RSAEncryptor,
    generate_key_fingerprint,
    generate_random_key,
    hash_data,
)

# cryptography 不可用时跳过需要它的测试
requires_crypto = pytest.mark.skipif(
    not CRYPTO_AVAILABLE,
    reason="cryptography library not installed",
)


# ──────────────────────────────────────────────
# EncryptedData 测试
# ──────────────────────────────────────────────
class TestEncryptedData:
    """EncryptedData 数据容器测试"""

    def test_to_dict_and_from_dict_roundtrip(self):
        """to_dict 与 from_dict 序列化往返一致"""
        original = EncryptedData(
            cipher_text=b"secret",
            encryption_type=EncryptionType.AES_256_GCM,
            iv=b"iv_value1234",
            tag=b"tag_value1234",
            key_id="key-1",
            encrypted_key=b"ek_data",
            salt=b"salt_val",
            iterations=200000,
            version=2,
        )
        d = original.to_dict()

        # 字典中的 bytes 字段应为 base64 字符串
        assert isinstance(d["cipher_text"], str)
        assert isinstance(d["iv"], str)
        assert isinstance(d["tag"], str)
        assert d["encryption_type"] == "AES-256-GCM"

        restored = EncryptedData.from_dict(d)
        assert restored.cipher_text == original.cipher_text
        assert restored.encryption_type == original.encryption_type
        assert restored.iv == original.iv
        assert restored.tag == original.tag
        assert restored.key_id == original.key_id
        assert restored.encrypted_key == original.encrypted_key
        assert restored.salt == original.salt
        assert restored.iterations == original.iterations
        assert restored.version == original.version

    def test_to_dict_optional_fields_none(self):
        """可选字段为 None 时序列化后仍为 None"""
        ed = EncryptedData(
            cipher_text=b"data",
            encryption_type=EncryptionType.RSA_2048,
        )
        d = ed.to_dict()
        assert d["iv"] is None
        assert d["tag"] is None
        assert d["key_id"] is None
        assert d["encrypted_key"] is None
        assert d["salt"] is None

    def test_from_dict_minimal(self):
        """from_dict 最小字段集构造"""
        d = {
            "cipher_text": base64.b64encode(b"hello").decode(),
            "encryption_type": "RSA-2048",
        }
        ed = EncryptedData.from_dict(d)
        assert ed.cipher_text == b"hello"
        assert ed.iv is None
        assert ed.iterations == 100000  # 默认值
        assert ed.version == 1

    def test_is_valid_aes_needs_iv(self):
        """AES 类型无 iv 时 is_valid 为 False"""
        for et in [
            EncryptionType.AES_128_GCM,
            EncryptionType.AES_192_GCM,
            EncryptionType.AES_256_GCM,
            EncryptionType.AES_128_CBC,
            EncryptionType.AES_256_CBC,
        ]:
            ed = EncryptedData(cipher_text=b"x", encryption_type=et)
            assert ed.is_valid is False, f"{et.value} 缺少 IV 应无效"

    def test_is_valid_aes_with_iv(self):
        """AES 类型有 iv 时 is_valid 为 True"""
        ed = EncryptedData(
            cipher_text=b"x",
            encryption_type=EncryptionType.AES_256_GCM,
            iv=b"123456789012",
        )
        assert ed.is_valid is True

    def test_is_valid_empty_cipher_text(self):
        """cipher_text 为空时 is_valid 为 False"""
        ed = EncryptedData(
            cipher_text=b"",
            encryption_type=EncryptionType.RSA_2048,
        )
        assert ed.is_valid is False

    def test_is_valid_rsa_no_iv_needed(self):
        """RSA 类型不需要 iv 即可有效"""
        ed = EncryptedData(
            cipher_text=b"data",
            encryption_type=EncryptionType.RSA_2048,
        )
        assert ed.is_valid is True

    def test_to_base64_and_from_base64_roundtrip(self):
        """to_base64 与 from_base64 序列化往返一致"""
        original = EncryptedData(
            cipher_text=b"payload",
            encryption_type=EncryptionType.AES_256_GCM,
            iv=b"my_iv_12_bytes",
            tag=b"my_tag_16bytes",
        )
        b64 = original.to_base64()
        assert isinstance(b64, str)

        restored = EncryptedData.from_base64(b64)
        assert restored.cipher_text == original.cipher_text
        assert restored.encryption_type == original.encryption_type
        assert restored.iv == original.iv
        assert restored.tag == original.tag


# ──────────────────────────────────────────────
# AESEncryptor 测试
# ──────────────────────────────────────────────
@requires_crypto
class TestAESEncryptor:
    """AESEncryptor 加解密测试"""

    def test_gcm_256_encrypt_decrypt(self):
        """AES-256-GCM 加密后解密恢复原文"""
        key = generate_random_key(32)
        enc = AESEncryptor(key, EncryptionType.AES_256_GCM)
        plain = b"Hello, AES-GCM!"
        encrypted = enc.encrypt(plain)

        assert encrypted.encryption_type == EncryptionType.AES_256_GCM
        assert encrypted.iv is not None
        assert encrypted.tag is not None
        assert encrypted.cipher_text != plain

        decrypted = enc.decrypt(encrypted)
        assert decrypted == plain

    def test_gcm_128_encrypt_decrypt(self):
        """AES-128-GCM 加密解密"""
        key = generate_random_key(16)
        enc = AESEncryptor(key, EncryptionType.AES_128_GCM)
        plain = b"AES-128 test"
        encrypted = enc.encrypt(plain)
        assert enc.decrypt(encrypted) == plain

    def test_gcm_192_encrypt_decrypt(self):
        """AES-192-GCM 加密解密"""
        key = generate_random_key(24)
        enc = AESEncryptor(key, EncryptionType.AES_192_GCM)
        plain = b"AES-192 test"
        encrypted = enc.encrypt(plain)
        assert enc.decrypt(encrypted) == plain

    def test_cbc_128_encrypt_decrypt(self):
        """AES-128-CBC 加密解密"""
        key = generate_random_key(16)
        enc = AESEncryptor(key, EncryptionType.AES_128_CBC)
        plain = b"AES-128-CBC test data"
        encrypted = enc.encrypt(plain)

        assert encrypted.encryption_type == EncryptionType.AES_128_CBC
        assert encrypted.iv is not None
        assert encrypted.tag is None  # CBC 无 tag

        decrypted = enc.decrypt(encrypted)
        assert decrypted == plain

    def test_cbc_256_encrypt_decrypt(self):
        """AES-256-CBC 加密解密"""
        key = generate_random_key(32)
        enc = AESEncryptor(key, EncryptionType.AES_256_CBC)
        plain = b"AES-256-CBC test data"
        encrypted = enc.encrypt(plain)
        assert enc.decrypt(encrypted) == plain

    def test_wrong_key_size_raises(self):
        """密钥长度不匹配时抛出 ValueError"""
        short_key = os.urandom(8)
        with pytest.raises(ValueError, match="Key size must be"):
            AESEncryptor(short_key, EncryptionType.AES_256_GCM)

    def test_wrong_key_cannot_decrypt_gcm(self):
        """使用错误密钥解密 GCM 应抛出 ValueError"""
        key1 = generate_random_key(32)
        key2 = generate_random_key(32)
        enc1 = AESEncryptor(key1, EncryptionType.AES_256_GCM)
        enc2 = AESEncryptor(key2, EncryptionType.AES_256_GCM)

        encrypted = enc1.encrypt(b"secret")
        with pytest.raises(ValueError, match="authentication tag mismatch"):
            enc2.decrypt(encrypted)

    def test_decrypt_without_iv_raises(self):
        """解密时 EncryptedData 缺少 IV 抛出 ValueError"""
        key = generate_random_key(32)
        enc = AESEncryptor(key, EncryptionType.AES_256_GCM)
        bad_data = EncryptedData(
            cipher_text=b"x",
            encryption_type=EncryptionType.AES_256_GCM,
        )
        with pytest.raises(ValueError, match="IV is required"):
            enc.decrypt(bad_data)

    def test_gcm_decrypt_without_tag_raises(self):
        """GCM 解密缺少 tag 时抛出 ValueError"""
        key = generate_random_key(32)
        enc = AESEncryptor(key, EncryptionType.AES_256_GCM)
        bad_data = EncryptedData(
            cipher_text=b"x",
            encryption_type=EncryptionType.AES_256_GCM,
            iv=b"123456789012",
        )
        with pytest.raises(ValueError, match="Tag is required"):
            enc.decrypt(bad_data)

    def test_cbc_padding_handles_various_lengths(self):
        """CBC 模式正确处理不同长度的明文"""
        key = generate_random_key(32)
        enc = AESEncryptor(key, EncryptionType.AES_256_CBC)
        for size in [0, 1, 15, 16, 17, 1024]:
            plain = os.urandom(max(size, 1))  # 空 bytes 也测试
            if size == 0:
                plain = b""
            encrypted = enc.encrypt(plain)
            assert enc.decrypt(encrypted) == plain

    def test_gcm_empty_plaintext(self):
        """GCM 模式加密空明文"""
        key = generate_random_key(32)
        enc = AESEncryptor(key, EncryptionType.AES_256_GCM)
        encrypted = enc.encrypt(b"")
        assert enc.decrypt(encrypted) == b""


# ──────────────────────────────────────────────
# RSAEncryptor 测试
# ──────────────────────────────────────────────
@requires_crypto
class TestRSAEncryptor:
    """RSAEncryptor 加解密与签名测试"""

    def test_generate_key_pair_2048(self):
        """RSA-2048 密钥对生成"""
        enc, priv, pub = RSAEncryptor.generate_key_pair(EncryptionType.RSA_2048)
        assert enc.private_key is not None
        assert enc.public_key is not None
        assert priv.key_size == 2048

    def test_generate_key_pair_4096(self):
        """RSA-4096 密钥对生成"""
        enc, priv, pub = RSAEncryptor.generate_key_pair(EncryptionType.RSA_4096)
        assert priv.key_size == 4096

    def test_encrypt_decrypt_roundtrip(self):
        """RSA 加密后解密恢复原文"""
        enc, _, _ = RSAEncryptor.generate_key_pair()
        plain = b"RSA encryption test"
        encrypted = enc.encrypt(plain)

        assert encrypted.encryption_type == EncryptionType.RSA_2048
        assert encrypted.cipher_text != plain
        assert encrypted.iv is None  # RSA 不需要 IV

        decrypted = enc.decrypt(encrypted)
        assert decrypted == plain

    def test_sign_and_verify(self):
        """RSA 签名和验证"""
        enc, _, _ = RSAEncryptor.generate_key_pair()
        data = b"data to sign"
        signature = enc.sign(data)

        assert isinstance(signature, bytes)
        assert len(signature) > 0
        assert enc.verify(data, signature) is True

    def test_verify_tampered_data_fails(self):
        """篡改数据后验证签名应失败"""
        enc, _, _ = RSAEncryptor.generate_key_pair()
        data = b"original data"
        signature = enc.sign(data)
        assert enc.verify(b"tampered data", signature) is False

    def test_verify_tampered_signature_fails(self):
        """篡改签名后验证应失败"""
        enc, _, _ = RSAEncryptor.generate_key_pair()
        data = b"some data"
        signature = enc.sign(data)
        bad_sig = bytearray(signature)
        bad_sig[0] ^= 0xFF
        assert enc.verify(data, bytes(bad_sig)) is False

    def test_encrypt_without_public_key_raises(self):
        """无公钥时加密应抛出 ValueError"""
        enc = RSAEncryptor(private_key=None, public_key=None)
        with pytest.raises(ValueError, match="Public key is required"):
            enc.encrypt(b"data")

    def test_decrypt_without_private_key_raises(self):
        """无私钥时解密应抛出 ValueError"""
        _, _, pub = RSAEncryptor.generate_key_pair()
        enc = RSAEncryptor(private_key=None, public_key=pub)
        fake_data = EncryptedData(
            cipher_text=b"x",
            encryption_type=EncryptionType.RSA_2048,
        )
        with pytest.raises(ValueError, match="Private key is required"):
            enc.decrypt(fake_data)

    def test_sign_without_private_key_raises(self):
        """无私钥时签名应抛出 ValueError"""
        _, _, pub = RSAEncryptor.generate_key_pair()
        enc = RSAEncryptor(private_key=None, public_key=pub)
        with pytest.raises(ValueError, match="Private key is required"):
            enc.sign(b"data")

    def test_verify_without_public_key_raises(self):
        """无公钥时验证应抛出 ValueError"""
        priv_key_obj = RSAEncryptor.generate_key_pair()[1]
        from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
        enc = RSAEncryptor(private_key=priv_key_obj, public_key=None)
        with pytest.raises(ValueError, match="Public key is required"):
            enc.verify(b"data", b"sig")

    def test_pem_roundtrip(self):
        """PEM 导出再导入保持密钥一致"""
        enc1, _, _ = RSAEncryptor.generate_key_pair()
        pub_pem = enc1.get_public_key_pem()
        priv_pem = enc1.get_private_key_pem()

        enc2 = RSAEncryptor.from_pem(public_pem=pub_pem, private_pem=priv_pem)

        # 用 enc1 加密，enc2 解密
        plain = b"PEM roundtrip test"
        encrypted = enc1.encrypt(plain)
        assert enc2.decrypt(encrypted) == plain

    def test_private_key_pem_with_password(self):
        """带密码的私钥 PEM 导出"""
        enc, _, _ = RSAEncryptor.generate_key_pair()
        password = b"test_pass"
        priv_pem = enc.get_private_key_pem(password=password)
        assert b"ENCRYPTED" in priv_pem

        # 用密码导入
        enc2 = RSAEncryptor.from_pem(private_pem=priv_pem, password=password)
        assert enc2.private_key is not None

    def test_public_key_only_encryptor(self):
        """仅公钥的加密器可以加密"""
        _, _, pub = RSAEncryptor.generate_key_pair()
        enc = RSAEncryptor(public_key=pub)
        encrypted = enc.encrypt(b"test")
        assert encrypted.cipher_text


# ──────────────────────────────────────────────
# HybridEncryptor 测试
# ──────────────────────────────────────────────
@requires_crypto
class TestHybridEncryptor:
    """HybridEncryptor 混合加密测试"""

    def test_generate_returns_components(self):
        """generate 返回加密器和 PEM 密钥"""
        enc, priv_pem, pub_pem = HybridEncryptor.generate()
        assert isinstance(enc, HybridEncryptor)
        assert b"PRIVATE KEY" in priv_pem
        assert b"PUBLIC KEY" in pub_pem

    def test_encrypt_decrypt_roundtrip(self):
        """混合加密后解密恢复原文"""
        enc, _, _ = HybridEncryptor.generate()
        plain = b"Hybrid encryption payload"
        encrypted = enc.encrypt(plain)

        assert encrypted.encryption_type == EncryptionType.HYBRID
        assert encrypted.iv is not None
        assert encrypted.encrypted_key is not None
        assert encrypted.cipher_text != plain

        decrypted = enc.decrypt(encrypted)
        assert decrypted == plain

    def test_encrypt_large_data(self):
        """混合加密大体积数据"""
        enc, _, _ = HybridEncryptor.generate()
        plain = os.urandom(100_000)  # 100KB
        encrypted = enc.encrypt(plain)
        assert enc.decrypt(encrypted) == plain

    def test_custom_aes_type(self):
        """使用自定义 AES 类型"""
        rsa_enc, priv, pub = RSAEncryptor.generate_key_pair()
        hybrid = HybridEncryptor(
            rsa_public_key=pub,
            rsa_private_key=priv,
            aes_type=EncryptionType.AES_128_GCM,
        )
        plain = b"custom AES type"
        encrypted = hybrid.encrypt(plain)
        assert hybrid.decrypt(encrypted) == plain

    def test_decrypt_without_private_key_raises(self):
        """无私钥时混合解密应抛出 ValueError"""
        rsa_enc, priv, pub = RSAEncryptor.generate_key_pair()
        hybrid = HybridEncryptor(rsa_public_key=pub, rsa_private_key=None)
        # 加密可以（用公钥），但解密不行
        encrypted = hybrid.encrypt(b"data")
        with pytest.raises(ValueError, match="RSA private key is required"):
            hybrid.decrypt(encrypted)


# ──────────────────────────────────────────────
# EncryptionManager 测试
# ──────────────────────────────────────────────
@requires_crypto
class TestEncryptionManager:
    """EncryptionManager 统一接口测试"""

    def test_aes_encrypt_decrypt(self):
        """通过 Manager 进行 AES 加解密"""
        mgr = EncryptionManager(EncryptionType.AES_256_GCM)
        key = generate_random_key(32)
        mgr.set_aes_key(key, EncryptionType.AES_256_GCM)

        plain = b"manager test"
        encrypted = mgr.encrypt(plain)
        assert mgr.decrypt(encrypted) == plain

    def test_encrypt_decrypt_string(self):
        """字符串加解密"""
        mgr = EncryptionManager(EncryptionType.AES_256_GCM)
        key = generate_random_key(32)
        mgr.set_aes_key(key, EncryptionType.AES_256_GCM)

        text = "你好，世界！Hello 🌍"
        encrypted_str = mgr.encrypt_string(text)
        assert isinstance(encrypted_str, str)
        assert mgr.decrypt_string(encrypted_str) == text

    def test_default_type_used(self):
        """未指定类型时使用默认类型"""
        mgr = EncryptionManager(EncryptionType.AES_128_CBC)
        key = generate_random_key(16)
        mgr.set_aes_key(key, EncryptionType.AES_128_CBC)

        encrypted = mgr.encrypt(b"test")
        assert encrypted.encryption_type == EncryptionType.AES_128_CBC

    def test_unconfigured_type_raises(self):
        """未配置的加密类型抛出 ValueError"""
        mgr = EncryptionManager()
        with pytest.raises(ValueError, match="No encryptor configured"):
            mgr.encrypt(b"data", EncryptionType.AES_256_CBC)

    def test_set_rsa_keys(self):
        """设置 RSA 密钥并通过 Manager 加解密"""
        rsa_enc, priv, pub = RSAEncryptor.generate_key_pair()
        mgr = EncryptionManager(EncryptionType.RSA_2048)
        mgr.set_rsa_keys(priv, pub, EncryptionType.RSA_2048)

        encrypted = mgr.encrypt(b"RSA via manager")
        assert mgr.decrypt(encrypted) == b"RSA via manager"

    def test_set_hybrid_encryptor(self):
        """设置混合加密器并通过 Manager 加解密"""
        hybrid, _, _ = HybridEncryptor.generate()
        mgr = EncryptionManager(EncryptionType.HYBRID)
        mgr.set_hybrid_encryptor(hybrid)

        encrypted = mgr.encrypt(b"hybrid via manager")
        assert mgr.decrypt(encrypted) == b"hybrid via manager"

    def test_derive_key(self):
        """密钥派生"""
        mgr = EncryptionManager()
        key1, salt1 = mgr.derive_key("password123")
        assert len(key1) == 32
        assert len(salt1) == 16

        # 相同密码 + 相同盐 → 相同密钥
        key2, _ = mgr.derive_key("password123", salt=salt1)
        assert key1 == key2

        # 不同密码 → 不同密钥
        key3, _ = mgr.derive_key("other_password", salt=salt1)
        assert key1 != key3

    def test_derive_key_custom_params(self):
        """自定义密钥派生参数"""
        mgr = EncryptionManager()
        salt = os.urandom(16)
        key, returned_salt = mgr.derive_key(
            "pass", salt=salt, iterations=50000, key_length=16,
        )
        assert len(key) == 16
        assert returned_salt == salt


# ──────────────────────────────────────────────
# 工具函数测试
# ──────────────────────────────────────────────
class TestUtilityFunctions:
    """generate_random_key / hash_data / generate_key_fingerprint 测试"""

    def test_generate_random_key_default(self):
        """默认生成 32 字节随机密钥"""
        key = generate_random_key()
        assert len(key) == 32
        assert isinstance(key, bytes)

    def test_generate_random_key_custom_size(self):
        """自定义密钥长度"""
        for size in [16, 24, 32, 48, 64]:
            key = generate_random_key(size)
            assert len(key) == size

    def test_generate_random_key_uniqueness(self):
        """多次生成的密钥不相同"""
        keys = {generate_random_key() for _ in range(10)}
        assert len(keys) == 10

    def test_hash_data_sha256(self):
        """SHA-256 哈希"""
        h = hash_data(b"hello")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 = 32 bytes = 64 hex chars
        # 确定性
        assert hash_data(b"hello") == h

    def test_hash_data_sha384(self):
        """SHA-384 哈希"""
        h = hash_data(b"hello", algorithm="sha384")
        assert len(h) == 96

    def test_hash_data_sha512(self):
        """SHA-512 哈希"""
        h = hash_data(b"hello", algorithm="sha512")
        assert len(h) == 128

    def test_hash_data_different_inputs(self):
        """不同输入产生不同哈希"""
        h1 = hash_data(b"hello")
        h2 = hash_data(b"world")
        assert h1 != h2

    def test_generate_key_fingerprint(self):
        """密钥指纹为 16 字符十六进制"""
        key = generate_random_key(32)
        fp = generate_key_fingerprint(key)
        assert isinstance(fp, str)
        assert len(fp) == 16
        # 确定性
        assert generate_key_fingerprint(key) == fp

    def test_generate_key_fingerprint_different_keys(self):
        """不同密钥产生不同指纹"""
        fp1 = generate_key_fingerprint(generate_random_key())
        fp2 = generate_key_fingerprint(generate_random_key())
        assert fp1 != fp2
