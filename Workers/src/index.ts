/**
 * Cloudflare Workers - Biliurl
 * 
 * Bilibili 视频下载 API
 */

import { Hono } from 'hono';
import { loginRouter } from './routes-login';
import { videoRouter } from './routes-video';

const app = new Hono();

// 健康检查端点
app.get('/health', (c: any) => {
  return c.json({ status: 'ok', message: 'Biliurl Workers 运行正常' });
});

// API 文档端点
app.get('/api/docs', (c: any) => {
  return c.json({
    title: 'Biliurl API - Cloudflare Workers',
    version: '1.0.0',
    description: 'Bilibili 视频下载 API',
    endpoints: {
      auth: {
        login: {
          method: 'POST',
          path: '/api/login',
          description: '登录并存储 cookies 以获取 pro key',
          body: { cookies: 'string' },
          response: { success: 'boolean', pro_key: 'string' }
        },
        logout: {
          method: 'POST',
          path: '/api/logout',
          description: '登出并删除存储的 cookies'
        },
        status: {
          method: 'GET',
          path: '/api/auth/status',
          description: '检查认证状态'
        }
      },
      video: {
        download: {
          method: 'GET',
          path: '/api/bili/:bvid',
          description: '下载视频或音频',
          parameters: {
            key: { required: true, description: 'API Key (public_xxx 或 pro_xxx)' },
            type: { required: false, description: 'video|audio|raw (默认: video)' },
            quality: { required: false, description: '画质代码 (16|32|64|125|266)' }
          }
        },
        info: {
          method: 'GET',
          path: '/api/bili/:bvid/info',
          description: '获取视频信息'
        },
        streams: {
          method: 'GET',
          path: '/api/bili/:bvid/streams',
          description: '获取视频流 URLs（包含签名，需要在浏览器中访问）'
        },
        proxyVideo: {
          method: 'GET',
          path: '/api/bili/:bvid/proxy-video',
          description: '通过 Workers 代理获取视频流（解决 403 跨域问题）',
          parameters: {
            key: { required: true, description: 'API Key' },
            quality: { required: false, description: '画质代码' }
          }
        },
        proxyAudio: {
          method: 'GET',
          path: '/api/bili/:bvid/proxy-audio',
          description: '通过 Workers 代理获取音频流（解决 403 跨域问题）',
          parameters: {
            key: { required: true, description: 'API Key' },
            quality: { required: false, description: '画质代码' }
          }
        }
      }
    }
  });
});

// 路由挂载
app.route('/', loginRouter);
app.route('/', videoRouter);

// 404 处理
app.all('*', (c: any) => {
  return c.json({
    error: '404 - 资源不存在',
    path: c.req.path
  }, 404);
});

export default app;
