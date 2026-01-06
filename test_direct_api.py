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

if __name__ == "__main__":
    print("\n🎵 VRChat MP3 播放 API 测试\n")
    
    try:
        # 测试旧端点
        test_old_redirect_endpoint()
        
        # 测试新端点（推荐用于 VRChat）
        test_new_direct_endpoint()
        
        # 测试关键词搜索
        test_with_keywords()
        
        print("=" * 60)
        print("📝 使用说明:")
        print("=" * 60)
        print("在 VRChat 中使用以下 URL 格式:")
        print(f"  1. 通过 ID: {API_BASE}/play/direct?id=歌曲ID")
        print(f"  2. 通过关键词: {API_BASE}/play/direct?keywords=歌曲名")
        print()
        print("⚠️ 注意: 需要在 USharpVideo 中实现 JSON 解析")
        print()
        
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到 API 服务: {API_BASE}")
        print("请确保服务器正在运行!")
    except Exception as e:
        print(f"❌ 测试出错: {e}")
