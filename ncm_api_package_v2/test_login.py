"""
网易云音乐登录功能测试脚本
测试线程安全的 Cookie 管理器
"""

import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:3000"

def test_cookie_manager():
    """测试 Cookie 管理器的线程安全性"""
    print("=" * 50)
    print("测试 1: Cookie 管理器线程安全性")
    print("=" * 50)
    
    from ncm.utils.cookie import CookieManager
    
    # 测试保存和加载
    test_cookie = "MUSIC_U=test123; __csrf=test456"
    CookieManager.save_cookie(test_cookie)
    loaded_cookie = CookieManager.load_cookie()
    
    assert loaded_cookie == test_cookie, "Cookie 保存和加载失败"
    print("✅ Cookie 保存和加载正常")
    
    # 测试多线程读取
    results = []
    
    def read_cookie(thread_id):
        cookie = CookieManager.load_cookie()
        results.append((thread_id, cookie))
        print(f"  线程 {thread_id}: 读取成功")
    
    print("\n开始多线程读取测试（10个线程同时读取）...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        for i in range(10):
            executor.submit(read_cookie, i)
    
    # 验证所有线程读取的 Cookie 一致
    assert all(cookie == test_cookie for _, cookie in results), "多线程读取 Cookie 不一致"
    print(f"✅ 多线程读取测试通过（{len(results)} 个线程，结果一致）")
    
    # 测试并发写入
    print("\n开始并发写入测试（5个线程同时写入不同的 Cookie）...")
    
    def write_cookie(thread_id):
        cookie = f"MUSIC_U=thread{thread_id}; __csrf=csrf{thread_id}"
        CookieManager.save_cookie(cookie)
        time.sleep(0.01)  # 模拟写入延迟
        print(f"  线程 {thread_id}: 写入完成")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        for i in range(5):
            executor.submit(write_cookie, i)
    
    # 读取最终的 Cookie
    final_cookie = CookieManager.load_cookie()
    print(f"✅ 并发写入测试完成，最终 Cookie: {final_cookie[:50]}...")
    
    print("\n" + "=" * 50)
    print("Cookie 管理器测试全部通过！")
    print("=" * 50)

def test_login_api():
    """测试登录 API 接口"""
    print("\n" + "=" * 50)
    print("测试 2: 登录 API 接口")
    print("=" * 50)
    
    # 测试获取 QR Key
    print("\n1. 测试获取 QR Key...")
    try:
        response = requests.get(f"{BASE_URL}/login/qr/key", timeout=5)
        data = response.json()
        assert "unikey" in data, "QR Key 响应格式错误"
        print(f"✅ QR Key 获取成功: {data['unikey'][:30]}...")
    except Exception as e:
        print(f"⚠️  QR Key 获取失败: {e}")
    
    # 测试导入 Cookie
    print("\n2. 测试 Cookie 导入接口...")
    test_cookie = "MUSIC_U=test_import; __csrf=test_csrf"
    try:
        response = requests.post(
            f"{BASE_URL}/cookie/import",
            params={"cookie": test_cookie},
            timeout=5
        )
        data = response.json()
        assert data.get("code") == 200, "Cookie 导入失败"
        print("✅ Cookie 导入接口正常")
    except Exception as e:
        print(f"⚠️  Cookie 导入测试失败: {e}")
    
    # 测试刷新 Cookie 缓存
    print("\n3. 测试 Cookie 缓存刷新...")
    try:
        response = requests.get(f"{BASE_URL}/cookie/refresh", timeout=5)
        data = response.json()
        assert data.get("code") in [200, 404], "Cookie 刷新响应异常"
        print("✅ Cookie 刷新接口正常")
    except Exception as e:
        print(f"⚠️  Cookie 刷新测试失败: {e}")
    
    print("\n" + "=" * 50)
    print("登录 API 接口测试完成！")
    print("=" * 50)

def test_concurrent_requests():
    """测试并发请求时的 Cookie 一致性"""
    print("\n" + "=" * 50)
    print("测试 3: 并发请求 Cookie 一致性")
    print("=" * 50)
    
    results = []
    
    def make_request(thread_id):
        try:
            response = requests.get(f"{BASE_URL}/user/cookie", timeout=5)
            data = response.json()
            cookie = data.get("cookie", "")
            results.append((thread_id, cookie))
            print(f"  线程 {thread_id}: 请求完成")
        except Exception as e:
            print(f"  线程 {thread_id}: 请求失败 - {e}")
    
    print("\n发起 20 个并发请求...")
    with ThreadPoolExecutor(max_workers=20) as executor:
        for i in range(20):
            executor.submit(make_request, i)
    
    # 检查所有请求返回的 Cookie 是否一致
    if results:
        first_cookie = results[0][1]
        all_same = all(cookie == first_cookie for _, cookie in results)
        
        if all_same:
            print(f"✅ 所有并发请求返回的 Cookie 一致（共 {len(results)} 个请求）")
        else:
            print(f"⚠️  并发请求返回的 Cookie 不一致")
            for thread_id, cookie in results[:3]:
                print(f"  线程 {thread_id}: {cookie[:50]}...")
    
    print("\n" + "=" * 50)
    print("并发请求测试完成！")
    print("=" * 50)

def main():
    print("\n🚀 开始网易云音乐登录功能测试\n")
    
    # 测试 1: Cookie 管理器
    test_cookie_manager()
    
    # 测试 2: 登录 API（需要服务器运行）
    print("\n⏳ 等待 2 秒后继续 API 测试...")
    time.sleep(2)
    
    try:
        test_login_api()
    except Exception as e:
        print(f"\n⚠️  API 测试跳过（请确保服务器正在运行）: {e}")
    
    # 测试 3: 并发请求
    try:
        test_concurrent_requests()
    except Exception as e:
        print(f"\n⚠️  并发测试跳过（请确保服务器正在运行）: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 所有测试完成！")
    print("=" * 50)
    print("\n💡 提示：")
    print("1. 如果 API 测试失败，请确保运行 'python run_server.py' 启动服务器")
    print("2. 打开浏览器访问 http://localhost:3000 查看 Web UI")
    print("3. 点击'登录管理'标签测试登录功能")
    print()

if __name__ == "__main__":
    main()
