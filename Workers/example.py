#!/usr/bin/env python3
"""
Biliurl Workers - Python 示例脚本

使用方法:
    python3 example.py <worker_url> <api_key> <bvid>

示例:
    python3 example.py https://biliurl.workers.dev pro_xxx BV1Xx411c7mD
"""

import sys
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

def print_header(text):
    """打印带格式的标题"""
    print("\n" + "=" * 42)
    print(text)
    print("=" * 42)

def fetch_json(url: str) -> dict:
    """获取 JSON 数据"""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode())
    except urllib.error.URLError as e:
        print(f"❌ 网络错误: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析错误: {e}")
        sys.exit(1)

def run_ffmpeg(video_url: str, audio_url: str, output_file: str) -> bool:
    """使用 ffmpeg 合成视频"""
    try:
        cmd = [
            'ffmpeg',
            '-i', video_url,
            '-i', audio_url,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-shortest',
            '-headers', 'Referer: https://www.bilibili.com',
            output_file,
            '-loglevel', 'warning'
        ]
        
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ 需要安装 ffmpeg")
        print("\n安装方法:")
        print("  macOS:   brew install ffmpeg")
        print("  Ubuntu:  sudo apt install ffmpeg")
        print("  Windows: choco install ffmpeg")
        return False
    except Exception as e:
        print(f"❌ ffmpeg 错误: {e}")
        return False

def main():
    """主函数"""
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <worker_url> <api_key> <bvid>")
        print("\nExamples:")
        print(f"  {sys.argv[0]} https://biliurl.workers.dev public_j389u4tc9w08u4pq4mqp9xwup4 BV1Xx411c7mD")
        print(f"  {sys.argv[0]} https://biliurl.workers.dev pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh BV1Xx411c7mD")
        sys.exit(1)
    
    worker_url = sys.argv[1].rstrip('/')
    api_key = sys.argv[2]
    bvid = sys.argv[3]
    
    print_header("Biliurl Workers - 下载示例")
    print(f"Worker URL: {worker_url}")
    print(f"API Key: {api_key[:20]}...")
    print(f"BVID: {bvid}")
    
    # 步骤 1: 获取视频信息
    print("\n[1/4] 获取视频信息...")
    info_url = f"{worker_url}/api/bili/{bvid}/info?key={api_key}"
    info = fetch_json(info_url)
    
    if 'error' in info:
        print(f"❌ 错误: {info['error']}")
        sys.exit(1)
    
    title = info.get('title', '未知')
    print(f"✓ 完成")
    print(f"标题: {title}")
    
    # 步骤 2: 获取流 URLs
    print("\n[2/4] 获取流 URLs...")
    streams_url = f"{worker_url}/api/bili/{bvid}/streams?key={api_key}&quality=125"
    streams = fetch_json(streams_url)
    
    if 'error' in streams:
        print(f"❌ 错误: {streams['error']}")
        sys.exit(1)
    
    video_url = streams.get('streams', {}).get('video')
    audio_url = streams.get('streams', {}).get('audio')
    quality = streams.get('quality_used', '未知')
    
    if not video_url or not audio_url:
        print("❌ 错误: 无法获取视频或音频 URL")
        sys.exit(1)
    
    print(f"✓ 完成")
    print(f"视频 URL: {video_url[:80]}...")
    print(f"音频 URL: {audio_url[:80]}...")
    print(f"使用画质: {quality}")
    
    # 步骤 3: 生成输出文件名
    print("\n[3/4] 准备下载...")
    output_file = f"{bvid}.mp4"
    print(f"输出文件: {output_file}")
    
    # 步骤 4: 合成视频
    print("\n[4/4] 使用 ffmpeg 下载并合成...")
    if not run_ffmpeg(video_url, audio_url, output_file):
        print("❌ 合成失败")
        sys.exit(1)
    
    # 获取文件大小
    output_path = Path(output_file)
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print_header("✅ 下载完成!")
        print(f"文件: {output_path.absolute()}")
        print(f"大小: {size_mb:.2f} MB")
    else:
        print("❌ 输出文件不存在")
        sys.exit(1)

if __name__ == '__main__':
    main()
