import requests
import time
import os
import urllib3
from ncm.config import API_BASE_URL, GUEST_COOKIE_FILE, COOKIE_FILE

# 禁用 SSL 警告（如果使用自签名证书）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
            print(f"🔗 正在连接: {url}")
            # 添加超时设置，明确使用 HTTP
            response = self.session.get(url, timeout=15, verify=False, allow_redirects=True)
            print(f"📡 响应状态码: {response.status_code}")
            
            if response.status_code != 200:
                print(f"⚠️ API 返回非 200 状态码: {response.status_code}")
                print(f"📄 响应内容: {response.text[:500]}")
                raise ValueError(f"API 返回错误状态码: {response.status_code}")
            
            response_data = response.json()
            print(f"📦 响应数据: {response_data.keys() if isinstance(response_data, dict) else type(response_data)}")

            if "cookie" in response_data:
                print("🌐 游客 Cookie 获取成功")
                import json
                with open(GUEST_COOKIE_FILE, "w", encoding="utf-8") as f:
                    json.dump({"cookie": response_data["cookie"]}, f)
                return response_data["cookie"]
            else:
                print("❌ 游客登录返回异常：", response_data)
                raise ValueError("游客登录失败，响应中缺少 cookie 字段")
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络请求失败: {type(e).__name__}: {e}")
            print(f"💡 提示: 请检查 Docker 容器是否正常运行，端口映射是否正确")
            raise
        except Exception as e:
            print(f"❌ 游客登录请求失败: {type(e).__name__}: {e}")
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
