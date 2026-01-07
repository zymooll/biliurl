# 快速开始指南

## 1. 启动服务

```bash
cd ncm_api_package_v2
python run_server.py
```

## 2. 访问 Web UI

打开浏览器访问：http://localhost:3000

## 3. 使用登录功能

### 方式一：扫码登录（推荐）
1. 点击页面底部的"登录管理"标签
2. 默认显示二维码登录界面
3. 使用网易云音乐 APP 扫描二维码
4. 在手机上确认登录
5. 登录成功后会自动保存 Cookie

### 方式二：短信验证码登录
1. 点击"短信登录"按钮
2. 输入手机号
3. 点击"发送验证码"
4. 输入收到的验证码
5. 点击"登录"

### 方式三：密码登录
1. 点击"密码登录"按钮
2. 输入手机号和密码
3. 点击"登录"

### 方式四：导入 Cookie
1. 点击"导入Cookie"按钮
2. 从浏览器开发者工具中复制 Cookie
3. 粘贴到输入框
4. 点击"导入Cookie"

## 4. 验证登录状态

登录成功后：
- 状态栏会显示"✅ 已登录：昵称 (UID: xxx)"
- 会出现"退出登录"按钮
- Cookie 自动保存到 `cookie.json` 文件
- 所有线程共享同一个 Cookie

## 5. 使用音乐功能

登录后可以：
- 搜索歌曲
- 播放高音质音乐
- 下载无损音频
- 生成歌词视频

## 6. 测试多线程安全性

```bash
python test_login.py
```

这个脚本会测试：
- Cookie 管理器的线程安全性
- 登录 API 接口
- 并发请求时的 Cookie 一致性

## 7. API 调用示例

### Python
```python
import requests

# 检查登录状态
response = requests.get('http://localhost:3000/user/info')
print(response.json())

# 导入 Cookie
cookie = "MUSIC_U=xxx; __csrf=yyy"
requests.post(f'http://localhost:3000/cookie/import?cookie={cookie}')
```

### JavaScript
```javascript
// 检查登录状态
fetch('/user/info')
  .then(res => res.json())
  .then(data => console.log(data));

// 扫码登录
async function qrLogin() {
  const keyRes = await fetch('/login/qr/key');
  const { unikey } = await keyRes.json();
  
  const qrRes = await fetch(`/login/qr/create?key=${unikey}`);
  const { qrimg } = await qrRes.json();
  
  // 显示二维码
  document.getElementById('qr').src = qrimg;
}
```

## 故障排除

### 问题：无法启动服务
- 检查端口是否被占用
- 确认 Python 环境是否正确
- 查看 requirements.txt 是否已安装

### 问题：二维码无法加载
- 检查网易云音乐 API 是否运行（默认端口 3002）
- 查看 ncm/config.py 中的 API_BASE_URL 配置

### 问题：登录后无法获取高音质
- 确认账号是否有 VIP 权限
- 尝试刷新 Cookie 缓存

## 更多信息

查看完整文档：[LOGIN_GUIDE.md](LOGIN_GUIDE.md)
