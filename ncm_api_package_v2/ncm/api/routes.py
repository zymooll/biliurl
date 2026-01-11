from fastapi import APIRouter, HTTPException, Query, Response, BackgroundTasks, Cookie, Header, Form
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import requests
import os
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
from ncm.core.login import LoginProtocol
from ncm.core.music import UserInteractive
from ncm.core.lyrics import process_lyrics_matching
from ncm.core.video import VideoGenerator
from ncm.utils.cookie import load_cookie, save_cookie
from ncm.utils.database import db
from ncm.utils.access_password import AccessPasswordManager
from ncm.api.web_ui import get_web_ui_html, get_login_page_html, STATIC_DIR

router = APIRouter()
login_handler = None
API_BASE_URL = "http://localhost:3002/"

# 静态文件目录路径（用于挂载）
STATIC_FILES_DIR = STATIC_DIR

# 创建线程池用于CPU密集型任务（如FFmpeg）
# 默认使用CPU核心数，可以根据需要调整
import multiprocessing
MAX_WORKERS = multiprocessing.cpu_count()
video_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="VideoGen")
print(f"🚀 视频生成线程池已初始化: {MAX_WORKERS} 个工作线程")

def init_login_handler():
    global login_handler
    login_handler = LoginProtocol()

def retry_request(func, *args, max_retries=3, timeout=10, **kwargs):
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
    
    raise Exception(f"请求失败: {str(last_error)}")

def create_json_response(content, status_code=200):
    """创建 JSON 响应并移除 Content-Length 头，防止协议错误"""
    response = JSONResponse(content=content, status_code=status_code)
    # 移除 Content-Length，让底层自动计算（使用 del 而不是 pop）
    if "content-length" in response.headers:
        del response.headers["content-length"]
    return response

def verify_access_password(access_password: str = Cookie(None), access_hash: str = None) -> bool:
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
        key = login_handler.getQRKey()
        return create_json_response({"code": 200, "unikey": key})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/login/qr/create")
async def create_qr_code(key: str):
    """2. 根据 Key 生成二维码 (返回 base64)"""
    try:
        qrimg = login_handler.getQRCode(key)
        return create_json_response({"code": 200, "qrimg": qrimg})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/login/qr/check")
async def check_qr_status(key: str):
    """3. 检查扫码状态"""
    try:
        data = login_handler.checkQRStatus(key)
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
    unblock: bool = False
):
    simple: bool = False,
    use_gpu: bool = False,
    threads: int | None = None,
    gpu_device: str | None = None
    cookie = load_cookie()
    result = UserInteractive.getDownloadUrl(id, level, unblock, cookie)
    
    status_code = 200 if result["success"] else 400
    return create_json_response(result, status_code)

@router.get("/song/detail")
async def get_song_detail(ids: str):
    """获取歌曲详情 (包含封面等信息)"""
    data = UserInteractive.getSongDetail(ids)
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
    result = login_handler.Logout()
    return create_json_response(result)

@router.post("/login/sms/send")
async def send_sms_code(phone: str):
    """8. 发送短信验证码"""
    try:
        result = login_handler.sendSMS(phone)
        return create_json_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login/sms/verify")
async def verify_sms_login(phone: str, captcha: str):
    """9. 短信验证码登录"""
    try:
        result = login_handler.verifySMS(phone, captcha)
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
        result = login_handler.PhonePasswordLogin(phone, password)
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
    id: str = None, 
    keywords: str = None,
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
        song_id = int(song_id)
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
    id: str = None, 
    keywords: str = None,
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
        song_id = int(song_id)
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
    id: str = None,
    keywords: str = None,
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
        song_id = int(song_id)
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

