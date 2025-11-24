/**
 * 请求验证模块
 */

import { DEFAULT_API_KEYS } from './config';
import { getCookies, hasCookies } from './cookies-manager';
import { VerifyResult } from './types';

/**
 * 验证请求的 API Key
 */
export async function verifyRequest(
  key: string | null | undefined,
  env: any
): Promise<VerifyResult> {
  // 检查 public key
  if (key && key in DEFAULT_API_KEYS) {
    return {
      valid: true,
      apiInfo: DEFAULT_API_KEYS[key]
    };
  }
  
  // 检查 pro key - 需要有效的 cookies
  if (key === 'pro_q3j984jjw4908jqcw94htw94ew84unt9ohogeh') {
    const cookiesValid = await hasCookies(env);
    if (cookiesValid) {
      return {
        valid: true,
        apiInfo: {
          max_quality: '125',
          name: '1080p 限制'
        }
      };
    } else {
      return {
        valid: false,
        error: '无效的 pro key：未检测到有效的 cookies'
      };
    }
  }
  
  // 如果没有提供 key，返回错误
  if (!key) {
    return {
      valid: false,
      error: '缺少 API Key'
    };
  }
  
  return {
    valid: false,
    error: '无效的 API Key'
  };
}

/**
 * 限制画质
 */
export function limitQuality(
  requestedQuality: string | null | undefined,
  maxQuality: string
): string {
  if (!requestedQuality) {
    return maxQuality;
  }
  
  try {
    const reqQualityInt = parseInt(requestedQuality, 10);
    const maxQualityInt = parseInt(maxQuality, 10);
    
    if (isNaN(reqQualityInt) || isNaN(maxQualityInt)) {
      return maxQuality;
    }
    
    if (reqQualityInt > maxQualityInt) {
      return maxQuality;
    }
    
    return requestedQuality;
  } catch {
    return maxQuality;
  }
}
