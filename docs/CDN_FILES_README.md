# CDN 分布式改造 - 文件说明

## 📁 新增文件清单

### 核心配置文件

| 文件 | 说明 | 用途 |
|------|------|------|
| `cloudflare-worker.js` | Workers路由脚本 | 部署到Cloudflare，实现智能路由和边缘缓存 |
| `wrangler.toml` | Workers部署配置 | 使用 `wrangler deploy` 时读取 |
| `nginx.conf.example` | Nginx配置示例 | 源站HTTPS和反向代理配置 |
| `biliurl.service.example` | systemd服务配置 | 将应用配置为系统服务（开机自启） |

### 部署和测试工具

| 文件 | 说明 | 用途 |
|------|------|------|
| `deploy.sh` | 一键部署脚本 | 在源站服务器上快速部署和配置 |
| `test_cdn.py` | 功能测试脚本 | 验证健康检查、视频/音乐播放等功能 |

### 文档

| 文件 | 说明 | 适合人群 |
|------|------|---------|
| `CDN_QUICKSTART.md` | 快速开始指南 | 想要5分钟快速部署的用户 |
| `CDN_SUMMARY.md` | 完整改造说明 | 想要了解架构设计和技术细节 |
| `CDN_DEPLOYMENT_GUIDE.md` | 详细部署指南 | 进行生产环境部署的运维人员 |
| `CDN_FILES_README.md` | 本文件 | 所有人 |

---

## 🚀 快速使用指南

### 第一步：选择你的场景

#### 场景1：单服务器测试（最简单）
```bash
# 1. 运行部署脚本
./deploy.sh

# 2. 启动服务
python run_server.py

# 3. 测试功能
python test_cdn.py http://localhost:7997
```

#### 场景2：多服务器 + Workers（完整CDN）
```bash
# 在每台服务器上：
./deploy.sh  # 分别配置为 changsha/singapore/sydney

# 本地部署Workers：
npm install -g wrangler
wrangler login
# 修改 cloudflare-worker.js 中的源站域名
wrangler deploy
```

---

## 📖 文档阅读顺序

### 如果你是第一次部署：
1. 先读 **CDN_QUICKSTART.md** - 了解基本流程
2. 再读 **CDN_SUMMARY.md** - 理解架构设计
3. 遇到问题时查 **CDN_DEPLOYMENT_GUIDE.md** - 故障排查

### 如果你只是想测试：
1. 运行 `./deploy.sh`
2. 运行 `python test_cdn.py http://localhost:7997`

### 如果你要生产环境部署：
1. 完整阅读 **CDN_DEPLOYMENT_GUIDE.md**
2. 参考 `nginx.conf.example` 配置HTTPS
3. 参考 `biliurl.service.example` 配置系统服务
4. 使用 `test_cdn.py` 验证所有功能

---

## 🔧 各文件详细说明

### `cloudflare-worker.js`

**核心功能：**
- 地理位置检测（基于 `CF-IPCountry`）
- 智能路由到最近源站
- 静态资源边缘缓存
- 健康检查与故障转移
- **不缓存媒体URL**（NCM和B站都是动态URL）

**需要修改的地方：**
```javascript
// 第15-27行：填写你的源站域名
const CONFIG = {
  origins: {
    changsha: {
      url: 'https://cn.yourdomain.com',  // ← 改这里
      // ...
    },
    // ...
  }
}
```

**路由规则：**
- 中国大陆(CN) → 长沙
- 澳大利亚(AU) → 悉尼
- 其他亚洲 → 新加坡

---

### `deploy.sh`

**功能：**
1. 检查Python/pip依赖
2. 安装requirements.txt
3. 配置环境变量（NODE_NAME, NODE_REGION）
4. 可选：创建systemd服务
5. 测试健康检查

**使用方法：**
```bash
chmod +x deploy.sh
./deploy.sh

# 按提示输入：
# - 节点名称: changsha-01 / singapore-01 / sydney-01
# - 节点区域: mainland_china / asia / australia
```

**生成的文件：**
- `.env` - 环境变量配置
- `/etc/systemd/system/biliurl.service` - systemd服务（可选）

---

### `test_cdn.py`

**测试项目：**
1. ✅ 健康检查端点
2. ✅ B站视频播放（多清晰度）
3. ✅ NCM音乐播放
4. ✅ 关键词搜索
5. ✅ 响应时间测试

**使用方法：**
```bash
# 测试本地服务
python test_cdn.py http://localhost:7997

# 测试生产环境
python test_cdn.py https://api.yourdomain.com

# 或直接运行（会提示输入URL）
python test_cdn.py
```

