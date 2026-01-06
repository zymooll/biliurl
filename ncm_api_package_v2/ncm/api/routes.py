from fastapi import APIRouter, HTTPException, Query, Response, BackgroundTasks
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
import requests
import os
import time
from pathlib import Path
from urllib.parse import quote
from ncm.core.login import LoginProtocol
from ncm.core.music import UserInteractive
from ncm.core.lyrics import process_lyrics_matching
from ncm.core.video import VideoGenerator
from ncm.utils.cookie import load_cookie, save_cookie
from ncm.utils.database import db

router = APIRouter()
login_handler = None
API_BASE_URL = "http://localhost:3002/"

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
    # 移除 Content-Length，让底层自动计算
    response.headers.pop("content-length", None)
    return response

@router.get("/")
async def root():
    return create_json_response({"message": "NCM API Service is running", "docs": "/docs"})

@router.get("/favicon.ico")
async def favicon():
    return JSONResponse(status_code=204, content="")

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

@router.get("/logout")
async def logout():
    """7. 退出登录"""
    result = login_handler.Logout()
    return create_json_response(result)

@router.get("/play")
async def play_song_redirect(
    id: str = None, 
    keywords: str = None,
    level: str = "standard", 
    unblock: bool = False
):
    """8. VRChat 播放专用 (支持 ID 或 关键词搜索)"""
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
    limit: int = 30,
    offset: int = 0,
    type: int = 1
):
    """10. 搜索歌曲"""
    result = UserInteractive.searchSong(keywords, limit, offset, type)
    return create_json_response(result)

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
    mv: bool = True
):
    """
    13. 生成MP4视频 (VRChat USharpVideo专用)
    
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
        
    返回:
        MP4视频文件流或MV直链重定向
    """
    if not id and not keywords:
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
            print(f"🎥 尝试获取 MV: 歌曲ID={song_id}")
            mv_url_api = f"{API_BASE_URL}mv/url?id={song_id}"
            print(f"DEBUG: {mv_url_api}")
            mv_response = retry_request(
                requests.get,
                mv_url_api,
                max_retries=2,  # MV 检查失败可快速降级，不需要太多重试
                timeout=5
            )
            mv_data = mv_response.json()
            print("DEBUG: ")
            print(mv_data)
            
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
        if not audio_result["success"] or not audio_result.get("url"):
            raise HTTPException(status_code=404, detail="无法获取歌曲链接")
        
        audio_url = audio_result["url"]
        
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
        
        # 3. 如果是简化模式，直接生成无字幕视频
        if simple:
            print("⚡ 使用简化模式生成视频（无字幕）")
            video_path = VideoGenerator.generate_video_simple(
                audio_url, cover_url, 
                use_gpu=use_gpu, threads=thread_count, gpu_device=gpu_device,
                song_id=song_id, level=level
            )
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
            print(f"⚠️ 无法获取歌词 (code={lyric_data.get('code')})，使用简化模式")
            video_path = VideoGenerator.generate_video_simple(
                audio_url, cover_url, 
                use_gpu=use_gpu, threads=thread_count, gpu_device=gpu_device,
                song_id=song_id, level=level
            )
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
            print("⚠️ 歌词内容为空，使用简化模式")
            video_path = VideoGenerator.generate_video_simple(
                audio_url, cover_url, 
                use_gpu=use_gpu, threads=thread_count, gpu_device=gpu_device,
                song_id=song_id, level=level
            )
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
        
        # 5. 生成完整视频（带字幕）
        print("🎬 生成完整视频（带字幕）")
        video_path = VideoGenerator.generate_video(
            audio_url=audio_url,
            cover_url=cover_url,
            lyrics_lrc=lrc,
            translation_lrc=tlyric,
            song_name=song_name,
            artist=artist_name,
            use_gpu=use_gpu,
            threads=thread_count,
            gpu_device=gpu_device,
            song_id=song_id,
            level=level
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
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 视频生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"视频生成失败: {str(e)}")
