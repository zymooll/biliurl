#!/bin/bash

echo "=== FFmpeg 诊断工具 ==="
echo ""

# 1. 检查 FFmpeg 版本和配置
echo "1️⃣ FFmpeg 版本和编译配置："
ffmpeg -version | head -n 3
echo ""

# 2. 检查是否支持 libass
echo "2️⃣ 检查 libass 支持："
if ffmpeg -filters 2>&1 | grep -q "subtitles"; then
    echo "✅ subtitles 滤镜可用"
else
    echo "❌ subtitles 滤镜不可用"
fi

if ffmpeg -version 2>&1 | grep -q "enable-libass"; then
    echo "✅ libass 已启用"
else
    echo "❌ libass 未启用 - 这是问题所在！"
fi
echo ""

# 3. 检查系统是否安装了 libass
echo "3️⃣ 检查系统 libass 库："
if ldconfig -p 2>/dev/null | grep -q libass; then
    echo "✅ 系统已安装 libass"
    ldconfig -p | grep libass
elif pkg-config --exists libass 2>/dev/null; then
    echo "✅ 系统已安装 libass"
    pkg-config --modversion libass
else
    echo "❌ 系统未安装 libass"
fi
echo ""

# 4. 测试简单的 subtitles 滤镜
echo "4️⃣ 测试 subtitles 滤镜："
echo "正在创建测试文件..."
echo -e "1\n00:00:00,000 --> 00:00:05,000\n测试字幕" > /tmp/test_subtitle.srt
ffmpeg -f lavfi -i color=black:s=1280x720:d=5 -vf "subtitles=/tmp/test_subtitle.srt" -t 1 -f null - 2>&1 | grep -E "(subtitles|libass|error)" | head -n 5
rm -f /tmp/test_subtitle.srt
echo ""

# 5. 给出建议
echo "=== 诊断结果 ==="
if ! ffmpeg -version 2>&1 | grep -q "enable-libass"; then
    echo "❌ 问题确认：FFmpeg 缺少 libass 支持"
    echo ""
    echo "📋 解决方案："
    echo "1. 安装 libass 开发库："
    echo "   sudo apt-get install libass-dev  # Debian/Ubuntu"
    echo "   sudo yum install libass-devel    # CentOS/RHEL"
    echo ""
    echo "2. 重新编译 FFmpeg，添加 --enable-libass："
    echo "   ./configure --enable-gpl --enable-libx264 --enable-vaapi --enable-libass --enable-libmfx"
    echo "   make -j$(nproc)"
    echo "   sudo make install"
    echo ""
    echo "3. 或者使用预编译版本："
    echo "   wget https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz"
    echo "   tar xf ffmpeg-git-amd64-static.tar.xz"
else
    echo "✅ FFmpeg 配置正常"
fi
