# biliurl 🎵📺

你好！我是 **biliurl**，一个统一媒体流服务器，专为 **VRChat** 等客户端设计。

我能让你通过一个简单的 HTTP 接口同时播放 **网易云音乐** 和 **哔哩哔哩视频**，无需关心两个平台的底层差异。

---

## ✨ 主要功能

- 🎵 **网易云音乐播放** — 按歌曲 ID 或关键词搜索并串流音乐，支持标准/高品质/无损等多种音质
- 📺 **哔哩哔哩视频播放** — 按 BV 号串流视频，支持 360P ~ 1080P60 多种清晰度
- 🔑 **统一登录管理** — 网页端扫码登录网易云 & B站，账号信息安全保存在服务器
- 📝 **歌词支持** — 自动获取并返回双语歌词（含翻译）
- 🖥️ **Web UI 管理面板** — 可视化登录状态、账号信息及播放控制
- ⚡ **动态线程池** — 自动按 CPU 核心数伸缩，高并发时稳定不崩

---

## 🚀 快速开始

### 1. 安装依赖

> 需要 **Python 3.7+**（推荐 Python 3.9 及以上）。

```bash
pip install -r requirements.txt
```

> 确保系统已安装 [FFmpeg](https://ffmpeg.org/)，可用 `bash check_ffmpeg.sh` 验证。

### 2. 启动服务器

```bash
python run_server.py
```

服务默认运行在 `http://localhost:7997`，浏览器打开即可看到 Web UI。

### 3. 登录账号（可选，解锁更高清晰度）

打开 Web UI → 点击顶部 **"登录管理"** → 扫码登录网易云 / 哔哩哔哩。

---

## 📡 核心接口

### 统一播放入口 `/play/vrc`

| 用途 | 示例 |
|------|------|
| 播放 B站视频（720P） | `GET /play/vrc?bvid=BV1HfK3zPEHE` |
| 播放 B站视频（1080P，需登录） | `GET /play/vrc?bvid=BV1HfK3zPEHE&qn=80` |
| 按 ID 播放网易云音乐 | `GET /play/vrc?id=1856336348` |
| 按关键词搜索并播放 | `GET /play/vrc?keywords=周杰伦` |
| 无损音质 | `GET /play/vrc?id=1856336348&level=lossless` |

接口会自动识别参数类型并分流到对应平台：

```
bvid=xxx      →  B站视频播放
id=BVxxx      →  B站视频播放（智能识别 BV 号）
id=数字       →  网易云音乐播放
keywords=xxx  →  网易云音乐搜索播放
```

### 其他常用接口

| 接口 | 说明 |
|------|------|
| `GET /` | Web UI 管理面板 |
| `GET /bili/login/qr` | 获取 B站登录二维码 |
| `GET /bili/login/info` | 查看 B站登录状态 |
| `GET /lyric?id=xxx` | 获取歌词（含翻译） |
| `GET /search?keywords=xxx` | 搜索歌曲 / 歌单 |
| `GET /threadpool/status` | 查看线程池状态 |

---

## 🎬 视频清晰度（`qn` 参数）

| qn 值 | 清晰度 | 要求 |
|-------|--------|------|
| 16 | 360P | 无 |
| 32 | 480P | 无 |
| **64** | **720P（默认）** | 无 |
| 80 | 1080P | 需登录 |
| 112 | 1080P+ | 需大会员 |
| 116 | 1080P60 | 需大会员 |

---

## 🎵 音乐音质（`level` 参数）

| level | 音质 |
|-------|------|
| `standard` | 标准 |
| `higher` | 较高 |
| `exhigh` | 极高 |
| `lossless` | 无损 |
| `hires` | Hi-Res |

---

## 🛠️ 技术栈

- **Python 3** + **FastAPI** + **Uvicorn**
- **FFmpeg** — 音视频处理与格式转换
- **SQLite** — 歌词及数据缓存
- **JSON** — Cookie 与配置持久化

---

## 📂 项目结构

```
biliurl/
├── run_server.py          # 服务入口（端口 7997）
├── requirements.txt       # Python 依赖
├── core/                  # B站核心模块
│   ├── bili.py            # BiliLogin / BiliVideo
│   └── bili_cookie.py     # 线程安全 Cookie 管理
└── ncm/                   # 网易云 & 主 API
    ├── main.py            # FastAPI 应用初始化
    ├── config.py          # 全局配置
    ├── api/routes.py      # 所有 API 路由（35+ 个接口）
    ├── core/              # 登录 / 音乐 / 视频 / 歌词
    └── utils/             # Cookie / 数据库 / 密码认证
```

---

## 📖 详细文档

- [B站 API 文档](./BILI_API_README.md) — B站接口说明与使用示例
- [功能更新说明](./BILI_UPDATE_LOG.md) — 各版本新增功能说明
- [统一接口设计](./UNIFIED_API_DESIGN.md) — `/play/vrc` 接口设计思路

---

## ⚠️ 注意事项

1. **账号共享（重要）** — 服务器上 **所有访问者共享同一个** B站 / 网易云登录账号，请勿在公开网络中部署。若需多用户隔离，请确保网络访问受限，并妥善保管账号安全。
2. **视频流有效期** — B站视频流 URL 有效期约 120 分钟，过期后重新请求即可
3. **防盗链** — 直接访问 B站视频流时，请确保设置 `Referer: https://www.bilibili.com`
4. **清晰度限制** — 未登录最高 720P；登录后可访问 1080P；大会员可访问更高清晰度
