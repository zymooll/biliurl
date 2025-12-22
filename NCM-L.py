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


# 全局配置
API_BASE_URL = "http://localhost:3000/"
#API_BASE_URL = "https://163.0061226.xyz/"
#API_BASE_URL = "http://192.168.101.6:3000/"
DEFAULT_SONG_ID = 520459140
DEFAULT_BIT_RATE = 320000
COOKIE_FILE = "cookie.json"
GUEST_COOKIE_FILE = "cookie-guest.json"

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

def printQRcode(data):
    """打印二维码到终端"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=1
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr.print_ascii(invert=True)

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
            print("[DEBUG] 状态码:", resp.status_code)
            print("[DEBUG] 响应内容:", resp.text[:200])
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
            baseStr = response["data"]["qrimg"].split(",", 1)[1]
            img_data = base64.b64decode(baseStr)
            image = Image.open(BytesIO(img_data))
            decoded = decode(image)
            if not decoded:
                print("二维码无法识别")
                return
            QRText = decoded[0].data.decode()
            print("● 二维码内容:", QRText)
            print("● 请扫码登录：\n")
            printQRcode(QRText)
        except Exception as e:
            print(f"❌ 获取QR码失败: {e}")
            raise

    def checkQRStatus(self, key):
        """检查二维码扫描状态"""
        print("传入的key: ", key)
        try:
            while True:
                timestamp = int(time.time() * 1000)
                url = f"{API_BASE_URL}login/qr/check?key={key}&timestamp={timestamp}"

                resp = self.session.get(url, headers=self.headers)
                data = resp.json()
                code = data.get("code")

                if code == 800:
                    print("❌ 二维码已过期")
                    return None
                elif code == 801:
                    print("⌛ 等待扫码中...")
                elif code == 802:
                    print("📱 已扫码，请手机确认...")
                elif code == 803:
                    print("✅ 登录成功！")
                    print("响应数据：", data)
                    return data.get("cookie")
                else:
                    print("⚠️ 未知状态码：", code, data)
                time.sleep(1)
        except Exception as e:
            print(f"❌ 检查QR状态时出错: {e}")
            return None

    def qrLogin(self):
        """使用二维码登录流程"""
        try:
            key = self.getQRKey()
            self.getQRCode(key)
            cookie = self.checkQRStatus(key)
            return cookie
        except Exception as e:
            print(f"❌ QR登录流程出错: {e}")
            return None
        
    def SMSLogin(self, phone, captcha):
        """短信验证码登录"""
        url = f"{API_BASE_URL}login/cellphone?phone={phone}&captcha={captcha}"
        try:
            response = requests.get(url)
            response_data = response.json()
            print(response_data)
            return response_data.get("cookie")
        except Exception as e:
            print(f"❌ 短信登录失败: {e}")
            return None

    def sendSMS(self, phone):
        """发送短信验证码"""
        url = f"{API_BASE_URL}captcha/sent?phone={phone}"
        try:
            sendSMSResponse = requests.get(url)
            print(sendSMSResponse.json())
        except Exception as e:
            print(f"❌ 发送短信失败: {e}")

    def verifySMS(self, phone, captcha):
        """验证短信验证码"""
        url = f"{API_BASE_URL}captcha/verify?phone={phone}&captcha={captcha}"
        try:
            verifySMSResponse = requests.get(url)
            response_data = verifySMSResponse.json()
            print(response_data)
            if response_data.get("code") != 200:
                print("验证码错误或登录失败")
                return False
            else:
                cookie = self.SMSLogin(phone, captcha)
                if cookie:
                    save_cookie(cookie)
                    return True
                return False
        except Exception as e:
            print(f"❌ 验证短信失败: {e}")
            return False

    def SMSHandle(self, phone):
        """短信验证码登录流程处理"""
        self.sendSMS(phone)
        captcha = input("请输入验证码：")
        return self.verifySMS(phone, captcha)

    def PhonePasswordLogin(self, phone, password):
        """手机号密码登录"""
        url = f"{API_BASE_URL}login/cellphone?phone={phone}&password={password}"
        try:
            response = requests.get(url)
            response_data = response.json()
            print(response_data)
            cookie = response_data.get("cookie")
            if cookie:
                save_cookie(cookie)
                return cookie
            return None
        except Exception as e:
            print(f"❌ 密码登录失败: {e}")
            return None
        
    def Logout(self):
        """退出登录"""
        url = f"{API_BASE_URL}logout"
        try:
            response = requests.get(url)
            print(response.json())
            if os.path.exists(COOKIE_FILE):
                os.remove(COOKIE_FILE)
                print("✅ Cookie文件已删除")
        except Exception as e:
            print(f"❌ 退出登录失败: {e}")


class UserInteractive:
    """用户交互功能类"""
    
    @staticmethod
    def getDownloadUrl(songID, level="exhigh", unblock=False, cookie=None):
        """获取歌曲下载链接"""
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
                resp = requests.get(url, params=params)
                return resp.json()

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
                print(f"❌ 解析失败。API 响应: {data}")
                return None
            
            print(f"\n✅ 解析成功！")
            print(f"🎵 实际音质: {song_info.get('level', '未知')}")
            print(f"🔗 下载链接: {downloadUrl}")
            return downloadUrl

        except Exception as e:
            print(f"❌ 获取下载链接失败: {e}")
            return None

    @staticmethod
    def getUserAccount(cookie):
        """获取用户账号信息"""
        try:
            if not cookie:
                print("⚠️ Cookie为空，无法获取用户信息")
                return None
                
            encoded_cookie = urllib.parse.quote(cookie)
            url = f"{API_BASE_URL}user/account?cookie={encoded_cookie}"
            
            response = requests.get(url)
            data = response.json()
            print("用户信息：", data)
            return data
        except Exception as e:
            print(f"❌ 获取用户信息失败: {e}")
            return None


def mainMenu(current_cookie=None):
    """主菜单交互功能"""
    login = LoginProtocol()
    if current_cookie is None:
        current_cookie = load_cookie()
        
    while True:
        print("\n==== 网易云音乐登录菜单 ====")
        print("1. 短信验证码登录")
        print("2. 手机密码登录")
        print("3. 扫码二维码登录")
        print("4. 解析歌曲直链")
        print("5. 获取用户账号信息")
        print("6. 手动导入 Cookie（JSON 格式）")
        print("7. 退出登录")
        print("0. 退出程序")
        
        try:
            choice = input("请选择功能编号：").strip()
            
            if choice == "1":
                phone = input("请输入手机号：").strip()
                if login.SMSHandle(phone):
                    print("✅ 短信登录成功")
                    current_cookie = load_cookie()
                
            elif choice == "2":
                phone = input("请输入手机号：").strip()
                password = input("请输入密码：").strip()
                cookie = login.PhonePasswordLogin(phone, password)
                if cookie:
                    current_cookie = cookie
                    print("✅ 密码登录成功")
                
            elif choice == "3":
                new_cookie = login.qrLogin()
                if new_cookie:
                    save_cookie(new_cookie)
                    current_cookie = new_cookie  # 修复这一行
                    print("✅ 二维码登录成功")
                    
            elif choice == "4":
                try:
                    song_id = input("请输入歌曲ID（默认520459140）：").strip()
                    if not song_id:
                        song_id = DEFAULT_SONG_ID
                    else:
                        song_id = int(song_id)
                        
                    print("\n可选音质等级：")
                    print("1. standard (标准)")
                    print("2. higher (较高)")
                    print("3. exhigh (极高)")
                    print("4. lossless (无损)")
                    print("5. hires (Hi-Res)")
                    level_choice = input("请选择音质编号（默认 3）：").strip()
                    
                    level_map = {
                        "1": "standard",
                        "2": "higher",
                        "3": "exhigh",
                        "4": "lossless",
                        "5": "hires"
                    }
                    level = level_map.get(level_choice, "exhigh")

                    unblock_choice = input("是否尝试解灰/VIP破解 (y/n，默认 n)：").strip().lower()
                    unblock = True if unblock_choice == 'y' else False
                        
                    UserInteractive.getDownloadUrl(song_id, level, unblock, current_cookie)
                except ValueError as e:
                    print(f"❌ 输入格式错误: {e}")
                    
            elif choice == "5":
                if current_cookie:
                    UserInteractive.getUserAccount(current_cookie)
                else:
                    print("⚠️ 请先登录以获取 cookie，再尝试查看账号信息")
                    
            elif choice == "6":
                try:
                    cookie_input = input("请输入完整 JSON 字符串（包含 'cookie' 字段）：\n")
                    # 将单引号替换成双引号，防止用户复制的是 Python 风格
                    cookie_json = json.loads(cookie_input.replace("'", '"'))
                    imported_cookie = cookie_json.get("cookie")
                    if imported_cookie:
                        current_cookie = imported_cookie
                        save_cookie(current_cookie)
                        print("✅ Cookie 导入成功")
                    else:
                        print("⚠️ 未找到有效 cookie 字段")
                except Exception as e:
                    print(f"❌ 解析失败，请确认格式正确：{e}")
                    
            elif choice == "7":
                login.Logout()
                current_cookie = None
                print("✅ 已退出登录")
                
            elif choice == "0":
                print("👋 感谢使用，再见！")
                break
                
            else:
                print("⚠️ 无效的选择，请重新输入")
                
        except Exception as e:
            print(f"❌ 操作出错: {e}")


if __name__ == "__main__":
    try:
        cookie = initSession()
        mainMenu(cookie)
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断，再见！")
    except Exception as e:
        print(f"\n❌ 程序遇到未处理的异常: {e}")
