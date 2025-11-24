/**
 * TypeScript 类型定义
 */

export interface VideoInfo {
  title: string;
  description: string;
  duration: number;
  author: string;
  cover: string;
  pubdate: number;
  bvid: string;
}

export interface StreamUrls {
  video: string;
  audio: string;
}

export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data?: T;
}

export interface BilibiliApiResponse<T = any> {
  code: number;
  message: string;
  data?: T;
}

export interface DashData {
  video: Array<{ baseUrl: string; bandwidth: number }>;
  audio: Array<{ baseUrl: string; bandwidth: number }>;
}

export interface PlayUrlResponse {
  code: number;
  data: {
    dash: DashData;
  };
}

export interface CookiesData {
  cookies: string;
  expires_at: number;
  user_id?: string;
}

export interface VerifyResult {
  valid: boolean;
  error?: string;
  apiInfo?: {
    max_quality: string;
    name: string;
  };
}

export interface WorkerEnv {
  COOKIES_KV: any;
}

// KV 中存储的 cookies 信息
export interface StoredCookies {
  [key: string]: {
    value: string;
    timestamp: number;
    valid: boolean;
  };
}
