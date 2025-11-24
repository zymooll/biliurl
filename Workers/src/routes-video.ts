/**
 * 视频下载路由处理
 */

import { Hono } from 'hono';
import { verifyRequest, limitQuality } from './auth';
import { getCid, getVideoInfo, getStream } from './bilibili';
import { getCookies } from './cookies-manager';

export const videoRouter = new Hono();

/**
 * 获取视频或音频流
 * GET /api/bili/:bvid
 * 
 * Query Parameters:
 * - key: API Key (required)
 * - type: 'video', 'audio', or 'raw' (default: 'video')
 * - quality: 画质代码 (default: API Key 允许的最高画质)
 */
videoRouter.get('/api/bili/:bvid', async (c) => {
  try {
    const bvid = c.req.param('bvid');
    const apiKey = c.req.query('key') || c.req.header('X-API-Key');
    const streamType = (c.req.query('type') || 'video').toLowerCase();
    const requestedQuality = c.req.query('quality');
    
    // 验证 API Key
    const verifyResult = await verifyRequest(apiKey, c.env);
    if (!verifyResult.valid) {
      return c.json({
        error: verifyResult.error || '无效的 API Key'
      }, 401);
    }
    
    // 验证 type 参数
    if (!['video', 'audio', 'raw'].includes(streamType)) {
      return c.json({
        error: 'Invalid type. Use type=video, type=audio, or type=raw'
      }, 400);
    }
    
    // 限制画质
    const maxQuality = verifyResult.apiInfo!.max_quality;
    const quality = limitQuality(requestedQuality, maxQuality);
    
    // 获取 cookies（如果使用 pro key）
    let cookies: string | null = null;
    if (apiKey === 'pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh') {
      cookies = await getCookies(c.env);
    }
    
    // 获取视频信息
    const cid = await getCid(bvid, cookies || undefined);
    const streamUrl = await getStream(bvid, cid, quality, cookies || undefined);
    const videoInfo = await getVideoInfo(bvid, cookies || undefined);
    
    // 根据 type 返回不同的结果
    if (streamType === 'raw') {
      return c.json({
        info: videoInfo,
        video_url: streamUrl.video,
        audio_url: streamUrl.audio,
        api_level: verifyResult.apiInfo!.name,
        quality_used: quality
      });
    }
    
    // 对于 video 和 audio，重定向到原始 URL
    // 浏览器会自动携带正确的 Referer，避免 403 错误
    if (streamType === 'video') {
      return c.redirect(streamUrl.video, 302);
    } else {
      return c.redirect(streamUrl.audio, 302);
    }
  } catch (error) {
    console.error('获取视频流失败:', error);
    return c.json({
      error: '获取视频流失败: ' + (error as any).message
    }, 400);
  }
});

/**
 * 获取视频信息
 * GET /api/bili/:bvid/info
 */
videoRouter.get('/api/bili/:bvid/info', async (c) => {
  try {
    const bvid = c.req.param('bvid');
    const apiKey = c.req.query('key') || c.req.header('X-API-Key');
    
    // 验证 API Key
    const verifyResult = await verifyRequest(apiKey, c.env);
    if (!verifyResult.valid) {
      return c.json({
        error: verifyResult.error || '无效的 API Key'
      }, 401);
    }
    
    // 获取 cookies（如果使用 pro key）
    let cookies: string | null = null;
    if (apiKey === 'pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh') {
      cookies = await getCookies(c.env);
    }
    
    const videoInfo = await getVideoInfo(bvid, cookies || undefined);
    
    if (!videoInfo) {
      return c.json({
        error: '无法获取视频信息'
      }, 404);
    }
    
    return c.json(videoInfo);
  } catch (error) {
    console.error('获取视频信息失败:', error);
    return c.json({
      error: '获取视频信息失败: ' + (error as any).message
    }, 400);
  }
});

/**
 * 获取原始流 URLs
 * GET /api/bili/:bvid/streams
 */
