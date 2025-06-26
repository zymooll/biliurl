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



baseUrl = "https://163.0061226.xyz/"
#baseUrl = "http://192.168.101.6:3000/"
songID = 520459140
bitRate = 320000
COOKIE_FILE = "cookie.json"

def save_cookie(cookie):
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        json.dump({"cookie": cookie}, f)
    print("💾 Cookie 已保存至 cookie.json")

def load_cookie():
    if not os.path.exists(COOKIE_FILE):
        return None
    try:
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("cookie")
    except Exception as e:
        print("❌ 加载 cookie 失败：", e)
        return None

def initSession():
    print("🔍 正在检查 Cookie 状态...")
    login = LoginProtocol()  # ✅ 第1行：实例化登录模块

    cookie = load_cookie()
    if cookie:
        try:
            data = userInteractive.getUserAccount(cookie)
            if data.get("code") == 200:
                print(f"✅ 当前登录身份：{data.get('profile', {}).get('nickname', '未知')} (UID: {data.get('account', {}).get('id')})")
                return cookie
            else:
                print("⚠️ Cookie 已失效，将尝试使用游客身份登录")
        except Exception as e:
            print("❌ Cookie 校验失败：", e)
            print("➡️ 正在尝试游客身份登录...")  # ✅ 第2行：出错时切换游客流程

    try:
        guest_cookie = login.guestLogin()  # ✅ 第3行：调用游客登录
        save_cookie(guest_cookie)          # ✅ 第4行：保存游客 Cookie
        print("✅ 已使用游客身份登录")
        return guest_cookie
    except Exception as e:
        print("❌ 游客身份登录失败：", e)
        return None

# 定义一个函数，用于打印二维码
def printQRcode(data):
    # 创建一个QRCode对象，设置版本、错误纠正级别、每个小方格的像素大小、边框大小
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=1
    )
    # 向QRCode对象中添加数据
    qr.add_data(data)
    # 生成二维码
    qr.make(fit=True)
    # 打印二维码，并设置反转颜色
    qr.print_ascii(invert=True)


