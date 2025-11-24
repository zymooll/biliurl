/**
 * Cookies 管理模块
 */

import { CookiesData } from './types';

const COOKIES_STORE_KEY = 'bili_cookies';
const COOKIES_EXPIRY = 30 * 24 * 60 * 60 * 1000; // 30 天过期

/**
 * 存储 cookies 到 KV
 */
export async function storeCookies(
  env: any,
  cookieString: string,
  userId?: string
): Promise<boolean> {
  try {
    const cookiesData: CookiesData = {
      cookies: cookieString,
      expires_at: Date.now() + COOKIES_EXPIRY,
      user_id: userId
    };
    
    await env.COOKIES_KV.put(COOKIES_STORE_KEY, JSON.stringify(cookiesData), {
      expirationTtl: 30 * 24 * 60 * 60 // 30 天
    });
    
    return true;
  } catch (error) {
    console.error('存储 cookies 失败:', error);
    return false;
  }
}

/**
 * 从 KV 获取 cookies
 */
export async function getCookies(env: any): Promise<string | null> {
  try {
    const data = await env.COOKIES_KV.get(COOKIES_STORE_KEY);
    
    if (!data) {
      return null;
    }
    
    const cookiesData: CookiesData = JSON.parse(data);
    
    // 检查是否过期
    if (cookiesData.expires_at < Date.now()) {
      await env.COOKIES_KV.delete(COOKIES_STORE_KEY);
      return null;
    }
    
    return cookiesData.cookies;
  } catch (error) {
    console.error('获取 cookies 失败:', error);
    return null;
  }
}

/**
 * 删除存储的 cookies
 */
export async function deleteCookies(env: any): Promise<void> {
  try {
    await env.COOKIES_KV.delete(COOKIES_STORE_KEY);
  } catch (error) {
    console.error('删除 cookies 失败:', error);
  }
}

/**
 * 检查是否有有效的 cookies
 */
export async function hasCookies(env: any): Promise<boolean> {
  const cookies = await getCookies(env);
  return cookies !== null && cookies.length > 0;
}
