from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, StreamingResponse
import requests
import os
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

def init_login_handler():
    global login_handler
    login_handler = LoginProtocol()

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
    level: str = "exhigh", 
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
    level: str = "exhigh", 
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

@router.get("/video")
async def generate_video_for_vrchat(
    id: int = None,
    keywords: str = None,
    level: str = "exhigh",
    unblock: bool = False,
    simple: bool = False,
    use_gpu: bool = False,
    threads: int | None = None,
    gpu_device: str | None = None
):
    """
    11. 生成MP4视频 (VRChat USharpVideo专用)
    
    参数:
        id: 歌曲ID
        keywords: 搜索关键词（如果没有提供id）
        level: 音质等级 (standard/higher/exhigh/lossless)
        unblock: 是否开启解灰模式
        simple: 是否使用简化模式（无字幕，生成更快）
        use_gpu: 是否尝试使用硬件编码 (macOS=videotoolbox, Linux默认vaapi，Win=nvenc)
        threads: 手动指定FFmpeg线程数，留空让FFmpeg自行分配
        gpu_device: Linux VAAPI 设备路径，例如 /dev/dri/renderD128
        
    返回:
        MP4视频文件流
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

    try:
        thread_count = threads if threads and threads > 0 else None
        # 1. 获取音频链接
        cookie = load_cookie()
        audio_result = UserInteractive.getDownloadUrl(song_id, level, unblock, cookie)
        if not audio_result["success"] or not audio_result.get("url"):
            raise HTTPException(status_code=404, detail="无法获取歌曲链接")
        
        audio_url = audio_result["url"]
        
        # 2. 获取歌曲详情（封面）
        song_detail = UserInteractive.getSongDetail(str(song_id))
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
            video_path = VideoGenerator.generate_video_simple(audio_url, cover_url, use_gpu=use_gpu, threads=thread_count, gpu_device=gpu_device)
            return FileResponse(
                video_path,
                media_type="video/mp4",
                filename=f"{song_name} - {artist_name}.mp4"
            )
        
        # 4. 获取歌词
        lyric_url = f"https://lyrics.0061226.xyz/api/lyric?id={song_id}"
        print(f"🔍 请求歌词: {lyric_url}")
        lyric_response = requests.get(lyric_url, timeout=10)
        lyric_data = lyric_response.json()
        print(f"📄 歌词API响应: code={lyric_data.get('code')}")
        
        if lyric_data.get("code") != 200:
            print(f"⚠️ 无法获取歌词 (code={lyric_data.get('code')})，使用简化模式")
            video_path = VideoGenerator.generate_video_simple(audio_url, cover_url, use_gpu=use_gpu, threads=thread_count, gpu_device=gpu_device)
            return FileResponse(
                video_path,
                media_type="video/mp4",
                filename=f"{song_name} - {artist_name}.mp4"
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
            video_path = VideoGenerator.generate_video_simple(audio_url, cover_url, use_gpu=use_gpu, threads=thread_count, gpu_device=gpu_device)
            return FileResponse(
                video_path,
                media_type="video/mp4",
                filename=f"{song_name} - {artist_name}.mp4"
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
            gpu_device=gpu_device
        )
        
        # 6. 返回视频文件
        # 确保文件完全写入
        if not os.path.exists(video_path):
            raise HTTPException(status_code=500, detail="视频文件生成失败")
        
        # 读取整个文件到内存（对于小文件），避免 Content-Length 问题
        with open(video_path, "rb") as f:
            video_data = f.read()
        
        print(f"📦 视频文件大小: {len(video_data)} bytes")
        
        # URL 编码文件名以支持中文
        encoded_filename = quote(f"{song_name} - {artist_name}.mp4")
        
        # 使用 Response 直接返回二进制数据
        # FastAPI 会自动处理 Content-Length
        from fastapi import Response
        return Response(
            content=video_data,
            media_type="video/mp4",
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 视频生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"视频生成失败: {str(e)}")
