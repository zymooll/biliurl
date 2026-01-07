# 密码系统修复说明

## 问题
1. 输入默认密码无法登录系统
2. 修改的密码在重启后无法保持

## 原因
在添加salt加密后，hash算法发生了变化，导致旧的密码文件（如果存在）与新的验证逻辑不兼容。

## 解决方案

### 1. 自动迁移机制
系统现在会自动检测旧格式的密码文件并进行迁移：
- 旧格式：没有 `salt_version` 字段
- 新格式：包含 `salt_version: "v2"` 字段

当检测到旧格式文件时，系统会：
1. 自动删除旧文件
2. 使用新的hash算法重新初始化
3. 使用默认密码 `ncm2024`

### 2. 密码持久化
所有密码更新都会：
- 保存到 `access_password.json` 文件
- 包含 `salt_version` 版本标记
- 系统重启后自动加载

### 3. 密码文件格式

**新格式示例：**
```json
{
  "password_hash": "a38af889030c49522610d0fcfd170cc46ed3d9b3d42b94e78d588c2851978431",
  "salt_version": "v2",
  "created_at": "initialized"
}
```

## 使用说明

### 登录系统
1. **默认密码**：`ncm2024`（在 `config.py` 中配置）
2. 首次启动时系统会自动初始化密码文件
3. 如果之前有旧格式文件，会自动迁移

### 修改密码
有两种方式修改密码：

#### 方式1：通过Web UI
1. 登录系统后访问 `/auth/refresh` 接口
2. 提供当前密码
3. 系统会生成新的随机密码

#### 方式2：通过代码
```python
from ncm.utils.access_password import AccessPasswordManager

# 更新密码
new_password = "your_new_password"
AccessPasswordManager.update_password(new_password)
```

### 自定义Salt值
在 `config.py` 中修改：
```python
ACCESS_PASSWORD_SALT = "your_custom_salt_here"
```

⚠️ **警告**：修改salt后，所有现有密码将失效，需要删除 `access_password.json` 让系统重新初始化。

## 测试验证

已通过以下测试：
- ✅ 默认密码验证
- ✅ 旧格式自动迁移
- ✅ 密码持久化（重启后保持）
- ✅ Hash值验证（用于API调用）
- ✅ 错误密码拒绝

## 当前状态
- 密码已重置为默认：`ncm2024`
- 密码文件：`access_password.json`（已包含v2版本标记）
- 可以正常登录系统

## API调用示例

登录成功后，系统会返回hash值：
```json
{
  "code": 200,
  "message": "验证成功",
  "hash": "a38af889030c49522610d0fcfd170cc46ed3d9b3d42b94e78d588c2851978431"
}
```

使用hash调用API：
```
http://your-domain:7997/video?id=1856336348&access_hash=a38af889030c49522610d0fcfd170cc46ed3d9b3d42b94e78d588c2851978431
```

Web UI会自动在API URL中包含 `access_hash` 参数。
