# 快速开始指南

## 前置要求

- Node.js 18 或更高版本
- Cloudflare 账户（免费账户即可）
- Wrangler CLI

## 步骤 1: 安装 Wrangler

```bash
npm install -g wrangler
```

验证安装：
```bash
wrangler --version
```

## 步骤 2: 登录 Cloudflare

```bash
wrangler login
```

这会打开浏览器进行认证。

## 步骤 3: 创建 KV 命名空间

```bash
# 创建生产 KV 命名空间
wrangler kv:namespace create "biliurl-cookies"

# 记下输出中的 ID，例如：
# 🎉 Created kv namespace 'biliurl-cookies'
# [[kv_namespaces]]
# binding = "COOKIES_KV"
# id = "xxx_xxx_xxx"
```

也可创建预览用命名空间：
```bash
wrangler kv:namespace create "biliurl-cookies" --preview
```

## 步骤 4: 更新 wrangler.toml

编辑 `Workers/wrangler.toml`，添加你的 KV 命名空间 ID：

```toml
name = "biliurl-workers"
main = "src/index.ts"
compatibility_date = "2024-01-01"

# 用你的实际 ID 替换
[[kv_namespaces]]
binding = "COOKIES_KV"
id = "你的_KV_ID_在这里"
```

## 步骤 5: 安装依赖

```bash
cd Workers
npm install
```

## 步骤 6: 本地测试

```bash
npm run dev
```

打开 http://localhost:8787

测试健康检查：
```bash
curl http://localhost:8787/health
```

## 步骤 7: 部署到 Cloudflare

```bash
npm run deploy
```

成功后会显示你的 Worker URL，例如：
```
✅ Deployed to https://biliurl-workers.your-account.workers.dev/
```

## 部署后的首次使用

### 1. 获取 Bilibili Cookies

访问 https://www.bilibili.com 并登录，然后：

1. 打开浏览器开发者工具（F12）
2. 进入 Application → Cookies → bilibili.com
3. 复制所有 cookies（或至少复制 SESSDATA, DedeUserID 等关键字段）

或者使用脚本自动提取：

```javascript
// 在 bilibili.com 的控制台执行此代码
document.cookie.split('; ').join('; ')
```

### 2. 登录获取 Pro Key

```bash
curl -X POST https://biliurl-workers.your-account.workers.dev/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "cookies": "SESSDATA=xxx; DedeUserID=xxx; ..."
  }'
```

成功响应示例：
```json
{
  "success": true,
  "message": "登录成功",
  "pro_key": "pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh",
  "user_id": 123456789
}
```

### 3. 获取视频流 URLs

使用 pro key 获取 1080p：

```bash
curl 'https://biliurl-workers.your-account.workers.dev/api/bili/BV1Xx411c7mD/streams?key=pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh&quality=125'
```

或使用 public key 获取 720p：

```bash
curl 'https://biliurl-workers.your-account.workers.dev/api/bili/BV1Xx411c7mD/streams?key=public_j389u4tc9w08u4pq4mqp9xwup4'
```

### 4. 下载视频

使用 ffmpeg 或其他工具合成下载：

```bash
#!/bin/bash

BVID="BV1Xx411c7mD"
API_KEY="pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh"
WORKER_URL="https://biliurl-workers.your-account.workers.dev"

# 获取流 URLs
STREAMS=$(curl -s "${WORKER_URL}/api/bili/${BVID}/streams?key=${API_KEY}&quality=125")

# 提取视频和音频 URL
VIDEO_URL=$(echo $STREAMS | jq -r '.streams.video')
AUDIO_URL=$(echo $STREAMS | jq -r '.streams.audio')

# 使用 ffmpeg 合成
ffmpeg -i "$VIDEO_URL" -i "$AUDIO_URL" \
  -c:v copy -c:a aac -shortest \
  -headers "Referer: https://www.bilibili.com" \
  "${BVID}.mp4"
```

