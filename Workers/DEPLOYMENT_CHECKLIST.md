# 部署检查清单

使用此清单确保所有部署步骤都已完成。

## 预部署检查

- [ ] 安装 Node.js 18+（运行 `node --version` 验证）
- [ ] 安装 Wrangler（运行 `npm install -g wrangler`）
- [ ] 拥有有效的 Cloudflare 账户
- [ ] 账户中已启用 Workers

## 本地设置

- [ ] 克隆或下载项目到本地
- [ ] 进入 `Workers` 目录
- [ ] 运行 `npm install` 安装依赖
- [ ] 运行 `wrangler login` 登录 Cloudflare

## 环境配置

- [ ] 创建 KV 命名空间：`wrangler kv:namespace create "biliurl-cookies"`
- [ ] 记下返回的 KV ID
- [ ] 编辑 `wrangler.toml`，填入正确的 KV ID
- [ ] 验证 `wrangler.toml` 中的 `name` 字段（Workers 名称）

## 代码审查

- [ ] 检查 `src/config.ts` 中的 API Keys 配置
- [ ] 确认 Bilibili API 端点仍然有效
- [ ] 验证 TypeScript 编译无错误（可选：`npm run build`）

## 本地测试

- [ ] 运行 `npm run dev` 启动本地开发服务器
- [ ] 访问 `http://localhost:8787/health` 验证服务运行
- [ ] 访问 `http://localhost:8787/api/docs` 查看 API 文档
- [ ] 测试登录端点：`curl -X POST http://localhost:8787/api/login -H "Content-Type: application/json" -d '{"cookies":"test"}'`

## 部署

- [ ] 运行 `npm run deploy` 部署到 Cloudflare
- [ ] 记下返回的 Worker URL（例如：`https://biliurl-xxx.workers.dev`）
- [ ] 等待部署完成（通常 1-2 分钟）

## 部署后验证

- [ ] 访问 `https://your-worker.workers.dev/health` 验证部署成功
- [ ] 访问 `https://your-worker.workers.dev/api/docs` 查看完整文档
- [ ] 检查 `https://your-worker.workers.dev/api/auth/status` （应返回 `authenticated: false`）

## 测试功能

### 基础测试（无需登录）

- [ ] 测试 public key：
  ```bash
  curl 'https://your-worker.workers.dev/api/bili/BV1Xx411c7mD/info?key=public_j389u4tc9w08u4pq4mqp9xwup4'
  ```

### 登录流程测试

- [ ] 获取有效的 Bilibili Cookies
- [ ] 调用登录端点：
  ```bash
  curl -X POST 'https://your-worker.workers.dev/api/login' \
    -H "Content-Type: application/json" \
    -d '{"cookies":"your_cookies_here"}'
  ```
- [ ] 验证返回 `success: true` 和 pro key
- [ ] 检查 `https://your-worker.workers.dev/api/auth/status` （应返回 `authenticated: true`）

### Pro Key 测试

- [ ] 使用 pro key 获取 1080p 视频：
  ```bash
  curl 'https://your-worker.workers.dev/api/bili/BV1Xx411c7mD/streams?key=pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh&quality=125'
  ```
- [ ] 验证返回的视频 URL 可访问

### 完整下载测试

- [ ] 使用提供的脚本进行完整下载测试
- [ ] 验证最终 MP4 文件可以播放

## 监控设置

- [ ] 订阅 Workers 监控告警（可选）
- [ ] 设置日志收集（可选，使用 wrangler tail）
- [ ] 定期检查使用配额

## 文档

- [ ] 阅读 `README.md` 了解完整功能
- [ ] 阅读 `QUICKSTART.md` 快速上手
- [ ] 保存 Worker URL 用于分享
- [ ] 为用户准备使用说明

## 安全检查

- [ ] 不将 API Keys 提交到公开仓库
- [ ] 定期更新 Bilibili Cookies
- [ ] 不在客户端代码中暴露 API Key
- [ ] 定期审计访问日志

## 故障排除

如果部署失败：

- [ ] 检查 Wrangler 版本（运行 `wrangler --version`）
- [ ] 验证网络连接
- [ ] 检查 `wrangler.toml` 语法
- [ ] 查看详细错误：运行 `wrangler deploy --verbose`

如果测试失败：

- [ ] 检查 Bilibili API 是否可访问
- [ ] 验证 Cookies 是否有效和未过期
- [ ] 检查网络是否有代理/防火墙限制
- [ ] 使用 `wrangler tail` 查看实时日志

## 成功标志 ✅

当以下条件都满足时，部署成功：

1. ✅ Worker 已在 Cloudflare 上运行
2. ✅ `/health` 端点返回 `status: ok`
3. ✅ `/api/docs` 返回完整的 API 文档
4. ✅ 能够登录并获得 Pro Key
5. ✅ 能够获取视频信息和流 URLs
6. ✅ 支持 1080p 视频下载（使用 Pro Key）

## 常见问题

### Q: KV 命名空间 ID 在哪里找？
**A:** 运行 `wrangler kv:namespace create "biliurl-cookies"` 时会显示，或在 Cloudflare Dashboard > Workers > KV 中查看

### Q: 可以改变 Worker 名称吗？
**A:** 可以，编辑 `wrangler.toml` 的 `name` 字段，然后重新部署

### Q: 如何查看实时日志？
**A:** 运行 `wrangler tail`

### Q: 能否升级代码而不丢失 Cookies？
**A:** 可以，Cookies 存储在 KV 中，升级代码不会影响

### Q: 免费配额是多少？
**A:** 每月 100,000 请求（足以满足小规模使用）

## 维护任务

每月定期：
- [ ] 检查 Worker 错误日志
- [ ] 验证 Cookies 仍然有效
- [ ] 测试下载功能是否正常
- [ ] 检查 Cloudflare 的相关公告（API 变更等）

## 支持和反馈

- 查看 GitHub Issues
- 检查 Cloudflare Workers 官方文档
- 参考 Bilibili API 文档

---

**部署状态:** ⏳ 准备就绪

**预计部署时间:** 5-10 分钟

**完成后可以开始下载 Bilibili 视频！** 🎉
