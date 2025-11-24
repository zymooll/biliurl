@echo off
REM Biliurl Workers - Windows 批处理脚本示例
REM
REM 使用方法: example.bat <worker_url> <api_key> <bvid>
REM 示例: example.bat https://biliurl.workers.dev pro_xxx BV1Xx411c7mD

setlocal enabledelayedexpansion

if "%3"=="" (
    echo Usage: %0 ^<worker_url^> ^<api_key^> ^<bvid^>
    echo.
    echo Examples:
    echo   %0 https://biliurl.workers.dev public_j389u4tc9w08u4pq4mqp9xwup4 BV1Xx411c7mD
    echo   %0 https://biliurl.workers.dev pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh BV1Xx411c7mD
    exit /b 1
)

set WORKER_URL=%1
set API_KEY=%2
set BVID=%3

echo ==========================================
echo Biliurl Workers - 下载示例
echo ==========================================
echo Worker URL: %WORKER_URL%
echo API Key: %API_KEY:~0,20%...
echo BVID: %BVID%
echo.

REM 步骤 1: 获取视频信息
echo [1/4] 获取视频信息...
curl -s "%WORKER_URL%/api/bili/%BVID%/info?key=%API_KEY%" > info.json
echo ✓ 完成

REM 步骤 2: 获取流 URLs
echo.
echo [2/4] 获取流 URLs...
curl -s "%WORKER_URL%/api/bili/%BVID%/streams?key=%API_KEY%^&quality=125" > streams.json
echo ✓ 完成

REM 检查 ffmpeg
where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ❌ 需要安装 ffmpeg
    echo.
    echo 安装 ffmpeg:
    echo   使用 Chocolatey: choco install ffmpeg
    echo   或从 https://ffmpeg.org/download.html 下载
    exit /b 1
)

REM 步骤 3: 生成输出文件名
echo.
echo [3/4] 准备下载...
set OUTPUT_FILE=%BVID%.mp4

REM 步骤 4: 使用 jq 或 PowerShell 提取 URLs (这里简化处理)
REM 实际使用可能需要安装 jq 或使用 PowerShell 解析 JSON

echo.
echo [4/4] 注意: 该脚本需要额外配置
echo.
echo 推荐方案:
echo 1. 手动在浏览器中获取流 URLs
echo 2. 或使用 PowerShell 脚本解析 JSON
echo 3. 然后运行 ffmpeg 合成视频
echo.
echo ==========================================
echo 示例 ffmpeg 命令:
echo ==========================================
echo ffmpeg -i "视频_URL" -i "音频_URL" ^
echo   -c:v copy -c:a aac -shortest ^
echo   -headers "Referer: https://www.bilibili.com" ^
echo   "%OUTPUT_FILE%"
echo ==========================================
