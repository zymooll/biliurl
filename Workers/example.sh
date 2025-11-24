#!/bin/bash

# Biliurl Workers - 使用示例脚本
# 
# 使用方法: ./example.sh <worker_url> <api_key> <bvid>
# 示例: ./example.sh https://biliurl.workers.dev pro_xxx BV1Xx411c7mD

set -e

# 检查参数
if [ $# -lt 3 ]; then
    echo "Usage: $0 <worker_url> <api_key> <bvid>"
    echo ""
    echo "Examples:"
    echo "  $0 https://biliurl.workers.dev public_j389u4tc9w08u4pq4mqp9xwup4 BV1Xx411c7mD"
    echo "  $0 https://biliurl.workers.dev pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh BV1Xx411c7mD"
    exit 1
fi

WORKER_URL=$1
API_KEY=$2
BVID=$3

echo "=========================================="
echo "Biliurl Workers - 下载示例"
echo "=========================================="
echo "Worker URL: $WORKER_URL"
echo "API Key: ${API_KEY:0:20}..."
echo "BVID: $BVID"
echo ""

# 步骤 1: 获取视频信息
echo "[1/4] 获取视频信息..."
INFO=$(curl -s "${WORKER_URL}/api/bili/${BVID}/info?key=${API_KEY}")
echo "✓ 完成"

# 提取标题
TITLE=$(echo $INFO | jq -r '.title // "unknown"')
echo "标题: $TITLE"

# 步骤 2: 获取流 URLs
echo ""
echo "[2/4] 获取流 URLs..."
STREAMS=$(curl -s "${WORKER_URL}/api/bili/${BVID}/streams?key=${API_KEY}&quality=125")
echo "✓ 完成"

# 提取 URLs
VIDEO_URL=$(echo $STREAMS | jq -r '.streams.video // empty')
AUDIO_URL=$(echo $STREAMS | jq -r '.streams.audio // empty')
QUALITY=$(echo $STREAMS | jq -r '.quality_used // "未知"')

if [ -z "$VIDEO_URL" ] || [ -z "$AUDIO_URL" ]; then
    echo "❌ 错误: 无法获取视频或音频 URL"
    exit 1
fi

echo "视频 URL: ${VIDEO_URL:0:80}..."
echo "音频 URL: ${AUDIO_URL:0:80}..."
echo "使用画质: $QUALITY"

# 步骤 3: 生成输出文件名
echo ""
echo "[3/4] 准备下载..."
OUTPUT_FILE="${BVID}.mp4"

# 检查 ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ 需要安装 ffmpeg"
    echo ""
    echo "安装 ffmpeg:"
    echo "  macOS:   brew install ffmpeg"
    echo "  Ubuntu:  sudo apt install ffmpeg"
    echo "  Windows: choco install ffmpeg"
    exit 1
fi

# 步骤 4: 下载并合成
echo "[4/4] 使用 ffmpeg 下载并合成..."
echo "输出文件: $OUTPUT_FILE"
echo ""

ffmpeg -i "$VIDEO_URL" \
       -i "$AUDIO_URL" \
       -c:v copy \
       -c:a aac \
       -shortest \
       -headers "Referer: https://www.bilibili.com" \
       "$OUTPUT_FILE" \
       -loglevel warning

echo ""
echo "=========================================="
echo "✅ 下载完成!"
echo "文件: $(pwd)/$OUTPUT_FILE"
echo "大小: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo "=========================================="
