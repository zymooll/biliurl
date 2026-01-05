#!/bin/bash

echo "=========================================="
echo "FFmpeg 硬件加速检测工具"
echo "=========================================="
echo ""

# 1. 检查 DRI 设备
echo "1️⃣ 检查 DRI 设备："
ls -la /dev/dri/ 2>/dev/null || echo "❌ /dev/dri/ 不存在"
echo ""

# 2. 检查 FFmpeg 支持的硬件加速
echo "2️⃣ FFmpeg 支持的硬件设备类型："
ffmpeg -hide_banner -hwaccels
echo ""

# 3. 测试 QSV
echo "3️⃣ 测试 QSV (Quick Sync Video)："
if ffmpeg -hide_banner -init_hw_device qsv=hw -f lavfi -i nullsrc=s=256x256:d=1 -vf hwupload=extra_hw_frames=64,format=qsv -c:v h264_qsv -f null - 2>&1 | grep -q "error\|failed\|Error"; then
    echo "❌ QSV 不可用"
else
    echo "✅ QSV 可用"
fi
echo ""

# 4. 测试 VAAPI
echo "4️⃣ 测试 VAAPI："
for device in /dev/dri/renderD*; do
    if [ -e "$device" ]; then
        echo "   测试设备: $device"
        if ffmpeg -hide_banner -vaapi_device $device -f lavfi -i nullsrc=s=256x256:d=1 -vf format=nv12,hwupload -c:v h264_vaapi -f null - 2>&1 | grep -q "error\|failed\|Error"; then
            echo "   ❌ $device VAAPI 不可用"
        else
            echo "   ✅ $device VAAPI 可用"
        fi
    fi
done
echo ""

# 5. 列出可用的 VAAPI 设备属性
echo "5️⃣ VAAPI 设备详细信息："
if command -v vainfo &> /dev/null; then
    for device in /dev/dri/renderD*; do
        if [ -e "$device" ]; then
            echo "   设备: $device"
            vainfo --display drm --device $device 2>&1 | grep -E "VAProfile|VAEntrypoint" | head -5
            echo ""
        fi
    done
else
    echo "   ⚠️ vainfo 未安装，运行: sudo apt install vainfo"
fi
echo ""

# 6. 推荐配置
echo "=========================================="
echo "📋 推荐配置："
echo "=========================================="

# 检查哪个可用
qsv_available=false
vaapi_available=false

if ffmpeg -hide_banner -init_hw_device qsv=hw -f lavfi -i nullsrc=s=256x256:d=1 -vf hwupload=extra_hw_frames=64,format=qsv -c:v h264_qsv -f null - 2>&1 | grep -q "Successful"; then
    qsv_available=true
fi

for device in /dev/dri/renderD*; do
    if [ -e "$device" ]; then
        if ! ffmpeg -hide_banner -vaapi_device $device -f lavfi -i nullsrc=s=256x256:d=1 -vf format=nv12,hwupload -c:v h264_vaapi -f null - 2>&1 | grep -q "error\|failed\|Error"; then
            vaapi_available=true
            vaapi_device=$device
            break
        fi
    fi
done

if [ "$qsv_available" = true ]; then
    echo "✅ 推荐使用: QSV (Quick Sync Video)"
    echo "   use_gpu=true (无需指定设备)"
elif [ "$vaapi_available" = true ]; then
    echo "✅ 推荐使用: VAAPI"
    echo "   use_gpu=true&gpu_device=$vaapi_device"
else
    echo "❌ 无可用硬件加速，使用 CPU 编码"
    echo "   不要传 use_gpu 参数"
fi