**输出示例：**
```
============================================================
CDN 系统功能测试
============================================================

ℹ️  测试目标: http://localhost:7997

============================================================
测试 1: 健康检查端点
============================================================
✅ 健康检查通过
ℹ️  状态: healthy
ℹ️  节点: changsha-01
ℹ️  区域: mainland_china
...
```

---

### `nginx.conf.example`

**配置内容：**
- HTTP自动跳转HTTPS
- SSL证书配置
- 反向代理到Python应用（端口7997）
- 静态文件加速（可选）
- 安全头部
- 日志配置

**部署步骤：**
```bash
# 1. 复制配置
sudo cp nginx.conf.example /etc/nginx/sites-available/biliurl

# 2. 修改域名和证书路径
sudo nano /etc/nginx/sites-available/biliurl

# 3. 启用站点
sudo ln -s /etc/nginx/sites-available/biliurl /etc/nginx/sites-enabled/

# 4. 测试配置
sudo nginx -t

# 5. 重载Nginx
sudo systemctl reload nginx
```

---

### `biliurl.service.example`

**systemd服务配置，用于：**
- 开机自动启动
- 进程守护（崩溃自动重启）
- 日志管理

**部署步骤：**
```bash
# 1. 复制并修改配置
sudo cp biliurl.service.example /etc/systemd/system/biliurl.service
sudo nano /etc/systemd/system/biliurl.service
# 修改: User, WorkingDirectory, NODE_NAME, NODE_REGION

# 2. 重载systemd
sudo systemctl daemon-reload

# 3. 启动服务
sudo systemctl start biliurl

# 4. 开机自启
sudo systemctl enable biliurl

# 5. 查看状态
sudo systemctl status biliurl

# 6. 查看日志
sudo journalctl -u biliurl -f
```

---

### `wrangler.toml`

**Cloudflare Workers部署配置**

**修改说明：**
```toml
name = "biliurl-cdn"  # Worker名称

[env.production]
route = "api.yourdomain.com/*"  # ← 改为你的域名
```

**使用方法：**
```bash
# 开发环境部署（临时域名）
wrangler deploy

# 生产环境部署
wrangler deploy --env production

# 查看日志
wrangler tail
```

---

## 🎯 典型部署流程

### 单服务器部署（5分钟）

```bash
# 1. 克隆代码
git clone <your-repo>
cd biliurl

# 2. 部署
./deploy.sh
# 输入: changsha-01, mainland_china

# 3. 启动
python run_server.py

# 4. 测试
python test_cdn.py http://localhost:7997
```

### 完整CDN部署（30分钟）

```bash
# === 在每台服务器上 ===
./deploy.sh
sudo systemctl start biliurl
sudo systemctl enable biliurl

# === 配置Nginx（每台服务器）===
sudo cp nginx.conf.example /etc/nginx/sites-available/biliurl
# 修改域名和证书
sudo ln -s /etc/nginx/sites-available/biliurl /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# === 部署Workers（本地）===
npm install -g wrangler
wrangler login
# 修改 cloudflare-worker.js 中的源站域名
wrangler deploy

# === 在Cloudflare绑定域名 ===
# Dashboard → Workers → 你的Worker → Settings → Triggers
# → Add Custom Domain: api.yourdomain.com

# === 测试 ===
python test_cdn.py https://api.yourdomain.com
```

---

## 💡 常见问题

### Q: 需要修改哪些文件？
**A:** 只需要修改 `cloudflare-worker.js` 中的源站域名（第15-27行）

### Q: 是否需要修改Python代码？
**A:** 不需要！所有必要的改动已经在 `ncm/api/routes.py` 中完成

### Q: 如何知道Workers路由到了哪个源站？
**A:** 查看响应头 `X-Origin-Server`：
```bash
curl -I https://api.yourdomain.com/health | grep X-Origin-Server
```

### Q: 如何监控系统状态？
**A:** 
- Cloudflare Dashboard - 查看请求统计
- `wrangler tail` - 实时查看Workers日志
- `sudo journalctl -u biliurl -f` - 查看源站日志

---

## 📞 获取帮助

1. **快速问题** → 查看 CDN_QUICKSTART.md
2. **部署问题** → 查看 CDN_DEPLOYMENT_GUIDE.md 的故障排查章节
3. **架构理解** → 查看 CDN_SUMMARY.md
4. **功能测试** → 运行 `python test_cdn.py`

---

## 📊 文件依赖关系

```
部署流程:
  deploy.sh
    ├─> 安装 requirements.txt
    ├─> 生成 .env
    └─> 可选: 生成 /etc/systemd/system/biliurl.service

生产环境:
  nginx.conf.example → /etc/nginx/sites-enabled/
  biliurl.service.example → /etc/systemd/system/
  cloudflare-worker.js + wrangler.toml → Cloudflare Workers

测试验证:
  test_cdn.py → 验证所有端点功能
```

---

**祝部署顺利！🚀**
