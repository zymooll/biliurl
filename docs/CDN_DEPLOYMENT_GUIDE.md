# CDN 分布式部署方案文档

## 📐 架构概述

本项目采用 **Cloudflare Workers + 多区域源站** 的分布式架构：

```
用户请求
    ↓
Cloudflare Workers（全球边缘网络）
    ├─ 静态资源 → 边缘缓存
    ├─ 媒体请求 → 智能路由到最近源站
    └─ 健康检查 → 故障转移
    ↓
源站服务器（长沙/新加坡/澳洲）
    ├─ NCM API（固定IP请求api-enhanced）
    └─ B站视频（实时获取一次性URL）
```

### 核心特性

✅ **智能路由** - 根据用户地理位置自动选择最近服务器
✅ **静态缓存** - WebUI静态资源边缘缓存，减轻源站压力
✅ **不缓存媒体URL** - NCM和B站URL都是动态/一次性的，不做缓存
✅ **健康检查** - 自动检测源站状态，故障自动转移
✅ **全球加速** - Cloudflare 200+节点DNS加速

---

## 🚀 部署步骤

### 第一步：准备源站服务器

#### 1.1 设置环境变量

在每台服务器上设置节点信息：

```bash
# 长沙服务器
export NODE_NAME="changsha-01"
export NODE_REGION="mainland_china"

# 新加坡服务器
export NODE_REGION="singapore-01"
export NODE_REGION="asia"

# 澳洲服务器
export NODE_NAME="sydney-01"
export NODE_REGION="australia"
```

#### 1.2 启动服务

```bash
# 确保已安装依赖
pip install -r requirements.txt

# 启动服务
python run_server.py
```

#### 1.3 验证健康检查

```bash
curl http://localhost:7997/health
```

应该返回：
```json
{
  "status": "healthy",
  "node": "changsha-01",
  "region": "mainland_china",
  "timestamp": 1737619200,
  "services": {
    "ncm_api": "healthy",
    "bili_video": "healthy"
  },
  "uptime": 3600
}
```

---

### 第二步：配置域名和SSL

为每个源站配置域名（推荐使用Cloudflare托管DNS）：

```
cn.yourdomain.com  → 长沙服务器IP
sg.yourdomain.com  → 新加坡服务器IP
au.yourdomain.com  → 澳洲服务器IP
```

**SSL证书配置：**

方案1：使用Cloudflare免费SSL（推荐）
- 在Cloudflare开启Full SSL模式
- 源站使用Cloudflare Origin Certificate

方案2：Let's Encrypt + Nginx反向代理
```bash
# 安装certbot
sudo apt install certbot python3-certbot-nginx

# 申请证书
sudo certbot --nginx -d cn.yourdomain.com
```

---

### 第三步：部署Cloudflare Workers

#### 3.1 安装Wrangler CLI

```bash
npm install -g wrangler

# 登录Cloudflare
wrangler login
```

#### 3.2 修改配置

编辑 `cloudflare-worker.js` 第15-27行，填写你的源站域名：

```javascript
const CONFIG = {
  origins: {
    changsha: {
      url: 'https://cn.yourdomain.com',  // ← 修改这里
      region: 'mainland_china',
      weight: 10
    },
    singapore: {
      url: 'https://sg.yourdomain.com',  // ← 修改这里
      region: 'asia',
      weight: 8
    },
    sydney: {
      url: 'https://au.yourdomain.com',  // ← 修改这里
      region: 'australia',
      weight: 7
    }
  },
  // ...
}
```

#### 3.3 部署到Cloudflare

```bash
# 测试部署（会生成一个临时域名）
wrangler deploy

# 查看部署的URL
# 输出类似：https://biliurl-cdn.your-subdomain.workers.dev
```

#### 3.4 绑定自定义域名

在Cloudflare Dashboard中：
1. 进入 Workers & Pages
2. 选择你的Worker（biliurl-cdn）
3. 点击 Settings → Triggers → Add Custom Domain
4. 输入你的主域名：`api.yourdomain.com`