@router.get("/lyric")
async def get_lyric(id: int):
    """9. 获取歌词 (代理 lyrics.0061226.xyz) - 支持本地缓存"""
    # 1. 尝试从缓存获取
    cached_data = db.get_lyrics(id)
    if cached_data:
        print(f"💾 [Cache] 命中歌词缓存 ID: {id}")
        return cached_data

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
            
            # 2. 保存到缓存 (仅当获取成功时)
            db.save_lyrics(id, data)
                
        return create_json_response(data)
    except Exception as e:
        print(f"❌ 获取歌词失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
    id: int = None,
    keywords: str = None,
    level: str = "standard",
    unblock: bool = False,
    simple: bool = False,
    use_gpu: bool = True,
    threads: int | None = None,
    gpu_device: str | None = None,
    mv: bool = True,
    access_password: str = Cookie(None),
    access_hash: str = Query(None)
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
        access_password: 访问密码hash（通过Cookie传递）
        access_hash: 访问密码hash（通过URL参数传递，优先级高于Cookie）
        
    返回:
        MP4视频文件流或MV直链重定向
    """
    request_start_time = time.time()
    print(f"\n{'='*60}")
    print(f"🎬 [视频请求] ID={id}, keywords={keywords}, level={level}, mv={mv}")
    
    # 验证访问密码或hash
    if not verify_access_password(access_password, access_hash):
        print(f"❌ [视频请求] 访问密码验证失败")
        raise HTTPException(status_code=403, detail="需要访问密码。请先在Web UI中登录，或在URL中提供access_hash参数。")
    
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
        song_id = int(song_id)
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
            mv_id = song_detail['songs'][0]['mv']
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
              mv_data = mv_response.json()
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
            if song_detail.get("code") == 200 and song_detail.get("songs"):
                song_info = song_detail["songs"][0]
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
        audio_result = retry_request(
            UserInteractive.getDownloadUrl,
            song_id, level, unblock, cookie,
            max_retries=3
        )
        
        # 详细输出获取结果
        print(f"🎵 音频获取结果: success={audio_result.get('success')}, has_url={bool(audio_result.get('url'))}")
        if audio_result.get("is_grey_unlocked"):
            print(f"🔓 使用灰色歌曲解锁API获取到音源")
        
        if not audio_result["success"]:
            error_msg = audio_result.get("error", "未知错误")
            error_data = audio_result.get("data", {})
            print(f"❌ 音频获取失败: {error_msg}")
            if error_data:
                print(f"📊 API返回数据: {error_data}")
            raise HTTPException(
                status_code=404, 
                detail=f"无法获取歌曲链接: {error_msg}"
            )
        
        if not audio_result.get("url"):
            print(f"❌ 音频URL为空，完整结果: {audio_result}")
            raise HTTPException(
                status_code=404, 
                detail="无法获取歌曲链接: URL为空，可能是版权受限或歌曲不存在"
            )
        
        audio_url = audio_result["url"]
        print(f"✅ 成功获取音频URL: {audio_url[:100]}...")
        
        # 2. 获取歌曲详情（封面）- 带重试
        song_detail = retry_request(
            UserInteractive.getSongDetail,
            str(song_id),
            max_retries=3
        )
        if song_detail.get("code") != 200:
            raise HTTPException(status_code=404, detail="无法获取歌曲详情")
        
        songs = song_detail.get("songs", [])
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
        lyric_data = lyric_response.json()
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
            c = tlyric_obj.get("lyric") if isinstance(tlyric_obj, dict) else None
        
        print(f"📝 歌词结构: lyrics_data类型={type(lyrics_data)}, lrc_obj类型={type(lrc_obj)}")
        print(f"📝 歌词数据: lrc={'存在' if lrc else '空'} ({len(lrc) if lrc else 0} 字符), tlyric={'存在' if tlyric else '空'} ({len(tlyric) if tlyric else 0} 字符)")
        
        if not lrc:
            print("⚠️ 歌词内容为空，使用简化模式 - 使用线程池")
            loop = asyncio.get_event_loop()
            video_path = await loop.run_in_executor(
                video_executor,
                VideoGenerator.generate_video_simple,
                audio_url,
                cover_url,
                None,
                use_gpu,
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
        print(f"{'='*60}\n
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
        )
        
        # 6. 返回视频文件
        if not os.path.exists(video_path):
            raise HTTPException(status_code=500, detail="视频文件生成失败")
        
        file_size = os.path.getsize(video_path)
        print(f"📦 视频文件大小: {file_size} bytes")
        
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
