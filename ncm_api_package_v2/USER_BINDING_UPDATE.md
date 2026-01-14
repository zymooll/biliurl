# 用户绑定功能更新说明

## 更新内容

用户绑定功能现在不仅保存绑定的歌曲ID，还会保存MV参数的值。

## 数据结构

### 旧格式（已弃用但仍兼容）
```python
user_id_bindings = {
    "zymooll": 123456789
}
```

### 新格式
```python
user_id_bindings = {
    "zymooll": {
        "id": 123456789,
        "mv": True
    }
}
```

## 使用场景

### 场景1：绑定用户和歌曲ID（同时保存MV偏好）

**请求：**
```
GET /video?user=zymooll&id=1969519579&mv=0&access_hash=xxx
```

**效果：**
- 保存用户 `zymooll` 绑定到歌曲ID `1969519579`
- 同时保存 `mv=0`（不使用MV）的偏好
- 日志输出：`💾 [用户绑定] 用户 'zymooll' 绑定到 ID: 1969519579, MV: False`

### 场景2：使用绑定信息播放（自动应用MV偏好）

**请求：**
```
GET /video?user=zymooll&access_hash=xxx
```

**效果：**
- 自动使用之前绑定的歌曲ID `1969519579`
- 自动应用之前保存的MV偏好 `mv=0`
- 日志输出：`🔗 [用户绑定] 用户 'zymooll' 使用绑定的 ID: 1969519579, MV: False`

### 场景3：覆盖绑定的MV偏好

**请求：**
```
GET /video?user=zymooll&mv=1&access_hash=xxx
```

**效果：**
- 使用绑定的歌曲ID `1969519579`
- **注意**：当前实现会使用绑定的MV值，如需支持覆盖，请参考下方的"改进建议"

## 兼容性

代码向后兼容旧格式：
- 如果 `user_id_bindings[user]` 是一个整数（旧格式），代码会正常处理
- 如果是字典（新格式），会同时读取 `id` 和 `mv` 值

## API接口

### `/play/vrc` 接口
- 该接口保存用户绑定时，MV参数默认设置为 `True`（因为该接口不支持MV参数）
- 恢复绑定时只使用ID，不使用MV参数

### `/video` 接口
- 保存用户绑定时，同时保存ID和MV参数
- 恢复绑定时，同时恢复ID和MV参数

## 改进建议

如果希望在恢复绑定时允许URL参数覆盖保存的MV值，可以修改 `/video` 接口的逻辑：

```python
if user:
    if id:
        user_id_bindings[user] = {"id": id, "mv": mv}
        print(f"💾 [用户绑定] 用户 '{user}' 绑定到 ID: {id}, MV: {mv}")
    elif user in user_id_bindings:
        binding = user_id_bindings[user]
        if isinstance(binding, dict):
            # 如果没有提供ID，使用绑定的ID
            if not id:
                id = binding.get("id")
            # 仅在MV参数为默认值时使用绑定的MV值
            # 如果URL中明确指定了mv参数，则优先使用URL参数
            if 'mv' not in request.query_params:  # 需要检查请求中是否有mv参数
                mv = binding.get("mv", True)
            print(f"🔗 [用户绑定] 用户 '{user}' 使用 ID: {id}, MV: {mv}")
```

## 示例场景

假设用户 `zymooll` 想要：
1. 播放某首歌，且不想看MV（想生成带字幕的视频）
2. 下次播放时，只需提供用户名，自动使用相同的设置

**第一次请求（绑定）：**
```
https://ncm.206601.xyz/video?user=zymooll&id=1969519579&mv=0&access_hash=xxx
```

**后续请求（使用绑定）：**
```
https://ncm.206601.xyz/video?user=zymooll&access_hash=xxx
```

系统会自动：
- 使用歌曲ID `1969519579`
- 不尝试获取MV（`mv=0`）
- 生成带字幕的音频+封面视频

## 注意事项

1. 用户绑定数据存储在内存中（`user_id_bindings`），服务器重启后会丢失
2. 如需持久化存储，可以考虑将数据保存到数据库或文件中
3. 当前实现在恢复绑定时会直接使用保存的MV值，不会检查URL参数是否明确指定了MV
