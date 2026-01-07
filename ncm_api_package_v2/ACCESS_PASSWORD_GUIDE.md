# 访问密码保护功能使用说明

## 🔐 功能概述

已实现完整的访问密码保护机制，确保只有授权用户才能访问 Web UI 和视频生成接口。

## ✨ 主要特性

### 1. **访问控制**
- ✅ 首次访问需要输入访问密码
- ✅ 密码验证成功后自动保存到浏览器 Cookie（有效期30天）
- ✅ 后续访问自动验证，无需重复输入
- ✅ 密码错误时自动显示登录页面

### 2. **视频接口保护**
- ✅ `/video` 接口**必须**提供有效的访问密码
- ✅ 通过 Cookie 自动传递密码
- ✅ 无效密码返回 403 错误

### 3. **密码管理**
- ✅ 支持在 Web UI 中刷新访问密码
- ✅ 刷新后生成随机的16位密码
- ✅ 刷新需要验证当前密码
- ✅ 密码保存在配置文件中（哈希存储）

## 🚀 使用方法

### 初次使用

1. **启动服务**
   ```bash
   cd ncm_api_package_v2
   python run_server.py
   ```

2. **访问 Web UI**
   - 打开浏览器访问 http://localhost:3000
   - 系统会自动显示访问密码输入页面

3. **输入默认密码**
   - 默认密码：`ncm2024`
   - 点击"进入系统"

4. **自动登录**
   - 密码验证成功后，系统会自动保存到 Cookie
   - 30天内再次访问无需重新输入

### 修改默认密码

**方法一：修改配置文件**

编辑 `ncm/config.py`：
```python
DEFAULT_ACCESS_PASSWORD = "your_custom_password"  # 修改为你的密码
```

然后删除 `access_password.json` 文件并重启服务。

**方法二：通过 Web UI 刷新**

1. 访问 Web UI
2. 点击底部"登录管理"标签
3. 滚动到"访问密码管理"区域
4. 输入当前密码
5. 点击"🔄 刷新访问密码"
6. 系统会生成新的随机密码并显示
7. **立即保存新密码**（5秒后自动跳转到登录页）

### 使用新密码登录

刷新密码后：
1. 自动跳转到登录页面
2. 输入新生成的密码
3. 点击"进入系统"

## 🔧 API 接口说明

### 1. 验证访问密码
```http
POST /auth/verify
Content-Type: application/x-www-form-urlencoded

password=your_password
```

**响应**：
```json
{
  "code": 200,
  "message": "验证成功"
}
```

成功后会设置 `access_password` Cookie。

### 2. 检查授权状态
```http
GET /auth/check
Cookie: access_password=your_password
```

**响应**：
```json
{
  "code": 200,
  "message": "已授权",
  "authorized": true
}
```

### 3. 刷新访问密码
```http
POST /auth/refresh?current_password=old_password
```

**响应**：
```json
{
  "code": 200,
  "message": "密码已刷新",
  "new_password": "AbCdEf1234567890"
}
```

### 4. 访问视频接口（需要密码）
```http
GET /video?id=1234567&level=exhigh
Cookie: access_password=your_password
```

**无密码或密码错误时**：
```json
{
  "detail": "需要访问密码。请先在Web UI中登录。"
}
```

## 🔒 安全特性

### 密码存储
- 密码使用 SHA-256 哈希存储
- 配置文件 `access_password.json` 中只保存哈希值
- 原始密码不会被保存

### Cookie 安全
- 设置 `httponly=True` 防止 JavaScript 访问
- 设置 `samesite="lax"` 防止 CSRF 攻击
- 有效期30天，自动过期

### 线程安全
- 使用 `threading.RLock` 保护密码读写
- 支持多线程并发访问
- 密码缓存机制提高性能

## 📊 文件结构

```
ncm_api_package_v2/
├── ncm/
│   ├── config.py                    # ✅ 新增：默认密码配置
│   ├── utils/
│   │   └── access_password.py       # ✅ 新增：密码管理模块
│   └── api/
│       ├── routes.py                # ✅ 修改：添加密码验证
│       └── web_ui.py                # ✅ 修改：添加登录页面
└── access_password.json             # 自动生成：密码哈希存储
```

## 🧪 测试场景

### 测试 1: 首次访问
1. 清除浏览器 Cookie
2. 访问 http://localhost:3000
3. ✅ 应该显示密码输入页面
4. 输入正确密码
5. ✅ 自动跳转到主界面

### 测试 2: Cookie 自动登录
1. 已登录状态下关闭浏览器
2. 重新打开浏览器访问
3. ✅ 自动登录，直接显示主界面

### 测试 3: 错误密码
1. 输入错误的密码
2. ✅ 显示"密码错误，请重试"
3. ✅ 停留在登录页面

### 测试 4: 视频接口保护
```bash
# 无 Cookie 访问
curl http://localhost:3000/video?id=1234567

# 应该返回 403 错误
```

### 测试 5: 密码刷新
1. 在 Web UI 中点击"登录管理"
2. 滚动到"访问密码管理"
3. 输入当前密码并刷新
4. ✅ 显示新密码
5. ✅ 5秒后自动跳转
6. 使用新密码重新登录

## 🐛 故障排除

### Q: 忘记密码怎么办？
**A**: 方法 1：删除 `access_password.json` 文件并重启服务，将使用默认密码 `ncm2024`

方法 2：手动修改 `access_password.json`，设置为默认密码的哈希值：
```json
{
  "password_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "created_at": "reset"
}
```

### Q: Cookie 失效后怎么办？
**A**: Cookie 有效期30天。失效后会自动跳转到登录页面，重新输入密码即可。

### Q: 多个用户如何使用？
**A**: 所有用户共享同一个访问密码。每个用户在自己的浏览器中输入一次即可。

### Q: 如何在 VRChat 中使用？
**A**: VRChat 的 USharpVideo 不支持 Cookie。需要使用其他方法（如修改代码添加 URL 参数传递密码）。

### Q: 密码文件在哪里？
**A**: `access_password.json` 在项目根目录下。不要将此文件提交到公开仓库！

## 🔐 安全建议

1. **修改默认密码**
   - 生产环境必须修改默认密码
   - 使用强密码（字母+数字+特殊字符）

2. **定期刷新密码**
   - 建议每月刷新一次访问密码
   - 刷新后通知所有用户

3. **保护配置文件**
   - 不要将 `access_password.json` 上传到 Git
   - 添加到 `.gitignore`

4. **使用 HTTPS**
   - 生产环境建议配置 HTTPS
   - 防止密码在网络传输中被截获

5. **日志监控**
   - 定期检查后端日志
   - 关注异常的访问尝试

## 📝 配置示例

### config.py
```python
# 访问密码配置
ACCESS_PASSWORD_FILE = "access_password.json"
DEFAULT_ACCESS_PASSWORD = "your_strong_password_here"  # 修改为强密码
```

### .gitignore
```
# 密码文件
access_password.json
cookie.json
cookie-guest.json
```

## 🎯 后续改进建议

- [ ] 支持多用户系统（每个用户独立密码）
- [ ] 添加密码错误次数限制（防止暴力破解）
- [ ] 支持 API Token 认证
- [ ] 添加访问日志和审计功能
- [ ] 支持密码重置邮件通知

---

**现在所有功能都已就绪！** 🎉

重启服务器，首次访问会要求输入密码，之后会自动保存 Cookie 实现无缝访问。
