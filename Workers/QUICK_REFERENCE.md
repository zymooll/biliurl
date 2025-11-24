# Biliurl Workers - 快速参考

## 基础信息

- **Worker URL**: https://biliurl-workers.shirasuazusa.workers.dev
- **Public API Key**: `public_j389u4tc9w08u4pq4mqp9xwup4`
- **Base BVID**: `BV1Qj1tB5ESY` (用于测试)

---

## 一键命令

### 1️⃣ 获取视频信息
```bash
curl "https://biliurl-workers.shirasuazusa.workers.dev/api/bili/BV1Qj1tB5ESY/info?key=public_j389u4tc9w08u4pq4mqp9xwup4" | jq
```

### 2️⃣ 获取流 URLs（推荐）
```bash
curl "https://biliurl-workers.shirasuazusa.workers.dev/api/bili/BV1Qj1tB5ESY/streams?key=public_j389u4tc9w08u4pq4mqp9xwup4&quality=64" | jq '.streams'
```

### 3️⃣ 下载视频（3 行代码）
```bash
# 替换 BV 号
BVID="BV1Qj1tB5ESY"
KEY="public_j389u4tc9w08u4pq4mqp9xwup4"

# 获取 URL
RESPONSE=$(curl -s "https://biliurl-workers.shirasuazusa.workers.dev/api/bili/$BVID/streams?key=$KEY&quality=64")
VIDEO_URL=$(echo "$RESPONSE" | jq -r '.streams.video')
AUDIO_URL=$(echo "$RESPONSE" | jq -r '.streams.audio')

# 合成
ffmpeg -i "$VIDEO_URL" -i "$AUDIO_URL" -c:v copy -c:a aac -shortest output.mp4
```

### 4️⃣ 重定向下载（最简单）
```bash
KEY="public_j389u4tc9w08u4pq4mqp9xwup4"
curl -L "https://biliurl-workers.shirasuazusa.workers.dev/api/bili/BV1Qj1tB5ESY?key=$KEY&type=video&quality=64" -o video.m4s
curl -L "https://biliurl-workers.shirasuazusa.workers.dev/api/bili/BV1Qj1tB5ESY?key=$KEY&type=audio" -o audio.m4s
```

---

## 画质参数

| 代码 | 画质 | Public | Pro |
|------|------|--------|-----|
| 16 | 360p | ✅ | ✅ |
| 32 | 480p | ✅ | ✅ |
| 64 | 720p | ✅ | ✅ |
| 125 | 1080p | ❌ | ✅ |
| 266 | 4K | ❌ | ✅ |

**示例**：获取 1080p（需要 Pro Key）
```bash
curl "https://biliurl-workers.shirasuazusa.workers.dev/api/bili/BV1Qj1tB5ESY/streams?key=pro_KEY&quality=125" | jq
```

---

## Pro Key 获取

### 1. 获取 Cookies

登录 bilibili.com，F12 → Application → Cookies，复制整个 Cookie 字符串

### 2. 登录 Workers

```bash
curl -X POST "https://biliurl-workers.shirasuazusa.workers.dev/api/login" \
  -H "Content-Type: application/json" \
  -d '{
    "cookies": "SESSDATA=xxx;DedeUserID=xxx;..."
  }'
```

会返回你的 Pro Key

### 3. 使用 Pro Key

```bash
curl "https://biliurl-workers.shirasuazusa.workers.dev/api/bili/BV1Qj1tB5ESY/streams?key=pro_xxx&quality=125" | jq
```

---

## 常见错误

### ❌ 403 错误
**原因**: URL 过期或直接 curl 访问  
**解决**: 在浏览器中访问或使用 ffmpeg

### ❌ JSON 解析错误
**原因**: 获取的是 HTML 而不是 JSON  
**解决**: 检查 API Key 和 BV 号是否正确

### ❌ 网络超时
**原因**: 网络慢或 Bilibili 服务不可用  
**解决**: 重试或检查网络连接

---

## 批量下载脚本

```bash
#!/bin/bash

KEY="public_j389u4tc9w08u4pq4mqp9xwup4"
BVIDS=("BV1Qj1tB5ESY" "BV1xxx" "BV1yyy")

for BVID in "${BVIDS[@]}"; do
  echo "正在下载 $BVID..."
  RESPONSE=$(curl -s "https://biliurl-workers.shirasuazusa.workers.dev/api/bili/$BVID/streams?key=$KEY&quality=64")
  VIDEO_URL=$(echo "$RESPONSE" | jq -r '.streams.video')
  AUDIO_URL=$(echo "$RESPONSE" | jq -r '.streams.audio')
  TITLE=$(echo "$RESPONSE" | jq -r '.info.title')
  
  ffmpeg -i "$VIDEO_URL" -i "$AUDIO_URL" -c:v copy -c:a aac -shortest "$TITLE.mp4"
done
```

---

## 检查状态

```bash
# 健康检查
curl "https://biliurl-workers.shirasuazusa.workers.dev/health" | jq

# 认证状态
curl "https://biliurl-workers.shirasuazusa.workers.dev/api/auth/status" | jq

# API 文档
curl "https://biliurl-workers.shirasuazusa.workers.dev/api/docs" | jq
```

---

## 环境变量快捷设置

```bash
# 保存到 ~/.bashrc 或 ~/.zshrc
export BILIURL_WORKER="https://biliurl-workers.shirasuazusa.workers.dev"
export BILIURL_KEY="public_j389u4tc9w08u4pq4mqp9xwup4"

# 然后可以直接用：
curl "$BILIURL_WORKER/api/bili/BV1Qj1tB5ESY/streams?key=$BILIURL_KEY&quality=64" | jq
```

---

## 更多帮助

- 详细文档：[USAGE_GUIDE.md](./USAGE_GUIDE.md)
- 部署信息：[DEPLOYMENT_SUMMARY.md](./DEPLOYMENT_SUMMARY.md)
- 调试报告：[DEBUG_REPORT.md](./DEBUG_REPORT.md)

---

**最后更新**: 2025-11-24
