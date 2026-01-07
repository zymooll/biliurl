import requests
import urllib.parse
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
                print(f"📡 正在请求: {current_level} (VIP={bool(current_cookie)}, Unblock={current_unblock})")
                # 改用 POST 请求，防止 Cookie 过长导致 URL 超出限制 (HTTP 502)
                resp = requests.post(url, data=params)
                return resp.json()
            
            def try_grey_song_api(song_id):
                """尝试使用灰色歌曲备用API获取音源"""
                try:
                    grey_api_url = f"{API_BASE_URL}song/url/match?id={song_id}"
                    print(f"🔓 检测到灰色歌曲，尝试使用备用API: {grey_api_url}")
                    resp = requests.get(grey_api_url, timeout=10)
                    data = resp.json()
                    
                    if data.get('code') == 200 and data.get('data'):
                        url = data['data'].get('url')
                        if url:
                            print(f"✅ 备用API成功获取音源: {url[:80]}...")
                            return {
                                "url": url,
                                "level": data['data'].get('type', 'unknown'),
                                "source": "grey_api"
                            }
                    print(f"⚠️ 备用API未返回有效音源")
                    return None
                except Exception as e:
                    print(f"⚠️ 备用API请求失败: {e}")
                    return None

            # 初始化变量，防止未赋值错误
            downloadUrl = None
            song_info = {}

            # 第一次尝试：使用当前设置
            data = fetch(level, unblock, cookie)
            
            if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                song_info = data['data'][0]
                downloadUrl = song_info.get('url')
                
                # 检查是否为灰色歌曲（无URL或状态异常）
                is_grey = False
                if not downloadUrl:
                    print("⚠️ 未获取到下载链接，可能是灰色歌曲")
                    is_grey = True
                # 检查是否为酷狗占位符
                elif "1325645003.mp3" in downloadUrl:
                    print("⚠️ 检测到 VIP 身份未生效或音源受限（返回了酷狗占位符）")
                    is_grey = True
                
                # 如果是灰色歌曲，尝试备用方案
                if is_grey:
                    # 方案1: 尝试备用灰色歌曲API
                    grey_result = try_grey_song_api(songID)
                    if grey_result and grey_result.get('url'):
                        return {
                            "success": True,
                            "level": grey_result.get('level', '未知'),
                            "url": grey_result['url'],
                            "raw": {"source": "grey_api"},
                            "is_grey_unlocked": True
                        }
                    
                    # 方案2: 尝试解灰模式
                    if not unblock:
                        print("🔄 正在尝试开启解灰模式重新获取...")
                        data = fetch(level, True, None) # 开启解灰，且不带 Cookie 避免干扰
                    else:
                        print("🔄 正在尝试强制切换咪咕音源...")
                        # 强制咪咕
                        params_migu = {"id": songID, "level": "standard", "unblock": "true", "source": "migu"}
                        data = requests.get(f"{API_BASE_URL}song/url/v1", params=params_migu).json()
                    
                    # 重新提取结果
                    if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                        song_info = data['data'][0]
                        downloadUrl = song_info.get('url')
                        
                        # 如果还是没有URL，最后再尝试一次备用API
                        if not downloadUrl:
                            grey_result = try_grey_song_api(songID)
                            if grey_result and grey_result.get('url'):
                                return {
                                    "success": True,
                                    "level": grey_result.get('level', '未知'),
                                    "url": grey_result['url'],
                                    "raw": {"source": "grey_api_fallback"},
                                    "is_grey_unlocked": True
                                }

            if not downloadUrl:
                # 最后尝试：直接使用备用API
                print("⚠️ 常规方式全部失败，最后尝试备用API...")
                grey_result = try_grey_song_api(songID)
                if grey_result and grey_result.get('url'):
                    return {
                        "success": True,
                        "level": grey_result.get('level', '未知'),
                        "url": grey_result['url'],
                        "raw": {"source": "grey_api_last_resort"},
                        "is_grey_unlocked": True
                    }
                
                print(f"❌ 所有方式均失败，无法获取歌曲 {songID} 的下载链接")
                print(f"📊 最后的API响应数据: {data}")
                return {
                    "success": False, 
                    "data": data,
                    "error": "所有获取方式均失败，包括备用灰色歌曲API"
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
            if not cookie:
                return None
            
            # 使用 POST 请求避免 URL 过长，同时保留完整 Cookie
            url = f"{API_BASE_URL}user/account"
            # 确保包含 os=pc
            if "os=pc" not in cookie.lower():
                cookie += "; os=pc"
            
            print(f"🔗 正在验证 Cookie: {url}")    
            # 添加超时和更好的错误处理
            response = requests.post(url, data={"cookie": cookie}, timeout=15, verify=False)
            
            if response.status_code != 200:
                print(f"⚠️ API 返回非 200 状态码: {response.status_code}")
                return None
                
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            print(f"❌ 获取用户信息网络错误: {type(e).__name__}: {e}")
            return None
        except Exception as e:
            print(f"❌ 获取用户信息失败: {type(e).__name__}: {e}")
            return None

    @staticmethod
    def searchSong(keywords, limit=30, offset=0, type=1):
        """搜索歌曲"""
        try:
            url = f"{API_BASE_URL}cloudsearch"
            params = {
                "keywords": keywords,
                "limit": limit,
                "offset": offset,
                "type": type
            }
            response = requests.get(url, params=params)
            data = response.json()
            return data
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
            return {"code": 500, "message": str(e)}

    @staticmethod
    def getSongDetail(ids):
        """获取歌曲详情"""
        try:
            url = f"{API_BASE_URL}song/detail"
            params = {
                "ids": ids
            }
            response = requests.get(url, params=params)
            data = response.json()
            return data
        except Exception as e:
            print(f"❌ 获取歌曲详情失败: {e}")
            return {"code": 500, "message": str(e)}

