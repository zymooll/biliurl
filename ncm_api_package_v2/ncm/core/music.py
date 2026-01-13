import requests
import urllib.parse
import time
from ncm.config import API_BASE_URL
from ncm.utils.cookie import load_cookie, filter_cookie

class UserInteractive:
    """用户交互功能类"""
    
    @staticmethod
    def getDownloadUrl(songID, level="standard", unblock=False, cookie=None):
        """获取歌曲下载链接（支持灰色歌曲检测和备用API）"""
        try:
            if not cookie:
                cookie = load_cookie()
            
            # 内部函数：发起核心请求
            def fetch(current_level, current_unblock, current_cookie):
                params = {
                    "id": songID,
                    "level": current_level,
                    "unblock": "true" if current_unblock else "false",
                }
                if current_cookie:
                    c_str = current_cookie
                    if "os=pc" not in c_str.lower():
                        c_str += "; os=pc"
                    params["cookie"] = c_str
                
                if current_unblock:
                    params["source"] = "migu,qq"
                
                # 🛠️ 修复点 1: 在请求上游 API 时强制添加毫秒级时间戳，防止网易云服务端缓存
                ts = int(time.time() * 1000)
                url = f"{API_BASE_URL}song/url/v1?timestamp={ts}"
                
                print(
                    f"📡 [SongURL] 请求 | songID={songID} "
                    f"level={current_level} unblock={current_unblock} "
                    f"ts={ts}"
                )
                # 使用 POST 请求
                resp = requests.post(url, data=params)
                return resp.json()
            
            def try_grey_song_api(song_id):
                """尝试使用灰色歌曲备用API获取音源"""
                try:
                    # 备用 API 也加上时间戳
                    ts = int(time.time() * 1000)
                    grey_api_url = f"{API_BASE_URL}song/url/match?id={song_id}&timestamp={ts}"
                    print(f"🔓 检测到灰色/ID不匹配，尝试使用备用API: {grey_api_url}")
                    resp = requests.get(grey_api_url, timeout=60)
                    data = resp.json()
                    
                    if data.get('code') == 200:
                        url_data = data.get('data')
                        if isinstance(url_data, str) and url_data:
                            print(f"✅ 备用API成功获取音源: {url_data[:80]}...")
                            return {"url": url_data, "level": "grey_unlocked", "source": "grey_api"}
                        elif isinstance(url_data, dict):
                            url = url_data.get('url')
                            if url:
                                print(f"✅ 备用API成功获取音源: {url[:80]}...")
                                return {"url": url, "level": url_data.get('type', 'grey_unlocked'), "source": "grey_api"}
                    return None
                except Exception as e:
                    print(f"⚠️ 备用API请求失败: {e}")
                    return None

            downloadUrl = None
            song_info = {}

            # 第一次尝试：使用当前设置
            data = fetch(level, unblock, cookie)
            
            # 解析数据
            if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                song_info = data['data'][0]
                downloadUrl = song_info.get('url')
                api_song_id = song_info.get('id')

                # 🛠️ 修复点 2: 严格校验返回的 ID 是否与请求的 ID 一致
                # 如果网易云发神经返回了上一首的 ID，直接视为无效，强制走重试流程
                if str(api_song_id) != str(songID):
                    print(f"⚠️ [严重错误] ID不匹配! 请求:{songID} 实际返回:{api_song_id} -> 判定为脏读，丢弃结果。")
                    downloadUrl = None 
                else:
                    print(
                        f"📊 [SongURL] API响应正常 | req_id={songID} api_id={api_song_id} "
                        f"url={str(downloadUrl)[:80]}"
                    )

                # 检查是否为灰色歌曲或无效
                is_grey = False
                if not downloadUrl:
                    print("⚠️ 未获取到下载链接，可能是灰色歌曲或脏读")
                    is_grey = True
                elif "1325645003.mp3" in downloadUrl:
                    print("⚠️ 检测到酷狗占位符，视为灰色")
                    is_grey = True
                
                # 如果是灰色歌曲或脏读，尝试解灰/备用逻辑
                if is_grey:
                    if not unblock:
                        print("🔄 正在尝试开启解灰模式重新获取...")
                        data = fetch(level, True, None) 
                    else:
                        print("🔄 正在尝试强制切换咪咕音源...")
                        params_migu = {"id": songID, "level": "standard", "unblock": "true", "source": "migu"}
                        # 咪咕请求也加时间戳
                        migu_url = f"{API_BASE_URL}song/url/v1?timestamp={int(time.time() * 1000)}"
                        data = requests.get(migu_url, params=params_migu).json()
                    
                    # 重新提取并校验
                    if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                        song_info = data['data'][0]
                        downloadUrl = song_info.get('url')
                        # 再次校验 ID
                        if str(song_info.get('id')) != str(songID):
                             downloadUrl = None

            # 如果常规方式失败，最后尝试备用API
            if not downloadUrl:
                print("⚠️ 常规方式失败(或ID不匹配)，尝试使用备用API...")
                grey_result = try_grey_song_api(songID)
                if grey_result and grey_result.get('url'):
                    return {
                        "success": True,
                        "level": grey_result.get('level', '未知'),
                        "url": grey_result['url'],
                        "raw": {"source": "grey_api"},
                        "is_grey_unlocked": True
                    }
                
                print(f"❌ 所有方式均失败，无法获取歌曲 {songID}")
                return {
                    "success": False, 
                    "data": data,
                    "error": "获取失败或ID不匹配"
                }
            
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
            if not cookie: return None
            # 加上时间戳防缓存
            url = f"{API_BASE_URL}user/account?timestamp={int(time.time() * 1000)}"
            if "os=pc" not in cookie.lower(): cookie += "; os=pc"
            response = requests.post(url, data={"cookie": cookie}, timeout=15, verify=False)
            if response.status_code != 200: return None
            return response.json()
        except: return None

    @staticmethod
    def searchSong(keywords, limit=30, offset=0, type=1):
        """搜索歌曲"""
        try:
            url = f"{API_BASE_URL}cloudsearch"
            params = {
                "keywords": keywords,
                "limit": limit,
                "offset": offset,
                "type": type,
                "timestamp": int(time.time() * 1000) # 加时间戳
            }
            response = requests.get(url, params=params)
            return response.json()
        except Exception as e:
            return {"code": 500, "message": str(e)}

    @staticmethod
    def getSongDetail(ids):
        """获取歌曲详情"""
        try:
            url = f"{API_BASE_URL}song/detail"
            params = {
                "ids": ids,
                "timestamp": int(time.time() * 1000) # 加时间戳
            }
            response = requests.get(url, params=params)
            return response.json()
        except Exception as e:
            return {"code": 500, "message": str(e)}
    
    @staticmethod
    def getPlaylistDetail(playlist_id, cookie=None):
        try:
            if not cookie: cookie = load_cookie()
            url = f"{API_BASE_URL}playlist/detail"
            params = {"id": playlist_id, "timestamp": int(time.time() * 1000)}
            if cookie: params["cookie"] = cookie
            response = requests.get(url, params=params, timeout=30)
            return response.json()
        except Exception as e:
            return {"code": 500, "message": str(e)}
    
    @staticmethod
    def getPlaylistTracks(playlist_id, cookie=None):
        try:
            # 复用 getPlaylistDetail
            playlist_data = UserInteractive.getPlaylistDetail(playlist_id, cookie)
            if playlist_data.get('code') != 200: return playlist_data
            
            playlist = playlist_data.get('playlist', {})
            track_ids = [item.get('id') for item in playlist.get('trackIds', [])]
            
            if not track_ids:
                return {"code": 200, "songs": [], "total": 0}
            
            # 批量获取详情
            batch_size = 1000
            all_songs = []
            for i in range(0, len(track_ids), batch_size):
                batch_ids = track_ids[i:i+batch_size]
                ids_str = ','.join(map(str, batch_ids))
                url = f"{API_BASE_URL}song/detail"
                params = {"ids": ids_str, "timestamp": int(time.time() * 1000)}
                if cookie: params["cookie"] = cookie
                
                resp = requests.get(url, params=params, timeout=30)
                batch_data = resp.json()
                if batch_data.get('code') == 200:
                    all_songs.extend(batch_data.get('songs', []))
            
            return {
                "code": 200,
                "playlist_info": {
                    "id": playlist.get('id'),
                    "name": playlist.get('name'),
                    "coverImgUrl": playlist.get('coverImgUrl'),
                    "trackCount": playlist.get('trackCount'),
                },
                "songs": all_songs,
                "total": len(all_songs)
            }
        except Exception as e:
            return {"code": 500, "message": str(e)}