---

### 第四步：测试验证

#### 4.1 测试健康检查

```bash
curl https://api.yourdomain.com/health
```

#### 4.2 测试B站视频播放

```bash
# 应该返回302重定向
curl -I "https://api.yourdomain.com/play/vrc?bvid=BV1HfK3zPEHE"
```

#### 4.3 测试NCM音乐播放

```bash
curl -I "https://api.yourdomain.com/play/vrc?id=1856336348"
```

#### 4.4 测试地理路由

```bash
# 从不同地区测试，查看响应头中的 X-Origin-Server
curl -H "CF-IPCountry: CN" https://api.yourdomain.com/health
# 应该路由到 changsha

curl -H "CF-IPCountry: AU" https://api.yourdomain.com/health
# 应该路由到 sydney
```

---

## 📊 监控和维护

### 实时监控

在Cloudflare Dashboard可查看：
- 请求数量和响应时间
- 错误率和状态码分布
- 流量来源地理分布

### 日志查看

```bash
# 实时查看Workers日志
wrangler tail

# 查看源站日志
tail -f /var/log/your-app.log
```

### 性能优化建议

1. **启用Argo Smart Routing**（付费，$5/月）
   - 进一步优化全球路由路径
   - 平均减少30%延迟

2. **增加Workers计算资源**（按需）
   - 免费版：100k请求/天
   - 付费版：$5起/1000万请求

3. **源站优化**
   - 使用SSD硬盘
   - 增加内存（推荐4GB+）
   - 开启BBR拥塞控制算法

---

## 💰 成本估算

| 项目 | 免费版 | 付费版 |
|------|--------|--------|
| **Cloudflare Workers** | 100k请求/天 | $5/1000万请求 |
| **源站服务器** | | |
| - 长沙VPS（主力） | - | ¥200-300/月 |
| - 新加坡VPS | - | ¥150/月 |
| - 澳洲VPS | - | ¥150/月 |
| **域名** | - | ¥50/年 |
| **SSL证书** | 免费 | - |
| **合计（月）** | ¥0 | ¥500-600 |

**流量成本：**
- Cloudflare：无限流量（免费）
- 源站：根据VPS提供商计费（通常1-5TB免费）

---

## 🔧 故障排查

### Workers无法访问源站

1. 检查源站SSL证书是否有效
2. 确认源站防火墙允许Cloudflare IP
3. 查看Workers日志：`wrangler tail`

### 健康检查失败

1. 检查源站 `/health` 端点是否正常
2. 确认源站防火墙开放7997端口
3. 检查api-enhanced服务是否运行

### 地理路由不准确

1. 检查Workers配置中的地区映射
2. 确认源站设置了正确的 NODE_REGION
3. 查看响应头 `X-Origin-Server` 确认实际路由

---

## 📝 高级配置

### 自定义路由规则

编辑 `cloudflare-worker.js` 的 `selectBestOrigin()` 函数：

```javascript
// 例如：让香港/台湾用户走长沙（而不是新加坡）
const regionMapping = {
  'CN': 'changsha',
  'HK': 'changsha',  // 修改这里
  'TW': 'changsha',  // 修改这里
  'AU': 'sydney',
  // ...
}
```

### 启用访问日志

在源站代码中添加：

```python
# ncm/api/routes.py
@router.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    print(f"📊 {request.method} {request.url.path} - "
          f"{response.status_code} - {duration:.3f}s")
    
    return response
```

---

## 🎯 下一步改进

- [ ] 添加Redis缓存层（共享登录状态）
- [ ] 实现请求限流（防止滥用）
- [ ] 添加Prometheus监控
- [ ] 自动扩缩容（K8s）
- [ ] 添加更多区域节点

---

## 📞 支持

遇到问题？
1. 检查本文档的故障排查章节
2. 查看Workers日志：`wrangler tail`
3. 查看源站日志：`tail -f /path/to/log`
