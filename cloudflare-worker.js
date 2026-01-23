/**
 * Cloudflare Workers - 智能路由层
 * 
 * 功能：
 * 1. 地理位置检测，路由到最近源站
 * 2. 静态资源边缘缓存（WebUI）
 * 3. 健康检查与故障转移
 * 4. 不缓存媒体URL（NCM和B站都是动态URL）
 */

// ==========================================
// 配置区域
// ==========================================
const CONFIG = {
  // 源站配置
  origins: {
    changsha: {
      url: 'https://cn.yourdomain.com',  // 替换为你的长沙服务器域名
      region: 'mainland_china',
      weight: 10  // 权重
    },
    singapore: {
      url: 'https://sg.yourdomain.com',  // 替换为你的新加坡服务器域名
      region: 'asia',
      weight: 8
    },
    sydney: {
      url: 'https://au.yourdomain.com',  // 替换为你的澳洲服务器域名
      region: 'australia',
      weight: 7
    }
  },
  
  // 静态资源路径（可以缓存）
  staticPaths: [
    '/static/',
    '/favicon.ico',
  ],
  
  // 缓存时间配置
  cacheTTL: {
    static: 3600,      // 静态资源缓存1小时
    health: 30,        // 健康检查缓存30秒
    media: 0           // 媒体URL不缓存
  },
  
  // 健康检查路径
  healthCheckPath: '/health',
  healthCheckTimeout: 3000,  // 3秒超时
}

// ==========================================
// 主处理函数
// ==========================================
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  const clientCountry = request.cf?.country || 'US'
  const clientIP = request.headers.get('CF-Connecting-IP') || 'unknown'
  
  console.log(`📍 请求来自: ${clientCountry} (${clientIP}) - ${url.pathname}`)
  
  // 1. 静态资源请求 → 边缘缓存
  if (isStaticResource(url.pathname)) {
    return handleStaticRequest(request, url)
  }
  
  // 2. 健康检查请求 → 返回Workers状态
  if (url.pathname === CONFIG.healthCheckPath) {
    return handleHealthCheck()
  }
  
  // 3. 媒体流请求 → 智能路由到源站（不缓存）
  return handleMediaRequest(request, url, clientCountry)
}

// ==========================================
// 静态资源处理（边缘缓存）
// ==========================================
async function handleStaticRequest(request, url) {
  // 尝试从边缘缓存获取
  const cache = caches.default
  let response = await cache.match(request)
  
  if (response) {
    console.log('✅ 静态资源命中缓存')
    return response
  }
  
  // 缓存未命中，从源站获取
  const origin = await selectBestOrigin(request.cf?.country)
  const originUrl = `${origin.url}${url.pathname}${url.search}`
  
  response = await fetch(originUrl, {
    headers: request.headers,
    cf: {
      cacheTtl: CONFIG.cacheTTL.static,
      cacheEverything: true
    }
  })
  
  // 添加缓存头
  response = new Response(response.body, response)
  response.headers.set('Cache-Control', `public, max-age=${CONFIG.cacheTTL.static}`)
  response.headers.set('X-Served-By', 'Cloudflare Workers')
  
  // 存入边缘缓存
  await cache.put(request, response.clone())
  
  return response
}

// ==========================================
// 媒体请求处理（智能路由，不缓存）
// ==========================================
async function handleMediaRequest(request, url, clientCountry) {
  // 选择最佳源站
  const origin = await selectBestOrigin(clientCountry)
  const originUrl = `${origin.url}${url.pathname}${url.search}`
  
  console.log(`🎯 路由到: ${origin.url} (${origin.region})`)
  
  try {
    // 转发请求到源站
    const response = await fetch(originUrl, {
      method: request.method,
      headers: request.headers,
      body: request.body,
      redirect: 'follow'  // 跟随302重定向
    })
    
    // 添加追踪头
    const newResponse = new Response(response.body, response)
    newResponse.headers.set('X-Origin-Server', origin.url)
    newResponse.headers.set('X-Client-Country', clientCountry)
    
    // 确保不缓存媒体URL响应
    newResponse.headers.set('Cache-Control', 'no-cache, no-store, must-revalidate')
    
    return newResponse
    
  } catch (error) {
    console.error(`❌ 源站请求失败: ${error.message}`)
    
    // 故障转移：尝试备用源站
    return await handleFailover(request, url, origin)
  }
}

