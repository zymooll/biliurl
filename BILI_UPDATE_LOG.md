# B站功能更新说明

## 核心设计

### ✅ 统一接口 - 参数分流

**设计理念：** 保持 `/play/vrc` 作为统一入口，根据参数自动分流到不同的处理逻辑。

**分流规则：**
```
/play/vrc?bvid=xxx    → B站视频播放
/play/vrc?id=xxx      → 网易云音乐播放
/play/vrc?keywords=xxx → 网易云音乐搜索播放
```

**优势：**
- ✅ 保持 API 的简洁性，一个接口支持多种播放源
- ✅ 向后兼容，不影响原有网易云音乐播放功能
- ✅ VRChat 等客户端无需修改，只需添加新参数即可支持 B站视频

---

## 接口说明

### `/play/vrc` - 统一播放接口

### `/play/vrc` - 统一播放接口

**支持的参数组合：**

#### 1. B站视频播放
```
GET /play/vrc?bvid=BV1HfK3zPEHE&qn=64
```
- `bvid` (必需): B站视频BV号
- `qn` (可选): 清晰度，默认64 (720P)

#### 2. 网易云音乐播放
```
GET /play/vrc?id=1856336348&level=standard
```
- `id` (可选): 歌曲ID
- `keywords` (可选): 搜索关键词
- `level` (可选): 音质等级
- `user` (可选): 用户绑定
- 其他网易云相关参数...

**分流逻辑：**
```python
if bvid:
    # B站视频播放逻辑
    return RedirectResponse(video_url)
else:
    # 网易云音乐播放逻辑（原有逻辑）
    ...
```

---

## WebUI 登录管理界面

**界面布局：**
```
┌─────────────────────────────────────────────────┐
│            登录管理（Login Management）           │
├────────────────────┬────────────────────────────┤
│   🎵 网易云音乐     │      📺 哔哩哔哩           │
│                    │                            │
│  • 扫码登录         │   • 扫码登录               │
│  • 短信登录         │   • 登录状态显示           │
│  • 密码登录         │   • 退出登录               │
│  • 导入Cookie       │                            │
│  • 登录状态显示     │                            │
│  • 退出登录         │                            │
└────────────────────┴────────────────────────────┘
```

**功能特性：**
- ✅ B站二维码扫码登录
- ✅ 实时登录状态显示（用户名、UID、等级）
- ✅ 自动轮询登录状态（每2秒检查一次）
- ✅ 二维码过期自动提示
- ✅ 登录成功后显示用户信息
- ✅ 一键退出登录
- ✅ 样式统一，与网易云登录界面风格一致

---

## 技术实现

### 前端更新

**文件：** `ncm/api/templates/index.html`
- 使用 Grid 布局实现双列排列
- 左侧：网易云音乐登录（🎵 红色主题 #ec4141）
- 右侧：哔哩哔哩登录（📺 蓝色主题 #00a1d6）
- 响应式设计，保持视觉平衡

**文件：** `ncm/api/static/js/app.js`
- 新增 `checkBiliLoginStatus()` - 检查B站登录状态
- 新增 `startBiliQRLogin()` - 启动二维码登录
- 新增 `biliLogout()` - 退出登录
- 页面加载时自动检查登录状态

### 后端更新

**文件：** `ncm/api/routes.py`
- `/play/vrc` 改为 `/play/bili` （避免冲突）
- 其他 B站接口保持不变：
  - `/bili/login/qr` - 获取二维码
  - `/bili/login/poll` - 轮询登录状态
  - `/bili/login/info` - 获取登录信息
  - `DELETE /bili/login` - 退出登录

---

## 使用方式

### 1. 访问登录管理页面

打开 Web UI，点击顶部的 **"登录管理"** 标签页。

### 2. B站登录步骤

1. 在右侧的 **"哔哩哔哩"** 区域查看二维码
2. 使用 **哔哩哔哩 APP** 扫描二维码
3. 在手机上确认登录
4. 等待页面自动更新（约2秒）
5. 登录成功后显示用户信息

### 播放视频

**方式 1：直接浏览器访问**
```
# B站视频
http://localhost:8000/play/vrc?bvid=BV1HfK3zPEHE

# 网易云音乐
http://localhost:8000/play/vrc?id=1856336348
```

**方式 2：HTML 视频标签**
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

**方式 3：API 调用**
```python
import requests

# B站视频
response = requests.get('http://localhost:8000/play/vrc?bvid=BV1HfK3zPEHE')

# 网易云音乐
response = requests.get('http://localhost:8000/play/vrc?id=1856336348')
```

---

## 视频清晰度说明

通过 `qn` 参数控制：

| qn 值 | 清晰度 | 说明 |
|-------|--------|------|
| 16 | 360P | 流畅 |
| 32 | 480P | 清晰 |
| **64** | **720P** | **高清（默认）** |
| 80 | 1080P | 需登录 |
| 112 | 1080P+ | 需大会员 |
| 116 | 1080P60 | 需大会员 |

**示例：**
```
/play/vrc?bvid=BV1HfK3zPEHE&qn=80  # B站 1080P 视频
/play/vrc?id=1856336348&level=higher  # 网易云高品质音乐
```

---

## 注意事项

### 1. 账号共享
- B站登录账号**在服务器上全局共享**
- 所有用户使用同一个 B站账号
- 类似网易云音乐的处理方式

### 2. Cookie 管理
- Cookie 保存在 `bili_cookie.json`
- 线程安全的读写操作
- 支持自动缓存

### 3. 视频流有效期
- 视频流 URL 有效期为 **120 分钟**
- 过期后需要重新获取
- 服务器会动态生成新的 URL

### 4. 防盗链说明
- B站视频流需要正确的 Referer
- 服务器已配置必要的请求头
- 重定向后浏览器会自动处理

---

## 文件变更清单

### 新增文件
- ✅ `core/bili.py` - B站核心功能模块
- ✅ `core/bili_cookie.py` - Cookie 管理器
- ✅ `BILI_API_README.md` - API 文档

### 修改文件
- ✅ `ncm/api/routes.py` - 添加 B站接口，修复路由冲突
- ✅ `ncm/api/templates/index.html` - 添加 B站登录界面
- ✅ `ncm/api/static/js/app.js` - 添加 B站登录 JS 函数
- ✅ `ncm/config.py` - 添加 B站配置常量

---

## 测试建议

1. **登录功能测试**
   - 打开登录管理页面
   - 扫码登录 B站
   - 检查登录状态显示
   - 测试退出登录

2. **视频播放测试**
   ```bash
   # B站视频
   http://localhost:8000/play/vrc?bvid=BV1HfK3zPEHE
   
   # 网易云音乐
   http://localhost:8000/play/vrc?id=1856336348
   ```

3. **接口测试**
   ```bash
   # 获取B站二维码
   curl http://localhost:8000/bili/login/qr
   
   # 查看B站登录状态
   curl http://localhost:8000/bili/login/info
   ```

---

## 升级步骤

1. 拉取最新代码
2. 确保依赖已安装：`pip install requests qrcode pillow`
3. 重启服务器
4. 访问 Web UI 查看新的登录管理界面
5. 完成 B站登录后即可使用视频播放功能

**现在可以在登录管理页面同时管理网易云音乐和哔哩哔哩账号了！** 🎉
