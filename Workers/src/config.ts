/**
 * API 配置和常量
 */

export interface ApiKeyConfig {
  max_quality: string;
  name: string;
}

export interface ApiKeysMap {
  [key: string]: ApiKeyConfig;
}

// 默认 API 密钥配置
export const DEFAULT_API_KEYS: ApiKeysMap = {
  'public_j389u4tc9w08u4pq4mqp9xwup4': {
    max_quality: '64',
    name: '720p 限制'
  }
  // pro key 将根据有效的 cookies 动态添加
};

// HTTP Headers 配置
export const BILIBILI_HEADERS: Record<string, string> = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
  'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
  'Accept-Encoding': 'gzip, deflate',
  'Connection': 'keep-alive',
  'Upgrade-Insecure-Requests': '1',
  'Cache-Control': 'max-age=0',
  'Origin': 'https://www.bilibili.com',
  'Referer': 'https://www.bilibili.com'
};

// Bilibili API 端点
export const BILIBILI_API = {
  PAGELIST: 'https://api.bilibili.com/x/player/pagelist',
  VIEW: 'https://api.bilibili.com/x/web-interface/view',
  PLAYURL: 'https://api.bilibili.com/x/player/wbi/playurl',
  LOGIN: 'https://passport.bilibili.com/x/passport-login/oauth2/access_token',
  USERINFO: 'https://api.bilibili.com/x/space/myinfo'
};

// 画质代码
export const QUALITY_CODES = {
  '360p': '16',
  '480p': '32',
  '720p': '64',
  '1080p': '125',
  '4K': '266'
};
