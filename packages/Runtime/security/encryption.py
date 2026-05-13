"""
加密工具模块

提供 AES、RSA 和混合加密实现
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Union
import hashlib
import os
import base64
import json

# 尝试导入 cryptography 库
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding, hashes
    from cryptography.hazmat.primitives.asymmetric import rsa, padding as rsa_padding
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
    from cryptography.hazmat.backends import default_backend
    from cryptography.exceptions import InvalidTag
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    RSAPrivateKey = RSAPublicKey = None


class EncryptionType(Enum):
    """加密类型"""
    AES_128_GCM = "AES-128-GCM"
    AES_192_GCM = "AES-192-GCM"
    AES_256_GCM = "AES-256-GCM"
    AES_128_CBC = "AES-128-CBC"
    AES_256_CBC = "AES-256-CBC"
    RSA_2048 = "RSA-2048"
    RSA_4096 = "RSA-4096"
    HYBRID = "HYBRID"  # RSA + AES


@dataclass
class EncryptedData:
    """
    加密数据容器
    
    存储加密后的数据和元信息
    """
    cipher_text: bytes
    encryption_type: EncryptionType
    
    # AES 相关
    iv: Optional[bytes] = None          # 初始向量
    tag: Optional[bytes] = None         # 认证标签 (GCM)
    
    # RSA 相关
    key_id: Optional[str] = None        # 使用的密钥 ID
    
    # 混合加密相关
    encrypted_key: Optional[bytes] = None  # 用 RSA 加密的 AES 密钥
    
    # 元数据
    salt: Optional[bytes] = None
    iterations: int = 100000            # PBKDF2 迭代次数
    version: int = 1
    
    @property
    def is_valid(self) -> bool:
        """检查数据是否有效"""
        if not self.cipher_text:
            return False
        if self.encryption_type in [
            EncryptionType.AES_128_GCM,
            EncryptionType.AES_192_GCM,
            EncryptionType.AES_256_GCM,
            EncryptionType.AES_128_CBC,
            EncryptionType.AES_256_CBC,
        ]:
            return self.iv is not None
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "cipher_text": base64.b64encode(self.cipher_text).decode(),
            "encryption_type": self.encryption_type.value,
            "iv": base64.b64encode(self.iv).decode() if self.iv else None,
            "tag": base64.b64encode(self.tag).decode() if self.tag else None,
            "key_id": self.key_id,
            "encrypted_key": base64.b64encode(self.encrypted_key).decode() if self.encrypted_key else None,
            "salt": base64.b64encode(self.salt).decode() if self.salt else None,
            "iterations": self.iterations,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EncryptedData":
        """从字典创建"""
        return cls(
            cipher_text=base64.b64decode(data["cipher_text"]),
            encryption_type=EncryptionType(data["encryption_type"]),
            iv=base64.b64decode(data["iv"]) if data.get("iv") else None,
            tag=base64.b64decode(data["tag"]) if data.get("tag") else None,
            key_id=data.get("key_id"),
            encrypted_key=base64.b64decode(data["encrypted_key"]) if data.get("encrypted_key") else None,
            salt=base64.b64decode(data["salt"]) if data.get("salt") else None,
            iterations=data.get("iterations", 100000),
            version=data.get("version", 1),
        )
    
    def to_base64(self) -> str:
        """转换为 Base64 字符串"""
        return base64.b64encode(json.dumps(self.to_dict()).encode()).decode()
    
    @classmethod
    def from_base64(cls, data: str) -> "EncryptedData":
        """从 Base64 字符串创建"""
        return cls.from_dict(json.loads(base64.b64decode(data).decode()))


class AESEncryptor:
    """
    AES 加密器
    
    支持 GCM 和 CBC 模式
    """
    
    # 密钥大小映射
    KEY_SIZES = {
        EncryptionType.AES_128_GCM: 16,
        EncryptionType.AES_192_GCM: 24,
        EncryptionType.AES_256_GCM: 32,
        EncryptionType.AES_128_CBC: 16,
        EncryptionType.AES_256_CBC: 32,
    }
    
    # IV 大小
    IV_SIZE = 12  # GCM 推荐 12 字节
    CBC_IV_SIZE = 16
    
    # Tag 大小 (GCM)
    TAG_SIZE = 16
    
    def __init__(self, key: bytes, encryption_type: EncryptionType):
        """
        初始化 AES 加密器
        
        Args:
            key: 密钥 (16, 24 或 32 字节)
            encryption_type: 加密类型
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library not available")
        
        expected_size = self.KEY_SIZES.get(encryption_type)
        if expected_size and len(key) != expected_size:
            raise ValueError(f"Key size must be {expected_size} bytes for {encryption_type.value}")
        
        self.key = key
        self.encryption_type = encryption_type
        self.is_gcm = "GCM" in encryption_type.value
    
    def encrypt(self, plain_text: bytes) -> EncryptedData:
        """
        加密数据
        
        Args:
            plain_text: 明文数据
            
        Returns:
            加密数据容器
        """
        # 生成 IV
        iv = os.urandom(self.IV_SIZE if self.is_gcm else self.CBC_IV_SIZE)
        
        if self.is_gcm:
            return self._encrypt_gcm(plain_text, iv)
        else:
            return self._encrypt_cbc(plain_text, iv)
    
    def _encrypt_gcm(self, plain_text: bytes, iv: bytes) -> EncryptedData:
        """GCM 模式加密"""
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.GCM(iv),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()
        cipher_text = encryptor.update(plain_text) + encryptor.finalize()
        
        return EncryptedData(
            cipher_text=cipher_text,
            encryption_type=self.encryption_type,
            iv=iv,
            tag=encryptor.tag,
        )
    
    def _encrypt_cbc(self, plain_text: bytes, iv: bytes) -> EncryptedData:
        """CBC 模式加密"""
        # PKCS7 填充
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plain_text) + padder.finalize()
        
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CBC(iv),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()
        cipher_text = encryptor.update(padded_data) + encryptor.finalize()
        
        return EncryptedData(
            cipher_text=cipher_text,
            encryption_type=self.encryption_type,
            iv=iv,
        )
    
    def decrypt(self, encrypted_data: EncryptedData) -> bytes:
        """
        解密数据
        
        Args:
            encrypted_data: 加密数据容器
            
        Returns:
            明文数据
        """
        if encrypted_data.iv is None:
            raise ValueError("IV is required for decryption")
        
        if self.is_gcm:
            return self._decrypt_gcm(encrypted_data)
        else:
            return self._decrypt_cbc(encrypted_data)
    
    def _decrypt_gcm(self, encrypted_data: EncryptedData) -> bytes:
        """GCM 模式解密"""
        if encrypted_data.tag is None:
            raise ValueError("Tag is required for GCM decryption")
        
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.GCM(encrypted_data.iv, encrypted_data.tag),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        
        try:
            return decryptor.update(encrypted_data.cipher_text) + decryptor.finalize()
        except InvalidTag:
            raise ValueError("Decryption failed: authentication tag mismatch")
    
    def _decrypt_cbc(self, encrypted_data: EncryptedData) -> bytes:
        """CBC 模式解密"""
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CBC(encrypted_data.iv),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        
        padded_data = decryptor.update(encrypted_data.cipher_text) + decryptor.finalize()
        
        # 移除 PKCS7 填充
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(padded_data) + unpadder.finalize()


