import requests
import time
import os
import threading
from typing import Optional, Dict, Tuple

class BiliLogin:
    """B站登录协议实现"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Origin': 'https://www.bilibili.com',
            'Referer': 'https://www.bilibili.com'
        }
        self._lock = threading.RLock()
        
    def getQRCode(self) -> Tuple[str, str]:
        """
        获取登录二维码信息
        
        返回:
            (qr_url, qr_key) 二维码URL和key的元组
        """
        try:
            response = requests.get(
                'https://passport.bilibili.com/x/passport-login/web/qrcode/generate',
                headers=self.headers,
                timeout=10
            )
            data = response.json()
            
            if data.get('code') == 0:
                qr_url = data['data']['url']
                qr_key = data['data']['qrcode_key']
                print(f"✅ 二维码获取成功")
                return qr_url, qr_key
            else:
                raise ValueError(f"获取二维码失败: {data.get('message', '未知错误')}")
        except Exception as e:
            print(f"❌ 获取二维码失败: {e}")
            raise
    
    def pollQRStatus(self, qr_key: str) -> Dict:
        """
        轮询二维码扫描状态
        
        参数:
            qr_key: 二维码的key
            
        返回:
            包含状态码和cookies的字典
            {
                'code': 86101/86090/86038/0,
                'message': '状态描述',
                'cookies': requests.cookies.RequestsCookieJar (仅当code=0时)
            }
        """
        try:
            response = requests.get(
                f'https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={qr_key}',
                headers=self.headers,
                timeout=10
            )
            data = response.json()
            code = data['data']['code']
            
            status_map = {
                86101: '等待扫码',
                86090: '已扫码，等待确认',
                86038: '二维码已失效',
                0: '登录成功'
            }
            
            result = {
                'code': code,
                'message': status_map.get(code, '未知状态')
            }
            
            if code == 0:
                # 登录成功，返回cookies
                result['cookies'] = response.cookies
                print(f"✅ 登录成功")
            else:
                print(f"⏳ {result['message']}")
            
            return result
            
        except Exception as e:
            print(f"❌ 查询登录状态失败: {e}")
            raise
    
    def getLoginInfo(self, cookies) -> Dict:
        """
        获取当前登录用户信息
        
        参数:
            cookies: 登录后的cookies
            
        返回:
            包含用户信息的字典
        """
        try:
            response = requests.get(
                'https://api.bilibili.com/x/web-interface/nav',
                headers=self.headers,
                cookies=cookies,
                timeout=10
            )
            data = response.json()
            
            if data.get('code') == 0:
                user_data = data['data']
                return {
                    'logged_in': user_data['isLogin'],
                    'mid': user_data.get('mid', 0),
                    'uname': user_data.get('uname', ''),
                    'face': user_data.get('face', ''),
                    'vip_status': user_data.get('vipStatus', 0),
                    'level': user_data.get('level_info', {}).get('current_level', 0)
                }
            else:
                return {'logged_in': False, 'message': '未登录'}
        except Exception as e:
            print(f"❌ 获取用户信息失败: {e}")
            return {'logged_in': False, 'error': str(e)}


class BiliVideo:
    """B站视频流获取"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Origin': 'https://www.bilibili.com',
            'Referer': 'https://www.bilibili.com'
        }
    
    def getCid(self, bvid: str, cookies=None) -> str:
        """
        获取视频的cid
        
        参数:
            bvid: 视频的BV号
            cookies: 可选的cookies（用于访问会员视频）
            
        返回:
            视频的cid字符串
        """
        try:
            response = requests.get(
                f'https://api.bilibili.com/x/player/pagelist?bvid={bvid}',
                headers=self.headers,
                cookies=cookies,
                timeout=10
            )
            data = response.json()
            
            if data.get('code') == 0 and data['data']:
                cid = str(data['data'][0]['cid'])
                print(f"✅ 获取cid成功: {cid}")
                return cid
            else:
                raise ValueError(f"获取cid失败: {data.get('message', '未知错误')}")
        except Exception as e:
            print(f"❌ 获取cid失败: {e}")
            raise
    
    def getVideoStream(self, bvid: str, cid: str, qn: int = 64, cookies=None) -> Dict:
        """
        获取视频流地址
        
        参数:
            bvid: 视频的BV号
            cid: 视频的cid
            qn: 清晰度 (16=360P, 32=480P, 64=720P, 80=1080P, 112=1080P+, 116=1080P60)
            cookies: 可选的cookies（用于访问会员视频或更高清晰度）
            
        返回:
            包含视频流信息的字典
            {
                'format': 'mp4'/'dash',
                'quality': 64,
                'url': 'xxx' (仅MP4格式),
                'dash': {...} (仅DASH格式)
            }
        """
        try:
            # 优先使用MP4格式 (fnval=1)，便于直接重定向播放
            params = {
                'bvid': bvid,
                'cid': cid,
                'qn': qn,
                'fnval': 1,  # MP4格式
                'fnver': 0,
                'fourk': 1,
                'from_client': 'BROWSER'
            }
            
            response = requests.get(
                'https://api.bilibili.com/x/player/wbi/playurl',
                params=params,
                headers=self.headers,
                cookies=cookies,
                timeout=15
            )
            data = response.json()
            
            if data.get('code') == 0:
                video_data = data['data']
                result = {
                    'quality': video_data.get('quality', qn),
                    'format': video_data.get('format', 'mp4'),
                    'timelength': video_data.get('timelength', 0),
                    'accept_quality': video_data.get('accept_quality', []),
                    'accept_description': video_data.get('accept_description', [])
                }
                
                # MP4格式 - 直接返回URL
                if 'durl' in video_data and video_data['durl']:
                    url = video_data['durl'][0]['url']
                    backup_urls = video_data['durl'][0].get('backup_url', [])
                    result['url'] = url
                    result['backup_urls'] = backup_urls
                    print(f"✅ 获取MP4视频流成功: {url[:100]}...")
                
                # DASH格式 - 返回DASH信息
                elif 'dash' in video_data:
                    result['dash'] = video_data['dash']
                    print(f"✅ 获取DASH视频流成功")
                
                else:
                    raise ValueError("响应中没有视频流信息")
                
                return result
            else:
                raise ValueError(f"获取视频流失败: {data.get('message', '未知错误')}")
                
        except Exception as e:
            print(f"❌ 获取视频流失败: {e}")
            raise
    
    def getPlayUrl(self, bvid: str, qn: int = 64, cookies=None) -> str:
        """
        一键获取视频播放URL（整合getCid和getVideoStream）
        
        参数:
            bvid: 视频的BV号
            qn: 清晰度
            cookies: 可选的cookies
            
        返回:
            视频流URL字符串
        """
        cid = self.getCid(bvid, cookies)
        stream_data = self.getVideoStream(bvid, cid, qn, cookies)
        
        if 'url' in stream_data:
            return stream_data['url']
        else:
            raise ValueError("只支持返回MP4格式的直接播放URL，当前视频返回了DASH格式")
