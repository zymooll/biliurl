# biliurl 🎬🎵

你好！我是 **biliurl**，一个基于 Python + FastAPI 构建的多媒体播放代理服务。

## 我是谁？

我是专为 **VRChat（VRC）** 等客户端设计的统一媒体播放接口，支持：

- 🎵 **网易云音乐**：通过歌曲 ID 或关键词搜索播放音乐
- 📺 **哔哩哔哩（B站）**：通过 BV 号播放视频，支持多种清晰度

只需一个接口 `/play/vrc`，根据传入的参数自动分流到对应的播放源。

## 功能特性

- ✅ **统一播放入口**：`/play/vrc` 同时支持网易云音乐和 B 站视频
- ✅ **B站扫码登录**：支持扫描二维码登录，解锁 1080P 及更高清晰度
- ✅ **网易云音乐登录**：支持扫码、短信、密码及 Cookie 导入等多种登录方式
- ✅ **WebUI 管理界面**：可视化管理网易云 & B站账号登录状态
- ✅ **多清晰度支持**：B站视频支持 360P 至 1080P60（需大会员）
- ✅ **多音质支持**：网易云音乐支持标准、较高、极高、无损、Hi-Res 等音质

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

### 播放示例

```
# 播放 B站视频（720P）
GET /play/vrc?bvid=BV1HfK3zPEHE

# 播放 B站视频（1080P，需登录）
GET /play/vrc?bvid=BV1HfK3zPEHE&qn=80

# 播放网易云音乐（通过 ID）
GET /play/vrc?id=1856336348

# 播放网易云音乐（通过关键词搜索）
GET /play/vrc?keywords=周杰伦
```

## 参数说明

### B站视频清晰度（`qn` 参数）

| 值 | 清晰度 | 要求 |
|----|--------|------|
| 16 | 360P 流畅 | 无 |
| 32 | 480P 清晰 | 无 |
| **64** | **720P 高清（默认）** | 无 |
| 80 | 1080P 高清 | 需登录 |
| 112 | 1080P+ 高码率 | 需大会员 |
| 116 | 1080P60 高帧率 | 需大会员 |

### 网易云音质（`level` 参数）

| 值 | 音质 |
|----|------|
| standard | 标准 |
| higher | 较高 |
| exhigh | 极高 |
| lossless | 无损 |
| hires | Hi-Res |

## 目录结构

```
biliurl/
├── core/
│   ├── bili.py           # B站核心功能（登录、视频获取）
│   └── bili_cookie.py    # B站 Cookie 管理
├── ncm/
│   ├── api/              # FastAPI 路由与 Web 界面
│   ├── config.py         # 配置文件
│   └── main.py           # 应用入口
├── run_server.py         # 启动脚本
├── requirements.txt      # 依赖列表
└── BILI_API_README.md    # B站 API 详细文档
```

## 更多文档

- [B站 API 详细文档](BILI_API_README.md)
- [功能更新日志](BILI_UPDATE_LOG.md)
- [统一接口设计说明](UNIFIED_API_DESIGN.md)

## 依赖

- Python 3.8+
- FastAPI + Uvicorn
- requests、Pillow、qrcode 等（详见 `requirements.txt`）
