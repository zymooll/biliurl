import requests
import json
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

tempVideoFile = 'temp\\video.m4s'

tempAudioFile = 'temp\\audio.m4s'


# get the cid of video by bvid
def getCid(bvid, session=None, cookies=None):
    sess = session or requests
    respCid = sess.get(
        'https://api.bilibili.com/x/player/pagelist?bvid=' + bvid,
        headers=headers,
        cookies=cookies,
        timeout=15,
    )
    plist = respCid.json()
    cid = str(plist['data'][0]['cid'])
    return cid


# get video&audio stream by cid
def _select_best_stream(dash_list, prefer_id=None, max_id=None):
    if not dash_list:
        return None

    def _get_id(item):
        try:
            return int(item.get('id') or 0)
        except Exception:
            return 0

    candidates = list(dash_list)
    if max_id is not None:
        candidates = [x for x in candidates if _get_id(x) <= max_id]
        if not candidates:
            candidates = list(dash_list)

    if prefer_id is not None:
        for x in candidates:
            if _get_id(x) == prefer_id:
                return x

    return max(candidates, key=_get_id)


def getStream(bvid, cid, qn=125, session=None, cookies=None):
    sess = session or requests
    base_params = f'from_client=BROWSER&cid={cid}&qn={qn}&fourk=1&fnver=0&fnval=4048&bvid={bvid}'
    urls = [
        'https://api.bilibili.com/x/player/wbi/playurl?' + base_params,
        'https://api.bilibili.com/x/player/playurl?' + base_params,
    ]

    last_plist = None
    for url in urls:
        respUrl = sess.get(url, headers=headers, cookies=cookies, timeout=15)
        plist = respUrl.json()
        last_plist = plist
        if plist.get('code') == 0 and plist.get('data') and plist['data'].get('dash'):
            dash = plist['data']['dash']
            video = dash.get('video') or []
            audio = dash.get('audio') or []
            best_video = _select_best_stream(video)
            best_audio = _select_best_stream(audio)
            if best_video and best_audio:
                return [str(best_video.get('baseUrl')), str(best_audio.get('baseUrl'))]

    raise RuntimeError(f'Failed to get stream urls: {last_plist}')


# download video&audio stream
def downloadStream(streamUrl, videoFile=tempVideoFile, audioFile=tempAudioFile):  # 0:video 1:audio
    respVideo = requests.get(streamUrl[0], headers=headers)
    with open(videoFile, 'wb') as f:
        f.write(respVideo.content)
    respAudio = requests.get(streamUrl[1], headers=headers)
    with open(audioFile, 'wb') as f:
        f.write(respAudio.content)


# integrate video&audio stream
def integrateStream(outputFile, videoFile=tempVideoFile, audioFile=tempAudioFile):
    command = f'ffmpeg -i ' + videoFile + ' -i ' + audioFile + ' -c:v copy -c:a copy ' + outputFile
    os.system(command)


# remove temp downloaded file
def removeTempFile():
    os.remove(tempVideoFile)
    os.remove(tempAudioFile)


if __name__ == '__main__':
    infos = [['BV1HfK3zPEHE', 32]]
    for info in infos:
        bvid = info[0]
        qn = int(info[1])  # 16:360p 32:480p 64:720p 80/112/116/120/125 etc.
        print(bvid, qn)
        cid = getCid(bvid)
        streamUrl = getStream(bvid, cid, qn=qn)
        downloadStream(streamUrl)
        integrateStream('output\\BillUrl-' + time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime()) + '.mp4')
        removeTempFile()
