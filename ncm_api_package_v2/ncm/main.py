from fastapi import FastAPI
from ncm.api.routes import router, init_login_handler
from ncm.core.login import LoginProtocol
from ncm.core.music import UserInteractive
from ncm.utils.cookie import load_cookie, save_cookie

app = FastAPI(title="NCM API Service")

@app.on_event("startup")
async def startup_event():
    init_login_handler()
    initSession()

def initSession():
    """初始化会话，获取有效cookie"""
    print("🔍 正在检查 Cookie 状态...")
    login = LoginProtocol()

    cookie = load_cookie()
    if cookie:
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
                print("⚠️ Cookie 已失效或无法获取用户信息，将尝试使用游客身份登录")
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

app.include_router(router)