videoRouter.get('/api/bili/:bvid/streams', async (c) => {
  try {
    const bvid = c.req.param('bvid');
    const apiKey = c.req.query('key') || c.req.header('X-API-Key');
    const requestedQuality = c.req.query('quality');
    
    // 验证 API Key
    const verifyResult = await verifyRequest(apiKey, c.env);
    if (!verifyResult.valid) {
      return c.json({
        error: verifyResult.error || '无效的 API Key'
      }, 401);
    }
    
    // 限制画质
    const maxQuality = verifyResult.apiInfo!.max_quality;
    const quality = limitQuality(requestedQuality, maxQuality);
    
    // 获取 cookies（如果使用 pro key）
    let cookies: string | null = null;
    if (apiKey === 'pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh') {
      cookies = await getCookies(c.env);
    }
    
    const cid = await getCid(bvid, cookies || undefined);
    const streamUrl = await getStream(bvid, cid, quality, cookies || undefined);
    const videoInfo = await getVideoInfo(bvid, cookies || undefined);
    
    return c.json({
      info: videoInfo,
      streams: {
        video: streamUrl.video,
        audio: streamUrl.audio
      },
      api_level: verifyResult.apiInfo!.name,
      quality_used: quality,
      note: '返回的 URL 包含签名和时间戳，需要在浏览器中访问，请不要直接 curl 测试。可使用 ffmpeg 或其他工具下载。'
    });
  } catch (error) {
    console.error('获取流 URLs 失败:', error);
    return c.json({
      error: '获取流 URLs 失败: ' + (error as any).message
     }, 400);
  }
});

/**
 * 代理视频流下载 - 流式传输
 * GET /api/bili/:bvid/proxy-video
 * 
 * Workers 作为代理服务器，从 Bilibili 获取视频流并转发给客户端
 * 支持 Range 请求以便断点续传
 */
