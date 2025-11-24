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
    // Cloudflare Workers 不能直接返回文件流，所以我们返回重定向 URL
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
      quality_used: quality
    });
  } catch (error) {
    console.error('获取流 URLs 失败:', error);
    return c.json({
      error: '获取流 URLs 失败: ' + (error as any).message
    }, 400);
  }
});
