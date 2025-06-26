import requests
import json
import ffmpeg
import time
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
tempVideoFile='temp\\video.m4s'
tempAudioFile='temp\\audio.m4s'

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
    respVideo=requests.get(streamUrl[0],headers=headers)
    with open(videoFile,'wb') as f:
        f.write(respVideo.content)
    respAudio=requests.get(streamUrl[1],headers=headers)
    with open(audioFile,'wb') as f:
        f.write(respAudio.content)

#integrate video&audio stream
def integrateStream(outputFile,videoFile=tempVideoFile,audioFile=tempAudioFile):
    command=f'ffmpeg -i '+videoFile+' -i '+audioFile+' -c:v copy -c:a copy '+outputFile
    os.system(command)

#remove temp downloaded file
def removeTempFile():
    os.remove(tempVideoFile)
    os.remove(tempAudioFile)

infos=[['BV1HfK3zPEHE',-2]]

for info in infos:
    bvid=info[0]
    quality=str(info[1]) #-1:360p -2:480p -3:720p -4:1080p
    print(bvid,quality)
    cid=getCid(bvid)
    streamUrl=getStream(bvid,cid,quality)
    downloadStream(streamUrl)
    integrateStream('output\\BillUrl-'+time.strftime('%Y-%m-%d-%H-%M-%S',time.localtime())+'.mp4')
    removeTempFile()