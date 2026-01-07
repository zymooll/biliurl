import json
import os
import threading
from ncm.config import COOKIE_FILE

# 全局线程安全的 Cookie 管理器
_cookie_lock = threading.RLock()
_cached_cookie = None

class CookieManager:
    """线程安全的 Cookie 管理器"""
    
    @staticmethod
    def save_cookie(cookie, filename=COOKIE_FILE):
        """保存Cookie到文件（线程安全）"""
        global _cached_cookie
        with _cookie_lock:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump({"cookie": cookie}, f)
            _cached_cookie = cookie
            print(f"💾 Cookie 已保存至 {filename}")
    
    @staticmethod
    def load_cookie(filename=COOKIE_FILE, use_cache=True):
        """从文件加载Cookie（线程安全）"""
        global _cached_cookie
        
        # 如果使用缓存且缓存存在，直接返回
        if use_cache and _cached_cookie:
            return _cached_cookie
        
        with _cookie_lock:
            if not os.path.exists(filename):
                return None
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cookie = data.get("cookie")
                    _cached_cookie = cookie
                    return cookie
            except Exception as e:
                print(f"❌ 加载 cookie 失败：{e}")
                return None
    
    @staticmethod
    def clear_cookie(filename=COOKIE_FILE):
        """清除Cookie（线程安全）"""
        global _cached_cookie
        with _cookie_lock:
            _cached_cookie = None
            if os.path.exists(filename):
                os.remove(filename)
                print(f"🗑️ Cookie 文件已删除: {filename}")
    
    @staticmethod
    def refresh_cache():
        """刷新缓存（从文件重新加载）"""
        return CookieManager.load_cookie(use_cache=False)

# 为了向后兼容，保留原来的函数名
def save_cookie(cookie, filename=COOKIE_FILE):
    """保存Cookie到文件"""
    return CookieManager.save_cookie(cookie, filename)

def load_cookie(filename=COOKIE_FILE):
    """从文件加载Cookie"""
    return CookieManager.load_cookie(filename)

def filter_cookie(cookie_str):
    """
    过滤 Cookie，只保留核心字段，防止 Header/URL 过长导致 502
    """
    if not cookie_str:
        return ""
        
    # 确保包含 os=pc
    if "os=pc" not in cookie_str.lower():
        cookie_str += "; os=pc"
    
    # 核心字段列表
    core_keys = ["MUSIC_U", "__csrf", "NMTID", "os"]
    filtered_parts = []
    
    for part in cookie_str.split(';'):
        part = part.strip()
        if not part: continue
        try:
            key = part.split('=')[0].strip()
            if key in core_keys or key == "os":
                filtered_parts.append(part)
        except:
            continue
            
    result = "; ".join(filtered_parts)
    
    # 如果过滤后为空（可能格式不对），或者结果依然太长（极少见），则回退或截断
    if not result:
        return cookie_str[:2000]
        
    return result
