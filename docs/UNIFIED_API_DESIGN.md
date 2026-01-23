# 统一接口设计说明

## 核心改进 ✅

### 保持 `/play/vrc` 作为统一入口

**原因：** 避免路由冲突，保持 API 简洁性

**设计：** 根据参数自动分流

---

## 使用方式

### 🎬 B站视频播放

```bash
# 基础用法（720P）
/play/vrc?bvid=BV1HfK3zPEHE

# 指定清晰度（1080P）
/play/vrc?bvid=BV1HfK3zPEHE&qn=80
```

### 🎵 网易云音乐播放

```bash
# 歌曲ID播放
/play/vrc?id=1856336348

# 关键词搜索播放
/play/vrc?keywords=周杰伦

# 用户绑定
/play/vrc?id=1856336348&user=myname
```

---

## 参数优先级

接口检测参数的顺序：

1. **检测 `bvid`** → 如果存在 → B站视频播放
2. **检测 `id` 或 `keywords`** → 网易云音乐播放
3. **都没有** → 返回错误

---

## 实现逻辑

```python
@router.get("/play/vrc")
async def play_vrc_main(
    bvid: Optional[str] = None,  # B站视频
    id: Optional[str] = None,     # 网易云ID
    keywords: Optional[str] = None, # 网易云搜索
    qn: int = 64,                 # B站清晰度
    level: str = "standard",      # 网易云音质
    ...
):
    # 分流逻辑
    if bvid:
        # B站视频播放
        return RedirectResponse(bili_video_url)
    else:
        # 网易云音乐播放（原有逻辑）
        ...
```

---

## 清晰度对照表

### B站视频 (`qn` 参数)

| 值 | 清晰度 | 要求 |
|----|--------|------|
| 16 | 360P | 无 |
| 32 | 480P | 无 |
| **64** | **720P (默认)** | 无 |
| 80 | 1080P | 需登录 |
| 112 | 1080P+ | 需大会员 |
| 116 | 1080P60 | 需大会员 |

### 网易云音乐 (`level` 参数)

| 值 | 音质 |
|----|------|
| standard | 标准 |
| higher | 较高 |
| exhigh | 极高 |
| lossless | 无损 |
| hires | Hi-Res |

---

## 完整示例

```html
<!DOCTYPE html>
<html>
<body>
    <!-- B站视频 -->
    <h2>B站视频播放</h2>
    <video controls width="640">
        <source src="/play/vrc?bvid=BV1HfK3zPEHE&qn=64" type="video/mp4">
    </video>

    <!-- 网易云音乐 -->
    <h2>网易云音乐播放</h2>
    <video controls width="640">
        <source src="/play/vrc?id=1856336348" type="video/mp4">
    </video>
</body>
</html>
```

---

## WebUI 登录管理

访问 `/` 主页，点击 **"登录管理"** 标签页：

- **左侧：** 🎵 网易云音乐登录
- **右侧：** 📺 哔哩哔哩登录

登录后可享受：
- 网易云：更高音质、会员歌曲
- B站：更高清晰度（1080P+）

---

## 技术优势

✅ **统一接口** - 一个入口支持多种播放源  
✅ **向后兼容** - 不影响原有功能  
✅ **参数清晰** - 通过参数名自动识别播放类型  
✅ **易于扩展** - 未来可继续添加其他平台（如 YouTube、SoundCloud 等）  
✅ **保持简洁** - 无需为每个平台创建独立接口  

**设计理念：** 一个接口，多种可能 🚀
