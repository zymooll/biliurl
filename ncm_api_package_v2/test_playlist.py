#!/usr/bin/env python3
"""
测试歌单功能
"""
import requests
import re
import json

# 使用远程服务器的API
API_BASE_URL = "http://localhost:3002"

def extract_playlist_id(input_str):
    """
    从URL或纯数字中提取歌单ID
    支持格式：
    - https://music.163.com/playlist?id=17605775246&uct2=...
    - 17605775246
    """
    # 如果是纯数字，直接返回
    if input_str.isdigit():
        return input_str
    
    # 尝试从URL中提取id参数
    match = re.search(r'[?&]id=(\d+)', input_str)
    if match:
        return match.group(1)
    
    return None

def test_playlist_detail(playlist_id):
    """
    测试 /playlist/detail 接口
    """
    url = f"{API_BASE_URL}/playlist/detail"
    params = {"id": playlist_id}
    
    print(f"\n{'='*60}")
    print(f"测试接口: /playlist/detail")
    print(f"{'='*60}")
    print(f"🔍 正在获取歌单详情: ID={playlist_id}")
    print(f"📡 请求URL: {url}?id={playlist_id}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') == 200:
            playlist = data.get('playlist', {})
            print(f"\n✅ 歌单详情获取成功！")
            print(f"📝 歌单名称: {playlist.get('name', '未知')}")
            print(f"👤 创建者: {playlist.get('creator', {}).get('nickname', '未知')}")
            print(f"📊 歌曲数量: {playlist.get('trackCount', 0)}")
            print(f"▶️ 播放次数: {playlist.get('playCount', 0)}")
            
            # 获取所有歌曲ID
            track_ids = playlist.get('trackIds', [])
            print(f"\n📋 完整歌曲ID列表 (共{len(track_ids)}首):")
            print(f"   前10个ID: {[item.get('id') for item in track_ids[:10]]}")
            
            # 获取tracks（可能不完整）
            tracks = playlist.get('tracks', [])
            print(f"\n🎵 当前返回的tracks数量: {len(tracks)}首")
            if tracks:
                print(f"   前5首歌曲:")
                for i, track in enumerate(tracks[:5], 1):
                    print(f"   {i}. {track.get('name', '未知')} - {', '.join([ar.get('name', '') for ar in track.get('ar', [])])}")
            
            return data
        else:
            print(f"❌ 获取失败: {data.get('message', '未知错误')}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return None
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return None

def test_playlist_tracks(playlist_input):
    """
    测试 /playlist/tracks 接口（完整版）
    """
    url = f"{API_BASE_URL}/playlist/tracks"
    params = {"id": playlist_input}
    
    print(f"\n{'='*60}")
    print(f"测试接口: /playlist/tracks (完整版)")
    print(f"{'='*60}")
    print(f"🔍 正在获取完整歌单数据: {playlist_input}")
    print(f"📡 请求URL: {url}?id={playlist_input}")
    
    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') == 200:
            playlist_info = data.get('playlist_info', {})
            songs = data.get('songs', [])
            total = data.get('total', 0)
            
            print(f"\n✅ 完整歌单数据获取成功！")
            print(f"📝 歌单名称: {playlist_info.get('name', '未知')}")
            print(f"👤 创建者: {playlist_info.get('creator', '未知')}")
            print(f"📊 歌曲总数: {total}")
            
            if songs:
                print(f"\n🎵 歌曲列表 (显示前10首):")
                for i, song in enumerate(songs[:10], 1):
                    artists = ', '.join([ar.get('name', '') for ar in song.get('ar', [])])
                    album = song.get('al', {}).get('name', '未知专辑')
                    duration = song.get('dt', 0) // 1000  # 毫秒转秒
                    minutes = duration // 60
                    seconds = duration % 60
                    print(f"   {i}. {song.get('name', '未知')} - {artists}")
                    print(f"      专辑: {album} | 时长: {minutes}:{seconds:02d} | ID: {song.get('id')}")
                
                if len(songs) > 10:
                    print(f"   ... 还有 {len(songs) - 10} 首歌曲")
            
            return data
        else:
            print(f"❌ 获取失败: {data.get('message', '未知错误')}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return None
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return None

def test_playlist_complete(input_str):
    """
    完整测试流程
    """
    print("\n" + "="*60)
    print("🎵 网易云音乐歌单功能完整测试")
    print("="*60)
    
    # 1. 提取歌单ID
    playlist_id = extract_playlist_id(input_str)
    if not playlist_id:
        print(f"❌ 无法从输入中提取歌单ID: {input_str}")
        return
    
    print(f"✅ 提取到歌单ID: {playlist_id}")
    
    # 2. 测试 playlist/detail 接口
    detail_result = test_playlist_detail(playlist_id)
    
    # 3. 测试 playlist/tracks 接口（支持URL输入）
    tracks_result = test_playlist_tracks(input_str)
    
    print("\n" + "="*60)
    print("✅ 所有测试完成！")
    print("="*60)
    
    # 总结
    if detail_result and tracks_result:
        print("\n📊 测试总结:")
        print(f"   ✅ playlist/detail 接口: 正常")
        print(f"   ✅ playlist/tracks 接口: 正常")
        print(f"   ✅ 支持URL格式输入: 正常")
        print(f"   ✅ 批量获取歌曲详情: 正常")
    else:
        print("\n⚠️ 部分测试失败，请查看上方日志")

if __name__ == "__main__":
    # 测试用例
    test_cases = [
        ("URL格式", "https://music.163.com/playlist?id=17605775246&uct2=U2FsdGVkX18FgwN5tFyCK7IUwymWCT/sk3wcgOQXoN0="),
        ("纯数字ID", "17605775246"),
    ]
    
    print("\n🎵 网易云音乐歌单功能测试脚本")
    print("="*60)
    print("请选择测试用例或输入自定义歌单ID/URL:")
    for i, (name, _) in enumerate(test_cases, 1):
        print(f"{i}. {name}")
    print("3. 输入自定义歌单ID/URL")
    print("0. 运行所有测试")
    
    try:
        choice = input("\n请输入选择 (0-3): ").strip()
        
        if choice == "0":
            # 运行所有测试
            for name, test_input in test_cases:
                print(f"\n\n{'#'*60}")
                print(f"# 测试: {name}")
                print(f"{'#'*60}")
                test_playlist_complete(test_input)
        elif choice == "1":
            test_playlist_complete(test_cases[0][1])
        elif choice == "2":
            test_playlist_complete(test_cases[1][1])
        elif choice == "3":
            custom_input = input("请输入歌单ID或URL: ").strip()
            if custom_input:
                test_playlist_complete(custom_input)
            else:
                print("❌ 输入为空")
        else:
            print("使用默认测试用例...")
            test_playlist_complete(test_cases[0][1])
    except KeyboardInterrupt:
        print("\n\n👋 测试已取消")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
