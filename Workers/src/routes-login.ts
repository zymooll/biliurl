/**
 * 登录路由处理
 */

import { Hono } from 'hono';
import { storeCookies, deleteCookies } from './cookies-manager';
import { getUserInfo } from './bilibili';

export const loginRouter = new Hono();

/**
 * 登录端点 - 接收 cookies 并存储
 * POST /api/login
 * 
 * Request Body:
 * {
 *   "cookies": "SESSDATA=xxx; DedeUserID=xxx; ..."
 * }
 * 
 * Response:
 * {
 *   "success": true,
 *   "message": "登录成功",
 *   "pro_key": "pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh"
 * }
 */
loginRouter.post('/api/login', async (c) => {
  try {
    const body = await c.req.json();
    const cookies = body.cookies;
    
    if (!cookies || typeof cookies !== 'string') {
      return c.json({
        success: false,
        error: '缺少或无效的 cookies 参数'
      }, 400);
    }
    
    // 验证 cookies 是否有效
    const userInfo = await getUserInfo(cookies);
    
    if (!userInfo.valid) {
      return c.json({
        success: false,
        error: 'cookies 无效或过期'
      }, 401);
    }
    
    // 存储 cookies 到 KV
    const env = c.env as any;
    const stored = await storeCookies(env, cookies, String(userInfo.userId));
    
    if (!stored) {
      return c.json({
        success: false,
        error: '存储 cookies 失败'
      }, 500);
    }
    
    return c.json({
      success: true,
      message: '登录成功',
      pro_key: 'pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh',
      user_id: userInfo.userId
    });
  } catch (error) {
    console.error('登录出错:', error);
    return c.json({
      success: false,
      error: '登录失败: ' + (error as any).message
    }, 500);
  }
});

/**
 * 登出端点 - 删除存储的 cookies
 * POST /api/logout
 */
loginRouter.post('/api/logout', async (c) => {
  try {
    const env = c.env as any;
    await deleteCookies(env);
    
    return c.json({
      success: true,
      message: '登出成功'
    });
  } catch (error) {
    console.error('登出出错:', error);
    return c.json({
      success: false,
      error: '登出失败'
    }, 500);
  }
});

/**
 * 获取当前登录状态
 * GET /api/auth/status
 */
loginRouter.get('/api/auth/status', async (c) => {
  try {
    const env = c.env as any;
    
    // 检查是否有有效的 cookies
    const cookies = await (await import('./cookies-manager')).getCookies(env);
    
    return c.json({
      authenticated: cookies !== null,
      pro_key: cookies ? 'pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh' : null
    });
  } catch (error) {
    return c.json({
      authenticated: false,
      error: '检查认证状态失败'
    }, 500);
  }
});
