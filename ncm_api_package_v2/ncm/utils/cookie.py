import json
import os
from ncm.config import COOKIE_FILE

def save_cookie(cookie, filename=COOKIE_FILE):
    """保存Cookie到文件"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({"cookie": cookie}, f)
    print(f"💾 Cookie 已保存至 {filename}")

def load_cookie(filename=COOKIE_FILE):
    """从文件加载Cookie"""
    if not os.path.exists(filename):
        return None
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("cookie")
    except Exception as e:
        print(f"❌ 加载 cookie 失败：{e}")
        return None

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
