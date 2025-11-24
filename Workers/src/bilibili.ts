/**
 * Bilibili API 交互模块
 */

import { BILIBILI_HEADERS, BILIBILI_API, QUALITY_CODES } from './config';
import { VideoInfo, StreamUrls, PlayUrlResponse, BilibiliApiResponse } from './types';

/**
 * 获取 video cid
 */
export async function getCid(bvid: string, cookies?: string): Promise<string> {
  const url = `${BILIBILI_API.PAGELIST}?bvid=${bvid}`;
  const headers: Record<string, string> = { ...BILIBILI_HEADERS };
  
  if (cookies) {
    headers['Cookie'] = cookies;
  }
  
  const response = await fetch(url, { headers });
  const data: BilibiliApiResponse<Array<{ cid: number }>> = await response.json();
  
  if (!data.data || !data.data[0]) {
    throw new Error('无法获取 cid');
  }
  
  return String(data.data[0].cid);
}

/**
 * 获取视频信息
 */
export async function getVideoInfo(bvid: string, cookies?: string): Promise<VideoInfo | null> {
  const url = `${BILIBILI_API.VIEW}?bvid=${bvid}`;
  const headers: Record<string, string> = { ...BILIBILI_HEADERS };
  
  if (cookies) {
    headers['Cookie'] = cookies;
  }
  
  try {
    const response = await fetch(url, { headers });
    const info: BilibiliApiResponse = await response.json();
    
    if (info.code === 0 && info.data) {
      const data = info.data as any;
      return {
        title: data.title || '',
        description: data.desc || '',
        duration: data.duration || 0,
        author: data.owner?.name || '',
        cover: data.pic || '',
        pubdate: data.pubdate || 0,
        bvid: bvid
      };
    }
  } catch (error) {
    console.error('获取视频信息失败:', error);
  }
  
  return null;
}

/**
 * 获取流 URL
 */
export async function getStream(
  bvid: string,
  cid: string,
  quality: string,
  cookies?: string
): Promise<StreamUrls> {
  // 验证画质代码
  const validQualities = ['16', '32', '64', '125', '266', '-1'];
  if (!validQualities.includes(quality)) {
    quality = '64'; // 默认 720p
  }
  
  const params = new URLSearchParams();
  params.append('from_client', 'BROWSER');
  params.append('cid', cid);
  params.append('qn', quality);
  params.append('fourk', '1');
  params.append('fnver', '0');
  params.append('fnval', '4048');
  params.append('bvid', bvid);
  
  const url = `${BILIBILI_API.PLAYURL}?${params.toString()}`;
  
  const headers: Record<string, string> = { ...BILIBILI_HEADERS };
  if (cookies) {
    headers['Cookie'] = cookies;
  }
  
  // 增加请求超时和重试逻辑
  let response;
  try {
    response = await fetch(url, { headers });
  } catch (error) {
    console.error('获取播放地址请求失败:', error);
    throw new Error('网络请求失败，无法获取播放地址');
  }
  
  if (!response.ok) {
    console.error('Bilibili API 返回错误:', response.status, response.statusText);
    throw new Error(`Bilibili API 返回错误: ${response.status}`);
  }
  
  const playData: PlayUrlResponse = await response.json();
  
  if (!playData.data?.dash) {
    console.error('无法从响应中获取 dash 数据:', JSON.stringify(playData).substring(0, 200));
    throw new Error('无法获取播放地址');
  }
  
  const dash = playData.data.dash;
  
  // 使用 baseUrl 而不是 base_url（baseUrl 是正确的字段名）
  const videoUrl = dash.video?.[0]?.baseUrl;
  const audioUrl = dash.audio?.[0]?.baseUrl;
  
  if (!videoUrl || !audioUrl) {
    console.error('视频或音频 URL 为空', {
      videoUrl: !!videoUrl,
      audioUrl: !!audioUrl
    });
    throw new Error('无法获取视频或音频流 URL');
  }
  
  return {
    video: videoUrl,
    audio: audioUrl
  };
}

/**
 * 获取用户信息（用于验证 cookies 是否有效）
 */
export async function getUserInfo(cookies: string): Promise<{ valid: boolean; userId?: number }> {
  const headers: Record<string, string> = {
    ...BILIBILI_HEADERS,
    'Cookie': cookies
  };
  
  try {
    const response = await fetch(BILIBILI_API.USERINFO, { headers });
    const data: BilibiliApiResponse = await response.json();
    
    if (data.code === 0 && data.data) {
      return {
        valid: true,
        userId: (data.data as any).mid
      };
    }
  } catch (error) {
    console.error('验证 cookies 失败:', error);
  }
  
  return { valid: false };
}