class RSAEncryptor:
    """
    RSA 加密器
    
    支持 OAEP 填充
    """
    
    KEY_SIZES = {
        EncryptionType.RSA_2048: 2048,
        EncryptionType.RSA_4096: 4096,
    }
    
    def __init__(
        self,
        private_key: Optional[RSAPrivateKey] = None,
        public_key: Optional[RSAPublicKey] = None,
        encryption_type: EncryptionType = EncryptionType.RSA_2048,
    ):
        """
        初始化 RSA 加密器
        
        Args:
            private_key: RSA 私钥
            public_key: RSA 公钥
            encryption_type: 加密类型
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library not available")
        
        self.private_key = private_key
        self.public_key = public_key
        self.encryption_type = encryption_type
    
    @classmethod
    def generate_key_pair(
        cls,
        encryption_type: EncryptionType = EncryptionType.RSA_2048,
    ) -> Tuple["RSAEncryptor", RSAPrivateKey, RSAPublicKey]:
        """
        生成 RSA 密钥对
        
        Args:
            encryption_type: 加密类型
            
        Returns:
            (RSAEncryptor, 私钥, 公钥)
        """
        key_size = cls.KEY_SIZES.get(encryption_type, 2048)
        
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend(),
        )
        public_key = private_key.public_key()
        
        encryptor = cls(private_key, public_key, encryption_type)
        return encryptor, private_key, public_key
    
    def get_public_key_pem(self) -> bytes:
        """获取公钥 PEM 格式"""
        from cryptography.hazmat.primitives import serialization
        
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    
    def get_private_key_pem(self, password: Optional[bytes] = None) -> bytes:
        """获取私钥 PEM 格式"""
        from cryptography.hazmat.primitives import serialization
        
        encryption = serialization.BestAvailableEncryption(password) if password else serialization.NoEncryption()
        
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption,
        )
    
    @classmethod
    def from_pem(
        cls,
        public_pem: Optional[bytes] = None,
        private_pem: Optional[bytes] = None,
        password: Optional[bytes] = None,
    ) -> "RSAEncryptor":
        """
        从 PEM 数据创建加密器
        
        Args:
            public_pem: 公钥 PEM 数据
            private_pem: 私钥 PEM 数据
            password: 私钥密码
            
        Returns:
            RSAEncryptor 实例
        """
        from cryptography.hazmat.primitives import serialization
        
        public_key = None
        private_key = None
        
        if public_pem:
            public_key = serialization.load_pem_public_key(
                public_pem,
                backend=default_backend(),
            )
        
        if private_pem:
            private_key = serialization.load_pem_private_key(
                private_pem,
                password=password,
                backend=default_backend(),
            )
        
        return cls(private_key, public_key)
    
    def encrypt(self, plain_text: bytes) -> EncryptedData:
        """
        加密数据 (使用公钥)
        
        Args:
            plain_text: 明文数据
            
        Returns:
            加密数据容器
        """
        if self.public_key is None:
            raise ValueError("Public key is required for encryption")
        
        # OAEP 填充加密
        cipher_text = self.public_key.encrypt(
            plain_text,
            rsa_padding.OAEP(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        
        return EncryptedData(
            cipher_text=cipher_text,
            encryption_type=self.encryption_type,
        )
    
    def decrypt(self, encrypted_data: EncryptedData) -> bytes:
        """
        解密数据 (使用私钥)
        
        Args:
            encrypted_data: 加密数据容器
            
        Returns:
            明文数据
        """
        if self.private_key is None:
            raise ValueError("Private key is required for decryption")
        
        return self.private_key.decrypt(
            encrypted_data.cipher_text,
            rsa_padding.OAEP(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    
    def sign(self, data: bytes) -> bytes:
        """
        签名数据
        
        Args:
            data: 要签名的数据
            
        Returns:
            签名
        """
        if self.private_key is None:
            raise ValueError("Private key is required for signing")
        
        return self.private_key.sign(
            data,
            rsa_padding.PSS(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                salt_length=rsa_padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
    
    def verify(self, data: bytes, signature: bytes) -> bool:
        """
        验证签名
        
        Args:
            data: 原始数据
            signature: 签名
            
        Returns:
            是否验证通过
        """
        if self.public_key is None:
            raise ValueError("Public key is required for verification")
        
        try:
            self.public_key.verify(
                signature,
                data,
                rsa_padding.PSS(
                    mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                    salt_length=rsa_padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except Exception:
            return False


class HybridEncryptor:
    """
    混合加密器
    
    使用 RSA + AES 的混合加密方案:
    1. 生成随机 AES 密钥
    2. 用 AES 加密数据
    3. 用 RSA 公钥加密 AES 密钥
    4. 将加密的密钥和数据一起传输/存储
    """
    
    def __init__(
        self,
        rsa_public_key: RSAPublicKey,
        rsa_private_key: Optional[RSAPrivateKey] = None,
        aes_type: EncryptionType = EncryptionType.AES_256_GCM,
    ):
        """
        初始化混合加密器
        
        Args:
            rsa_public_key: RSA 公钥 (用于加密)
            rsa_private_key: RSA 私钥 (用于解密)
            aes_type: AES 加密类型
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library not available")
        
        self.rsa_public_key = rsa_public_key
        self.rsa_private_key = rsa_private_key
        self.aes_type = aes_type
        self.aes_key_size = AESEncryptor.KEY_SIZES[aes_type]
        
        # RSA 加密器
        self.rsa_encryptor = RSAEncryptor(
            rsa_private_key,
            rsa_public_key,
        )
    
    @classmethod
    def generate(cls) -> Tuple["HybridEncryptor", bytes, bytes]:
        """
        生成混合加密器及密钥
        
        Returns:
            (HybridEncryptor, RSA私钥PEM, RSA公钥PEM)
        """
        # 生成 RSA 密钥对
        rsa_encryptor, private_key, public_key = RSAEncryptor.generate_key_pair()
        
        encryptor = cls(
            private_key.public_key(),
            private_key,
        )
        
        return encryptor, rsa_encryptor.get_private_key_pem(), rsa_encryptor.get_public_key_pem()
    
    def encrypt(self, plain_text: bytes) -> EncryptedData:
        """
        混合加密数据
        
        Args:
            plain_text: 明文数据
            
        Returns:
            加密数据容器 (包含加密的 AES 密钥)
        """
        # 生成随机 AES 密钥
        aes_key = os.urandom(self.aes_key_size)
        
        # 用 AES 加密数据
        aes_encryptor = AESEncryptor(aes_key, self.aes_type)
        encrypted_data = aes_encryptor.encrypt(plain_text)
        
        # 用 RSA 加密 AES 密钥
        encrypted_key = self.rsa_encryptor.encrypt(aes_key)
        
        # 组装混合加密数据
        return EncryptedData(
            cipher_text=encrypted_data.cipher_text,
            encryption_type=EncryptionType.HYBRID,
            iv=encrypted_data.iv,
            tag=encrypted_data.tag,
            encrypted_key=encrypted_key.cipher_text,
            salt=encrypted_key.salt,
            iterations=encrypted_key.iterations,
        )
    
    def decrypt(self, encrypted_data: EncryptedData) -> bytes:
        """
        混合解密数据
        
        Args:
            encrypted_data: 加密数据容器
            
        Returns:
            明文数据
        """
        if self.rsa_private_key is None:
            raise ValueError("RSA private key is required for decryption")
        
        # 用 RSA 解密 AES 密钥
        encrypted_key_data = EncryptedData(
            cipher_text=encrypted_data.encrypted_key,
            encryption_type=self.rsa_encryptor.encryption_type,
            salt=encrypted_data.salt,
            iterations=encrypted_data.iterations,
        )
        aes_key = self.rsa_encryptor.decrypt(encrypted_key_data)
        
        # 用 AES 解密数据
        aes_encryptor = AESEncryptor(aes_key, self.aes_type)
        return aes_encryptor.decrypt(encrypted_data)


