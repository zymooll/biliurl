import requests, time, qrcode
import pickle
import sys, os
import shutil
import ffmpeg
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QTimer, QThread

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

cookies = None
saveDir = "./"

# Use pathlib for cross-platform paths
temp_dir = Path('temp')
output_dir = Path('output')
tempVideoFile = temp_dir / 'video.m4s'
tempAudioFile = temp_dir / 'audio.m4s'

def resourcePath(relativePath):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relativePath)
    return os.path.join(os.path.abspath("."), relativePath)

# Download helper functions from biliurl.py
def getCid(bvid, cookies):
    respCid = requests.get('https://api.bilibili.com/x/player/pagelist?bvid=' + bvid, 
                          headers=headers, cookies=cookies)
    plist = respCid.json()
    cid = str(plist['data'][0]['cid'])
    return cid

def getStream(bvid, cid, cookies):
    respUrl = requests.get('https://api.bilibili.com/x/player/wbi/playurl?from_client=BROWSER&cid=' + cid + 
                          '&qn=125&fourk=1&fnver=0&fnval=4048&bvid=' + bvid, 
                          headers=headers, cookies=cookies)
    plist = respUrl.json()
    streamUrlVideo = str(plist['data']['dash']['video'][0]['baseUrl'])
    streamUrlAudio = str(plist['data']['dash']['audio'][0]['baseUrl'])
    return [streamUrlVideo, streamUrlAudio]

def downloadStream(streamUrl, cookies, videoFile=tempVideoFile, audioFile=tempAudioFile):
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    def _download_to_path(url, path):
        resp = requests.get(url, headers=headers, cookies=cookies, stream=True)
        resp.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(_download_to_path, streamUrl[0], videoFile): 'video',
            executor.submit(_download_to_path, streamUrl[1], audioFile): 'audio'
        }
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                fut.result()
            except Exception as e:
                print(f'{name} download failed:', e)
                raise

def integrateStream(outputFile, videoFile=tempVideoFile, audioFile=tempAudioFile):
    output_dir.mkdir(parents=True, exist_ok=True)
    if not shutil.which('ffmpeg'):
        print("ffmpeg executable not found in PATH. Install ffmpeg and try again.")
        raise FileNotFoundError('ffmpeg executable not found')
    
    try:
        v_input = ffmpeg.input(str(videoFile))
        a_input = ffmpeg.input(str(audioFile))
        out = ffmpeg.output(v_input, a_input, str(outputFile), vcodec='copy', acodec='copy')
        out = out.overwrite_output()
        out.run(capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as e:
        print('ffmpeg failed:', e)
        raise

def removeTempFile(videoFile=tempVideoFile, audioFile=tempAudioFile):
    for p in (videoFile, audioFile):
        try:
            if isinstance(p, Path) and p.exists():
                p.unlink()
            elif isinstance(p, str) and os.path.exists(p):
                os.remove(p)
        except Exception as e:
            print(f'failed to remove {p}:', e)

class downloadManager(QThread):
    def __init__(self, bvid, cookies, saveDir):
        super().__init__()
        self.bvid = bvid
        self.cookies = cookies
        self.saveDir = saveDir
    
    def run(self):
        try:
            cid = getCid(self.bvid, self.cookies)
            streamUrl = getStream(self.bvid, cid, self.cookies)
            downloadStream(streamUrl, self.cookies)
            
            output_file = Path(self.saveDir) / f'{self.bvid}.mp4'
            integrateStream(output_file)
            removeTempFile()
        except Exception as e:
            print(f'Download failed: {e}')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(resourcePath("./ui/main.ui"), self)
        self.setWindowTitle("biliDownloader")
        self.LoginStatus.setText("未登录")
        self.DownloadStatus.setText("未开始...")
        self.OutputFileInput.setText(saveDir)
        self.ConfirmBVBtn.clicked.connect(self.startDownload)
        self.OutputFileChangeBtn.clicked.connect(self.chooseSavePath)
        self.RefreshLoginBtn.clicked.connect(self.refreshLoginStatus)
        if os.path.exists('cookies.pkl'):
            with open('cookies.pkl', 'rb') as f:
                global cookies
                cookies = pickle.load(f)
            self.LoginStatus.setText("已登录")
    
    def startDownload(self):
        bvid = self.BVInput.text()
        self.downloadThread = downloadManager(bvid, cookies, saveDir)
        self.downloadThread.start()
        self.DownloadStatus.setText("下载中...")
        self.downloadThread.finished.connect(lambda: self.DownloadStatus.setText("下载完成，等待下一次下载..."))
    
    def refreshLoginStatus(self):
        global cookies
        if cookies is not None:
            return
        if os.path.exists('cookies.pkl'):
            with open('cookies.pkl', 'rb') as f:
                cookies = pickle.load(f)
            self.LoginStatus.setText("已登录")
        else:
            QRShowWindow.showQRCode()
    
    def chooseSavePath(self):
        global saveDir
        saveDir = QFileDialog.getExistingDirectory(None, "选取文件夹", "C:/")
        self.OutputFileInput.setText(saveDir)

class QRShow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(resourcePath("./ui/QRShow.ui"), self)
        self.setWindowTitle("QR Code")
    
    def getQRCode(self):
        respLogin = requests.get('https://passport.bilibili.com/x/passport-login/web/qrcode/generate', headers=headers)
        QRUrl = respLogin.json()['data']['url']
        QRKey = respLogin.json()['data']['qrcode_key']
        QRImg = qrcode.QRCode()
        QRImg.add_data(QRUrl)
        QRImg.make()
        Img = QRImg.make_image()
        temp_dir.mkdir(parents=True, exist_ok=True)
        Img.save(str(temp_dir / "QRCode.png"))
        self.QRImg.setPixmap(QPixmap(str(temp_dir / "QRCode.png")).scaled(280, 280))
        return QRKey
    
    def checkLoginStatus(self, QRKey):
        respStatus = requests.get('https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key=' + QRKey, headers=headers)
        respCode = int(respStatus.json()['data']['code'])
        if respCode == 86038:
            QRKey = self.getQRCode()
            self.Status.setText('上一二维码已失效，请用新二维码扫码')
        elif respCode == 86101:
            self.Status.setText('等待扫码')
        elif respCode == 86090:
            self.Status.setText('已扫码，等待确认')
        elif respCode == 0:
            self.Status.setText('登录成功')
            global cookies
            cookies = respStatus.cookies
            with open('cookies.pkl', 'wb') as f:
                pickle.dump(respStatus.cookies, f)
            self.timer.stop()
            window.LoginStatus.setText("已登录")
            self.hide()
    
    def showQRCode(self):
        self.Status.setText("等待扫码")
        QRKey = self.getQRCode()
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.checkLoginStatus(QRKey))
        self.timer.start(1000)
        self.show()
    
    def closeEvent(self, event):
        self.timer.stop()
        qr_file = temp_dir / "QRCode.png"
        try:
            if qr_file.exists():
                qr_file.unlink()
        except Exception as e:
            print(f'failed to remove QRCode.png: {e}')
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    QRShowWindow = QRShow()
    window.show()
    sys.exit(app.exec())
