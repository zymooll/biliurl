#!/usr/bin/env python3
"""
CDN 系统测试脚本
测试健康检查、B站视频、NCM音乐等功能
"""

import requests
import sys
import time
from urllib.parse import urlencode

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")

def test_health_check(base_url):
    """测试健康检查端点"""
    print("\n" + "="*60)
    print("测试 1: 健康检查端点")
    print("="*60)
    
    try:
        resp = requests.get(f"{base_url}/health", timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            print_success(f"健康检查通过")
            print_info(f"状态: {data.get('status')}")
            print_info(f"节点: {data.get('node')}")
            print_info(f"区域: {data.get('region')}")
            print_info(f"运行时长: {data.get('uptime')}秒")
            
            services = data.get('services', {})
            for service, status in services.items():
                if status == 'healthy':
                    print_success(f"  {service}: {status}")
                else:
                    print_error(f"  {service}: {status}")
            
            return data.get('status') == 'healthy'
        else:
            print_error(f"健康检查失败: HTTP {resp.status_code}")
            return False
            
    except Exception as e:
        print_error(f"健康检查异常: {e}")
        return False

def test_bili_video(base_url):
    """测试B站视频播放"""
    print("\n" + "="*60)
    print("测试 2: B站视频播放")
    print("="*60)
    
    test_bvids = [
        ("BV1HfK3zPEHE", "测试视频1"),
        ("BV1xx411c7XD", "测试视频2"),
    ]
    
    success_count = 0
    
    for bvid, desc in test_bvids:
        print(f"\n测试: {desc} ({bvid})")
        
        try:
            # 测试不同清晰度
            for qn in [64, 80]:
                params = {'bvid': bvid, 'qn': qn}
                url = f"{base_url}/play/vrc?{urlencode(params)}"
                
                resp = requests.get(url, timeout=10, allow_redirects=False)
                
                if resp.status_code in [302, 301]:
                    redirect_url = resp.headers.get('Location', '')
                    print_success(f"  qn={qn}: 重定向成功")
                    if redirect_url:
                        print_info(f"  URL前缀: {redirect_url[:80]}...")
                    
                    # 检查缓存头
                    cache_control = resp.headers.get('Cache-Control', '')
                    if 'no-cache' in cache_control or 'no-store' in cache_control:
                        print_success(f"  ✓ 缓存控制正确: {cache_control}")
                    else:
                        print_warning(f"  缓存控制可能有问题: {cache_control}")
                    
                    success_count += 1
                else:
                    print_error(f"  qn={qn}: HTTP {resp.status_code}")
                    
        except Exception as e:
            print_error(f"  请求异常: {e}")
    
    print(f"\n总结: {success_count}/{len(test_bvids)*2} 个测试通过")
    return success_count > 0

def test_ncm_music(base_url):
    """测试网易云音乐播放"""
    print("\n" + "="*60)
    print("测试 3: 网易云音乐播放")
    print("="*60)
    
    test_songs = [
        ("1856336348", "测试歌曲1"),
        ("28391863", "测试歌曲2"),
    ]
    
    success_count = 0
    
    for song_id, desc in test_songs:
        print(f"\n测试: {desc} (ID: {song_id})")
        
        try:
            params = {'id': song_id}
            url = f"{base_url}/play/vrc?{urlencode(params)}"
            
            # 模拟播放器请求（带Range头）
            headers = {'Range': 'bytes=0-'}
            resp = requests.get(url, headers=headers, timeout=10, allow_redirects=False)
            
            if resp.status_code in [302, 301]:
                redirect_url = resp.headers.get('Location', '')
                print_success(f"  重定向成功")
                if redirect_url:
                    print_info(f"  URL前缀: {redirect_url[:80]}...")
                
                # 检查缓存头
                cache_control = resp.headers.get('Cache-Control', '')
                if 'no-cache' in cache_control or 'no-store' in cache_control:
                    print_success(f"  ✓ 缓存控制正确: {cache_control}")
                else:
                    print_warning(f"  缓存控制可能有问题: {cache_control}")
                
                success_count += 1
            else:
                print_error(f"  HTTP {resp.status_code}")
                
        except Exception as e:
            print_error(f"  请求异常: {e}")
    
    print(f"\n总结: {success_count}/{len(test_songs)} 个测试通过")
    return success_count > 0

def test_keyword_search(base_url):
    """测试关键词搜索播放"""
    print("\n" + "="*60)
    print("测试 4: 关键词搜索播放")
    print("="*60)
    
    keywords = "周杰伦"
    print(f"\n搜索关键词: {keywords}")
    
    try:
        params = {'keywords': keywords}
        url = f"{base_url}/play/vrc?{urlencode(params)}"
        
        # 模拟播放器请求
        headers = {'Range': 'bytes=0-'}
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=False)
        
        if resp.status_code in [302, 301]:
            print_success("搜索并重定向成功")
            return True
        else:
            print_error(f"HTTP {resp.status_code}")
            return False
            
    except Exception as e:
        print_error(f"请求异常: {e}")
        return False

def test_response_time(base_url):
    """测试响应时间"""
    print("\n" + "="*60)
    print("测试 5: 响应时间")
    print("="*60)
    
    endpoints = [
        ("/health", "健康检查"),
        ("/play/vrc?bvid=BV1HfK3zPEHE", "B站视频"),
        ("/play/vrc?id=1856336348", "NCM音乐"),
    ]
    
    for path, name in endpoints:
        times = []
        print(f"\n{name} ({path}):")
        
        for i in range(3):
            try:
                start = time.time()
                resp = requests.get(f"{base_url}{path}", timeout=10, allow_redirects=False)
                elapsed = (time.time() - start) * 1000  # 转换为毫秒
                times.append(elapsed)
                print(f"  请求 {i+1}: {elapsed:.0f}ms")
            except Exception as e:
                print_error(f"  请求 {i+1}: 失败 ({e})")
        
        if times:
            avg_time = sum(times) / len(times)
            if avg_time < 200:
                print_success(f"  平均响应时间: {avg_time:.0f}ms (优秀)")
            elif avg_time < 500:
                print_warning(f"  平均响应时间: {avg_time:.0f}ms (良好)")
            else:
                print_warning(f"  平均响应时间: {avg_time:.0f}ms (需要优化)")
    
    return True

def main():
    print(f"\n{Colors.BLUE}{'='*60}")
    print("CDN 系统功能测试")
    print(f"{'='*60}{Colors.END}\n")
    
    # 获取测试URL
    if len(sys.argv) > 1:
        base_url = sys.argv[1].rstrip('/')
    else:
        base_url = input("请输入测试URL (如 http://localhost:7997): ").strip().rstrip('/')
    
    if not base_url:
        print_error("URL不能为空")
        sys.exit(1)
    
    print_info(f"测试目标: {base_url}\n")
    
    # 执行测试
    results = {
        "健康检查": test_health_check(base_url),
        "B站视频": test_bili_video(base_url),
        "NCM音乐": test_ncm_music(base_url),
        "关键词搜索": test_keyword_search(base_url),
        "响应时间": test_response_time(base_url),
    }
    
    # 总结
    print(f"\n{Colors.BLUE}{'='*60}")
    print("测试总结")
    print(f"{'='*60}{Colors.END}\n")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        if result:
            print_success(f"{test_name}: 通过")
        else:
            print_error(f"{test_name}: 失败")
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print_success("\n🎉 所有测试通过！系统运行正常。")
        sys.exit(0)
    else:
        print_warning(f"\n⚠️  有 {total - passed} 个测试失败，请检查日志。")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\n\n测试被中断")
        sys.exit(1)
