import requests
import urllib
import json
import ffmpeg
import os

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

bvid='BV1kK4y1Y7Zq'
respCid=requests.get('https://api.bilibili.com/x/player/pagelist?bvid='+bvid,headers=headers)
plist=respCid.json()
cid=str(plist['data'][0]['cid'])

respUrl=requests.get('https://api.bilibili.com/x/player/wbi/playurl?from_client=BROWSER&cid='+cid+'&qn=125&fourk=1&fnver=0&fnval=4048&bvid='+bvid,headers=headers)
plist=respUrl.json()
# -1:360p -2:480p -3:720p -4:1080p
streamUrlVideo=str(plist['data']['dash']['video'][0]['baseUrl'])
streamUrlAudio=str(plist['data']['dash']['audio'][0]['baseUrl'])

respVideo=requests.get(streamUrlVideo,headers=headers)
with open(r'video.m4s','wb') as f:
    f.write(respVideo.content)

respAudio=requests.get(streamUrlAudio,headers=headers)
with open(r'audio.m4s','wb') as f:
    f.write(respAudio.content)

videoFile=r"C:\Coding\biliurl\video.m4s"
audioFile=r"C:\Coding\biliurl\audio.m4s"
outputFile='output.mp4'
command=f"ffmpeg -i "+videoFile+" -i "+audioFile+" -c:v copy -c:a copy "+outputFile
os.system(command)