class LoginProtocol:
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
        url = f"{baseUrl}register/anonimous"
        response = self.session.get(url)
        response = response.json()

        # ✅ 正确解析 cookie 字段（第 144 行）
        if "cookie" in response:
            print("🌐 游客 Cookie 获取成功")
            # ✅ 保存到独立的文件 cookie-guest.json
            with open("cookie-guest.json", "w", encoding="utf-8") as f:
                json.dump({"cookie": response["cookie"]}, f)
            return response["cookie"]
        else:
            print("❌ 游客登录返回异常：", response)
            raise ValueError("游客登录失败，响应中缺少 cookie 字段")
    
    def getLoginInfo(self):
        url = f"{baseUrl}user/account"
        response = requests.get(url)
        response = response.json()
        if response.get("account") is None:
            return "未登录"
        return f"登录用户ID: {response['account'].get('id')}"

    def getQRKey(self):
        url = f"{baseUrl}login/qr/key"
        resp = requests.get(url)
        print("[DEBUG] 状态码:", resp.status_code)
        print("[DEBUG] 响应内容:", resp.text[:200])
        response = resp.json()
        return response["data"]["unikey"]
    
    def getQRCode(self, key):
        url = f"{baseUrl}login/qr/create?key={key}&qrimg=true"
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

    def checkQRStatus(self, key):
        print("传入的key: ", key)
        while True:
            timestamp = int(time.time() * 1000)
            url = f"{baseUrl}login/qr/check?key={key}&timestamp={timestamp}"

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
                #Usage:响应数据： {'code': 803, 'message': '授权登陆成功', 'cookie': 'MUSIC_R_T=1750954032723; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/openapi/clientlog;;__csrf=a73e80f3df2ebbaad6fe072ea4e3f4f3; Max-Age=1296010; Expires=Fri, 11 Jul 2025 16:34:37 GMT; Path=/;;MUSIC_R_T=1750954032723; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/eapi/clientlog;;MUSIC_U=005C79041294531F507C5568A19B305D6ACC1A9DBB9B605F47E6EA786286D1FB6E6C6BCC5C0982019069674E919A26CF563A40DBCA68364F21934F48B7723B262E4C3C73FFB4F6C9BEDC09A6C8E40882E1E7C73844248FDADCF983C40B0645A497A9CA654A2F51345FE2743D1767E8D79EEEFA96AC957A6F12DDA5C6C192B0D666AE548BBC27DDA18DD5BAC5E83E3A49A7ADD9BF3CBC929437EBCC0896D85DAA77EAEF37EE4D3DBDDC7F603B53D998100F1A62B39B6B7CF5BCA454737640C3DF79F9A3403D22BBE101D66AE474D0C993B4EC08B8FA6A876782D5A34A56DB882C50FE49E0C8AA88888A2A9CE5EB6A98A041AC5612AE469DDCC0CAA181DC7F8D37A7FCE1AB5F37794C277EC88A8B71A1A2030F2937904A02A13D87CA5AEF8DA89F05758AE83D37885306A30357AECDB7EE8AB8B3FB1C93F2E4FF6188AAA0D1E395ACFB2EAE8A1E3721ADC9542823B93C126A; Max-Age=15552000; Expires=Tue, 23 Dec 2025 16:34:27 GMT; Path=/;;MUSIC_A_T=1750954032625; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/neapi/feedback;;MUSIC_R_T=1750954032723; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/weapi/clientlog;;MUSIC_R_T=1750954032723; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/neapi/clientlog;;MUSIC_R_T=1750954032723; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/api/feedback;;MUSIC_R_T=1750954032723; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/neapi/feedback;;MUSIC_R_T=1750954032723; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/wapi/feedback;;MUSIC_A_T=1750954032625; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/api/clientlog;;MUSIC_A_T=1750954032625; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/weapi/feedback;;MUSIC_A_T=1750954032625; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/neapi/clientlog;;MUSIC_R_T=1750954032723; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/eapi/feedback;;MUSIC_A_T=1750954032625; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/openapi/clientlog;;MUSIC_A_T=1750954032625; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/wapi/clientlog;;MUSIC_R_T=1750954032723; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/weapi/feedback;;MUSIC_SNS=; Max-Age=0; Expires=Thu, 26 Jun 2025 16:34:27 GMT; Path=/;MUSIC_A_T=1750954032625; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/eapi/feedback;;MUSIC_A_T=1750954032625; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/wapi/feedback;;MUSIC_A_T=1750954032625; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/eapi/clientlog;;MUSIC_R_T=1750954032723; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/wapi/clientlog;;MUSIC_A_T=1750954032625; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/weapi/clientlog;;MUSIC_R_T=1750954032723; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/api/clientlog;;MUSIC_A_T=1750954032625; Max-Age=2147483647; Expires=Tue, 14 Jul 2093 19:48:34 GMT; Path=/api/feedback;'}
                #{'code': 803, 'message': '授权登陆成功', 'cookie': '123123'}
                cookie_example = "{'code': 803, 'message': '授权登陆成功', 'cookie': '123123'}"
                return data.get("cookie")
            
            else:
                print("⚠️ 未知状态码：", code, data)
            time.sleep(2)

    def qrLogin(self):
        key = self.getQRKey()
        self.getQRCode(key)
        cookie = self.checkQRStatus(key)
        return cookie
        
    def SMSLogin(self,phone,captcha):
        url = f"{baseUrl}login/cellphone?phone={phone}&captcha={captcha}"
        response = requests.get(url)
        print(response.json())

    def sendSMS(self,phone):
        url = f"{baseUrl}captcha/sent?phone={phone}"
        sendSMSResponse = requests.get(url)
        print(sendSMSResponse.json())
        #

    def verifySMS(self,phone,captcha):
        url = f"{baseUrl}captcha/verify?phone={phone}&captcha={captcha}"
        verifySMSResponse = requests.get(url)
        print(verifySMSResponse.json())
        if verifySMSResponse.json().get("code") != 200:
            print("验证码错误或登录失败")
            return False
        else:
            self.SMSLogin(phone,captcha)

    def SMSHandle(self,phone):
        self.sendSMS(phone)
        captcha = input("请输入验证码：")
        self.verifySMS(phone,captcha)

    def PhonePasswordLogin(self,phone,password):
        url = f"{baseUrl}login/cellphone?phone={phone}&password={password}"
        response = requests.get(url)
        print(response.json())
        
    def Logout(self):
        url = f"{baseUrl}logout"
        response = requests.get(url)
        print(response.json())


