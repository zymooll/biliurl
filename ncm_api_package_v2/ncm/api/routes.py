from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
import requests
from ncm.core.login import LoginProtocol
from ncm.core.music import UserInteractive
from ncm.core.lyrics import process_lyrics_matching
from ncm.utils.cookie import load_cookie, save_cookie
from ncm.utils.database import db

router = APIRouter()
login_handler = None

def init_login_handler():
    global login_handler
    login_handler = LoginProtocol()

@router.get("/")
async def root():
    return {"message": "NCM API Service is running", "docs": "/docs"}

@router.get("/favicon.ico")
async def favicon():
    return JSONResponse(status_code=204, content={})

@router.get("/login/qr/key")
async def get_qr_key():
    """1. 获取扫码登录所需的 Key"""
    try:
        key = login_handler.getQRKey()
        return {"code": 200, "unikey": key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/login/qr/create")
async def create_qr_code(key: str):
    """2. 根据 Key 生成二维码 (返回 base64)"""
    try:
        qrimg = login_handler.getQRCode(key)
        return {"code": 200, "qrimg": qrimg}
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
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/cookie")
async def get_current_cookie():
    """4. 查询当前保存的 Cookie"""
    cookie = load_cookie()
    if not cookie:
        return {"code": 404, "message": "未找到已保存的 Cookie"}
    return {"code": 200, "cookie": cookie}

@router.get("/user/info")
async def get_user_info():
    """5. 获取当前登录用户信息"""
    cookie = load_cookie()
    if not cookie:
        raise HTTPException(status_code=401, detail="未登录")
    data = UserInteractive.getUserAccount(cookie)
    return data

@router.get("/resolve")
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

@router.get("/logout")
async def logout():
    """7. 退出登录"""
    return login_handler.Logout()

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
                
        return data
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
    return result
