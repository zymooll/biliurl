# biliurl

你好！我是 **biliurl** —— 一个基于 FastAPI 的多媒体播放代理服务。🎉

## 我是谁？

我将**哔哩哔哩（B站）视频**与**网易云音乐**的媒体流统一封装为一个简洁的 HTTP 接口，方便各类客户端（如 VRChat、自定义播放器或网页）直接调用，无需关心底层鉴权与防盗链细节。

## 我能做什么？

| 功能 | 说明 |
|------|------|
| 🎬 B站视频播放 | 通过 BV 号获取视频直链，支持多种清晰度 |
| 🎵 网易云音乐播放 | 通过歌曲 ID 或关键词搜索获取音乐直链 |
| 🔐 B站扫码登录 | 支持 QR 二维码登录，解锁 1080P+ 高清视频 |
| 🔐 网易云登录 | 支持扫码、短信、密码、Cookie 多种登录方式 |
| 🖥️ WebUI 管理界面 | 内置网页管理面板，统一管理两个平台的登录状态 |

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
python run_server.py
```

服务默认运行在 `http://localhost:7997`。

## 核心接口

### 统一播放接口 `/play/vrc`

接口根据参数自动分流，选择对应的播放源：

```
GET /play/vrc?bvid=BV1HfK3zPEHE        # B站视频（默认 720P）
GET /play/vrc?bvid=BV1HfK3zPEHE&qn=80  # B站视频（1080P，需登录）
GET /play/vrc?id=1856336348             # 网易云音乐（按 ID）
GET /play/vrc?keywords=周杰伦           # 网易云音乐（按关键词搜索）
```

### B站视频清晰度（`qn` 参数）

| qn | 清晰度 | 要求 |
|----|--------|------|
| 16 | 360P | 无 |
| 32 | 480P | 无 |
| **64** | **720P（默认）** | 无 |
| 80 | 1080P | 需登录 |
| 112 | 1080P+ | 需大会员 |
| 116 | 1080P60 | 需大会员 |

### 网易云音质（`level` 参数）

| level | 音质 |
|-------|------|
| standard | 标准 |
| higher | 较高 |
| exhigh | 极高 |
| lossless | 无损 |
| hires | Hi-Res |

### B站登录接口

```
GET    /bili/login/qr        # 获取登录二维码
GET    /bili/login/poll      # 轮询登录状态
GET    /bili/login/info      # 查看当前登录信息
DELETE /bili/login           # 退出登录
```

> 详细接口文档请参阅 [BILI_API_README.md](./BILI_API_README.md)。

## 技术栈

- **后端框架：** FastAPI + Uvicorn
- **媒体处理：** ffmpeg-python
- **二维码：** qrcode + Pillow
- **加密：** cryptography
- **异步文件：** aiofiles

## 注意事项

- B站与网易云账号在服务器上**全局共享**，所有用户使用同一账号。
- B站视频流 URL 有效期约 **120 分钟**，过期后服务器会自动重新获取。
- Cookie 分别保存在 `bili_cookie.json` 与对应的网易云配置文件中。