// ==========================================
// 源站选择逻辑
// ==========================================
async function selectBestOrigin(clientCountry) {
  // 地理位置映射
  const regionMapping = {
    'CN': 'changsha',      // 中国大陆
    'HK': 'singapore',     // 香港
    'TW': 'singapore',     // 台湾
    'AU': 'sydney',        // 澳大利亚
    'NZ': 'sydney',        // 新西兰
    'SG': 'singapore',     // 新加坡
    'MY': 'singapore',     // 马来西亚
    'TH': 'singapore',     // 泰国
  }
  
  const preferredOrigin = regionMapping[clientCountry] || 'singapore'
  
  // 检查首选源站健康状态
  const isHealthy = await checkOriginHealth(preferredOrigin)
  
  if (isHealthy) {
    return CONFIG.origins[preferredOrigin]
  }
  
  // 首选源站不健康，选择备用
  console.log(`⚠️ ${preferredOrigin} 不健康，选择备用源站`)
  
  for (const [name, origin] of Object.entries(CONFIG.origins)) {
    if (name !== preferredOrigin && await checkOriginHealth(name)) {
      return origin
    }
  }
  
  // 所有源站都不健康，返回默认
  console.error('❌ 所有源站都不健康，使用默认源站')
  return CONFIG.origins.singapore
}

// ==========================================
// 健康检查
// ==========================================
async function checkOriginHealth(originName) {
  const origin = CONFIG.origins[originName]
  const healthUrl = `${origin.url}${CONFIG.healthCheckPath}`
  
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.healthCheckTimeout)
    
    const response = await fetch(healthUrl, {
      signal: controller.signal,
      cf: {
        cacheTtl: CONFIG.cacheTTL.health
      }
    })
    
    clearTimeout(timeoutId)
    
    if (response.ok) {
      const data = await response.json()
      return data.status === 'healthy'
    }
    
    return false
    
  } catch (error) {
    console.error(`健康检查失败 ${originName}: ${error.message}`)
    return false
  }
}

// ==========================================
// 故障转移
// ==========================================
async function handleFailover(request, url, failedOrigin) {
  console.log(`🔄 故障转移：${failedOrigin.url} 失败`)
  
  // 尝试其他源站
  for (const [name, origin] of Object.entries(CONFIG.origins)) {
    if (origin.url === failedOrigin.url) continue
    
    try {
      const originUrl = `${origin.url}${url.pathname}${url.search}`
      const response = await fetch(originUrl, {
        method: request.method,
        headers: request.headers,
        body: request.body,
        redirect: 'follow'
      })
      
      if (response.ok) {
        console.log(`✅ 故障转移成功: ${origin.url}`)
        return response
      }
    } catch (error) {
      console.error(`备用源站 ${origin.url} 也失败: ${error.message}`)
    }
  }
  
  // 所有源站都失败
  return new Response(JSON.stringify({
    code: 503,
    message: '所有源站不可用，请稍后重试',
    timestamp: Date.now()
  }), {
    status: 503,
    headers: { 'Content-Type': 'application/json' }
  })
}

// ==========================================
// Workers健康检查端点
// ==========================================
async function handleHealthCheck() {
  const healthStatus = {}
  
  for (const [name, origin] of Object.entries(CONFIG.origins)) {
    healthStatus[name] = await checkOriginHealth(name) ? 'healthy' : 'unhealthy'
  }
  
  return new Response(JSON.stringify({
    status: 'healthy',
    worker: 'cloudflare-edge',
    origins: healthStatus,
    timestamp: Date.now()
  }), {
    headers: { 'Content-Type': 'application/json' }
  })
}

// ==========================================
// 工具函数
// ==========================================
function isStaticResource(pathname) {
  return CONFIG.staticPaths.some(path => pathname.startsWith(path))
}
