# biliurl 🎬🎵

你好！我是 **biliurl**，一个基于 [FastAPI](https://fastapi.tiangolo.com/) 搭建的多媒体播放代理服务器。

## 我是谁？

我整合了 **哔哩哔哩（B站）** 视频与 **网易云音乐** 两大平台的播放能力，通过统一的 HTTP 接口向客户端（如 VRChat 等）提供音视频流。无需繁琐配置，一个接口即可玩转两大平台。

## 我能做什么？

### 🎬 B站视频播放

- 通过 BV 号获取视频流，支持 360P ~ 1080P60 多种清晰度
- 支持 B站账号扫码登录，登录后可解锁更高清晰度（1080P+、大会员内容）
- 视频流以 HTTP 302 重定向的方式返回，客户端直接播放

```
GET /play/vrc?bvid=BV1HfK3zPEHE&qn=64
```

### 🎵 网易云音乐播放

- 通过歌曲 ID 或关键词搜索，获取音频流并实时生成带封面的视频
- 支持标准、较高、极高、无损、Hi-Res 多种音质
- 支持网易云账号登录，解锁会员歌曲

```
GET /play/vrc?id=1856336348
GET /play/vrc?keywords=周杰伦
```

### 🖥️ Web 管理界面

访问根路径 `/` 即可打开 Web UI，支持：

- **网易云音乐**：扫码 / 短信 / 密码 / Cookie 导入登录
- **哔哩哔哩**：扫码登录
- 实时查看登录状态（用户名、UID、等级）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务器

```bash
python run_server.py
```

服务器默认监听 `http://0.0.0.0:7997`。

### 3. 播放示例

```
# B站视频（720P）
http://localhost:7997/play/vrc?bvid=BV1HfK3zPEHE

# B站视频（1080P，需登录）
http://localhost:7997/play/vrc?bvid=BV1HfK3zPEHE&qn=80

# 网易云音乐（按ID）
http://localhost:7997/play/vrc?id=1856336348

# 网易云音乐（按关键词）
http://localhost:7997/play/vrc?keywords=晴天
```

## 接口参数说明

### `/play/vrc` 统一播放接口

| 参数 | 说明 | 示例 |
|------|------|------|
| `bvid` | B站视频 BV 号（与 `id`/`keywords` 互斥） | `BV1HfK3zPEHE` |
| `qn` | B站清晰度（默认 64） | `16`/`32`/`64`/`80`/`112`/`116` |
| `id` | 网易云歌曲 ID | `1856336348` |
| `keywords` | 网易云搜索关键词 | `周杰伦` |
| `level` | 网易云音质（默认 standard） | `standard`/`higher`/`exhigh`/`lossless`/`hires` |

### B站清晰度对照表

| `qn` 值 | 清晰度 | 要求 |
|---------|--------|------|
| 16 | 360P | 无 |
| 32 | 480P | 无 |
| **64** | **720P（默认）** | 无 |
| 80 | 1080P | 需登录 |
| 112 | 1080P+ | 需大会员 |
| 116 | 1080P60 | 需大会员 |

## 技术栈

- **后端框架**：FastAPI + Uvicorn
- **B站模块**：`core/bili.py`（登录 & 视频流获取）
- **Cookie 管理**：`core/bili_cookie.py`（线程安全）
- **前端**：原生 HTML/CSS/JavaScript

## 注意事项

- B站和网易云登录账号在服务器上**全局共享**，所有用户使用同一账号
- B站视频流 URL 有效期约 **120 分钟**，过期后自动重新获取
- 访问 B站视频流时需设置正确的 `Referer: https://www.bilibili.com`

## 依赖

```
requests, Pillow, qrcode, fastapi, uvicorn, ffmpeg-python, aiofiles
```

---

> 设计理念：**一个接口，多种可能** 🚀
