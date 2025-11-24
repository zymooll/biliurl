import requests
import json
import time
import os
import subprocess
from pathlib import Path

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
tempVideoFile = temp_dir / 'video.m4s'
tempAudioFile = temp_dir / 'audio.m4s'

#get the cid of video by bvid
def getCid(bvid):
    respCid=requests.get('https://api.bilibili.com/x/player/pagelist?bvid='+bvid,headers=headers)
    plist=respCid.json()
    cid=str(plist['data'][0]['cid'])
    return cid

#get video&audio stream by cid
def getStream(bvid,cid,quality):
    respUrl=requests.get('https://api.bilibili.com/x/player/wbi/playurl?from_client=BROWSER&cid='+cid+'&qn=125&fourk=1&fnver=0&fnval=4048&bvid='+bvid,headers=headers)
    plist=respUrl.json()
    streamUrlVideo=str(plist['data']['dash']['video'][0]['baseUrl'])
    streamUrlAudio=str(plist['data']['dash']['audio'][0]['baseUrl'])
    return [streamUrlVideo,streamUrlAudio]

#download video&audio stream
def downloadStream(streamUrl,videoFile=tempVideoFile,audioFile=tempAudioFile): # 0:video 1:audio
    # ensure temp dir exists
    temp_dir.mkdir(parents=True, exist_ok=True)

    # stream download to avoid loading whole file into memory
    respVideo = requests.get(streamUrl[0], headers=headers, stream=True)
    respVideo.raise_for_status()
    with open(videoFile, 'wb') as f:
        for chunk in respVideo.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    respAudio = requests.get(streamUrl[1], headers=headers, stream=True)
    respAudio.raise_for_status()
    with open(audioFile, 'wb') as f:
        for chunk in respAudio.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

#integrate video&audio stream
def integrateStream(outputFile,videoFile=tempVideoFile,audioFile=tempAudioFile):
    # ensure output dir exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # call ffmpeg safely using a list of args
    cmd = [
        'ffmpeg', '-y',
        '-fflags', '+igndts',
        '-i', str(videoFile),
        '-fflags', '+igndts',
        '-i', str(audioFile),
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '128k',
        str(outputFile)
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print('ffmpeg failed:', e)

#remove temp downloaded file
def removeTempFile():
    for p in (tempVideoFile, tempAudioFile):
        try:
            if p.exists():
                p.unlink()
        except Exception as e:
            print(f'failed to remove {p}:', e)

infos = [['BV1u9kUBfEZA', -1]]

for info in infos:
    bvid = info[0]
    quality = str(info[1])  # -1:360p -2:480p -3:720p -4:1080p
    print(bvid, quality)
    cid = getCid(bvid)
    streamUrl = getStream(bvid, cid, quality)
    downloadStream(streamUrl)

    timestamp = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())
    output_file = output_dir / f'BillUrl-{timestamp}.mp4'
    integrateStream(output_file)
    #removeTempFile()