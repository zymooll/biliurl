from fastapi import FastAPI
from ncm.api.routes import router, init_login_handler
from ncm.core.login import LoginProtocol
from ncm.core.music import UserInteractive
from ncm.utils.cookie import load_cookie, save_cookie
from ncm.config import API_BASE_URL
import requests

app = FastAPI(title="NCM API Service")

@app.on_event("startup")
async def startup_event():
    # 先检查 API 连接
    checkAPIConnection()
    init_login_handler()
    initSession()

def checkAPIConnection():
    """检查 API 服务连接"""
    print(f"🔍 检查 API 服务连接: {API_BASE_URL}")
    try:
        # 尝试访问一个简单的端点
        response = requests.get(f"{API_BASE_URL}", timeout=5)
        print(f"✅ API 服务连接正常 (状态码: {response.status_code})")
        return True
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 无法连接到 API 服务: {API_BASE_URL}")
        print(f"💡 请检查:")
        print(f"   1. Docker 容器是否正常运行")
        print(f"   2. 端口映射是否正确 (容器端口 -> 宿主机 3002)")
        print(f"   3. 在宿主机执行: curl {API_BASE_URL}")
        return False
    except Exception as e:
        print(f"⚠️ API 连接检查异常: {type(e).__name__}: {e}")
        return False

def initSession():
    """初始化会话，获取有效cookie"""
    print("🔍 正在检查 Cookie 状态...")
    login = LoginProtocol()

    cookie = load_cookie()
    if cookie:
        print(f"📄 检测到已有 Cookie (长度: {len(cookie)})")
        try:
            data = UserInteractive.getUserAccount(cookie)
            if data and data.get("code") == 200:
                profile = data.get('profile') or {}
                account = data.get('account') or {}
                nickname = profile.get('nickname', '未知')
                uid = account.get('id', '未知')
                
                print(f"✅ 当前登录身份：{nickname} (UID: {uid})")
                return cookie
            else:
                print(f"⚠️ Cookie 校验返回: {data}")
                print("⚠️ Cookie 已失效或无法获取用户信息")
        except Exception as e:
            print("❌ Cookie 校验失败：", e)
    else:
        print("📭 未找到已保存的 Cookie 文件")

    # 尝试游客登录
    print("➡️ 正在尝试游客身份登录...")
    try:
        guest_cookie = login.guestLogin()
        if guest_cookie:
            save_cookie(guest_cookie)
            print("✅ 已使用游客身份登录")
            return guest_cookie
        else:
            print("⚠️ 游客登录未返回有效 cookie")
            return None
    except Exception as e:
        print(f"❌ 游客身份登录失败：{e}")
        print("💡 提示：如果有已登录的 cookie.json，服务仍可使用该 cookie")
        # 如果之前加载过 cookie，即使游客登录失败也返回它
        if cookie:
            print("✅ 将使用之前加载的 Cookie 继续运行")
            return cookie
        return None

app.include_router(router)
