import requests
import time
import qrcode
import base64
from io import BytesIO
from PIL import Image
from pyzbar.pyzbar import decode
import urllib.parse
import os
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
import uvicorn

# 全局配置
API_BASE_URL = "http://localhost:3002/"
DEFAULT_SONG_ID = 1856336348
DEFAULT_BIT_RATE = 320000
COOKIE_FILE = "cookie.json"
GUEST_COOKIE_FILE = "cookie-guest.json"

app = FastAPI(title="NCM API Service")
login_handler = None # 将在 startup 时初始化

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

def initSession():
    """初始化会话，获取有效cookie"""
    print("🔍 正在检查 Cookie 状态...")
    login = LoginProtocol()

    cookie = load_cookie()
    if cookie:
        try:
            data = UserInteractive.getUserAccount(cookie)
            if data.get("code") == 200:
                print(f"✅ 当前登录身份：{data.get('profile', {}).get('nickname', '未知')} (UID: {data.get('account', {}).get('id')})")
                return cookie
            else:
                print("⚠️ Cookie 已失效，将尝试使用游客身份登录")
        except Exception as e:
            print("❌ Cookie 校验失败：", e)
            print("➡️ 正在尝试游客身份登录...")

    try:
        guest_cookie = login.guestLogin()
        save_cookie(guest_cookie)
        print("✅ 已使用游客身份登录")
        return guest_cookie
    except Exception as e:
        print("❌ 游客身份登录失败：", e)
        return None

class LoginProtocol:
    """网易云音乐登录协议实现"""
    
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }

    def guestLogin(self):
        """游客登录，获取临时Cookie"""
        url = f"{API_BASE_URL}register/anonimous"
        try:
            response = self.session.get(url)
            response_data = response.json()

            if "cookie" in response_data:
                print("🌐 游客 Cookie 获取成功")
                with open(GUEST_COOKIE_FILE, "w", encoding="utf-8") as f:
                    json.dump({"cookie": response_data["cookie"]}, f)
                return response_data["cookie"]
            else:
                print("❌ 游客登录返回异常：", response_data)
                raise ValueError("游客登录失败，响应中缺少 cookie 字段")
        except Exception as e:
            print(f"❌ 游客登录请求失败: {e}")
            raise
    

    def getLoginInfo(self):
        """获取当前登录信息"""
        url = f"{API_BASE_URL}user/account"
        try:
            response = requests.get(url)
            response_data = response.json()
            if response_data.get("account") is None:
                return "未登录"
            return f"登录用户ID: {response_data['account'].get('id')}"
        except Exception as e:
            print(f"❌ 获取登录信息失败: {e}")
            return "获取登录信息出错"

    def getQRKey(self):
        """获取二维码登录的key"""
        # 为请求添加禁用缓存的头部
        headers = {
            'Cache-Control': 'no-cache, no-store',
            'Pragma': 'no-cache',
            'User-Agent': f'Mozilla/5.0 NetEase-MusicBox/{time.time()}'  # 添加随机性
        }
        # 生成一个随机数作为查询参数而不是timestamp
        random_param = int(time.time() * 1000)  
        url = f"{API_BASE_URL}login/qr/key?random={random_param}"
        
        try:
            # 使用实例的session对象而非全局requests
            resp = self.session.get(url, headers=headers)
            response = resp.json()
            return response["data"]["unikey"]
        except Exception as e:
            print(f"❌ 获取QR Key失败: {e}")
            raise


    def getQRCode(self, key):
        """获取并显示二维码"""
        url = f"{API_BASE_URL}login/qr/create?key={key}&qrimg=true"
        try:
            response = requests.get(url).json()
            return response["data"]["qrimg"] # 返回 base64 图片字符串
        except Exception as e:
            print(f"❌ 获取QR码失败: {e}")
            raise

    def checkQRStatus(self, key):
        """检查二维码扫描状态"""
        try:
            timestamp = int(time.time() * 1000)
            url = f"{API_BASE_URL}login/qr/check?key={key}&timestamp={timestamp}"

            resp = self.session.get(url, headers=self.headers)
            data = resp.json()
            return data
        except Exception as e:
            print(f"❌ 检查QR状态时出错: {e}")
            return {"code": -1, "message": str(e)}

    def Logout(self):
        """退出登录"""
        url = f"{API_BASE_URL}logout"
        try:
            response = requests.get(url)
            if os.path.exists(COOKIE_FILE):
                os.remove(COOKIE_FILE)
            return response.json()
        except Exception as e:
            print(f"❌ 退出登录失败: {e}")
            return {"code": -1, "message": str(e)}