## API 端点摘要

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/docs` | GET | API 文档 |
| `/api/login` | POST | 登录并存储 cookies |
| `/api/logout` | POST | 登出 |
| `/api/auth/status` | GET | 检查认证状态 |
| `/api/bili/:bvid` | GET | 下载视频/音频或获取原始 URLs |
| `/api/bili/:bvid/info` | GET | 获取视频信息 |
| `/api/bili/:bvid/streams` | GET | 获取流 URLs |

## 常见参数

### Query 参数

```
key              - API Key (必需)
type             - video|audio|raw (默认: video)
quality          - 画质代码: 16|32|64|125|266 (默认: max_quality)
```

### 画质代码

| 代码 | 画质 | 需求 |
|------|------|------|
| 16 | 360p | 无 |
| 32 | 480p | 无 |
| 64 | 720p | 无 |
| 125 | 1080p | 大会员 / pro key |
| 266 | 4K | 大会员 / pro key |

## 环境变量和自定义配置

### 修改 API 密钥

编辑 `src/config.ts` 中的 `DEFAULT_API_KEYS`：

```typescript
export const DEFAULT_API_KEYS: ApiKeysMap = {
  'your_public_key': {
    max_quality: '64',
    name: '720p 限制'
  }
};
```

### 自定义 Headers

修改 `src/config.ts` 中的 `BILIBILI_HEADERS`。

## 监控和调试

### 查看 Worker 日志

```bash
# 实时日志
wrangler tail

# 或在 Cloudflare Dashboard 查看：
# Workers & Pages → 你的 Worker → Logs
```

### 测试 Pro Key

```bash
# 检查认证状态
curl 'https://biliurl-workers.your-account.workers.dev/api/auth/status'

# 返回示例 (登录后):
# {"authenticated": true, "pro_key": "pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh"}
```

## 常见问题

### Q: Pro key 不能获取 1080p
**A:** 
- 检查 cookies 是否过期（需要重新登录）
- 确保使用 `quality=125` 参数
- 验证账号是否有大会员权限

### Q: Cookies 过期了怎么办
**A:** 重新登录即可：
```bash
curl -X POST https://biliurl-workers.your-account.workers.dev/api/login \
  -H "Content-Type: application/json" \
  -d '{"cookies": "新的_cookies"}'
```

### Q: 下载很慢
**A:**
- 这是 Bilibili 服务器限速，不是 Workers 的问题
- 尝试使用 aria2 或 curl 的多线程参数

### Q: 视频无法播放
**A:**
- 确保同时有视频和音频 URL
- 使用 ffmpeg 合成：`ffmpeg -i video.mp4 -i audio.m4a -c copy output.mp4`

## 扩展和自定义

### 添加自定义路由

在 `src/index.ts` 中添加新的路由：

```typescript
app.get('/custom/path', async (c: any) => {
  return c.json({ message: 'Custom response' });
});
```

### 使用 Workers KV 存储用户数据

```typescript
import { getCookies } from './cookies-manager';

// 在任何路由中
const cookies = await getCookies(c.env);
```

### 添加速率限制

可以使用 Cloudflare 的防护功能或自定义中间件实现。

## 安全注意事项

⚠️ **重要**：

1. **不要**将 API Keys 提交到公共仓库
2. **不要**在客户端代码中暴露 API Key
3. 考虑添加请求签名或时间戳验证
4. 定期更换 Cookies 和 API Keys
5. 使用 HTTPS（Workers 默认支持）

## 成本概览

Cloudflare Workers 免费额度（每月）：
- 100,000 个请求
- 30 毫秒 CPU 时间/请求

查看详情：https://developers.cloudflare.com/workers/platform/pricing/

## 后续步骤

1. ✅ 部署到 Cloudflare
2. 📝 配置自定义域名（可选）
3. 🔐 添加身份验证和速率限制
4. 📊 集成分析和监控
5. 🚀 扩展功能（如视频列表、搜索等）

## 需要帮助？

- 查看完整 README.md
- 查看 API 文档：`/api/docs`
- Cloudflare Workers 文档：https://developers.cloudflare.com/workers/
- Bilibili API 参考

祝你使用愉快！🚀
