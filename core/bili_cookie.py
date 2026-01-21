import json
import os
import threading
from typing import Optional
from requests.cookies import RequestsCookieJar

# 全局线程安全的 B站 Cookie 管理器
_bili_cookie_lock = threading.RLock()
_bili_cached_cookie = None

# B站 Cookie 文件路径
BILI_COOKIE_FILE = "bili_cookie.json"

class BiliCookieManager:
    """线程安全的 B站 Cookie 管理器"""
    
    @staticmethod
    def save_cookie(cookies: RequestsCookieJar, filename: str = BILI_COOKIE_FILE):
        """
        保存 B站 Cookie 到文件（线程安全）
        
        参数:
            cookies: RequestsCookieJar 对象
            filename: 保存的文件名
        """
        global _bili_cached_cookie
        with _bili_cookie_lock:
            # 将 RequestsCookieJar 转换为字典
            cookie_dict = dict(cookies)
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(cookie_dict, f, indent=2)
            _bili_cached_cookie = cookie_dict
            print(f"💾 B站 Cookie 已保存至 {filename}")
    
    @staticmethod
    def load_cookie(filename: str = BILI_COOKIE_FILE, use_cache: bool = True) -> Optional[dict]:
        """
        从文件加载 B站 Cookie（线程安全）
        
        参数:
            filename: Cookie文件名
            use_cache: 是否使用缓存
            
        返回:
            Cookie字典，如果不存在则返回None
        """
        global _bili_cached_cookie
        
        # 如果使用缓存且缓存存在，直接返回
        if use_cache and _bili_cached_cookie:
            return _bili_cached_cookie
        
        with _bili_cookie_lock:
            if not os.path.exists(filename):
                return None
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    cookie_dict = json.load(f)
                    _bili_cached_cookie = cookie_dict
                    return cookie_dict
            except Exception as e:
                print(f"❌ 加载 B站 cookie 失败：{e}")
                return None
    
    @staticmethod
    def clear_cookie(filename: str = BILI_COOKIE_FILE):
        """
        清除 B站 Cookie（线程安全）
        
        参数:
            filename: Cookie文件名
        """
        global _bili_cached_cookie
        with _bili_cookie_lock:
            _bili_cached_cookie = None
            if os.path.exists(filename):
                os.remove(filename)
                print(f"🗑️ B站 Cookie 已清除")
    
    @staticmethod
    def dict_to_cookiejar(cookie_dict: dict) -> RequestsCookieJar:
        """
        将字典转换为 RequestsCookieJar
        
        参数:
            cookie_dict: Cookie字典
            
        返回:
            RequestsCookieJar 对象
        """
        jar = RequestsCookieJar()
        for key, value in cookie_dict.items():
            jar.set(key, value)
        return jar
    
    @staticmethod
    def is_logged_in(filename: str = BILI_COOKIE_FILE) -> bool:
        """
        检查是否已登录（通过检查Cookie文件是否存在且有效）
        
        参数:
            filename: Cookie文件名
            
        返回:
            是否已登录
        """
        cookie_dict = BiliCookieManager.load_cookie(filename)
        if cookie_dict and 'SESSDATA' in cookie_dict:
            # 简单检查是否包含关键cookie
            return True
        return False


# 便捷函数
def save_bili_cookie(cookies: RequestsCookieJar, filename: str = BILI_COOKIE_FILE):
    """保存 B站 Cookie（便捷函数）"""
    BiliCookieManager.save_cookie(cookies, filename)

def load_bili_cookie(filename: str = BILI_COOKIE_FILE, use_cache: bool = True) -> Optional[dict]:
    """加载 B站 Cookie（便捷函数）"""
    return BiliCookieManager.load_cookie(filename, use_cache)

def clear_bili_cookie(filename: str = BILI_COOKIE_FILE):
    """清除 B站 Cookie（便捷函数）"""
    BiliCookieManager.clear_cookie(filename)

def is_bili_logged_in(filename: str = BILI_COOKIE_FILE) -> bool:
    """检查是否已登录 B站（便捷函数）"""
    return BiliCookieManager.is_logged_in(filename)