class UserInteractive:
    """用户交互功能类"""
    
    @staticmethod
    def getDownloadUrl(songID, level="exhigh", unblock=False, cookie=None):
        """获取歌曲下载链接"""
        try:
            print(f"🎵 [getDownloadUrl] 传入参数: songID={songID}, level={level}")
            if not cookie:
                cookie = load_cookie()
            
            def fetch(current_level, current_unblock, current_cookie):
                params = {
                    "id": songID,
                    "level": current_level,
                    "unblock": "true" if current_unblock else "false",
                }
                if current_cookie:
                    # 确保包含 os=pc 且格式正确
                    c_str = current_cookie
                    if "os=pc" not in c_str.lower():
                        c_str += "; os=pc"
                    params["cookie"] = c_str
                
                if current_unblock:
                    params["source"] = "migu,qq"
                
                url = f"{API_BASE_URL}song/url/v1"
                print(f"📡 正在请求音频URL: songID={songID}, level={current_level} (VIP={bool(current_cookie)}, Unblock={current_unblock})")
                # 改用 POST 请求，防止 Cookie 过长导致 URL 超出限制 (HTTP 502)
                resp = requests.post(url, data=params)
                return resp.json()

            # 初始化变量，防止未赋值错误
            downloadUrl = None
            song_info = {}

            # 第一次尝试：使用当前设置
            data = fetch(level, unblock, cookie)
            
            if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                song_info = data['data'][0]
                downloadUrl = song_info.get('url')
                
                # 检查是否为酷狗占位符
                if downloadUrl and "1325645003.mp3" in downloadUrl:
                    print("⚠️ 检测到 VIP 身份未生效或音源受限（返回了酷狗占位符）")
                    if not unblock:
                        print("🔄 正在尝试开启解灰模式重新获取...")
                        data = fetch(level, True, None) # 开启解灰，且不带 Cookie 避免干扰
                    else:
                        print("🔄 正在尝试强制切换咪咕音源...")
                        # 强制咪咕
                        params_migu = {"id": songID, "level": "standard", "unblock": "true", "source": "migu"}
                        data = requests.get(f"{API_BASE_URL}song/url/v1", params=params_migu).json()
                
                # 重新提取结果
                song_info = data['data'][0]
                downloadUrl = song_info.get('url')

            if not downloadUrl:
                return {"success": False, "data": data}
            
            # 验证返回的歌曲ID是否匹配
            returned_song_id = song_info.get('id')
            if returned_song_id and str(returned_song_id) != str(songID):
                print(f"⚠️ 警告: 请求的歌曲ID ({songID}) 与返回的ID ({returned_song_id}) 不匹配!")
            else:
                print(f"✅ 歌曲ID验证通过: {songID}")
            
            return {
                "success": True,
                "level": song_info.get('level', '未知'),
                "url": downloadUrl,
                "raw": song_info
            }

        except Exception as e:
            print(f"❌ 获取下载链接失败: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def getUserAccount(cookie):
        """获取用户账号信息"""
        try:
            if not cookie:
                return None
                
            encoded_cookie = urllib.parse.quote(cookie)
            url = f"{API_BASE_URL}user/account?cookie={encoded_cookie}"
            
            response = requests.get(url)
            data = response.json()
            return data
        except Exception as e:
            print(f"❌ 获取用户信息失败: {e}")
            return None

# --- API Endpoints ---

@app.on_event("startup")
async def startup_event():
    global login_handler
    login_handler = LoginProtocol()
    initSession()

@app.get("/")
async def root():
    return {"message": "NCM API Service is running", "docs": "/docs"}

@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(status_code=204, content={})

@app.get("/login/qr/key")
async def get_qr_key():
    """1. 获取扫码登录所需的 Key"""
    try:
        key = login_handler.getQRKey()
        return {"code": 200, "unikey": key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/login/qr/create")
async def create_qr_code(key: str):
    """2. 根据 Key 生成二维码 (返回 base64)"""
    try:
        qrimg = login_handler.getQRCode(key)
        return {"code": 200, "qrimg": qrimg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/login/qr/check")
async def check_qr_status(key: str):
    """3. 检查扫码状态"""
    try:
        data = login_handler.checkQRStatus(key)
        if data.get("code") == 803:
            # 登录成功，保存 Cookie
            cookie = data.get("cookie")
            save_cookie(cookie)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/cookie")
async def get_current_cookie():
    """4. 查询当前保存的 Cookie"""
    cookie = load_cookie()
    if not cookie:
        return {"code": 404, "message": "未找到已保存的 Cookie"}
    return {"code": 200, "cookie": cookie}

@app.get("/user/info")
async def get_user_info():
    """5. 获取当前登录用户信息"""
    cookie = load_cookie()
    if not cookie:
        raise HTTPException(status_code=401, detail="未登录")
    data = UserInteractive.getUserAccount(cookie)
    return data

@app.get("/resolve")
async def resolve_song(
    id: int, 
    level: str = "exhigh", 
    unblock: bool = False
):
    """6. 直链解析 (传入 id，返回直链)"""
    cookie = load_cookie()
    result = UserInteractive.getDownloadUrl(id, level, unblock, cookie)
    if result["success"]:
        return result
    else:
        return JSONResponse(status_code=400, content=result)

@app.get("/logout")
async def logout():
    """7. 退出登录"""
    return login_handler.Logout()

@app.get("/play")
async def play_song_redirect(
    id: int, 
    level: str = "exhigh", 
    unblock: bool = False
):
    """8. VRChat 播放专用 (重定向到直链)"""
    cookie = load_cookie()
    result = UserInteractive.getDownloadUrl(id, level, unblock, cookie)
    if result["success"] and result.get("url"):
        return RedirectResponse(url=result["url"])
    else:
        raise HTTPException(status_code=404, detail="无法获取歌曲链接")

import re

# ... existing code ...

@app.get("/lyric")
async def get_lyric(id: int):
    """9. 获取歌词 (代理 lyrics.0061226.xyz)"""
    try:
        url = f"https://lyrics.0061226.xyz/api/lyric?id={id}"
        # 设置超时防止卡死
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        # 增加判断逻辑
        if data.get("code") == 200:
            lyrics_data = data.get("data", {}).get("lyrics", {})
            yrc = lyrics_data.get("yrc")
            lrc = lyrics_data.get("lrc")
            tlyric = lyrics_data.get("tlyric")

            if yrc and yrc.get("lyric"):
                print(f"✅ [歌词] ID:{id} 包含逐字歌词 (YRC)")
                # 尝试处理翻译匹配
                if tlyric and tlyric.get("lyric"):
                    processed_lyrics = process_lyrics_matching(yrc["lyric"], tlyric["lyric"])
                    # 将处理后的歌词放入返回数据中，方便客户端直接使用
                    data["data"]["lyrics"]["processed"] = processed_lyrics
                    print(f"✅ [歌词] 已合并翻译 ({len(processed_lyrics)} 行)")

            elif lrc and lrc.get("lyric"):
                print(f"⚠️ [歌词] ID:{id} 仅包含普通歌词 (LRC)")
            else:
                print(f"❌ [歌词] ID:{id} 未找到有效歌词")
                
        return data
    except Exception as e:
        print(f"❌ 获取歌词失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def process_lyrics_matching(yrc_text, tlyric_text):
    """
    将 YRC 逐字歌词与翻译歌词进行匹配
    返回格式: List[{time: int, duration: int, content: str, translation: str, json_content: object}]
    """
    try:
        # 1. 解析翻译歌词 (LRC 格式) -> {time_ms: translation_text}
        tlyric_map = {}
        for line in tlyric_text.split('\n'):
            # 匹配 [mm:ss.xx] 或 [mm:ss.xxx]
            match = re.search(r'\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)', line)
            if match:
                m, s, ms_str = match.groups()[:3]
                text = match.group(4).strip()
                if not text: continue
                
                # 计算毫秒
                ms = int(ms_str.ljust(3, '0')[:3]) # 确保是3位
                total_ms = int(m) * 60000 + int(s) * 1000 + ms
                tlyric_map[total_ms] = text

        # 2. 解析 YRC 歌词
        result = []
        yrc_lines = yrc_text.split('\n')
        
        # 获取所有翻译的时间点并排序，用于查找最近的翻译
        t_times = sorted(tlyric_map.keys())
        
        for line in yrc_lines:
            # YRC 格式: [start, duration]...
            # 提取行开始时间
            match = re.search(r'^\[(\d+),(\d+)\]', line)
            if not match: continue
            
            start_time = int(match.group(1))
            duration = int(match.group(2))
            
            # 3. 查找匹配的翻译
            # 策略：在 YRC 开始时间附近寻找翻译 (容差 ±1000ms)
            # 优先找时间戳完全一致或非常接近的
            
            matched_trans = None
            min_diff = 1000 # 最大容差 1秒
            
            for t_time in t_times:
                diff = abs(start_time - t_time)
                if diff < min_diff:
                    min_diff = diff
                    matched_trans = tlyric_map[t_time]
                
                # 如果已经超过当前时间太多，后面的不用看了 (假设是有序的)
                if t_time > start_time + 1000:
                    break
            
            # 构造返回对象
            result.append({
                "time": start_time,
                "duration": duration,
                "raw": line, # 原始 YRC 行
                "translation": matched_trans # 匹配到的翻译
            })
            
        return result

    except Exception as e:
        print(f"❌ 歌词匹配处理出错: {e}")
        return []

if __name__ == "__main__":
    # 启动 API 服务
    uvicorn.run(app, host="0.0.0.0", port=7997)

