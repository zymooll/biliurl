import requests
import json
import qrcode
import base64
from io import BytesIO
from PIL import Image
from pyzbar.pyzbar import decode
import urllib.parse

baseUrl = "https://163.0061226.xyz/"
#songID = input("Enter the song ID: ")
#bitRate = int(input("Enter the bit rate: "))
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
        pass

    def LoginAsGuest(): 
        url = f"{baseUrl}register/anonimous"
        response = requests.get(url)
        response = response.json()
        Info = response["userId"]
        cookie = response["cookie"]
        print("本次用户ID: " + str(Info))
        cookie_encoded = urllib.parse.quote(cookie)
        return cookie_encoded
    
    def getLoginInfo():
        url = f"{baseUrl}user/account"
        response = requests.get(url)
        response = response.json()
        if response["account"] == None:
            isLogin = False
        else:
            isLogin = True
        Info = " 登录状态: " + str(isLogin)
        return Info

    def getQRKey():
        url = f"{baseUrl}login/qr/key"
        response = requests.get(url)
        response = response.json()
        #{"data":{"code":200,"unikey":"xxx"},"code":200}
        return response["data"]["unikey"]
    
    def getQRCode(key):
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

    def sendSMSCode(self, phone):
        url = f"{baseUrl}captcha/sent?phone={phone}"
        response = requests.get(url)
        response = response.json()
        #{"code":200,"data":true}
        if response["data"] == True:
            print("验证码已发送")
            verifyCode = input("请输入验证码: ")
            return self.verifySMSCode(phone, verifyCode)
        else:
            print("发生错误: " + response["code"] + " " + response["data"])
            return False
        
    def verifySMSCode(self, phone, code):
        url = f"{baseUrl}captcha/verify?phone={phone}&captcha={code}"
        response = requests.get(url)
        response = response.json()
        #{"code":200,"data":true}
        if response["data"] == True:
            print("验证码验证成功")
            return True
        else:
            print("发生错误: " + response["code"] + " " + response["data"])
            return False
    
    def Logout():
        url = f"{baseUrl}logout"
        response = requests.get(url)
        response = response.json()
        if response["code"] == 200:
            print("登出成功")
            print(LoginProtocol.getLoginInfo())
            return True
        else:
            print("发生错误: " + response["code"] + " " + response["data"])
            return False




def getDonwloadUrl(songID,bitRate):
    #下载API:/song/download/url
    #试听API:/song/url
    if bitRate == '': bitRate = 320000
    url = f"{baseUrl}song/url?id={songID}&bitrate={bitRate}"
    response = requests.get(url)
    response.json()
    downloadUrl = response.json()['data'][0]['url']
    print("解析的Url为: " + downloadUrl)
    return downloadUrl

key = LoginProtocol.getQRKey()
LoginProtocol.getQRCode(key)
