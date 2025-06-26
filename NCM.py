import requests
import time
import qrcode
import base64
from io import BytesIO
from PIL import Image
from pyzbar.pyzbar import decode
import urllib.parse

baseUrl = "https://163.0061226.xyz/"
#baseUrl = "http://192.168.101.6:3000/"
songID = 520459140
bitRate = 320000

def printQRcode(data):
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
                return data.get("cookie")
            else:
                print("⚠️ 未知状态码：", code, data)
            time.sleep(2)

    def qrLogin(self):
        key = self.getQRKey()
        self.getQRCode(key)
        cookie = self.checkQRStatus(key)
        
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

def getDownloadUrl(songID, bitRate):
    if not bitRate:
        bitRate = 320000
    url = f"{baseUrl}song/url?id={songID}&bitrate={bitRate}"
    response = requests.get(url)
    data = response.json()
    downloadUrl = data['data'][0]['url']
    print("解析的下载链接为: ", downloadUrl)
    return downloadUrl


def mainMenu():
    login = LoginProtocol()

    while True:
        print("\n==== 网易云音乐登录菜单 ====")
        print("1. 短信验证码登录")
        print("2. 手机密码登录")
        print("3. 扫码二维码登录")
        print("4. 解析歌曲直链")
        print("0. 退出程序")
        choice = input("请选择功能编号：").strip()

        if choice == "1":
            phone = input("请输入手机号：").strip()
            login.SMSHandle(phone)
        elif choice == "2":
            phone = input("请输入手机号：").strip()
            password = input("请输入密码：").strip()
            login.PhonePasswordLogin(phone, password)
        elif choice == "3":
            login.qrLogin()
        elif choice == "4":
            song_id = input("请输入歌曲ID（默认520459140）：").strip()
            if not song_id:
                song_id = 520459140
            else:
                song_id = int(song_id)
            bitrate = input("请输入音质码率（默认320000）：").strip()
            if not bitrate:
                bitrate = 320000
            else:
                bitrate = int(bitrate)
            getDownloadUrl(song_id, bitrate)
        elif choice == "0":
            print("👋 再见！")
            break
        else:
            print("⚠️ 无效选项，请重试。")



if __name__ == '__main__':
    mainMenu()
    
