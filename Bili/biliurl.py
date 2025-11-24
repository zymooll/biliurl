import requests
import json
import time
import os
import subprocess
import hmac
import hashlib
from pathlib import Path
from flask import Flask, send_file, jsonify, request
from io import BytesIO

app = Flask(__name__)

# API 配置
API_KEY = 'j40895nctyw34hpq9384udpmeg9854y985P(*YNP(*Y$P(W*YC)))' 
TIMESTAMP_TOLERANCE = 300  # 时间戳容差（秒），防止时钟不同步

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
    """验证 API Key 和时间戳"""
    api_key = request.args.get('key') or request.headers.get('X-API-Key')
    timestamp = request.args.get('ts') or request.headers.get('X-Timestamp')
    signature = request.args.get('sig') or request.headers.get('X-Signature')
    
    if not api_key or not timestamp or not signature:
        return False, {'error': '缺少 API Key、时间戳或签名'}
    
    # 验证 API Key
    if api_key != API_KEY:
        return False, {'error': '无效的 API Key'}
    
    # 验证时间戳
    try:
        ts = int(timestamp)
        current_time = int(time.time())
        if abs(current_time - ts) > TIMESTAMP_TOLERANCE:
            return False, {'error': '时间戳过期或不有效'}
    except (ValueError, TypeError):
        return False, {'error': '无效的时间戳格式'}
    
    # 验证签名
    sign_str = f"{api_key}:{timestamp}"
    expected_sig = hmac.new(API_KEY.encode(), sign_str.encode(), hashlib.sha256).hexdigest()
    if signature != expected_sig:
        return False, {'error': '签名验证失败'}
    
    return True, None

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
    """Get video&audio stream urls by cid"""
    respUrl = requests.get('https://api.bilibili.com/x/player/wbi/playurl?from_client=BROWSER&cid=' + cid + '&qn=125&fourk=1&fnver=0&fnval=4048&bvid=' + bvid, headers=headers)
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
    """Get video or audio stream for a bilibili video"""
    try:
        # 验证请求
        is_valid, error = verify_request()
        if not is_valid:
            return jsonify(error), 401
        
        stream_type = request.args.get('type', 'video').lower()
        
        if stream_type not in ['video', 'audio', 'raw']:
            return jsonify({'error': 'Invalid type. Use type=video, type=audio, or type=raw'}), 400
        
        cid = getCid(bvid)
        streamUrl = getStream(bvid, cid, '-1')
        video_info = getVideoInfo(bvid)
        
        if stream_type == 'raw':
            return jsonify({
                'info': video_info,
                'video': streamUrl[0],
                'audio': streamUrl[1]
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