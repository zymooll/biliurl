"""
访问密码管理模块
提供密码验证、存储和刷新功能
"""

import json
import os
import hashlib
import secrets
import threading
from ncm.config import ACCESS_PASSWORD_FILE, DEFAULT_ACCESS_PASSWORD, ACCESS_PASSWORD_SALT

# 线程安全锁
_password_lock = threading.RLock()
_cached_password_hash = None


class AccessPasswordManager:
    """访问密码管理器"""
    
    @staticmethod
    def _hash_password(password: str) -> str:
        """对密码进行哈希处理（带salt）"""
        salted_password = f"{password}{ACCESS_PASSWORD_SALT}"
        return hashlib.sha256(salted_password.encode('utf-8')).hexdigest()
    
    @staticmethod
    def _hash_with_salt(password: str) -> str:
        """对密码进行哈希处理（带salt），用于API调用"""
        return AccessPasswordManager._hash_password(password)
    
    @staticmethod
    def initialize():
        """初始化密码文件，如果不存在则创建"""
        global _cached_password_hash
        
        with _password_lock:
            if not os.path.exists(ACCESS_PASSWORD_FILE):
                # 创建默认密码
                password_hash = AccessPasswordManager._hash_password(DEFAULT_ACCESS_PASSWORD)
                data = {
                    "password_hash": password_hash,
                    "created_at": "initialized"
                }
                with open(ACCESS_PASSWORD_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                _cached_password_hash = password_hash
                print(f"🔐 访问密码已初始化，默认密码: {DEFAULT_ACCESS_PASSWORD}")
                return password_hash
            else:
                # 加载现有密码
                return AccessPasswordManager.load_password_hash()
    
    @staticmethod
    def load_password_hash() -> str:
        """加载密码哈希值"""
        global _cached_password_hash
        
        with _password_lock:
            if _cached_password_hash:
                return _cached_password_hash
            
            if not os.path.exists(ACCESS_PASSWORD_FILE):
                return AccessPasswordManager.initialize()
            
            try:
                with open(ACCESS_PASSWORD_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    _cached_password_hash = data.get("password_hash")
                    return _cached_password_hash
            except Exception as e:
                print(f"❌ 加载密码失败: {e}")
                return AccessPasswordManager.initialize()
    
    @staticmethod
    def verify_password(password: str) -> bool:
        """验证密码是否正确"""
        if not password:
            return False
        
        stored_hash = AccessPasswordManager.load_password_hash()
        input_hash = AccessPasswordManager._hash_password(password)
        return input_hash == stored_hash
    
    @staticmethod
    def verify_hash(access_hash: str) -> bool:
        """验证hash值是否正确（用于API鉴权）"""
        if not access_hash:
            return False
        
        stored_hash = AccessPasswordManager.load_password_hash()
        return access_hash == stored_hash
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """获取密码对应的hash值（用于API调用）"""
        return AccessPasswordManager._hash_password(password)
    
    @staticmethod
    def update_password(new_password: str) -> bool:
        """更新密码"""
        global _cached_password_hash
        
        try:
            with _password_lock:
                password_hash = AccessPasswordManager._hash_password(new_password)
                data = {
                    "password_hash": password_hash,
                    "updated_at": "refreshed"
                }
                with open(ACCESS_PASSWORD_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                _cached_password_hash = password_hash
                print(f"🔐 访问密码已更新")
                return True
        except Exception as e:
            print(f"❌ 更新密码失败: {e}")
            return False
    
    @staticmethod
    def generate_random_password(length: int = 16) -> str:
        """生成随机密码"""
        import string
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def refresh_password() -> str:
        """刷新密码（生成新的随机密码）"""
        new_password = AccessPasswordManager.generate_random_password()
        if AccessPasswordManager.update_password(new_password):
            return new_password
        return None


# 初始化密码
AccessPasswordManager.initialize()
