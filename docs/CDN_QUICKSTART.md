# CDN 分布式部署 - 快速开始

> **架构：** Cloudflare Workers（全球边缘）+ 多区域源站（长沙/新加坡/澳洲）

## 🚀 5分钟快速部署

### 前置要求
- 3台VPS服务器（长沙/新加坡/澳洲）
- 一个域名（可在Cloudflare托管）
- Cloudflare账号（免费）

---

## 第一步：部署源站（每台服务器执行）

```bash
# 1. 克隆代码
git clone <your-repo-url>
cd biliurl

# 2. 一键部署
./deploy.sh

# 根据提示输入：
# - 节点名称: changsha-01 / singapore-01 / sydney-01
# - 节点区域: mainland_china / asia / australia

# 3. 启动服务
python run_server.py
```

**验证：**
```bash
curl http://localhost:7997/health
# 应该返回 {"status": "healthy", ...}
```

---

## 第二步：配置域名

在Cloudflare DNS中添加A记录：

```
cn.yourdomain.com → 长沙服务器IP（主力）
sg.yourdomain.com → 新加坡服务器IP
au.yourdomain.com → 澳洲服务器IP
```

**配置SSL：**
1. Cloudflare开启 "Full" SSL模式
2. 在源站下载 Cloudflare Origin Certificate
3. 配置Nginx（参考 `nginx.conf.example`）

---

## 第三步：部署Workers

```bash
# 1. 安装Wrangler
npm install -g wrangler
wrangler login

# 2. 修改配置
# 编辑 cloudflare-worker.js 第15-27行
# 填写你的源站域名：
#   changsha.url: 'https://cn.yourdomain.com'
#   singapore.url: 'https://sg.yourdomain.com'  
#   sydney.url: 'https://au.yourdomain.com'

# 3. 部署
wrangler deploy

# 4. 在Cloudflare Dashboard绑定域名
# Workers & Pages → 你的Worker → Settings → Triggers
# → Add Custom Domain: api.yourdomain.com
```

---

## 第四步：测试验证

```bash
# 1. 测试健康检查
curl https://api.yourdomain.com/health

# 2. 测试B站视频播放
curl -I "https://api.yourdomain.com/play/vrc?bvid=BV1HfK3zPEHE"
# 应该返回 302 重定向

# 3. 测试NCM音乐播放  
curl -I "https://api.yourdomain.com/play/vrc?id=1856336348"
# 应该返回 302 重定向

# 4. 测试智能路由
curl -I https://api.yourdomain.com/health | grep X-Origin-Server
# 查看路由到了哪个源站
```

---

## ✅ 完成！

您的系统现在已经：
- ✅ 在全球200+节点加速
- ✅ 自动选择最近服务器
- ✅ 支持故障自动转移
- ✅ 满足NCM固定IP约束
- ✅ 正确处理B站一次性URL

---

## 📊 预期效果

| 用户地区 | 延迟改善 | 路由节点 |
|---------|---------|---------|
| 🇨🇳 中国大陆 | ↓ 30-50% | 长沙 |
| 🇦🇺 澳大利亚 | ↓ 60-70% | 悉尼 |
| 🇸🇬 东南亚 | ↓ 40-50% | 新加坡 |
| 🌏 其他地区 | ↓ 20-40% | 最近节点 |

---

## 📚 详细文档

- **[CDN_SUMMARY.md](CDN_SUMMARY.md)** - 完整改造说明和架构设计
- **[CDN_DEPLOYMENT_GUIDE.md](CDN_DEPLOYMENT_GUIDE.md)** - 详细部署指南和故障排查
- **[cloudflare-worker.js](cloudflare-worker.js)** - Workers代码（含详细注释）
- **[nginx.conf.example](nginx.conf.example)** - Nginx配置示例

---

## 🔧 常见问题

### Q: Workers会缓存媒体URL吗？
**A:** 不会。NCM和B站的URL都是动态/一次性的，Workers只做智能路由，不缓存URL。

### Q: 如何保证NCM的固定IP需求？
**A:** 所有NCM请求回源到固定的VPS，对api-enhanced来说IP不变。

### Q: 成本多少？
**A:** Cloudflare Workers免费（10万请求/天），主要成本是3台VPS约¥500-600/月。

### Q: 如何监控？
**A:** Cloudflare Dashboard查看请求统计，源站运行 `wrangler tail` 查看实时日志。

---

## 💡 提示

- 建议先在一台服务器测试完整流程
- 可以先不配置多台服务器，单服务器也能用
- Workers配置错误不影响源站直接访问
- 遇到问题查看 CDN_DEPLOYMENT_GUIDE.md 的故障排查章节

---

**需要帮助？** 查看完整文档或提交Issue