videoRouter.get('/api/bili/:bvid/proxy-video', async (c) => {
  try {
    const bvid = c.req.param('bvid');
    const apiKey = c.req.query('key') || c.req.header('X-API-Key');
    const requestedQuality = c.req.query('quality');
    
    // 验证 API Key
    const verifyResult = await verifyRequest(apiKey, c.env);
    if (!verifyResult.valid) {
      return c.json({
        error: verifyResult.error || '无效的 API Key'
      }, 401);
    }
    
    // 限制画质
    const maxQuality = verifyResult.apiInfo!.max_quality;
    const quality = limitQuality(requestedQuality, maxQuality);
    
    // 获取 cookies（如果使用 pro key）
    let cookies: string | null = null;
    if (apiKey === 'pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh') {
      cookies = await getCookies(c.env);
    }
    
    const cid = await getCid(bvid, cookies || undefined);
    const streamUrl = await getStream(bvid, cid, quality, cookies || undefined);
    
    // 构建请求头，包含 Referer 和 User-Agent，这样 Bilibili 就不会返回 403
    const proxyHeaders: Record<string, string> = {
      'Referer': 'https://www.bilibili.com/',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Accept': '*/*',
      'Accept-Language': 'zh-CN,zh;q=0.9',
      'Accept-Encoding': 'gzip, deflate, br'
    };
    
    // 支持 Range 请求
    const rangeHeader = c.req.header('Range');
    if (rangeHeader) {
      proxyHeaders['Range'] = rangeHeader;
    }
    
    const videoResponse = await fetch(streamUrl.video, { 
      headers: proxyHeaders,
      cf: {
        cacheTtl: 300, // 缓存 5 分钟
        cacheEverything: true
      }
    });
    
    if (!videoResponse.ok && videoResponse.status !== 206) {
      console.error('获取视频流失败:', {
        status: videoResponse.status,
        statusText: videoResponse.statusText
      });
      return c.json({
        error: `无法获取视频流: ${videoResponse.status} ${videoResponse.statusText}`
      }, 400);
    }
    
    // 获取原始响应的 headers
    const responseHeaders: Record<string, string> = {
      'Content-Type': videoResponse.headers.get('Content-Type') || 'video/mp4',
      'Accept-Ranges': 'bytes',
      'Access-Control-Allow-Origin': '*'
    };
    
    // 保留 Content-Length 和 Content-Range
    const contentLength = videoResponse.headers.get('Content-Length');
    const contentRange = videoResponse.headers.get('Content-Range');
    
    if (contentLength) {
      responseHeaders['Content-Length'] = contentLength;
    }
    if (contentRange) {
      responseHeaders['Content-Range'] = contentRange;
    }
    
    // 返回流式响应
    return new Response(videoResponse.body, {
      status: videoResponse.status,
      headers: responseHeaders
    });
  } catch (error) {
    console.error('代理视频流失败:', error);
    return c.json({
      error: '代理视频流失败: ' + (error as any).message
    }, 400);
  }
});

/**
 * 代理音频流下载 - 流式传输
 * GET /api/bili/:bvid/proxy-audio
 */
videoRouter.get('/api/bili/:bvid/proxy-audio', async (c) => {
  try {
    const bvid = c.req.param('bvid');
    const apiKey = c.req.query('key') || c.req.header('X-API-Key');
    const requestedQuality = c.req.query('quality');
    
    // 验证 API Key
    const verifyResult = await verifyRequest(apiKey, c.env);
    if (!verifyResult.valid) {
      return c.json({
        error: verifyResult.error || '无效的 API Key'
      }, 401);
    }
    
    // 限制画质
    const maxQuality = verifyResult.apiInfo!.max_quality;
    const quality = limitQuality(requestedQuality, maxQuality);
    
    // 获取 cookies（如果使用 pro key）
    let cookies: string | null = null;
    if (apiKey === 'pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh') {
      cookies = await getCookies(c.env);
    }
    
    const cid = await getCid(bvid, cookies || undefined);
    const streamUrl = await getStream(bvid, cid, quality, cookies || undefined);
    
    // 构建请求头
    const proxyHeaders: Record<string, string> = {
      'Referer': 'https://www.bilibili.com/',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Accept': '*/*',
      'Accept-Language': 'zh-CN,zh;q=0.9',
      'Accept-Encoding': 'gzip, deflate, br'
    };
    
    // 支持 Range 请求
    const rangeHeader = c.req.header('Range');
    if (rangeHeader) {
      proxyHeaders['Range'] = rangeHeader;
    }
    
    const audioResponse = await fetch(streamUrl.audio, { 
      headers: proxyHeaders,
      cf: {
        cacheTtl: 300,
        cacheEverything: true
      }
    });
    
    if (!audioResponse.ok && audioResponse.status !== 206) {
      console.error('获取音频流失败:', {
        status: audioResponse.status,
        statusText: audioResponse.statusText
      });
      return c.json({
        error: `无法获取音频流: ${audioResponse.status} ${audioResponse.statusText}`
      }, 400);
    }
    
    // 获取原始响应的 headers
    const responseHeaders: Record<string, string> = {
      'Content-Type': audioResponse.headers.get('Content-Type') || 'audio/mp4',
      'Accept-Ranges': 'bytes',
      'Access-Control-Allow-Origin': '*'
    };
    
    // 保留 Content-Length 和 Content-Range
    const contentLength = audioResponse.headers.get('Content-Length');
    const contentRange = audioResponse.headers.get('Content-Range');
    
    if (contentLength) {
      responseHeaders['Content-Length'] = contentLength;
    }
    if (contentRange) {
      responseHeaders['Content-Range'] = contentRange;
    }
    
    // 返回流式响应
    return new Response(audioResponse.body, {
      status: audioResponse.status,
      headers: responseHeaders
    });
  } catch (error) {
    console.error('代理音频流失败:', error);
    return c.json({
      error: '代理音频流失败: ' + (error as any).message
    }, 400);
  }
});
