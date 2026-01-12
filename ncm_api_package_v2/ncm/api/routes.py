from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
import requests
from ncm.core.music import UserInteractive
from ncm.utils.cookie import load_cookie

router = APIRouter()

# 这是一个纯粹的调试接口，用于查看 VRChat 发来的请求头到底长什么样
@router.get("/play/vrc")
async def debug_sniffer(
    request: Request,
    id: str = None,
    keywords: str = None
):
    """
    🔍 抓包嗅探模式
    不返回任何真实的媒体，只负责在控制台打印请求头，
    并返回 JSON 供 StringDownloader 查看。
    """
    
    # 1. 获取所有请求头
    headers = dict(request.headers)
    
    # 2. 提取关键信息
    user_agent = headers.get("user-agent", "无")
    accept = headers.get("accept", "无")
    content_type = headers.get("content-type", "无")
    range_header = headers.get("range", "无")
    host = request.client.host
    
    # 3. 在服务器控制台打印显眼的日志
    print("\n" + "="*50)
    print(f"📡 [收到请求] 来自 IP: {host}")
    print(f"🎵 参数 ID: {id} | Keywords: {keywords}")
    print("-" * 20 + " 关键特征 " + "-" * 20)
    print(f"👉 User-Agent: {user_agent}")
    print(f"👉 Accept:     {accept}")
    print(f"👉 Range:      {range_header}")
    print("-" * 50)
    
    # 4. 构造返回数据
    # 如果是 StringDownloader，它会把这个 JSON 显示在 Udon 日志里
    # 如果是 ImageDownloader，它会因为这只是文本不是图片而报错，但这正是我们想测试的
    response_data = {
        "msg": "这是一个调试响应",
        "your_headers": {
            "User-Agent": user_agent,
            "Accept": accept,
            "Range": range_header
        }
    }
    
    return JSONResponse(content=response_data)

# --- 保留一些基础接口防止报错 ---
@router.get("/")
async def root(): return "Debug Mode Active"

@router.get("/api")
async def api(): return {"msg": "ok"}