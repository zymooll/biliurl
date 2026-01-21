# B站视频播放功能 API 文档

## 概述

为服务器的 `/play/vrc` 接口添加了 B站视频播放支持。现在该接口支持：
1. **网易云音乐播放** - 提供 `id` 或 `keywords` 参数
2. **B站视频播放** - 提供 `bvid` 参数

接口会根据参数自动分流到对应的处理逻辑。

同时添加了 `/bili/login/*` 接口用于 B站账号登录管理。

## API 接口说明

### 1. 获取登录二维码

**请求:**
```
GET /bili/login/qr
```

**响应:**
```json
{
  "code": 200,
  "qr_url": "https://passport.bilibili.com/...",
  "qr_key": "abc123...",
  "qr_img": "data:image/png;base64,..." // 可选，base64编码的二维码图片
}
```

### 2. 轮询登录状态

**请求:**
```
GET /bili/login/poll?qr_key=abc123...
```

**响应:**
```json
{
  "code": 86101,  // 86101=等待扫码, 86090=已扫码待确认, 86038=已失效, 0=成功
  "message": "等待扫码"
}
```

登录成功后，Cookie 会自动保存到服务器，所有用户共享（类似 ncm 的处理方式）。

### 3. 获取登录信息

**请求:**
```
GET /bili/login/info
```

**响应（已登录）:**
```json
{
  "code": 200,
  "logged_in": true,
  "mid": 123456,
  "uname": "用户名",
  "face": "https://...",
  "vip_status": 1,
  "level": 6
}
```

**响应（未登录）:**
```json
{
  "code": 401,
  "logged_in": false,
  "message": "未登录"
}
```

### 4. 退出登录

**请求:**
```
DELETE /bili/login
```

**响应:**
```json
{
  "code": 200,
  "message": "已退出登录"
}
```

### 5. 播放视频/音乐（统一接口）

#### 播放 B站视频

**请求:**
```
GET /play/vrc?bvid=BV1HfK3zPEHE&qn=64
```

**参数:**
- `bvid` (必需): 视频的BV号，例如 `BV1HfK3zPEHE`
- `qn` (可选): 清晰度，默认 64
  - 16 = 360P 流畅
  - 32 = 480P 清晰
  - 64 = 720P 高清（默认）
  - 80 = 1080P 高清（需登录）
  - 112 = 1080P+ 高码率（需大会员）
  - 116 = 1080P60 高帧率（需大会员）

**响应:**
- HTTP 302 重定向到 B站视频流 URL
- 客户端会自动跳转到视频地址

#### 播放网易云音乐

**请求:**
```
GET /play/vrc?id=1856336348
```

**参数:**
- `id` (可选): 歌曲ID
- `keywords` (可选): 搜索关键词
- `level` (可选): 音质等级
- 其他网易云相关参数...

**说明:** 
- 接口会根据参数自动识别：
  - 提供 `bvid` → B站视频播放
  - 提供 `id` 或 `keywords` → 网易云音乐播放

**错误响应:**
```json
{
  "detail": "错误信息"
}
```

## 使用示例

### Web 前端登录流程

```javascript
// 1. 获取二维码
const qrResp = await fetch('/bili/login/qr');
const qrData = await qrResp.json();

// 显示二维码图片
document.getElementById('qr-img').src = qrData.qr_img;

// 2. 轮询登录状态
const pollInterval = setInterval(async () => {
  const statusResp = await fetch(`/bili/login/poll?qr_key=${qrData.qr_key}`);
  const statusData = await statusResp.json();
  
  if (statusData.code === 0) {
    // 登录成功
    clearInterval(pollInterval);
    alert('登录成功！');
  } else if (statusData.code === 86038) {
    // 二维码过期
    clearInterval(pollInterval);
    alert('二维码已过期，请刷新');
  }
}, 2000); // 每2秒检查一次
```

### 直接播放视频

在 HTML 中：
```html
<!-- B站视频 -->
<video controls>
  <source src="/play/vrc?bvid=BV1HfK3zPEHE&qn=64" type="video/mp4">
</video>

<!-- 网易云音乐 -->
<video controls>
  <source src="/play/vrc?id=1856336348" type="video/mp4">
</video>
```

或直接在浏览器中访问：
```
# B站视频
http://localhost:8000/play/vrc?bvid=BV1HfK3zPEHE

# 网易云音乐
http://localhost:8000/play/vrc?id=1856336348
```

### Python 客户端示例

```python
import requests

# 下载B站视频
bvid = "BV1HfK3zPEHE"
response = requests.get(
    f"http://localhost:8000/play/vrc?bvid={bvid}&qn=64",
    allow_redirects=True,
    headers={
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://www.bilibili.com'
    }
)

with open(f'{bvid}.mp4', 'wb') as f:
    f.write(response.content)

# 下载网易云音乐
song_id = "1856336348"
response = requests.get(
    f"http://localhost:8000/play/vrc?id={song_id}",
    headers={
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://www.bilibili.com'
    }
)
```

## 技术说明

### 架构设计

#### 统一入口 - 参数分流

`/play/vrc` 接口现在支持两种播放模式：

**1. B站视频模式（提供 `bvid` 参数）**
```
/play/vrc?bvid=BV1HfK3zPEHE&qn=64
```
- 检测到 `bvid` 参数后，自动路由到 B站视频处理逻辑
- 调用 `BiliVideo.getPlayUrl()` 获取视频流 URL
- 返回 302 重定向到视频流

**2. 网易云音乐模式（提供 `id` 或 `keywords` 参数）**
```
/play/vrc?id=1856336348
/play/vrc?keywords=周杰伦
```
- 检测到 `id` 或 `keywords` 参数后，路由到网易云处理逻辑
- 原有的音频+歌词+视频生成流程不变

#### 核心模块

1. **核心模块** (`core/bili.py`):
   - `BiliLogin`: 处理登录逻辑
   - `BiliVideo`: 处理视频流获取

2. **Cookie 管理** (`core/bili_cookie.py`):
   - 线程安全的 Cookie 存储和读取
   - 所有用户共享同一个 B站账号
   - 自动缓存机制

3. **API 路由** (`ncm/api/routes.py`):
   - RESTful 风格的接口设计
   - 统一的错误处理

### 视频流说明

- 优先返回 MP4 格式（`fnval=1`），便于直接重定向播放
- 视频流 URL 有效期为 120 分钟
- B站防盗链需要正确的 Referer 和 User-Agent
- 未登录时最高支持 720P
- 登录后可访问 1080P
- 大会员可访问更高清晰度

### 配置文件

在 `ncm/config.py` 中添加：
```python
BILI_COOKIE_FILE = "bili_cookie.json"  # B站Cookie存储文件
DEFAULT_BILI_QUALITY = 64  # 默认清晰度 (720P)
```

## 注意事项

1. **防盗链**: B站视频流需要正确的 Referer，建议客户端设置 `Referer: https://www.bilibili.com`
2. **URL 有效期**: 视频流 URL 有效期 120 分钟，过期需重新获取
3. **账号共享**: 所有用户共享同一个 B站登录账号
4. **清晰度限制**: 
   - 未登录最高 720P
   - 登录后可访问 1080P
   - 大会员可访问更高清晰度（1080P+、4K 等）

## 依赖

确保已安装以下依赖：
```bash
pip install requests qrcode pillow fastapi
```