class userInteractive:
    def getDownloadUrl(songID, bitRate,cookie=None):
        if not cookie:
            cookie = load_cookie()
            if not cookie:
                print("⚠️ 当前未登录，部分歌曲可能无法解析")
        else:
            encoded_cookie = urllib.parse.quote(cookie)
        if not bitRate:
            bitRate = 320000
        if encoded_cookie == "":

            print("⚠️ Cookie 不能为空，请先登录获取有效的 Cookie")
            return None
        url = f"{baseUrl}song/download/url?id={songID}&level=lossless&cookie={encoded_cookie}"
        print("请求链接: ",url)
        response = requests.get(url)
        data = response.json()
        downloadUrl = data['data']['url']
        print("\n解析的下载链接为: ", downloadUrl)
        if downloadUrl == None:
            print("⚠️ 该歌曲可能没有可用的下载链接, 或者是需要VIP才能下载")
            return None
        return downloadUrl


    def getUserAccount(cookie):
        encoded_cookie = urllib.parse.quote(cookie)  # 相当于 JavaScript 的 encodeURIComponent
        url = f"{baseUrl}user/account?cookie={encoded_cookie}"
        response = requests.get(url)
        data = response.json()
        print("用户信息：", data)
        return data


def mainMenu(current_cookie=None):
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
        choice = input("请选择功能编号：").strip()

        if choice == "1":
            phone = input("请输入手机号：").strip()
            login.SMSHandle(phone)
            # 如果你想支持 cookie 保存，也可以从 login.session.cookies 抽取
        elif choice == "2":
            phone = input("请输入手机号：").strip()
            password = input("请输入密码：").strip()
            login.PhonePasswordLogin(phone, password)
            # 同上
        elif choice == "3":
            current_cookie = login.qrLogin()
            if current_cookie:
                save_cookie(current_cookie)  # ✅ 保存扫码后的 cookie
        elif choice == "4":
            song_id = input("请输入歌曲ID（默认2048955734）：").strip()
            if not song_id:
                song_id = 2048955734
            else:
                song_id = int(song_id)
            bitrate = input("请输入音质码率（默认320000）：").strip()
            if not bitrate:
                bitrate = 320000
            else:
                bitrate = int(bitrate)
            userInteractive.getDownloadUrl(song_id, bitrate,current_cookie)
        elif choice == "5":
            if current_cookie:
                userInteractive.getUserAccount(current_cookie)
            else:
                print("⚠️ 请先登录以获取 cookie，再尝试查看账号信息")
        elif choice == "6":
            try:
                cookie_input = input("请输入完整 JSON 字符串（包含 'cookie' 字段）：\n")
                # 将单引号替换成双引号，防止用户复制的是 Python 风格
                import json
                cookie_json = json.loads(cookie_input.replace("'", '"'))
                current_cookie = cookie_json.get("cookie")
                if current_cookie:
                    print("✅ Cookie 导入成功")
                    save_cookie(current_cookie)  # ✅ 保存导入的 Cookie
                else:
                    print("⚠️ 未找到有效 cookie 字段")
            except Exception as e:
                print("❌ 解析失败，请确认格式正确：", e)
        elif choice == "0":
            print("退出程序")
            break
        elif choice == "7":
            login.Logout()
if __name__ == '__main__':
    current_cookie = initSession()
    mainMenu()
    
