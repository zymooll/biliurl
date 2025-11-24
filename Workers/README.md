# Biliurl - Cloudflare Workers 版本

这是原 Python Flask 应用的 Cloudflare Workers 实现，用于在边缘计算环境中下载 Bilibili 视频。

## 功能

✅ 获取 Bilibili 视频信息
✅ 下载视频和音频流
✅ API Key 认证系统
✅ 基于 Cookies 的 Pro 密钥支持
✅ 画质限制控制
✅ 在 Cloudflare Workers 上运行

## 安装

### 前置要求

- Node.js 18+
- Cloudflare 账户
- Wrangler CLI

```bash
npm install -g wrangler
```

### 设置

1. **安装依赖**

```bash
npm install
```

2. **配置 wrangler.toml**

编辑 `wrangler.toml` 文件：

```toml
name = "biliurl-workers"
main = "src/index.ts"
compatibility_date = "2024-01-01"

# 配置 KV 命名空间用于存储 cookies
[[kv_namespaces]]
binding = "COOKIES_KV"
id = "your_kv_namespace_id"
```

3. **创建 KV 命名空间**

```bash
wrangler kv:namespace create "biliurl-cookies"
# 记下返回的 ID，填入 wrangler.toml
```

## 使用

### 本地开发

```bash
npm run dev
```

访问 `http://localhost:8787`

### 部署到 Cloudflare

```bash
npm run deploy
```

## API 文档

### 获取 API 文档

```bash
curl https://your-worker.workers.dev/api/docs
```

### 登录 (获取 Pro Key)

```bash
curl -X POST https://your-worker.workers.dev/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "cookies": "SESSDATA=xxx; DedeUserID=xxx; ..."
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "登录成功",
  "pro_key": "pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh",
  "user_id": 12345
}
```

### 检查认证状态

```bash
curl https://your-worker.workers.dev/api/auth/status
```

**Response:**
```json
{
  "authenticated": true,
  "pro_key": "pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh"
}
```

### 下载视频

#### 获取原始流 URLs（推荐）

```bash
curl 'https://your-worker.workers.dev/api/bili/BV1234567890?key=public_j389u4tc9w08u4pq4mqp9xwup4&type=raw'
```

**Response:**
```json
{
  "info": {
    "title": "视频标题",
    "description": "视频描述",
    "duration": 1234,
    "author": "UP主",
    "cover": "https://...",
    "pubdate": 1234567890,
    "bvid": "BV1234567890"
  },
  "video_url": "https://vd1.bdstatic.com/...",
  "audio_url": "https://upos-sz-mirrorcos.bilivideo.com/...",
  "api_level": "720p 限制",
  "quality_used": "64"
}
```

#### 直接重定向下载（需要外部工具合成）

```bash
# 获取视频流 (返回 302 重定向)
curl -L 'https://your-worker.workers.dev/api/bili/BV1234567890?key=pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh&type=video&quality=125'

# 获取音频流 (返回 302 重定向)
curl -L 'https://your-worker.workers.dev/api/bili/BV1234567890?key=pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh&type=audio'
```

### 获取视频信息

```bash
curl 'https://your-worker.workers.dev/api/bili/BV1234567890/info?key=public_j389u4tc9w08u4pq4mqp9xwup4'
```

### 获取流 URLs

```bash
curl 'https://your-worker.workers.dev/api/bili/BV1234567890/streams?key=public_j389u4tc9w08u4pq4mqp9xwup4&quality=64'
```

## API Keys

### Public Key
- `public_j389u4tc9w08u4pq4mqp9xwup4` - 限制到 720p

### Pro Key
- `pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh` - 需要有效的 Bilibili cookies，可以获取 1080p

## 获取 Bilibili Cookies

### 方法 1: 浏览器开发者工具

1. 登录 [Bilibili.com](https://www.bilibili.com)
2. 按 F12 打开开发者工具
3. 进入 Application → Cookies
4. 找到 `bilibili.com` 域名
5. 复制以下 cookie 值：
   - `SESSDATA`
   - `DedeUserID`
   - `DedeUserID__ckMd5`
   - `bili_jct`
   - 等其他必要的 cookie

6. 组合成字符串：`SESSDATA=xxx; DedeUserID=xxx; DedeUserID__ckMd5=xxx; ...`

### 方法 2: 扫描二维码登录

可以在登录页面扫描二维码，获取对应的 cookies。

## 画质代码

| 代码 | 画质 |
|------|------|
| 16 | 360p |
| 32 | 480p |
| 64 | 720p |
| 125 | 1080p |
| 266 | 4K (需要会员) |

## 项目结构

```
Workers/
├── src/
│   ├── index.ts              # 主入口
│   ├── config.ts             # 配置文件
│   ├── types.ts              # TypeScript 类型定义
│   ├── bilibili.ts           # Bilibili API 交互
│   ├── cookies-manager.ts    # Cookies 管理
│   ├── auth.ts               # 认证和授权
│   ├── routes-login.ts       # 登录路由
│   └── routes-video.ts       # 视频路由
├── wrangler.toml             # Wrangler 配置
├── tsconfig.json             # TypeScript 配置
├── package.json              # 项目依赖
└── README.md                 # 本文件
```

## 限制

### Cloudflare Workers 限制
- 单次请求超时时间：30 秒（Streaming 模式）
- CPU 时间限制：30 秒
- 响应大小限制：128 MB
- 请求大小限制：100 MB

### 应用限制
- 无法直接下载完整的视频文件（大小超过限制）
- 返回流 URLs，用户需要使用外部工具（如 ffmpeg）来合成和下载

## 解决方案建议

### 下载完整视频

由于 Workers 的限制，推荐使用以下方案：

1. **客户端下载脚本**

```bash
#!/bin/bash
# 获取流 URLs
curl -s 'https://your-worker.workers.dev/api/bili/BV1234567890/streams?key=pro_xxx' \
  > streams.json

# 使用 ffmpeg 合成视频
VIDEO_URL=$(jq -r '.streams.video' streams.json)
AUDIO_URL=$(jq -r '.streams.audio' streams.json)

ffmpeg -i "$VIDEO_URL" -i "$AUDIO_URL" -c:v copy -c:a aac -shortest output.mp4
```

2. **自建下载服务**

在自己的服务器上使用 Python/Node.js 处理文件合成和下载。

## 注意事项

⚠️ **法律声明**

- 仅供学习和研究用途
- 不用于商业目的
- 遵守 Bilibili 服务条款
- 尊重内容创作者的版权

## 与原 Python 版本的区别

| 功能 | Python | Workers |
|------|--------|---------|
| 直接下载文件 | ✅ | ❌ (受限) |
| 返回流 URLs | ❌ | ✅ |
| Cookies 管理 | 本地文件 | KV 存储 |
| 部署方式 | 自建服务器 | Cloudflare |
| 成本 | 服务器费用 | 免费额度 |
| 画质限制 | 支持 | 支持 |

## 故障排除

### 问题：Pro Key 不能获取 1080p

**解决方案：**
1. 检查 cookies 是否仍然有效
2. 尝试重新登录
3. 确保使用了 `type=raw` 或 `type=video&quality=125`

### 问题：获取视频信息失败

**解决方案：**
1. 检查 bvid 是否正确
2. 确保 API Key 有效
3. 检查网络连接

### 问题：部署失败

**解决方案：**
1. 确认 Cloudflare 账户有效
2. 检查 `wrangler.toml` 配置
3. 运行 `wrangler login` 重新认证

## 贡献

欢迎提交 Issues 和 Pull Requests！

## 许可证

MIT License
