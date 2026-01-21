from fastapi import APIRouter, HTTPException, Query, Response, BackgroundTasks, Cookie, Header, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, StreamingResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import requests
import os
import time
import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor, Executor
from pathlib import Path
from urllib.parse import quote
import threading
from typing import Optional
from datetime import datetime, timedelta
from ncm.core.login import LoginProtocol
from ncm.core.music import UserInteractive
from ncm.core.lyrics import process_lyrics_matching
from ncm.core.video import VideoGenerator
from ncm.utils.cookie import load_cookie, save_cookie
from ncm.utils.database import db
from ncm.utils.access_password import AccessPasswordManager
from ncm.api.web_ui import get_web_ui_html, get_login_page_html, STATIC_DIR
from core.bili import BiliLogin, BiliVideo
from core.bili_cookie import BiliCookieManager

router = APIRouter()
login_handler: Optional[LoginProtocol] = None
bili_login_handler: Optional[BiliLogin] = None
bili_video_handler: Optional[BiliVideo] = None
API_BASE_URL = "http://localhost:3002/"

# 用户绑定的ID和MV参数存储 (内存缓存)
# 格式: {"user": {"id": 123, "mv": True}}
user_id_bindings = {}


# 静态文件目录路径（用于挂载）
STATIC_FILES_DIR = STATIC_DIR

# 动态线程池管理器
class DynamicThreadPoolManager(Executor):
    """动态线程池管理器 - 根据任务数量自动扩展和收缩"""
    
    def __init__(self, min_workers: int = 2, max_workers: Optional[int] = None, idle_timeout: int = 60):
        """
        初始化动态线程池管理器
        
        参数:
            min_workers: 最小保留的工作线程数（默认2个）
            max_workers: 最大工作线程数（默认为CPU核心数）
            idle_timeout: 空闲超时时间（秒），超过此时间后收缩到最小线程数（默认60秒）
        """
        import multiprocessing
        self.min_workers = min_workers
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.idle_timeout = idle_timeout
        
        # 初始化为最小线程数
        self._current_workers = min_workers
        self._executor = ThreadPoolExecutor(max_workers=min_workers, thread_name_prefix="VideoGen")
        
        # 任务计数器和锁
        self._active_tasks = 0
        self._total_submitted_tasks = 0
        self._lock = threading.Lock()
        
        # 最后活动时间
        self._last_activity_time = datetime.now()
        
        # 监控线程
        self._monitor_thread = None
        self._running = True
        self._start_monitor()
        
        print(f"🚀 动态线程池已初始化: 初始 {min_workers} 个线程, 最大 {self.max_workers} 个线程, 空闲超时 {idle_timeout}秒")
    
    def submit(self, fn, *args, **kwargs):
        """提交任务到线程池"""
        with self._lock:
            self._active_tasks += 1
            self._total_submitted_tasks += 1
            self._last_activity_time = datetime.now()
            
            # 检查是否需要扩展线程池
            if self._active_tasks > self._current_workers and self._current_workers < self.max_workers:
                self._expand_pool()
        
        # 包装任务以便在完成时更新计数器
        def wrapped_task():
            try:
                result = fn(*args, **kwargs)
                return result
            finally:
                with self._lock:
                    self._active_tasks -= 1
                    self._last_activity_time = datetime.now()
        
        return self._executor.submit(wrapped_task)
    
    def _expand_pool(self):
        """扩展线程池（需要在锁内调用）"""
        new_workers = min(self._current_workers + 1, self.max_workers)
        if new_workers > self._current_workers:
            print(f"📈 扩展线程池: {self._current_workers} -> {new_workers} 个线程 (活跃任务: {self._active_tasks})")
            
            # 创建新的线程池
            old_executor = self._executor
            self._executor = ThreadPoolExecutor(max_workers=new_workers, thread_name_prefix="VideoGen")
            self._current_workers = new_workers
            
            # 优雅关闭旧线程池（不等待，让任务自然完成）
            old_executor.shutdown(wait=False)
    
    def _shrink_pool(self):
        """收缩线程池到最小值（需要在锁内调用）"""
        if self._current_workers > self.min_workers:
            print(f"📉 收缩线程池: {self._current_workers} -> {self.min_workers} 个线程 (空闲超时)")
            
            # 创建新的线程池
            old_executor = self._executor
            self._executor = ThreadPoolExecutor(max_workers=self.min_workers, thread_name_prefix="VideoGen")
            self._current_workers = self.min_workers
            
            # 优雅关闭旧线程池
            old_executor.shutdown(wait=False)
    
    def _start_monitor(self):
        """启动监控线程，定期检查是否需要收缩线程池"""
        def monitor():
            while self._running:
                time.sleep(10)  # 每10秒检查一次
                
                with self._lock:
                    # 如果没有活跃任务且超过空闲超时时间，收缩线程池
                    if self._active_tasks == 0:
                        idle_time = (datetime.now() - self._last_activity_time).total_seconds()
                        if idle_time >= self.idle_timeout and self._current_workers > self.min_workers:
                            self._shrink_pool()
        
        self._monitor_thread = threading.Thread(target=monitor, daemon=True, name="PoolMonitor")
        self._monitor_thread.start()
    
    def get_status(self) -> dict:
        """获取线程池状态信息"""
        with self._lock:
            idle_time = (datetime.now() - self._last_activity_time).total_seconds()
            return {
                "current_workers": self._current_workers,
                "min_workers": self.min_workers,
                "max_workers": self.max_workers,
                "active_tasks": self._active_tasks,
                "total_submitted": self._total_submitted_tasks,
                "idle_seconds": round(idle_time, 2)
            }
    
    def shutdown(self, wait=True, *, cancel_futures=False):
        """关闭线程池"""
        self._running = False
        if self._executor:
            self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)

# 创建动态线程池管理器
video_executor = DynamicThreadPoolManager(min_workers=2, idle_timeout=60)

def init_login_handler():
    global login_handler, bili_login_handler, bili_video_handler
    login_handler = LoginProtocol()
    bili_login_handler = BiliLogin()
    bili_video_handler = BiliVideo()

