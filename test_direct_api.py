#!/usr/bin/env python3
"""
测试 /play/direct 端点
用于验证 VRChat 可以直接获取 MP3 URL
"""
import requests
import json

# 测试配置
API_BASE = "http://206601.xyz:7997"
TEST_SONG_ID = "1969519579"

def test_old_redirect_endpoint():
    """测试旧的重定向端点（VRChat不支持）"""
    print("=" * 60)
    print("测试 1: 旧端点 /play (重定向模式)")
    print("=" * 60)
    
    url = f"{API_BASE}/play?id={TEST_SONG_ID}"
    print(f"请求: {url}")
    
    # allow_redirects=False 防止自动跟随重定向
    response = requests.get(url, allow_redirects=False)
    
    print(f"状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")
    
    if response.status_code == 307:
        print(f"✅ 返回重定向到: {response.headers.get('location')}")
        print("⚠️ VRChat 不支持重定向，无法播放")
    print()

def test_new_direct_endpoint():
    """测试新的直接返回 JSON 端点（VRChat支持）"""
    print("=" * 60)
    print("测试 2: 新端点 /play/direct (JSON 模式)")
    print("=" * 60)
    
    url = f"{API_BASE}/play/direct?id={TEST_SONG_ID}"
    print(f"请求: {url}")
    
    response = requests.get(url)
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ 成功获取 JSON 响应:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if data.get("url"):
            mp3_url = data["url"]
            print(f"\n🎵 MP3 直链: {mp3_url[:100]}...")
            print("\n✅ 这个 URL 可以在 VRChat 中使用！")
    else:
        print(f"❌ 请求失败: {response.text}")
    print()

def test_with_keywords():
    """测试关键词搜索"""
    print("=" * 60)
    print("测试 3: 使用关键词搜索")
    print("=" * 60)
    
    keywords = "夜曲"
    url = f"{API_BASE}/play/direct?keywords={keywords}"
    print(f"请求: {url}")
    
    response = requests.get(url)
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ 搜索成功:")
        print(f"  歌曲: {data.get('song_name', 'N/A')}")
        print(f"  歌手: {data.get('artist', 'N/A')}")
        print(f"  ID: {data.get('song_id', 'N/A')}")
        print(f"  URL: {data.get('url', 'N/A')[:100]}...")
    else:
        print(f"❌ 搜索失败: {response.text}")
    print()

def test_stream_proxy():
    """测试音频流代理端点（VRChat 最终解决方案）"""
    print("=" * 60)
    print("测试 4: 音频流代理 /stream (VRChat 推荐)")
    print("=" * 60)
    
    url = f"{API_BASE}/stream?id={TEST_SONG_ID}"
    print(f"请求: {url}")
    
    # 只获取前1KB数据测试
    response = requests.get(url, stream=True)
    
    print(f"状态码: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Content-Length: {response.headers.get('Content-Length', 'N/A')}")
    
    if response.status_code == 200:
        # 读取前1KB验证
        chunk = next(response.iter_content(chunk_size=1024), None)
        if chunk:
            print(f"✅ 成功获取音频流 (已接收 {len(chunk)} 字节)")
            print(f"\n🎵 VRChat 使用此 URL: {url}")
            print("✅ 此方法通过你的服务器代理，VRChat 可以播放！")
        else:
            print("⚠️ 未收到数据")
    else:
        print(f"❌ 请求失败: {response.text}")
    print()

if __name__ == "__main__":
    print("\n🎵 VRChat MP3 播放 API 测试\n")
    
    try:
        # 测试旧端点
        test_old_redirect_endpoint()
        
        # 测试新端点（推荐用于 VRChat）
        test_new_direct_endpoint()
        
        # 测试关键词搜索
        test_with_keywords()
        
        # 测试音频流代理（VRChat 最终解决方案）
        test_stream_proxy()
        
        print("=" * 60)
        print("📝 VRChat 使用说明:")
        print("=" * 60)
        print("✅ 推荐使用流代理端点（已解决域名限制问题）:")
        print(f"  1. 通过 ID: {API_BASE}/stream?id=歌曲ID")
        print(f"  2. 通过关键词: {API_BASE}/stream?keywords=歌曲名")
        print()
        print("注意事项:")
        print("  • 确保 USharpVideo 切换到 Stream (AVPro) 模式")
        print("  • 音频通过你的服务器代理，不受 VRChat 域名限制")
        print("  • 支持所有音质等级 (standard/higher/exhigh/lossless)")
        print()
        
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到 API 服务: {API_BASE}")
        print("请确保服务器正在运行!")
    except Exception as e:
        print(f"❌ 测试出错: {e}")
