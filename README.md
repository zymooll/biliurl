# BiliURL — 媒体代理服务器

> 一个支持 **哔哩哔哩视频** 与 **网易云音乐** 的统一媒体播放代理服务，专为 VRChat 等场景设计。

---

## ✨ 功能特性

- 🎬 **B站视频播放** — 通过 BV 号直接获取视频流并重定向播放
- 🎵 **网易云音乐播放** — 通过歌曲 ID 或关键词搜索并播放
- 🔑 **账号登录管理** — 扫码登录 B站 / 网易云，解锁更高清晰度与音质
- 🖥️ **Web 管理界面** — 可视化管理登录状态、查看用户信息
- 🔀 **统一接口** — `/play/vrc` 单一入口，根据参数自动分流
- ⚡ **异步高性能** — 基于 FastAPI + 动态线程池，支持高并发请求

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

同时确保系统已安装 [FFmpeg](https://ffmpeg.org/download.html)。

### 2. 启动服务

```bash
python run_server.py
```

服务默认运行在 `http://localhost:7997`。

### 3. 访问 Web 界面

打开浏览器访问 `http://localhost:7997`，即可使用 Web 管理界面进行登录管理。

---

## 🎮 使用示例

### 播放 B站视频

```
GET /play/vrc?bvid=BV1HfK3zPEHE
GET /play/vrc?bvid=BV1HfK3zPEHE&qn=80   # 1080P（需登录）
```

### 播放网易云音乐

```
GET /play/vrc?id=1856336348
GET /play/vrc?keywords=周杰伦
```

### 在 HTML 中嵌入

```html
<!-- B站视频 -->
<video controls>
  <source src="http://localhost:7997/play/vrc?bvid=BV1HfK3zPEHE&qn=64" type="video/mp4">
</video>

<!-- 网易云音乐 -->
<video controls>
  <source src="http://localhost:7997/play/vrc?id=1856336348" type="video/mp4">
</video>
```

---

## 📡 主要 API

| 方法 | 接口 | 说明 |
|------|------|------|
| GET | `/play/vrc?bvid=...` | 播放 B站视频（302 重定向） |
| GET | `/play/vrc?id=...` | 播放网易云音乐 |
| GET | `/play/vrc?keywords=...` | 搜索并播放网易云音乐 |
| GET | `/bili/login/qr` | 获取 B站扫码登录二维码 |
| GET | `/bili/login/poll?qr_key=...` | 轮询 B站登录状态 |
| GET | `/bili/login/info` | 获取 B站登录信息 |
| DELETE | `/bili/login` | 退出 B站登录 |

更多详情请参阅 [BILI_API_README.md](BILI_API_README.md)。

---

## 🎞️ 清晰度说明（B站视频）

| `qn` 值 | 清晰度 | 要求 |
|---------|--------|------|
| 16 | 360P | 无 |
| 32 | 480P | 无 |
| **64** | **720P（默认）** | 无 |
| 80 | 1080P | 需登录 |
| 112 | 1080P+ 高码率 | 需大会员 |
| 116 | 1080P60 高帧率 | 需大会员 |

---

## 🛠️ 技术栈

- **后端框架**：[FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- **媒体处理**：[FFmpeg](https://ffmpeg.org/)
- **图像处理**：[Pillow](https://python-pillow.org/) + [qrcode](https://github.com/lincolnloop/python-qrcode)
- **HTTP 请求**：[requests](https://requests.readthedocs.io/)

---

## 📁 项目结构

```
biliurl/
├── core/
│   ├── bili.py           # B站核心功能（登录、视频流获取）
│   └── bili_cookie.py    # B站 Cookie 管理器
├── ncm/
│   ├── main.py           # FastAPI 应用入口
│   ├── config.py         # 全局配置
│   ├── api/
│   │   ├── routes.py     # API 路由定义
│   │   ├── templates/    # Web 界面模板
│   │   └── static/       # 静态资源（JS/CSS）
│   ├── core/             # 网易云核心逻辑
│   └── utils/            # 工具函数
├── requirements.txt      # Python 依赖
└── run_server.py         # 服务启动入口
```

---

## ⚠️ 注意事项

1. **防盗链**：访问 B站视频流时，客户端需设置 `Referer: https://www.bilibili.com`
2. **URL 有效期**：B站视频流 URL 有效期约 120 分钟，过期需重新请求
3. **账号共享**：B站和网易云账号在服务器上全局共享，所有用户使用同一账号
4. **清晰度限制**：未登录最高支持 720P，登录后可访问 1080P，大会员可访问更高清晰度
