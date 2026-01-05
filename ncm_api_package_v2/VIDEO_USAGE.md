# VRChat USharpVideo MP4视频生成功能使用指南

## 功能说明

本API新增了 `/video` 端点，可以将网易云音乐的MP3音频转换为MP4视频文件，专为VRChat的USharpVideo组件设计。

### 视频特性
- ✅ 全屏封面显示（1920x1080分辨率）
- ✅ 实时字幕显示（支持原文+翻译）
- ✅ 高质量音频（192kbps AAC）
- ✅ 兼容VRChat播放器

---

## API端点

### `/video` - 生成MP4视频

**方法**: GET

**参数**:

| 参数名 | 类型 | 必填 | 说明 | 默认值 |
|--------|------|------|------|--------|
| `id` | int | 否* | 歌曲ID | - |
| `keywords` | string | 否* | 搜索关键词 | - |
| `level` | string | 否 | 音质等级 | `exhigh` |
| `unblock` | bool | 否 | 是否开启解灰模式 | `false` |
| `simple` | bool | 否 | 是否使用简化模式（无字幕） | `false` |

> *注意: `id` 和 `keywords` 必须提供其中一个

**音质等级**:
- `standard`: 标准音质
- `higher`: 较高音质
- `exhigh`: 极高音质（推荐）
- `lossless`: 无损音质

---

## 使用示例

### 1. 通过歌曲ID获取视频

```
GET http://localhost:7997/video?id=1901371647
```

### 2. 通过关键词搜索并生成视频

```
GET http://localhost:7997/video?keywords=稻香
```

### 3. 使用简化模式（生成更快，无字幕）

```
GET http://localhost:7997/video?id=1901371647&simple=true
```

### 4. 高音质 + 解灰模式

```
GET http://localhost:7997/video?id=1901371647&level=lossless&unblock=true
```

---

## VRChat 中使用

### 方法1: 直接使用URL

在USharpVideo的URL输入框中输入：

```
http://你的服务器IP:7997/video?id=1901371647
```

### 方法2: 通过关键词搜索

```
http://你的服务器IP:7997/video?keywords=稻香
```

---

## 部署前准备

### 1. 安装FFmpeg

**macOS**:
```bash
brew install ffmpeg
```

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows**:
从 [FFmpeg官网](https://ffmpeg.org/download.html) 下载并添加到系统PATH

### 2. 验证FFmpeg安装

```bash
ffmpeg -version
```

### 3. 安装Python依赖

```bash
cd ncm_api_package_v2
pip install -r requirements.txt
```

### 4. 启动服务

```bash
python run_server.py
```

服务将运行在 `http://0.0.0.0:7997`

---

## 性能优化建议

### 1. 使用简化模式
如果不需要字幕，使用 `simple=true` 参数可以显著提高生成速度：

```
/video?id=1901371647&simple=true
```

### 2. 缓存视频文件
考虑添加缓存机制，避免重复生成相同的视频。

### 3. 使用反向代理
在生产环境使用Nginx等反向代理，可以：
- 启用gzip压缩
- 添加缓存控制
- 提高并发性能

---

## 故障排查

### 问题1: "FFmpeg执行失败"

**解决方案**:
1. 确认FFmpeg已正确安装
2. 检查FFmpeg是否在系统PATH中
3. 查看终端输出的详细错误信息

### 问题2: "无法获取歌曲链接"

**解决方案**:
1. 检查是否需要VIP权限
2. 尝试开启解灰模式 `unblock=true`
3. 降低音质等级 `level=standard`

### 问题3: 视频生成太慢

**解决方案**:
1. 使用简化模式 `simple=true`
2. 降低音质等级
3. 升级服务器硬件配置

### 问题4: VRChat无法播放

**解决方案**:
1. 确认USharpVideo支持的编码格式
2. 检查视频分辨率是否过高
3. 尝试降低码率（修改video.py中的`-crf`参数）

---

## 技术细节

### 视频编码参数

- **视频编码**: H.264 (libx264)
- **分辨率**: 1920x1080
- **帧率**: 自适应
- **CRF**: 23 (恒定质量模式)
- **音频编码**: AAC
- **音频码率**: 192kbps
- **像素格式**: yuv420p (最佳兼容性)

### 字幕样式

- **字体**: PingFang SC (macOS) / 系统默认字体
- **字号**: 32px
- **颜色**: 白色
- **描边**: 黑色2px
- **位置**: 底部居中

---

## API响应格式

成功时返回视频文件流，HTTP Headers:

```
Content-Type: video/mp4
Content-Disposition: attachment; filename="歌曲名 - 歌手名.mp4"
Cache-Control: public, max-age=3600
Accept-Ranges: bytes
```

失败时返回JSON:

```json
{
  "detail": "错误信息"
}
```

---

## 开发计划

- [ ] 添加视频缓存机制
- [ ] 支持自定义字幕样式
- [ ] 支持多种视频分辨率选项
- [ ] 添加视频生成队列
- [ ] 支持批量生成

---

## 许可证

本项目仅供学习交流使用，请勿用于商业用途。
