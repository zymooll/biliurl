import requests
import pickle
import qrcode
import time
import sys
from pathlib import Path
from io import StringIO

# Headers for API requests
headers = {
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


def get_qr_code():
    """Generate QR code and display in terminal"""
    try:
        respLogin = requests.get('https://passport.bilibili.com/x/passport-login/web/qrcode/generate', headers=headers)
        data = respLogin.json()['data']
        QRUrl = data['url']
        QRKey = data['qrcode_key']
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(QRUrl)
        qr.make(fit=True)
        
        # Display in terminal
        print("\n" + "="*50)
        print("请使用B站App扫码登录")
        print("="*50 + "\n")
        qr.print_ascii(invert=True)
        print("\n" + "="*50 + "\n")
        
        return QRKey
    except Exception as e:
        print(f"Error generating QR code: {e}")
        raise


def check_login_status(QRKey):
    """Check the login status by polling the server"""
    try:
        respStatus = requests.get(
            'https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key=' + QRKey,
            headers=headers
        )
        respCode = int(respStatus.json()['data']['code'])
        return respCode, respStatus
    except Exception as e:
        print(f"Error checking login status: {e}")
        raise


def show_qr_code():
    """Display QR code and start login polling"""
    print("正在生成二维码...")
    QRKey = get_qr_code()
    
    print("等待扫码...")
    polling_count = 0
    max_attempts = 600  # 10 minutes timeout
    
    while polling_count < max_attempts:
        try:
            respCode, respStatus = check_login_status(QRKey)
            
            if respCode == 86038:
                print("上一二维码已失效，请用新二维码扫码")
                QRKey = get_qr_code()
            elif respCode == 86101:
                print(".", end="", flush=True)
            elif respCode == 86090:
                print("\n已扫码，等待确认...", flush=True)
            elif respCode == 0:
                print("\n✓ 登录成功！")
                cookies = respStatus.cookies
                with open('cookies.pkl', 'wb') as f:
                    pickle.dump(cookies, f)
                print("✓ Cookies 已保存到 cookies.pkl")
                return cookies
            
            polling_count += 1
            time.sleep(1)
        except Exception as e:
            print(f"\n错误: {e}")
            raise
    
    print("\n登录超时，请重试")
    return None


def load_cookies():
    """Load cookies from file if exists"""
    if Path('cookies.pkl').exists():
        with open('cookies.pkl', 'rb') as f:
            return pickle.load(f)
    return None


if __name__ == "__main__":
    show_qr_code()
