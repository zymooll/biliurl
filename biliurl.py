import requests
import json
import time
import os
import subprocess
from pathlib import Path
from flask import Flask, send_file, jsonify, request
from io import BytesIO

app = Flask(__name__)

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

# Use pathlib for cross-platform paths
temp_dir = Path('temp')
output_dir = Path('output')

# Ensure directories exist
temp_dir.mkdir(parents=True, exist_ok=True)
output_dir.mkdir(parents=True, exist_ok=True)

def getCid(bvid):
    """Get the cid of video by bvid"""
    respCid = requests.get('https://api.bilibili.com/x/player/pagelist?bvid=' + bvid, headers=headers)
    plist = respCid.json()
    cid = str(plist['data'][0]['cid'])
    return cid

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
        stream_type = request.args.get('type', 'video').lower()
        
        if stream_type not in ['video', 'audio']:
            return jsonify({'error': 'Invalid type. Use type=video or type=audio'}), 400
        
        cid = getCid(bvid)
        streamUrl = getStream(bvid, cid, '-1')
        videoData, audioData = downloadStream(streamUrl)
        
        if stream_type == 'video':
            return send_file(videoData, mimetype='video/mp4', as_attachment=True, download_name=f'{bvid}.mp4')
        else:  # audio
            return send_file(audioData, mimetype='audio/mp4', as_attachment=True, download_name=f'{bvid}.m4a')
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)