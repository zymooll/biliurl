#!/usr/bin/env python3
"""
密码重置脚本 - 用于部署环境
删除旧的密码文件并重新初始化
"""
import sys
import os

# 确保能导入ncm模块
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

def reset_password():
    print("="*60)
    print("密码重置脚本")
    print("="*60)
    
    try:
        from ncm.config import ACCESS_PASSWORD_FILE, DEFAULT_ACCESS_PASSWORD
        from ncm.utils.access_password import AccessPasswordManager
        
        # 1. 删除旧的密码文件
        if os.path.exists(ACCESS_PASSWORD_FILE):
            print(f"\n1. 删除旧的密码文件: {ACCESS_PASSWORD_FILE}")
            os.remove(ACCESS_PASSWORD_FILE)
            print(f"   ✅ 已删除")
        else:
            print(f"\n1. 密码文件不存在: {ACCESS_PASSWORD_FILE}")
        
        # 2. 清除缓存
        print(f"\n2. 清除缓存")
        import ncm.utils.access_password as ap_module
        ap_module._cached_password_hash = None
        print(f"   ✅ 缓存已清除")
        
        # 3. 重新初始化
        print(f"\n3. 重新初始化密码系统")
        hash_val = AccessPasswordManager.initialize()
        print(f"   ✅ 初始化完成")
        print(f"   Hash: {hash_val}")
        
        # 4. 验证
        print(f"\n4. 验证默认密码")
        result = AccessPasswordManager.verify_password(DEFAULT_ACCESS_PASSWORD)
        if result:
            print(f"   ✅ 验证成功")
            print(f"\n默认密码: {DEFAULT_ACCESS_PASSWORD}")
            print(f"\n现在可以使用默认密码登录系统了！")
        else:
            print(f"   ❌ 验证失败")
            print(f"\n请检查 config.py 中的配置:")
            print(f"   - DEFAULT_ACCESS_PASSWORD")
            print(f"   - ACCESS_PASSWORD_SALT")
        
        print("\n" + "="*60)
        return result
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = reset_password()
    sys.exit(0 if success else 1)