class EncryptionManager:
    """
    加密管理器
    
    统一的加密接口，支持多种加密类型
    """
    
    def __init__(self, default_type: EncryptionType = EncryptionType.AES_256_GCM):
        """
        初始化加密管理器
        
        Args:
            default_type: 默认加密类型
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library not available")
        
        self.default_type = default_type
        self._encryptors: Dict[EncryptionType, Union[AESEncryptor, RSAEncryptor, HybridEncryptor]] = {}
    
    def set_aes_key(self, key: bytes, encryption_type: EncryptionType) -> None:
        """设置 AES 密钥"""
        self._encryptors[encryption_type] = AESEncryptor(key, encryption_type)
    
    def set_rsa_keys(
        self,
        private_key: Optional[RSAPrivateKey] = None,
        public_key: Optional[RSAPublicKey] = None,
        encryption_type: EncryptionType = EncryptionType.RSA_2048,
    ) -> None:
        """设置 RSA 密钥"""
        self._encryptors[encryption_type] = RSAEncryptor(private_key, public_key, encryption_type)
    
    def set_hybrid_encryptor(self, encryptor: HybridEncryptor) -> None:
        """设置混合加密器"""
        self._encryptors[EncryptionType.HYBRID] = encryptor
    
    def encrypt(
        self,
        data: bytes,
        encryption_type: Optional[EncryptionType] = None,
    ) -> EncryptedData:
        """
        加密数据
        
        Args:
            data: 明文数据
            encryption_type: 加密类型 (None 使用默认)
            
        Returns:
            加密数据
        """
        enc_type = encryption_type or self.default_type
        encryptor = self._encryptors.get(enc_type)
        
        if encryptor is None:
            raise ValueError(f"No encryptor configured for {enc_type.value}")
        
        return encryptor.encrypt(data)
    
    def decrypt(
        self,
        encrypted_data: EncryptedData,
    ) -> bytes:
        """
        解密数据
        
        Args:
            encrypted_data: 加密数据
            
        Returns:
            明文数据
        """
        encryptor = self._encryptors.get(encrypted_data.encryption_type)
        
        if encryptor is None:
            raise ValueError(f"No encryptor configured for {encrypted_data.encryption_type.value}")
        
        return encryptor.decrypt(encrypted_data)
    
    def encrypt_string(
        self,
        text: str,
        encoding: str = "utf-8",
        encryption_type: Optional[EncryptionType] = None,
    ) -> str:
        """
        加密字符串
        
        Args:
            text: 明文字符串
            encoding: 字符编码
            encryption_type: 加密类型
            
        Returns:
            Base64 编码的加密数据
        """
        encrypted = self.encrypt(text.encode(encoding), encryption_type)
        return encrypted.to_base64()
    
    def decrypt_string(
        self,
        encrypted_text: str,
        encoding: str = "utf-8",
    ) -> str:
        """
        解密字符串
        
        Args:
            encrypted_text: Base64 编码的加密数据
            encoding: 字符编码
            
        Returns:
            明文字符串
        """
        encrypted = EncryptedData.from_base64(encrypted_text)
        return self.decrypt(encrypted).decode(encoding)
    
    def derive_key(
        self,
        password: str,
        salt: Optional[bytes] = None,
        iterations: int = 100000,
        key_length: int = 32,
    ) -> Tuple[bytes, bytes]:
        """
        从密码派生密钥
        
        Args:
            password: 密码
            salt: 盐值 (None 则自动生成)
            iterations: 迭代次数
            key_length: 密钥长度
            
        Returns:
            (密钥, 盐值)
        """
        if salt is None:
            salt = os.urandom(16)
        
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            iterations,
            dklen=key_length,
        )
        
        return key, salt


def generate_random_key(key_size: int = 32) -> bytes:
    """
    生成随机密钥
    
    Args:
        key_size: 密钥大小 (字节)
        
    Returns:
        随机密钥
    """
    return os.urandom(key_size)


def hash_data(data: bytes, algorithm: str = "sha256") -> str:
    """
    计算数据哈希
    
    Args:
        data: 数据
        algorithm: 哈希算法 (sha256, sha384, sha512)
        
    Returns:
        十六进制哈希值
    """
    h = hashlib.new(algorithm)
    h.update(data)
    return h.hexdigest()


def generate_key_fingerprint(key: bytes) -> str:
    """
    生成密钥指纹
    
    Args:
        key: 密钥数据
        
    Returns:
        密钥指纹 (前8字节的十六进制)
    """
    return hashlib.sha256(key).hexdigest()[:16]
