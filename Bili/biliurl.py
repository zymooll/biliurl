import requests
import json
import time
import os
import subprocess
from pathlib import Path
from flask import Flask, send_file, jsonify, request
from io import BytesIO

app = Flask(__name__)

# API 配置 - 两组 API Key
API_KEYS = {
    'public_j389u4tc9w08u4pq4mqp9xwup4': {'max_quality': '64', 'name': '720p 限制'},      # 最高 720p
    'pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh': {'max_quality': '125', 'name': '1080p 限制'}   # 最高 1080p
}

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

def verify_request():
    """验证 API Key"""
    api_key = request.args.get('key') or request.headers.get('X-API-Key')
    
    if not api_key:
        return False, {'error': '缺少 API Key'}, None
    
    # 验证 API Key 并返回权限级别
    if api_key in API_KEYS:
        return True, None, API_KEYS[api_key]
    else:
        return False, {'error': '无效的 API Key'}, None

# Use pathlib for cross-platform paths
temp_dir = Path('temp')
output_dir = Path('output')

# Ensure directories exist
temp_dir.mkdir(parents=True, exist_ok=True)
output_dir.mkdir(parents=True, exist_ok=True)

def getCid(bvid):
    """Get the cid of video by bvid and return video info"""
    respCid = requests.get('https://api.bilibili.com/x/player/pagelist?bvid=' + bvid, headers=headers)
    plist = respCid.json()
    cid = str(plist['data'][0]['cid'])
    return cid

def getVideoInfo(bvid):
    """Get video info including title, description, etc."""
    respInfo = requests.get('https://api.bilibili.com/x/web-interface/view?bvid=' + bvid, headers=headers)
    info = respInfo.json()
    if info['code'] == 0:
        data = info['data']
        return {
            'title': data.get('title', ''),
            'description': data.get('desc', ''),
            'duration': data.get('duration', 0),
            'author': data.get('owner', {}).get('name', ''),
            'cover': data.get('pic', ''),
            'pubdate': data.get('pubdate', 0),
            'bvid': bvid
        }
    return None

def getStream(bvid, cid, quality):
    """Get video&audio stream urls by cid
    
    Quality codes:
    - 360p: 16
    - 480p: 32
    - 720p: 64
    - 1080p: 125
    - 4K: 266
    """
    # Default to 720p if not specified
    if quality not in ['16', '32', '64', '125', '266', '-1']:
        quality = '64'
    
    respUrl = requests.get('https://api.bilibili.com/x/player/wbi/playurl?from_client=BROWSER&cid=' + cid + '&qn=' + quality + '&fourk=1&fnver=0&fnval=4048&bvid=' + bvid, headers=headers)
    plist = respUrl.json()
    streamUrlVideo = str(plist['data']['dash']['video'][0]['baseUrl'])
    streamUrlAudio = str(plist['data']['dash']['audio'][0]['baseUrl'])
    return [streamUrlVideo, streamUrlAudio]

def downloadStream(streamUrl):
    """Download video&audio stream and return as bytes"""
    # Download video
    respVideo = requests.get(streamUrl[0], headers=headers, stream=True)
    respVideo.raise_for_status()
    videoData = BytesIO()
    for chunk in respVideo.iter_content(chunk_size=8192):
        if chunk:
            videoData.write(chunk)
    videoData.seek(0)

    # Download audio
    respAudio = requests.get(streamUrl[1], headers=headers, stream=True)
    respAudio.raise_for_status()
    audioData = BytesIO()
    for chunk in respAudio.iter_content(chunk_size=8192):
        if chunk:
            audioData.write(chunk)
    audioData.seek(0)

    return videoData, audioData

@app.route('/api/bili/<bvid>', methods=['GET'])
def get_stream(bvid):
    """Get video or audio stream for a bilibili video
    
    Query parameters:
    - key: API Key (required)
      - 'basic_720p': 最高 720p
      - 'premium_1080p': 最高 1080p
    - type: 'video', 'audio', or 'raw' (default: 'video')
    - quality: 画质代码 (default: 使用 API Key 允许的最高画质)
      - '16': 360p
      - '32': 480p
      - '64': 720p
      - '125': 1080p
      - '266': 4K
    """
    try:
        # 验证 API Key
        is_valid, error, api_info = verify_request()
        if not is_valid:
            return jsonify(error), 401
        
        stream_type = request.args.get('type', 'video').lower()
        requested_quality = request.args.get('quality', None)
        
        if stream_type not in ['video', 'audio', 'raw']:
            return jsonify({'error': 'Invalid type. Use type=video, type=audio, or type=raw'}), 400
        
        # 如果请求指定了画质，检查是否超过 API Key 允许的最高画质
        if requested_quality:
            max_quality = int(api_info['max_quality'])
            try:
                req_quality_int = int(requested_quality)
                if req_quality_int > max_quality:
                    # 超过限制，自动降低到最高允许画质
                    quality = api_info['max_quality']
                else:
                    quality = requested_quality
            except ValueError:
                return jsonify({'error': 'Invalid quality value'}), 400
        else:
            # 未指定画质，使用 API Key 允许的最高画质
            quality = api_info['max_quality']
        
        cid = getCid(bvid)
        streamUrl = getStream(bvid, cid, quality)
        video_info = getVideoInfo(bvid)
        
        if stream_type == 'raw':
            return jsonify({
                'info': video_info,
                'video': streamUrl[0],
                'audio': streamUrl[1],
                'api_level': api_info['name'],
                'quality_used': quality
            })
        
        videoData, audioData = downloadStream(streamUrl)
        
        if stream_type == 'video':
            return send_file(videoData, mimetype='video/mp4', as_attachment=True, download_name=f'{bvid}.mp4')
        else:  # audio
            return send_file(audioData, mimetype='audio/mp4', as_attachment=True, download_name=f'{bvid}.m4a')
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)