def retry_request(func, *args, max_retries=5, timeout=10, **kwargs):
    """
    重试机制包装器
    
    参数:
        func: 要执行的函数
        max_retries: 最大重试次数
        timeout: 超时时间（秒）
        *args, **kwargs: 传递给func的参数
    
    返回:
        函数执行结果
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                wait_time = min(2 ** attempt, 5)  # 指数退避，最多5秒
                print(f"🔄 重试第 {attempt + 1}/{max_retries} 次，等待 {wait_time}秒...")
                time.sleep(wait_time)
            
            # 如果是 requests 请求，添加 timeout
            if func == requests.get or func == requests.post:
                kwargs.setdefault('timeout', timeout)
            
            result = func(*args, **kwargs)
            return result
            
        except (requests.Timeout, requests.ConnectionError, requests.RequestException) as e:
            last_error = e
            print(f"⚠️ 请求失败 (尝试 {attempt + 1}/{max_retries}): {type(e).__name__} - {str(e)[:100]}")
            if attempt == max_retries - 1:
                raise Exception(f"请求失败，已重试 {max_retries} 次: {str(last_error)}")
        except Exception as e:
            # 其他异常直接抛出，不重试
            raise e

def extract_song_id_from_url(url_or_id: str) -> str:
    """
    从网易云音乐链接或纯ID中提取歌曲ID
    
    支持的格式：
    - 纯数字ID: "483242395"
    - 完整URL: "https://music.163.com/song?id=483242395&userid=1646867891"
    - 简化URL: "music.163.com/song?id=483242395"
    - 移动端URL: "https://music.163.com/#/song?id=483242395"
    
    参数:
        url_or_id: URL字符串或纯ID
    
    返回:
        提取的歌曲ID字符串，如果无法提取则返回原值
    """
    import re
    from urllib.parse import urlparse, parse_qs
    
    # 如果已经是纯数字ID，直接返回
    if url_or_id.isdigit():
        return url_or_id
    
    try:
        # 方法1: 使用正则表达式匹配 id=数字
        match = re.search(r'[?&]id=(\d+)', url_or_id)
        if match:
            song_id = match.group(1)
            print(f"🔗 [URL解析] 从URL提取ID: {url_or_id} -> {song_id}")
            return song_id
        
        # 方法2: 使用 urlparse 解析
        if '://' in url_or_id or url_or_id.startswith('music.163.com'):
            if not url_or_id.startswith('http'):
                url_or_id = 'https://' + url_or_id
            
            # 移除 # 标记（移动端URL可能有）
            url_or_id = url_or_id.replace('/#/', '/')
            
            parsed = urlparse(url_or_id)
            params = parse_qs(parsed.query)
            
            if 'id' in params and params['id']:
                song_id = params['id'][0]
                print(f"🔗 [URL解析] 从URL提取ID: {url_or_id} -> {song_id}")
                return song_id
    except Exception as e:
        print(f"⚠️ [URL解析] 解析失败: {e}, 返回原值")
    
    # 无法提取，返回原值
    return url_or_id

def fetch_lyrics_with_retry(song_id, max_retries=3, timeout=15):
    """
    带重试机制的歌词获取函数 (支持数据库缓存)
    
    参数:
        song_id: 歌曲ID
        max_retries: 最大重试次数 (默认3次)
        timeout: 超时时间 (默认15秒)
    
    返回:
        tuple: (success, lyrics_text, trans_lyrics_text, error_message)
    """
    # 1. 尝试从数据库缓存获取
    cached_data = db.get_lyrics(song_id)
    if cached_data:
        print(f"💾 [Cache] 命中歌词缓存 ID: {song_id}")
        if cached_data.get("code") == 200:
            lyrics_data = cached_data.get("data", {}).get("lyrics", {})
            lrc = lyrics_data.get("lrc", {})
            tlyric = lyrics_data.get("tlyric", {})
            trans_text = tlyric.get("lyric", "") if tlyric else ""
            if lrc and lrc.get("lyric"):
                return True, lrc["lyric"], trans_text, None
        return True, "暂无歌词", "", None
    
    # 2. 缓存未命中，从API获取
    last_error = None
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                wait_time = min(2 ** attempt, 8)  # 指数退避，最多8秒
                print(f"🔄 [歌词] 重试第 {attempt + 1}/{max_retries} 次，等待 {wait_time}秒... ID:{song_id}")
                time.sleep(wait_time)
            
            print(f"🎵 [歌词] 请求歌词 ID:{song_id} (尝试 {attempt + 1}/{max_retries}, 超时:{timeout}s)")
            lyric_url = f"https://lyrics.0061226.xyz/api/lyric?id={song_id}"
            resp = requests.get(lyric_url, timeout=timeout)
            data = resp.json()
            
            if data.get("code") == 200:
                # 保存到数据库缓存
                db.save_lyrics(song_id, data)
                
                lyrics_data = data.get("data", {}).get("lyrics", {})
                lrc = lyrics_data.get("lrc", {})
                tlyric = lyrics_data.get("tlyric", {})
                trans_text = tlyric.get("lyric", "") if tlyric else ""
                
                if lrc and lrc.get("lyric"):
                    print(f"✅ [歌词] 成功获取并缓存歌词 ID:{song_id} (尝试 {attempt + 1}/{max_retries})")
                    return True, lrc["lyric"], trans_text, None
                else:
                    print(f"⚠️ [歌词] 歌词内容为空 ID:{song_id}")
                    return True, "暂无歌词", "", None
            else:
                error_msg = f"API返回错误: code={data.get('code')}, msg={data.get('message', '未知错误')}"
                print(f"⚠️ [歌词] {error_msg} ID:{song_id}")
                last_error = error_msg
                
        except (requests.Timeout, requests.ConnectionError) as e:
            last_error = f"网络超时: {str(e)}"
            print(f"⚠️ [歌词] {last_error} ID:{song_id} (尝试 {attempt + 1}/{max_retries})")
            
        except requests.RequestException as e:
            last_error = f"请求异常: {str(e)}"
            print(f"⚠️ [歌词] {last_error} ID:{song_id} (尝试 {attempt + 1}/{max_retries})")
            
        except Exception as e:
            last_error = f"未知错误: {str(e)}"
            print(f"❌ [歌词] {last_error} ID:{song_id} (尝试 {attempt + 1}/{max_retries})")
    
    # 所有重试都失败了
    final_error = f"歌词请求失败 (重试{max_retries}次): {last_error}"
    print(f"❌ [歌词] {final_error} ID:{song_id}")
    return False, final_error, "", last_error

def create_json_response(content, status_code=200):
    """创建 JSON 响应并移除 Content-Length 头，防止协议错误"""
    response = JSONResponse(content=content, status_code=status_code)
    # 移除 Content-Length，让底层自动计算（使用 del 而不是 pop）
    if "content-length" in response.headers:
        del response.headers["content-length"]
    return response

def verify_access_password(access_password: Optional[str] = Cookie(None), access_hash: Optional[str] = None) -> bool:
    """
    验证访问密码或hash
    支持两种方式：
    1. Cookie中的hash值
    2. URL参数中的access_hash
    """
    # 优先使用URL参数中的access_hash
    if access_hash:
        return AccessPasswordManager.verify_hash(access_hash)
    
    # 其次使用Cookie中的hash值
    if access_password:
        return AccessPasswordManager.verify_hash(access_password)
    
    return False

@router.get("/threadpool/status")
async def get_threadpool_status():
    """获取线程池状态信息"""
    status = video_executor.get_status()
    return create_json_response({
        "code": 200,
        "message": "线程池状态获取成功",
        "data": status
    })

@router.get("/")
async def root(access_password: str = Cookie(None), access_hash: str = Query(None)):
    """返回可视化Web界面（需要密码验证）"""
    if not verify_access_password(access_password, access_hash):
        return HTMLResponse(content=get_login_page_html())
    return HTMLResponse(content=get_web_ui_html())

@router.post("/auth/verify")
async def verify_password(password: str = Form(...)):
    """验证访问密码"""
    if AccessPasswordManager.verify_password(password):
        # 获取密码对应的hash值（用于API调用）
        password_hash = AccessPasswordManager.get_password_hash(password)
        response = create_json_response({
            "code": 200, 
            "message": "验证成功",
            "hash": password_hash  # 返回hash值供API使用
        })
        # 设置 Cookie，存储hash值而不是明文密码，有效期30天
        response.set_cookie(
            key="access_password",
            value=password_hash,  # 存储hash而不是明文
            max_age=30 * 24 * 60 * 60,  # 30天
            httponly=True,
            samesite="lax"
        )
        return response
    else:
        return create_json_response({"code": 401, "message": "密码错误"}, 401)

@router.post("/auth/change-password")
async def change_password(
    current_password: str = Form(..., description="当前密码"),
    new_password: str = Form(..., description="新密码")
):
    """
    修改访问密码
    
    参数:
        current_password: 当前密码（必填）
        new_password: 新密码（必填）
    
    返回:
        新密码的hash值
    """
    # 验证当前密码
    if not AccessPasswordManager.verify_password(current_password):
        return create_json_response({
            "code": 403,
            "message": "当前密码错误"
        }, 403)
    
    # 验证新密码
    if not new_password or len(new_password) < 6:
        return create_json_response({
            "code": 400,
            "message": "新密码长度至少6位"
        }, 400)
    
    # 更新密码
    if AccessPasswordManager.update_password(new_password):
        print(f"🔐 访问密码已更改")
        # 获取新密码的hash
        new_hash = AccessPasswordManager.get_password_hash(new_password)
        return create_json_response({
            "code": 200,
            "message": "密码修改成功",
            "hash": new_hash
        })
    else:
        return create_json_response({
            "code": 500,
            "message": "密码修改失败"
        }, 500)

@router.get("/auth/check")
async def check_auth(access_password: str = Cookie(None), access_hash: str = Query(None)):
    """检查访问密码是否有效"""
    if verify_access_password(access_password, access_hash):
        return create_json_response({"code": 200, "message": "已授权", "authorized": True})
    else:
        return create_json_response({"code": 401, "message": "未授权", "authorized": False}, 401)

@router.get("/api")
async def api_info():
    """API信息接口"""
    return create_json_response({"message": "NCM API Service is running", "docs": "/docs"})

@router.get("/favicon.ico")
async def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)

@router.get("/login/qr/key")
async def get_qr_key():
    """1. 获取扫码登录所需的 Key"""
    try:
        key = login_handler.getQRKey()  # type: ignore
        return create_json_response({"code": 200, "unikey": key})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/login/qr/create")
async def create_qr_code(key: str):
    """2. 根据 Key 生成二维码 (返回 base64)"""
    try:
        qrimg = login_handler.getQRCode(key)  # type: ignore
        return create_json_response({"code": 200, "qrimg": qrimg})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/login/qr/check")
async def check_qr_status(key: str):
    """3. 检查扫码状态"""
    try:
        data = login_handler.checkQRStatus(key)  # type: ignore
        if data.get("code") == 803:
            # 登录成功，保存 Cookie
            cookie = data.get("cookie")
            save_cookie(cookie)
            # 立即刷新缓存，确保所有线程同步
            from ncm.utils.cookie import CookieManager
            CookieManager.refresh_cache()
            print(f"✅ 用户登录成功，Cookie 已保存并同步到所有线程")
        return create_json_response(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/cookie")
async def get_current_cookie():
    """4. 查询当前保存的 Cookie"""
    cookie = load_cookie()
    if not cookie:
        return create_json_response({"code": 404, "message": "未找到已保存的 Cookie"}, 404)
    return create_json_response({"code": 200, "cookie": cookie})

@router.get("/user/info")
async def get_user_info():
    """5. 获取当前登录用户信息"""
    cookie = load_cookie()
    if not cookie:
        raise HTTPException(status_code=401, detail="未登录")
    data = UserInteractive.getUserAccount(cookie)
    return create_json_response(data)

@router.get("/resolve")
async def resolve_song(
    id: int, 
    level: str = "standard", 
    unblock: bool = False,
    simple: bool = False,
    use_gpu: bool = False,
    threads: Optional[int] = None,
    gpu_device: Optional[str] = None
):
    cookie = load_cookie()
    result = UserInteractive.getDownloadUrl(id, level, unblock, cookie)
    
    status_code = 200 if result["success"] else 400
    return create_json_response(result, status_code)

@router.get("/song/detail")
async def get_song_detail(
    id: str,
    level: str = "standard",
    unblock: bool = False
):
    """获取歌曲详情 (包含封面等信息和播放链接)"""
    # 获取歌曲详情
    data = UserInteractive.getSongDetail(id)
    
    # 如果获取详情成功，尝试获取播放链接
    if data and data.get("code") == 200 and data.get("songs"):
        try:
            # 确保 id 是整数
            song_id = int(id)
            
            # 获取播放链接
            cookie = load_cookie()
            url_result = UserInteractive.getDownloadUrl(song_id, level, unblock, cookie)
            
            # 将播放链接信息添加到每首歌曲的数据中
            for song in data.get("songs", []):
                if url_result["success"] and url_result.get("url"):
                    song["playUrl"] = url_result["url"]
                    song["playLevel"] = level
                    song["playSuccess"] = True
                else:
                    song["playUrl"] = None
                    song["playLevel"] = level
                    song["playSuccess"] = False
                    song["playError"] = url_result.get("error", "无法获取播放链接")
        except (ValueError, TypeError):
            # ID格式错误时，不添加播放链接信息
            for song in data.get("songs", []):
                song["playUrl"] = None
                song["playSuccess"] = False
                song["playError"] = "无效的歌曲 ID"
        except Exception as e:
            # 获取播放链接失败时，不影响歌曲详情的返回
            for song in data.get("songs", []):
                song["playUrl"] = None
                song["playSuccess"] = False
                song["playError"] = f"获取播放链接失败: {str(e)}"
    
    return create_json_response(data)

@router.get("/playlist/detail")
async def get_playlist_detail(id: str):
    """
    获取歌单详情
    
    参数:
        id: 歌单ID（必填）
    
    返回:
        歌单详细信息，包括：
        - playlist.trackIds: 完整的歌曲ID列表
        - playlist.tracks: 部分歌曲详情（未登录可能不完整）
    
    说明:
        返回的 trackIds 是完整的，但 tracks 可能不完整。
        如需获取所有歌曲的完整详情，请使用 /playlist/tracks 接口。
    """
    cookie = load_cookie()
    data = UserInteractive.getPlaylistDetail(id, cookie)
    return create_json_response(data)

@router.get("/playlist/tracks")
async def get_playlist_tracks(id: str):
    """
    获取歌单的所有歌曲详情（完整版）
    
    参数:
        id: 歌单ID或URL（必填）
    
    返回:
        {
            "code": 200,
            "playlist_info": {
                "id": 歌单ID,
                "name": "歌单名称",
                "creator": "创建者",
                "coverImgUrl": "封面图片",
                "playCount": 播放次数,
                "trackCount": 歌曲总数
            },
            "songs": [
                {
                    "id": 歌曲ID,
                    "name": "歌曲名",
                    "ar": [{"name": "歌手名"}],
                    "al": {"name": "专辑名", "picUrl": "封面"},
                    "dt": 时长(毫秒)
                },
                ...
            ],
            "total": 歌曲总数
        }
    
    说明:
        此接口会先获取歌单的所有歌曲ID，然后批量获取完整的歌曲详情。
        支持传入歌单URL或纯数字ID。
    """
    import re
    
    # 从URL或纯数字中提取歌单ID
    playlist_id = id
    if not id.isdigit():
        # 尝试从URL中提取id参数
        match = re.search(r'[?&]id=(\d+)', id)
        if match:
            playlist_id = match.group(1)
        else:
            return create_json_response({
                "code": 400,
                "message": "无效的歌单ID或URL"
            }, 400)
    
    cookie = load_cookie()
    data = UserInteractive.getPlaylistTracks(playlist_id, cookie)
    return create_json_response(data)

@router.get("/logout")
async def logout():
    """7. 退出登录"""
    result = login_handler.Logout()  # type: ignore
    return create_json_response(result)

@router.post("/login/sms/send")
async def send_sms_code(phone: str):
    """8. 发送短信验证码"""
    try:
        result = login_handler.sendSMS(phone)  # type: ignore
        return create_json_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login/sms/verify")
async def verify_sms_login(phone: str, captcha: str):
    """9. 短信验证码登录"""
    try:
        result = login_handler.verifySMS(phone, captcha)  # type: ignore
        if result.get("code") == 200:
            cookie = result.get("cookie")
            if cookie:
                save_cookie(cookie)
                # 立即刷新缓存，确保所有线程同步
                from ncm.utils.cookie import CookieManager
                CookieManager.refresh_cache()
                print(f"✅ 用户通过短信登录成功，Cookie 已同步")
                return create_json_response({"code": 200, "message": "登录成功", "cookie": cookie})
        return create_json_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login/password")
async def phone_password_login(phone: str, password: str):
    """10. 手机号密码登录"""
    try:
        result = login_handler.PhonePasswordLogin(phone, password)  # type: ignore
        if result.get("code") == 200:
            cookie = result.get("cookie")
            if cookie:
                save_cookie(cookie)
                # 立即刷新缓存，确保所有线程同步
                from ncm.utils.cookie import CookieManager
                CookieManager.refresh_cache()
                print(f"✅ 用户通过密码登录成功，Cookie 已同步")
                return create_json_response({"code": 200, "message": "登录成功", "cookie": cookie})
        return create_json_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cookie/import")
async def import_cookie(cookie: str):
    """11. 手动导入 Cookie"""
    try:
        if not cookie or len(cookie) < 10:
            raise HTTPException(status_code=400, detail="Cookie 格式不正确")
        
        save_cookie(cookie)
        # 立即刷新缓存，确保所有线程同步
        from ncm.utils.cookie import CookieManager
        CookieManager.refresh_cache()
        print(f"✅ Cookie 已导入并同步到所有线程")
        return create_json_response({"code": 200, "message": "Cookie 导入成功"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cookie/refresh")
async def refresh_cookie():
    """12. 刷新 Cookie 缓存"""
    try:
        from ncm.utils.cookie import CookieManager
        cookie = CookieManager.refresh_cache()
        if cookie:
            return create_json_response({"code": 200, "message": "Cookie 刷新成功", "cookie": cookie})
        else:
            return create_json_response({"code": 404, "message": "未找到 Cookie"}, 404)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/play")
async def play_song_redirect(
    id: Optional[str] = None, 
    keywords: Optional[str] = None,
    level: str = "standard", 
    unblock: bool = False
):
    """8. VRChat 播放专用 (支持 ID 或 关键词搜索) - 重定向模式"""
    if not id and not keywords:
        raise HTTPException(status_code=400, detail="必须提供 id 或 keywords 参数")

    song_id = id

    # 如果提供了 keywords 且没有提供 id (或者 id 不是数字)，则进行搜索
    if keywords and (not song_id or not song_id.isdigit()):
        print(f"🔍 收到搜索请求: {keywords}")
        search_result = UserInteractive.searchSong(keywords, limit=1)
        
        if not search_result or search_result.get("code") != 200:
            raise HTTPException(status_code=404, detail="搜索失败")
            
        songs = search_result.get("result", {}).get("songs", [])
        if not songs:
            raise HTTPException(status_code=404, detail="未找到相关歌曲")
            
        first_song = songs[0]
        song_id = first_song.get("id")
        song_name = first_song.get("name")
        artist_name = first_song.get("ar", [{}])[0].get("name", "未知歌手")
        print(f"✅ 搜索匹配: {song_name} - {artist_name} (ID: {song_id})")
    
    # 确保 song_id 是整数
    try:
        song_id = int(song_id)  # type: ignore
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="无效的歌曲 ID")

    cookie = load_cookie()
    result = UserInteractive.getDownloadUrl(song_id, level, unblock, cookie)
    if result["success"] and result.get("url"):
        # 使用 status_code=307 保持请求方法不变，且不设置 body
        return RedirectResponse(url=result["url"], status_code=307)
    else:
        raise HTTPException(status_code=404, detail="无法获取歌曲链接")

@router.get("/play/direct")
async def play_song_direct(
    id: Optional[str] = None, 
    keywords: Optional[str] = None,
    level: str = "standard", 
    unblock: bool = False
):
    """
    8B. VRChat 播放专用 - 直接返回 MP3 URL (JSON格式)
    
    专为 VRChat 设计，因为 VRChat 不支持 HTTP 重定向
    
    参数:
        id: 歌曲 ID
        keywords: 搜索关键词（如果未提供ID）
        level: 音质等级 (standard/higher/exhigh/lossless)
        unblock: 是否尝试解锁
    
    返回示例:
        {
            "code": 200,
            "success": true,
            "url": "http://m801.music.126.net/...",
            "song_id": 1969519579,
            "song_name": "歌曲名",
            "artist": "歌手名"
        }
    """
    if not id and not keywords:
        raise HTTPException(status_code=400, detail="必须提供 id 或 keywords 参数")

    song_id = id
    song_info = {}

    # 如果提供了 keywords 且没有提供 id (或者 id 不是数字)，则进行搜索
    if keywords and (not song_id or not song_id.isdigit()):
        print(f"🔍 [Direct] 收到搜索请求: {keywords}")
        search_result = UserInteractive.searchSong(keywords, limit=1)
        
        if not search_result or search_result.get("code") != 200:
            return create_json_response({
                "code": 404,
                "success": False,
                "message": "搜索失败"
            }, 404)
            
        songs = search_result.get("result", {}).get("songs", [])
        if not songs:
            return create_json_response({
                "code": 404,
                "success": False,
                "message": "未找到相关歌曲"
            }, 404)
            
        first_song = songs[0]
        song_id = first_song.get("id")
        song_info["song_name"] = first_song.get("name", "")
        song_info["artist"] = first_song.get("ar", [{}])[0].get("name", "未知歌手")
        print(f"✅ [Direct] 搜索匹配: {song_info['song_name']} - {song_info['artist']} (ID: {song_id})")
    
    # 确保 song_id 是整数
    try:
        song_id = int(song_id)  # type: ignore
    except (ValueError, TypeError):
        return create_json_response({
            "code": 400,
            "success": False,
            "message": "无效的歌曲 ID"
        }, 400)

    # 获取下载链接
    cookie = load_cookie()
    result = UserInteractive.getDownloadUrl(song_id, level, unblock, cookie)
    
    if result["success"] and result.get("url"):
        # 如果搜索时没有获取歌曲信息，则通过 song detail API 获取
        if not song_info:
            try:
                detail_result = UserInteractive.getSongDetail(str(song_id))
                if detail_result and detail_result.get("code") == 200:
                    songs = detail_result.get("songs", [])
                    if songs:
                        song = songs[0]
                        song_info["song_name"] = song.get("name", "")
                        song_info["artist"] = song.get("ar", [{}])[0].get("name", "未知歌手")
            except Exception as e:
                print(f"⚠️ 获取歌曲详情失败: {e}")
        
        response_data = {
            "code": 200,
            "success": True,
            "url": result["url"],
            "song_id": song_id,
            "level": level
        }
        
        # 添加歌曲信息（如果有）
        if song_info:
            response_data.update(song_info)
        
        print(f"✅ [Direct] 返回直链 URL for ID: {song_id}")
        return create_json_response(response_data)
    else:
        return create_json_response({
            "code": 404,
            "success": False,
            "message": "无法获取歌曲链接",
            "song_id": song_id
        }, 404)

@router.get("/stream")
async def stream_audio_proxy(
    id: Optional[str] = None,
    keywords: Optional[str] = None,
    level: str = "standard",
    unblock: bool = False
):
    """
    音频流代理端点 - 专为 VRChat 设计
    
    解决 VRChat 无法访问某些音频域名的问题
    通过服务器流式传输音频数据
    
    使用方式:
        http://206601.xyz:7997/stream?id=歌曲ID
        http://206601.xyz:7997/stream?keywords=歌曲名
    """
    if not id and not keywords:
        raise HTTPException(status_code=400, detail="必须提供 id 或 keywords 参数")

    song_id = id

    # 关键词搜索
    if keywords and (not song_id or not song_id.isdigit()):
        print(f"🔍 [Stream] 收到搜索请求: {keywords}")
        search_result = UserInteractive.searchSong(keywords, limit=1)
        
        if not search_result or search_result.get("code") != 200:
            raise HTTPException(status_code=404, detail="搜索失败")
            
        songs = search_result.get("result", {}).get("songs", [])
        if not songs:
            raise HTTPException(status_code=404, detail="未找到相关歌曲")
            
        first_song = songs[0]
        song_id = first_song.get("id")
        song_name = first_song.get("name")
        artist_name = first_song.get("ar", [{}])[0].get("name", "未知歌手")
        print(f"✅ [Stream] 搜索匹配: {song_name} - {artist_name} (ID: {song_id})")
    
    # 确保 song_id 是整数
    try:
        song_id = int(song_id)  # type: ignore
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="无效的歌曲 ID")

    # 获取真实的音频 URL
    cookie = load_cookie()
    result = UserInteractive.getDownloadUrl(song_id, level, unblock, cookie)
    
    if not result["success"] or not result.get("url"):
        raise HTTPException(status_code=404, detail="无法获取歌曲链接")
    
    real_audio_url = result["url"]
    print(f"🎵 [Stream Proxy] 开始代理音频: ID={song_id}, URL={real_audio_url[:100]}...")
    
    try:
        # 发起请求获取音频流
        audio_response = requests.get(real_audio_url, stream=True, timeout=10)
        
        if audio_response.status_code != 200:
            raise HTTPException(
                status_code=audio_response.status_code, 
                detail=f"无法获取音频流: HTTP {audio_response.status_code}"
            )
        
        # 获取 Content-Type 和 Content-Length
        content_type = audio_response.headers.get("Content-Type", "audio/mpeg")
        content_length = audio_response.headers.get("Content-Length")
        
        # 创建流式响应
        def audio_stream():
            try:
                for chunk in audio_response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            except Exception as e:
                print(f"❌ [Stream Proxy] 流式传输错误: {e}")
        
        headers = {
            "Content-Type": content_type,
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
        }
        
        if content_length:
            headers["Content-Length"] = content_length
        
        print(f"✅ [Stream Proxy] 开始流式传输 (Content-Type: {content_type})")
        
        return StreamingResponse(
            audio_stream(),
            media_type=content_type,
            headers=headers
        )
        
    except requests.RequestException as e:
        print(f"❌ [Stream Proxy] 请求失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取音频流失败: {str(e)}")
    except Exception as e:
        print(f"❌ [Stream Proxy] 未知错误: {e}")
        raise HTTPException(status_code=500, detail=f"代理错误: {str(e)}")


# === 核心：IP 会话缓存 ===
# 格式: { "1.2.3.4": {"id": 123456, "time": 1700000000} }
# ... (前面的代码保持不变) ...

# ==========================================
# 🔧 核心工具：IP 会话管理
# ==========================================

# 格式: { "114.5.1.4": {"id": 123456, "time": 1700000000} }
ip_session_cache = {}

def get_real_ip(request: Request) -> str:
    """统一的 IP 提取逻辑，优先识别 Cloudflare"""
    headers = request.headers
    if "cf-connecting-ip" in headers:
        return headers["cf-connecting-ip"]
    if "x-forwarded-for" in headers:
        return headers["x-forwarded-for"].split(",")[0].strip()
    return request.client.host  # type: ignore

def get_song_id_by_ip(request: Request):
    """读取阶段：根据 IP 查 SongID (仅用于封面接口)"""
    client_ip = get_real_ip(request)
    session = ip_session_cache.get(client_ip)
    if session:
        # 10 分钟有效期
        if time.time() - session["time"] > 600:
            return None
        return session["id"]
    return None

# ==========================================
# 接口 1: VRChat 主入口 (处理音频 + 歌词 + B站视频)
# ==========================================
@router.get("/play/vrc")
async def play_vrc_main(
    request: Request,
    background_tasks: BackgroundTasks, 
    id: Optional[str] = None,
    keywords: Optional[str] = None,
    level: str = "standard",
    unblock: bool = False,
    user: Optional[str] = None,
    bvid: Optional[str] = None,  # B站视频BV号（兼容旧参数）
    qn: int = 64  # B站视频清晰度
):
    """
    VRChat 主入口 - 支持网易云音乐和B站视频
    
    智能参数识别：
    - id 为纯数字 -> 网易云音乐播放
    - id 以 BV 开头（不区分大小写）-> B站视频播放
    - bvid 参数（兼容旧接口）-> B站视频播放
    - keywords -> 网易云音乐搜索播放
    """
    
    # ==========================================
    # 🎯 智能识别 id 参数类型
    # ==========================================
    detected_bvid = None
    
    # 1. 优先检查 bvid 参数（兼容旧接口）
    if bvid is not None and bvid.strip():
        detected_bvid = bvid.strip()
        print(f"🎬 [智能识别] 检测到 bvid 参数: {detected_bvid}")
    
    # 2. 检查 id 参数，判断是 BV 号还是歌曲 ID
    elif id is not None and id.strip():
        id_stripped = id.strip()
        # 检查是否以 BV 开头（不区分大小写）
        if id_stripped.upper().startswith('BV'):
            detected_bvid = id_stripped
            print(f"🎬 [智能识别] id 参数识别为 B站视频: {detected_bvid}")
        else:
            # 不是 BV 开头，保持原样，后续作为歌曲 ID 处理
            print(f"🎵 [智能识别] id 参数识别为网易云歌曲: {id_stripped}")
    
    # ==========================================
    # 🎬 分支 0: B站视频播放
    # ==========================================
    if detected_bvid:
        try:
            if bili_video_handler is None:
                raise HTTPException(status_code=500, detail="B站视频处理器未初始化")
            
            # 加载已保存的cookies（如果有）
            cookie_dict = BiliCookieManager.load_cookie()
            cookies = None
            if cookie_dict:
                cookies = BiliCookieManager.dict_to_cookiejar(cookie_dict)
            
            # 获取视频播放URL
            video_url = bili_video_handler.getPlayUrl(detected_bvid, qn, cookies)
            
            print(f"✅ [B站视频] 重定向到视频流: {detected_bvid} (qn={qn})")
            
            # 重定向到视频流URL
            return RedirectResponse(url=video_url, status_code=302)
            
        except ValueError as e:
            # 参数错误或视频不存在
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            print(f"❌ 获取B站视频流失败: {e}")
            raise HTTPException(status_code=500, detail=f"获取视频流失败: {str(e)}")
    
    # ==========================================
    # 🎵 分支 1: 网易云音乐播放
    # ==========================================
    
    # 0. 如果 id 参数是URL，先提取出真实ID
    if id:
        id = extract_song_id_from_url(id)
    
    # 1. 优先处理 ID 绑定逻辑
    if user:
        if id:
            # 保存用户绑定的ID和MV参数
            user_id_bindings[user] = {"id": id, "mv": True}  # /play/vrc接口不支持mv参数，默认True
            print(f"💾 [用户绑定] 用户 '{user}' 绑定到 ID: {id}, MV: True")
        elif user in user_id_bindings and not id and not keywords:
            # 恢复用户绑定的ID（这里不需要恢复MV参数，因为/play/vrc不使用）
            binding = user_id_bindings[user]
            if isinstance(binding, dict):
                id = binding.get("id")
            else:
                # 兼容旧格式（只有ID的情况）
                id = binding
            print(f"🔗 [用户绑定] 用户 '{user}' 使用绑定的 ID: {id}")

    # 2. 解析目标 Song ID
    target_id = id 
    if keywords and (not target_id or not str(target_id).isdigit()):
        try:
            res = UserInteractive.searchSong(keywords, limit=1)
            songs = res.get("result", {}).get("songs", [])
            if songs: target_id = songs[0].get("id")
        except: pass

    if not target_id:
        raise HTTPException(status_code=400, detail="ID Missing")

    target_id = int(target_id)
    client_ip = get_real_ip(request)
    headers = request.headers
    user_agent = headers.get("user-agent", "").lower()
    range_header = headers.get("range") 

    is_player_request = range_header or any(ua in user_agent for ua in ["nsplayer", "wmfsdk", "lav", "altstream"])

    # ==========================================
    # 🎬 分支 A: 音频播放器请求 -> 直接重定向
    # ==========================================
    if is_player_request:
        cookie = load_cookie()
        audio_res = UserInteractive.getDownloadUrl(target_id, level, unblock, cookie)
        mp3_url = audio_res.get("url")
        
        if mp3_url:
            # 🛠️ 修复：删除了这里的 import time，直接使用全局的 time 模块
            separator = "&" if "?" in mp3_url else "?"
            # 添加 _t=时间戳，强制播放器认为这是一个新文件
            final_url = f"{mp3_url}{separator}_t={int(time.time())}"
            
            print(f"🔊 [Player] 播放请求: ID={target_id} -> 重定向音频 (已加防缓存戳)")
            return RedirectResponse(
                url=final_url, 
                status_code=302,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache"
                }
            )
        print(f"❌ [Player] 音频获取失败: ID={target_id}")
        raise HTTPException(404, "Audio URL Not Found")

    # ==========================================
    # 📝 分支 B: Udon 脚本请求 -> 返回 JSON 歌词
    # ==========================================
    # 记录 IP 和 ID 的对应关系，供封面接口使用
    # 这里直接使用全局的 time 模块，不会再报错了
    ip_session_cache[client_ip] = {
        "id": target_id,
        "time": time.time()
    }
    print(f"📝 [Udon] 脚本请求: ID={target_id} -> 更新 Session 并返回歌词")

    song_name = "未知歌曲"
    artist_name = "未知歌手"
    try:
        detail = UserInteractive.getSongDetail(str(target_id))
        if detail and detail.get("songs"):
            song = detail["songs"][0]
            song_name = song.get("name", "未知歌曲")
            artist_name = ", ".join([ar.get("name", "未知歌手") for ar in song.get("ar", [])])
    except: pass

    success, lrc_text, trans_lrc_text, error = fetch_lyrics_with_retry(target_id, max_retries=5, timeout=15)
    
    if not success:
        lrc_text = f"[00:00.00] 歌词加载失败 ID:{target_id}"
        trans_lrc_text = ""
    
    return JSONResponse(
        content={
            "songName": song_name,
            "artist": artist_name,
            "lyric": lrc_text,
            "transLyric": trans_lrc_text
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=86400"
        }
    )

# ==========================================
# 接口 2: 静态图片代理 (通过 IP 识别 ID)
# ==========================================
@router.get("/play/vrc/cover")
def play_vrc_cover_proxy(request: Request):
    """通过 IP 查找刚才 Udon 脚本注册的 ID，返回封面"""
    song_id = get_song_id_by_ip(request)
    
    if not song_id:
        print(f"🖼️ [Cover] Session 未命中, IP: {get_real_ip(request)}")
        return Response(status_code=404)

    try:
        detail = UserInteractive.getSongDetail(str(song_id))
        if not (detail and detail.get("songs")):
            return Response(status_code=404)
            
        cover_url = detail["songs"][0]["al"]["picUrl"]
        if cover_url:
            if "?" in cover_url: cover_url = cover_url.split("?")[0]
            cover_url += "?param=512y512" # 强制缩小提升加载速度
            
        img_resp = requests.get(cover_url, timeout=10)
        return Response(
            content=img_resp.content, 
            media_type=img_resp.headers.get("content-type", "image/jpeg"),
            headers={"Cache-Control": "no-cache, no-store"}
        )
    except Exception as e:
        print(f"❌ [Cover] 获取失败: {e}")
        return Response(status_code=500)

# ============================
# 调试接口：查看当前缓存
# ============================
@router.get("/debug/session")
def debug_session():
    return ip_session_cache


@router.get("/lyric")
async def get_lyric(id: int):
    """9. 获取歌词 (代理 lyrics.0061226.xyz) - 支持本地缓存"""
    # 1. 尝试从缓存获取
    cached_data = db.get_lyrics(id)
    if cached_data:
        print(f"💾 [Cache] 命中歌词缓存 ID: {id}")
        return cached_data

    # 使用重试机制获取完整歌词数据
    for attempt in range(3):  # 最多重试3次
        try:
            if attempt > 0:
                wait_time = min(2 ** attempt, 8)
                print(f"🔄 [歌词API] 重试第 {attempt + 1}/3 次，等待 {wait_time}秒... ID:{id}")
                time.sleep(wait_time)
            
            print(f"🎵 [歌词API] 请求完整歌词数据 ID:{id} (尝试 {attempt + 1}/3, 超时:15s)")
            url = f"https://lyrics.0061226.xyz/api/lyric?id={id}"
            resp = requests.get(url, timeout=15)
            data = resp.json()
            
            # 增加判断逻辑
            if data.get("code") == 200:
                lyrics_data = data.get("data", {}).get("lyrics", {})
                yrc = lyrics_data.get("yrc")
                lrc = lyrics_data.get("lrc")
                tlyric = lyrics_data.get("tlyric")

                if yrc and yrc.get("lyric"):
                    print(f"✅ [歌词API] ID:{id} 包含逐字歌词 (YRC)")
                    # 尝试处理翻译匹配
                    if tlyric and tlyric.get("lyric"):
                        processed_lyrics = process_lyrics_matching(yrc["lyric"], tlyric["lyric"])
                        # 将处理后的歌词放入返回数据中，方便客户端直接使用
                        data["data"]["lyrics"]["processed"] = processed_lyrics
                        print(f"✅ [歌词API] 已合并翻译 ({len(processed_lyrics)} 行)")

                elif lrc and lrc.get("lyric"):
                    print(f"⚠️ [歌词API] ID:{id} 仅包含普通歌词 (LRC)")
                else:
                    print(f"❌ [歌词API] ID:{id} 未找到有效歌词")
                
                # 保存到缓存 (仅当获取成功时)
                db.save_lyrics(id, data)
                print(f"✅ [歌词API] 成功获取并缓存歌词 ID:{id} (尝试 {attempt + 1}/3)")
                return create_json_response(data)
            else:
                error_msg = f"API返回错误: code={data.get('code')}, msg={data.get('message', '未知错误')}"
                print(f"⚠️ [歌词API] {error_msg} ID:{id} (尝试 {attempt + 1}/3)")
                if attempt == 2:  # 最后一次重试失败
                    raise HTTPException(status_code=500, detail=error_msg)
                    
        except (requests.Timeout, requests.ConnectionError) as e:
            error_msg = f"网络超时: {str(e)}"
            print(f"⚠️ [歌词API] {error_msg} ID:{id} (尝试 {attempt + 1}/3)")
            if attempt == 2:  # 最后一次重试失败
                raise HTTPException(status_code=500, detail=f"歌词请求失败 (重试3次): {error_msg}")
        except requests.RequestException as e:
            error_msg = f"请求异常: {str(e)}"
            print(f"⚠️ [歌词API] {error_msg} ID:{id} (尝试 {attempt + 1}/3)")
            if attempt == 2:  # 最后一次重试失败
                raise HTTPException(status_code=500, detail=f"歌词请求失败 (重试3次): {error_msg}")
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            print(f"❌ [歌词API] {error_msg} ID:{id} (尝试 {attempt + 1}/3)")
            raise HTTPException(status_code=500, detail=error_msg)

@router.get("/search")
async def search_song(
    keywords: str,
    limit: int = 10,
    offset: int = 0
):
    """
    10. 搜索歌曲列表（返回JSON格式）
    
    根据关键词搜索歌曲，返回歌曲列表供用户选择
    
    参数:
        keywords: 搜索关键词（必填）
        limit: 返回结果数量限制，默认10
        offset: 分页偏移量，默认0
    """
    print(f"🔍 搜索歌曲列表: {keywords}")
    
    try:
        # 执行搜索
        result = retry_request(UserInteractive.searchSong, keywords, limit=limit, offset=offset, type=1)
        
        if not result or result.get("code") != 200:
            return create_json_response({
                "code": 404,
                "message": "搜索失败",
                "songs": []
            }, 404)
        
        songs = result.get("result", {}).get("songs", [])
        if not songs:
            return create_json_response({
                "code": 200,
                "message": "未找到相关歌曲",
                "songs": []
            })
        
        # 格式化歌曲列表
        formatted_songs = []
        for song in songs:
            formatted_songs.append({
                "id": song.get("id"),
                "name": song.get("name"),
                "artist": ", ".join([ar.get("name", "") for ar in song.get("ar", [])]),
                "album": song.get("al", {}).get("name", ""),
                "duration": song.get("dt", 0),
                "picUrl": song.get("al", {}).get("picUrl", ""),
                "mvId": song.get("mv", 0),
                "fee": song.get("fee", 0)
            })
        
        print(f"✅ 找到 {len(formatted_songs)} 首歌曲")
        return create_json_response({
            "code": 200,
            "message": "搜索成功",
            "songs": formatted_songs,
            "total": len(formatted_songs)
        })
        
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        return create_json_response({
            "code": 500,
            "message": f"搜索错误: {str(e)}",
            "songs": []
        }, 500)

@router.get("/vrcsearch")
async def vrc_search_song(
    keywords: str,
    level: str = "standard",
    simple: bool = False,
    use_gpu: bool = True,
    threads: int | None = None,
    gpu_device: str | None = None,
    mv: bool = True
):
    """
    10b. VRChat搜索快捷方式 - 搜索第一首歌曲并重定向到视频
    
    自动搜索关键词，获取第一首歌曲，重定向到 /video API
    
    参数:
        keywords: 搜索关键词（必填）
        level: 音质等级 (standard/higher/exhigh/lossless)
        simple: 是否使用简化模式（无字幕）
        use_gpu: 是否使用硬件加速
        threads: FFmpeg线程数
        gpu_device: GPU设备路径
        mv: 是否优先尝试MV
    """
    print(f"🔍 [VRCSearch] 搜索并重定向: {keywords}")
    
    try:
        # 执行搜索
        result = retry_request(UserInteractive.searchSong, keywords, limit=1, offset=0, type=1)
        
        if not result or result.get("code") != 200:
            raise HTTPException(status_code=404, detail="搜索失败")
        
        songs = result.get("result", {}).get("songs", [])
        if not songs:
            raise HTTPException(status_code=404, detail="未找到相关歌曲")
        
        # 获取第一首歌曲的ID
        first_song = songs[0]
        song_id = first_song.get("id")
        song_name = first_song.get("name")
        artist_name = first_song.get("ar", [{}])[0].get("name", "未知歌手")
        print(f"✅ [VRCSearch] 匹配: {song_name} - {artist_name} (ID: {song_id})")
        
        # 构建重定向URL
        from urllib.parse import urlencode
        params = {
            "id": song_id,
            "level": level,
            "mv": "1" if mv else "0",
            "use_gpu": "1" if use_gpu else "0",
        }
        
        if simple:
            params["simple"] = "1"
        if threads:
            params["threads"] = threads
        if gpu_device:
            params["gpu_device"] = gpu_device
        
        redirect_url = f"/video?{urlencode(params)}"
        print(f"🔗 [VRCSearch] 重定向到: {redirect_url}")
        
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [VRCSearch] 错误: {e}")
        raise HTTPException(status_code=500, detail=f"搜索错误: {str(e)}")

@router.get("/video/cache/clear")
async def clear_video_cache():
    """11. 清理视频缓存"""
    import shutil
    try:
        cache_dir = VideoGenerator.CACHE_DIR
        if os.path.exists(cache_dir):
            # 统计文件数量和大小
            file_count = len([f for f in os.listdir(cache_dir) if f.endswith('.mp4')])
            total_size = sum(os.path.getsize(os.path.join(cache_dir, f)) 
                           for f in os.listdir(cache_dir) if f.endswith('.mp4'))
            
            # 删除缓存目录
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir, exist_ok=True)
            
            return {
                "success": True,
                "message": f"已清理 {file_count} 个缓存文件，释放 {total_size / 1024 / 1024:.2f} MB 空间"
            }
        return {"success": True, "message": "缓存目录不存在"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/video/cache/info")
async def get_cache_info():
    """12. 获取缓存信息"""
    try:
        cache_dir = VideoGenerator.CACHE_DIR
        if not os.path.exists(cache_dir):
            return {"exists": False, "files": 0, "size_mb": 0}
        
        files = [f for f in os.listdir(cache_dir) if f.endswith('.mp4')]
        total_size = sum(os.path.getsize(os.path.join(cache_dir, f)) for f in files)
        
        return {
            "exists": True,
            "path": cache_dir,
            "files": len(files),
            "size_mb": round(total_size / 1024 / 1024, 2)
        }
    except Exception as e:
        return {"error": str(e)}

def cleanup_file(path: str):
    """后台任务：清理临时文件"""
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"🗑️ 已清理临时文件: {path}")
    except Exception as e:
        print(f"⚠️ 清理临时文件失败: {e}")

@router.get("/video")
async def generate_video_for_vrchat(
    background_tasks: BackgroundTasks,
    id: Optional[int] = None,
    keywords: Optional[str] = None,
    level: str = "standard",
    unblock: bool = False,
    simple: bool = False,
    use_gpu: bool = True,
    threads: Optional[int] = None,
    gpu_device: Optional[str] = None,
    mv: bool = True,
    user: Optional[str] = None,
    access_password: Optional[str] = Cookie(None),
    access_hash: Optional[str] = Query(None)
):
    """
    13. 生成MP4视频 (VRChat USharpVideo专用) - **需要访问密码**
    
    参数:
        id: 歌曲ID
        keywords: 搜索关键词（如果没有提供id）
        level: 音质等级 (standard/higher/exhigh/lossless)
        unblock: 是否开启解灰模式
        simple: 是否使用简化模式（无字幕，生成更快）
        use_gpu: 是否使用硬件加速（默认True，自动检测并降级）
        threads: 手动指定FFmpeg线程数，留空让FFmpeg自行分配
        gpu_device: Linux VAAPI 设备路径，例如 /dev/dri/renderD128
        mv: 是否优先尝试获取MV（默认True，设为False跳过MV检查）
        user: 用户标识（用于绑定最后播放的歌曲ID）
        access_password: 访问密码hash（通过Cookie传递）
        access_hash: 访问密码hash（通过URL参数传递，优先级高于Cookie）
        
    返回:
        MP4视频文件流或MV直链重定向
    """
    request_start_time = time.time()
    print(f"\n{'='*60}")
    print(f"🎬 [视频请求] ID={id}, keywords={keywords}, level={level}, mv={mv}, user={user}")
    
    # 验证访问密码或hash
    if not verify_access_password(access_password, access_hash):
        print(f"❌ [视频请求] 访问密码验证失败")
        raise HTTPException(status_code=403, detail="需要访问密码。请先在Web UI中登录，或在URL中提供access_hash参数。")
    
    # 处理用户绑定逻辑
    if user:
        if id:
            # 如果同时提供了 user 和 id，保存绑定关系（包括ID和MV参数）
            user_id_bindings[user] = {"id": id, "mv": mv}
            print(f"💾 [用户绑定] 用户 '{user}' 绑定到 ID: {id}, MV: {mv}")
        elif user in user_id_bindings:
            # 如果只提供了 user，使用之前绑定的 id 和 mv 参数
            binding = user_id_bindings[user]
            if isinstance(binding, dict):
                id = int(binding.get("id", 0))  # type: ignore
                # 只有在未明确指定mv参数时才使用绑定的值
                # 检查mv参数是否为默认值（True）且URL中没有明确指定
                saved_mv = binding.get("mv", True)
                mv = saved_mv  # 使用保存的MV参数
                print(f"🔗 [用户绑定] 用户 '{user}' 使用绑定的 ID: {id}, MV: {mv}")
            else:
                # 兼容旧格式（只有ID的情况）
                id = int(binding)  # type: ignore
                print(f"🔗 [用户绑定] 用户 '{user}' 使用绑定的 ID: {id} (旧格式，MV保持默认)")
    
    if not id and not keywords:
        print(f"❌ [视频请求] 缺少必要参数")
        raise HTTPException(status_code=400, detail="必须提供 id 或 keywords 参数")

    song_id = id

    # 如果提供了 keywords，进行搜索
    if keywords and not song_id:
        print(f"🔍 收到视频搜索请求: {keywords}")
        search_result = UserInteractive.searchSong(keywords, limit=1)
        
        if not search_result or search_result.get("code") != 200:
            raise HTTPException(status_code=404, detail="搜索失败")
            
        songs = search_result.get("result", {}).get("songs", [])
        if not songs:
            raise HTTPException(status_code=404, detail="未找到相关歌曲")
            
        first_song = songs[0]
        song_id = first_song.get("id")
        song_name = first_song.get("name")
        artist_name = first_song.get("ar", [{}])[0].get("name", "未知歌手")
        print(f"✅ 搜索匹配: {song_name} - {artist_name} (ID: {song_id})")
    
    try:
        song_id = int(song_id)  # type: ignore
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="无效的歌曲 ID")

    # 🎬 优先尝试获取 MV（除非明确指定 mv=0）
    if mv:
        try:
            song_detail = retry_request(
                UserInteractive.getSongDetail,
                str(song_id),
                max_retries=2  # 缓存命中时重试次数少一些
            )
            # print("DEBUG: ")
            # print(song_detail)
            mv_id = song_detail['songs'][0]['mv']  # type: ignore
            if mv_id == 0:
              print(f"⚠️ MV 不存在，降级使用音频生成视频")
            else:
              print(f"🎥 尝试获取 MV: 歌曲ID={mv_id}")
              mv_url_api = f"{API_BASE_URL}mv/url?id={mv_id}"
              # print(f"DEBUG: {mv_url_api}")
              mv_response = retry_request(
                  requests.get,
                  mv_url_api,
                  max_retries=2,  # MV 检查失败可快速降级，不需要太多重试
                  timeout=5
              )
              mv_data = mv_response.json()  # type: ignore
              # print("DEBUG: ")
              # print(mv_data)
              
              # 检查 MV 是否存在且有效
              if (mv_data.get("code") == 200 and 
                  mv_data.get("data") and 
                  mv_data["data"].get("url") and 
                  mv_data["data"].get("code") == 200):
                  
                  mv_url = mv_data["data"]["url"]
                  mv_size = mv_data["data"].get("size", 0)
                  mv_resolution = mv_data["data"].get("r", 0)
                  print(f"✅ 找到 MV！分辨率={mv_resolution}p, 大小={mv_size / 1024 / 1024:.2f}MB")
                  print(f"🔗 重定向到 MV: {mv_url[:100]}...")
                  
                  # 直接返回 MV 直链的重定向
                  return RedirectResponse(
                      url=mv_url,
                      status_code=302,
                      headers={
                          "Cache-Control": "public, max-age=3600"
                      }
                  )
              else:
                  mv_code = mv_data.get("data", {}).get("code") if mv_data.get("data") else None
                  print(f"⚠️ MV 不存在 (code={mv_code})，降级使用音频生成视频")
                  
        except Exception as e:
            print(f"⚠️ MV 获取失败: {e}，降级使用音频生成视频")
    else:
        print(f"⏭️ 跳过 MV 检查（mv=0），直接生成视频")

    # 🚀 优先检查缓存，避免不必要的上游请求
    print(f"🔍 检查缓存: 歌曲ID={song_id}, 音质={level}, 模式={'简单' if simple else '完整'}")
    cached_video = VideoGenerator._get_cached_video(song_id, level, with_lyrics=not simple)
    if cached_video and os.path.exists(cached_video):
        file_size = os.path.getsize(cached_video)
        print(f"⚡ 缓存命中！直接返回视频文件 ({file_size / 1024 / 1024:.2f} MB)")
        
        # 获取歌曲名用于文件名（快速获取，不影响性能）
        try:
            song_detail = retry_request(
                UserInteractive.getSongDetail,
                str(song_id),
                max_retries=2  # 缓存命中时重试次数少一些
            )
            if song_detail.get("code") == 200 and song_detail.get("songs"):  # type: ignore
                song_info = song_detail["songs"][0]  # type: ignore
                song_name = song_info.get("name", "未知歌曲")
                artist_name = song_info.get("ar", [{}])[0].get("name", "未知歌手")
            else:
                song_name = f"Song_{song_id}"
                artist_name = "Unknown"
        except:
            song_name = f"Song_{song_id}"
            artist_name = "Unknown"
        
        return FileResponse(
            cached_video,
            media_type="video/mp4",
            filename=f"{song_name} - {artist_name}.mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=86400"
            }
        )
    
    print(f"📥 缓存未命中，开始生成新视频...")
    
    try:
        thread_count = threads if threads and threads > 0 else None
        # 1. 获取音频链接（带重试）
        cookie = load_cookie()
        print(f"🎵 准备获取音频URL: song_id={song_id}, level={level}")
        audio_result = retry_request(
            UserInteractive.getDownloadUrl,
            song_id, level, unblock, cookie,
            max_retries=3
        )
        
        # 详细输出获取结果
        print(f"🎵 音频获取结果: success={audio_result.get('success')}, has_url={bool(audio_result.get('url'))}")  # type: ignore
        if audio_result.get("is_grey_unlocked"):  # type: ignore
            print(f"🔓 使用灰色歌曲解锁API获取到音源")
        
        if not audio_result["success"]:  # type: ignore
            error_msg = audio_result.get("error", "未知错误")  # type: ignore
            error_data = audio_result.get("data", {})  # type: ignore
            print(f"❌ 音频获取失败: {error_msg}")
            if error_data:
                print(f"📊 API返回数据: {error_data}")
            raise HTTPException(
                status_code=404, 
                detail=f"无法获取歌曲链接: {error_msg}"
            )
        
        if not audio_result.get("url"):  # type: ignore
            print(f"❌ 音频URL为空，完整结果: {audio_result}")
            raise HTTPException(
                status_code=404, 
                detail="无法获取歌曲链接: URL为空，可能是版权受限或歌曲不存在"
            )
        
        audio_url = audio_result["url"]  # type: ignore
        print(f"✅ 成功获取音频URL (song_id={song_id}): {audio_url[:100]}...")
        
        # 2. 获取歌曲详情（封面）- 带重试
        song_detail = retry_request(
            UserInteractive.getSongDetail,
            str(song_id),
            max_retries=3
        )
        if song_detail.get("code") != 200:  # type: ignore
            raise HTTPException(status_code=404, detail="无法获取歌曲详情")
        
        songs = song_detail.get("songs", [])  # type: ignore
        if not songs:
            raise HTTPException(status_code=404, detail="歌曲信息为空")
        
        song_info = songs[0]
        cover_url = song_info.get("al", {}).get("picUrl")
        song_name = song_info.get("name", "未知歌曲")
        artist_name = song_info.get("ar", [{}])[0].get("name", "未知歌手")
        
        if not cover_url:
            raise HTTPException(status_code=404, detail="无法获取封面图片")
        
        # 3. 如果是简化模式，直接生成无字幕视频 - 在线程池中异步执行
        if simple:
            print("⚡ 使用简化模式生成视频（无字幕）- 使用线程池")
            loop = asyncio.get_event_loop()
            try:
                # 添加超时保护（最多5分钟）
                video_path = await asyncio.wait_for(
                    loop.run_in_executor(
                        video_executor,
                        VideoGenerator.generate_video_simple,
                        audio_url,
                        cover_url,
                        None,
                        use_gpu,
                        thread_count,
                        gpu_device,
                        song_id,
                        level
                    ),
                    timeout=300.0  # 5分钟超时
                )
                print(f"✅ 简化模式视频生成完成: {video_path}")
            except asyncio.TimeoutError:
                print(f"⏱️ 简化模式视频生成超时（5分钟）")
                raise HTTPException(status_code=504, detail="视频生成超时")
            except Exception as e:
                print(f"❌ 简化模式视频生成失败: {type(e).__name__}: {e}")
                raise
            
            # 验证文件存在
            if not os.path.exists(video_path):
                print(f"❌ 视频文件不存在: {video_path}")
                raise HTTPException(status_code=500, detail="视频文件生成失败")
            
            file_size = os.path.getsize(video_path)
            print(f"📦 返回视频文件: {video_path} ({file_size / 1024 / 1024:.2f} MB)")
            
            # 视频已持久化存储，无需清理
            return FileResponse(
                video_path,
                media_type="video/mp4",
                filename=f"{song_name} - {artist_name}.mp4",
                headers={
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "public, max-age=86400"  # 缓存1天
                }
            )
        
        # 4. 获取歌词（带重试）
        lyric_url = f"https://lyrics.0061226.xyz/api/lyric?id={song_id}"
        print(f"🔍 请求歌词: {lyric_url}")
        lyric_response = retry_request(
            requests.get,
            lyric_url,
            max_retries=3,
            timeout=10
        )
        lyric_data = lyric_response.json()  # type: ignore
        print(f"📄 歌词API响应: code={lyric_data.get('code')}")
        
        if lyric_data.get("code") != 200:
            print(f"⚠️ 无法获取歌词 (code={lyric_data.get('code')})，使用简化模式 - 使用线程池")
            loop = asyncio.get_event_loop()
            try:
                video_path = await asyncio.wait_for(
                    loop.run_in_executor(
                        video_executor,
                        VideoGenerator.generate_video_simple,
                        audio_url,
                        cover_url,
                        None,
                        use_gpu,
                        thread_count,
                        gpu_device,
                        song_id,
                        level
                    ),
                    timeout=300.0
                )
                print(f"✅ 降级简化模式视频生成完成: {video_path}")
            except asyncio.TimeoutError:
                print(f"⏱️ 降级简化模式视频生成超时（5分钟）")
                raise HTTPException(status_code=504, detail="视频生成超时")
            except Exception as e:
                print(f"❌ 降级简化模式视频生成失败: {type(e).__name__}: {e}")
                raise
            
            if not os.path.exists(video_path):
                print(f"❌ 视频文件不存在: {video_path}")
                raise HTTPException(status_code=500, detail="视频文件生成失败")
            
            file_size = os.path.getsize(video_path)
            print(f"📦 返回视频文件: {video_path} ({file_size / 1024 / 1024:.2f} MB)")
            
            # 视频已持久化存储，无需清理
            return FileResponse(
                video_path,
                media_type="video/mp4",
                filename=f"{song_name} - {artist_name}.mp4",
                headers={
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "public, max-age=86400"  # 缓存1天
                }
            )
        
        lyrics_data = (lyric_data.get("data") or {}).get("lyrics") or {}
        lrc_obj = lyrics_data.get("lrc") or {}
        tlyric_obj = lyrics_data.get("tlyric") or {}
        lrc = lrc_obj.get("lyric") if isinstance(lrc_obj, dict) else None
        tlyric = tlyric_obj.get("lyric") if isinstance(tlyric_obj, dict) else None
        
        print(f"📝 歌词结构: lyrics_data类型={type(lyrics_data)}, lrc_obj类型={type(lrc_obj)}")
        print(f"📝 歌词数据: lrc={'存在' if lrc else '空'} ({len(lrc) if lrc else 0} 字符), tlyric={'存在' if tlyric else '空'} ({len(tlyric) if tlyric else 0} 字符)")
        
        if not lrc:
            print("⚠️ 歌词内容为空，使用简化模式 - 使用线程池")
            loop = asyncio.get_event_loop()
            try:
                video_path = await asyncio.wait_for(
                    loop.run_in_executor(
                        video_executor,
                        VideoGenerator.generate_video_simple,
                        audio_url,
                        cover_url,
                        None,
                        use_gpu,
                        thread_count,
                        gpu_device,
                        song_id,
                        level
                    ),
                    timeout=300.0
                )
                print(f"✅ 无歌词简化模式视频生成完成: {video_path}")
            except asyncio.TimeoutError:
                print(f"⏱️ 无歌词简化模式视频生成超时（5分钟）")
                raise HTTPException(status_code=504, detail="视频生成超时")
            except Exception as e:
                print(f"❌ 无歌词简化模式视频生成失败: {type(e).__name__}: {e}")
                raise
            
            if not os.path.exists(video_path):
                print(f"❌ 视频文件不存在: {video_path}")
                raise HTTPException(status_code=500, detail="视频文件生成失败")
            
            file_size = os.path.getsize(video_path)
            print(f"📦 返回视频文件: {video_path} ({file_size / 1024 / 1024:.2f} MB)")
            
            # 视频已持久化存储，无需清理
            return FileResponse(
                video_path,
                media_type="video/mp4",
                filename=f"{song_name} - {artist_name}.mp4",
                headers={
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "public, max-age=86400"  # 缓存1天
                }
            )
        
        # 5. 生成完整视频（带字幕）- 在线程池中异步执行
        print("🎬 生成完整视频（带字幕）- 使用线程池")
        loop = asyncio.get_event_loop()
        try:
            # 添加超时保护（最多10分钟，因为带字幕的视频生成更慢）
            video_path = await asyncio.wait_for(
                loop.run_in_executor(
                    video_executor,
                    VideoGenerator.generate_video,
                    audio_url,
                    cover_url,
                    lrc,
                    tlyric,
                    song_name,
                    artist_name,
                    use_gpu,
                    thread_count,
                    gpu_device,
                    song_id,
                    level
                ),
                timeout=600.0  # 10分钟超时
            )
            print(f"✅ 完整视频生成完成: {video_path}")
        except asyncio.TimeoutError:
            print(f"⏱️ 完整视频生成超时（10分钟）")
            raise HTTPException(status_code=504, detail="视频生成超时")
        except Exception as e:
            print(f"❌ 完整视频生成失败: {type(e).__name__}: {e}")
            raise
        
        # 6. 返回视频文件
        if not os.path.exists(video_path):
            print(f"❌ 视频文件不存在: {video_path}")
            raise HTTPException(status_code=500, detail="视频文件生成失败")
        
        file_size = os.path.getsize(video_path)
        print(f"📦 视频文件大小: {file_size / 1024 / 1024:.2f} MB")
        elapsed = time.time() - request_start_time
        print(f"✅ [视频请求] 处理完成，总耗时: {elapsed:.2f}秒")
        print(f"{'='*60}\n")
        
        # 视频已持久化存储，无需清理
        # 使用 FileResponse 直接返回文件
        return FileResponse(
            video_path,
            media_type="video/mp4",
            filename=f"{song_name} - {artist_name}.mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=86400"  # 缓存1天
            }
        )
        
    except HTTPException as he:
        elapsed = time.time() - request_start_time
        print(f"❌ [视频请求] HTTP异常: {he.detail} (耗时: {elapsed:.2f}秒)")
        print(f"{'='*60}\n")
        raise
    except asyncio.TimeoutError:
        elapsed = time.time() - request_start_time
        print(f"⏱️ [视频请求] 超时: 处理时间超过限制 (耗时: {elapsed:.2f}秒)")
        print(f"{'='*60}\n")
        raise HTTPException(status_code=504, detail="视频生成超时，请稍后重试")
    except Exception as e:
        elapsed = time.time() - request_start_time
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ [视频请求] 未知错误: {type(e).__name__}: {str(e)}")
        print(f"📍 错误堆栈:\n{error_trace}")
        print(f"⏱️ 耗时: {elapsed:.2f}秒")
        print(f"{'='*60}\n")
        raise HTTPException(status_code=500, detail=f"视频生成失败: {str(e)}")


@router.post("/api/user_binding")
async def set_user_binding(
    user: str = Query(..., description="用户标识"),
    song_id: int = Query(..., description="歌曲ID"),
    mv: bool = Query(True, description="是否优先使用MV"),
    access_password: str = Cookie(None),
    access_hash: str = Query(None)
):
    """
    设置用户绑定 - 仅保存绑定关系，不播放视频
    
    参数:
        user: 用户标识
        song_id: 歌曲ID
        mv: 是否优先使用MV（默认True）
        access_password: 访问密码hash（通过Cookie传递）
        access_hash: 访问密码hash（通过URL参数传递）
        
    返回:
        绑定状态信息
    """
    # 验证访问密码或hash
    if not verify_access_password(access_password, access_hash):
        print(f"❌ [用户绑定] 访问密码验证失败")
        raise HTTPException(status_code=403, detail="需要访问密码")
    
    # 保存绑定关系
    user_id_bindings[user] = {"id": song_id, "mv": mv}
    print(f"💾 [用户绑定API] 用户 '{user}' 绑定到歌曲ID: {song_id}, MV: {mv}")
    
    return {
        "code": 200,
        "message": "绑定成功",
        "data": {
            "user": user,
            "song_id": song_id,
            "mv": mv
        }
    }


@router.get("/api/user_binding")
async def get_user_binding(
    user: str = Query(..., description="用户标识"),
    access_password: str = Cookie(None),
    access_hash: str = Query(None)
):
    """
    获取用户绑定信息
    
    参数:
        user: 用户标识
        access_password: 访问密码hash（通过Cookie传递）
        access_hash: 访问密码hash（通过URL参数传递）
        
    返回:
        用户绑定的歌曲信息
    """
    # 验证访问密码或hash
    if not verify_access_password(access_password, access_hash):
        raise HTTPException(status_code=403, detail="需要访问密码")
    
    if user in user_id_bindings:
        binding = user_id_bindings[user]
        if isinstance(binding, dict):
            return {
                "code": 200,
                "data": {
                    "user": user,
                    "song_id": binding.get("id"),
                    "mv": binding.get("mv", True)
                }
            }
        else:
            # 兼容旧格式
            return {
                "code": 200,
                "data": {
                    "user": user,
                    "song_id": binding,
                    "mv": True
                }
            }
    else:
        return {
            "code": 404,
            "message": "未找到绑定记录"
        }


@router.delete("/api/user_binding")
async def delete_user_binding(
    user: str = Query(..., description="用户标识"),
    access_password: str = Cookie(None),
    access_hash: str = Query(None)
):
    """
    删除用户绑定
    
    参数:
        user: 用户标识
        access_password: 访问密码hash（通过Cookie传递）
        access_hash: 访问密码hash（通过URL参数传递）
        
    返回:
        删除结果
    """
    # 验证访问密码或hash
    if not verify_access_password(access_password, access_hash):
        raise HTTPException(status_code=403, detail="需要访问密码")
    
    if user in user_id_bindings:
        del user_id_bindings[user]
        print(f"🗑️ [用户绑定API] 用户 '{user}' 的绑定已删除")
        return {
            "code": 200,
            "message": "删除成功"
        }
    else:
        return {
            "code": 404,
            "message": "未找到绑定记录"
        }


# ==================== B站相关接口 ====================

@router.get("/bili/login/qr")
async def bili_get_qr():
    """
    获取B站登录二维码
    
    返回:
        {
            "code": 200,
            "qr_url": "二维码URL",
            "qr_key": "轮询用的key"
        }
    """
    try:
        if bili_login_handler is None:
            raise HTTPException(status_code=500, detail="B站登录处理器未初始化")
        
        qr_url, qr_key = bili_login_handler.getQRCode()
        
        # 生成base64二维码图片（可选）
        try:
            import qrcode
            from io import BytesIO
            qr = qrcode.QRCode(border=1)
            qr.add_data(qr_url)
            qr.make()
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return {
                "code": 200,
                "qr_url": qr_url,
                "qr_key": qr_key,
                "qr_img": f"data:image/png;base64,{img_base64}"
            }
        except ImportError:
            # 如果没有qrcode库，只返回URL
            return {
                "code": 200,
                "qr_url": qr_url,
                "qr_key": qr_key
            }
    except Exception as e:
        print(f"❌ 获取B站登录二维码失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bili/login/poll")
async def bili_poll_login(qr_key: str = Query(..., description="二维码key")):
    """
    轮询B站登录状态
    
    参数:
        qr_key: 二维码的key
        
    返回:
        {
            "code": 86101/86090/86038/0,
            "message": "状态描述"
        }
    """
    try:
        if bili_login_handler is None:
            raise HTTPException(status_code=500, detail="B站登录处理器未初始化")
        
        result = bili_login_handler.pollQRStatus(qr_key)
        
        # 如果登录成功，保存cookies
        if result['code'] == 0 and 'cookies' in result:
            BiliCookieManager.save_cookie(result['cookies'])
            # 不返回cookies给前端，保护隐私
            del result['cookies']
            print("✅ B站登录成功，Cookie已保存")
        
        return result
    except Exception as e:
        print(f"❌ 轮询B站登录状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bili/login/info")
async def bili_get_login_info():
    """
    获取当前B站登录信息
    
    返回:
        用户信息或未登录状态
    """
    try:
        cookie_dict = BiliCookieManager.load_cookie()
        if not cookie_dict:
            return {
                "code": 401,
                "logged_in": False,
                "message": "未登录"
            }
        
        if bili_login_handler is None:
            raise HTTPException(status_code=500, detail="B站登录处理器未初始化")
        
        # 将字典转换为 RequestsCookieJar
        cookies = BiliCookieManager.dict_to_cookiejar(cookie_dict)
        user_info = bili_login_handler.getLoginInfo(cookies)
        
        return {
            "code": 200,
            **user_info
        }
    except Exception as e:
        print(f"❌ 获取B站登录信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/bili/login")
async def bili_logout():
    """
    退出B站登录（清除本地Cookie）
    
    返回:
        操作结果
    """
    try:
        BiliCookieManager.clear_cookie()
        return {
            "code": 200,
            "message": "已退出登录"
        }
    except Exception as e:
        print(f"❌ 退出B站登录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
