import uvicorn
import logging

if __name__ == "__main__":
    # 过滤 uvicorn 的无效请求警告
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
    
    # 单进程配置 - 使用动态线程池管理并发
    # 注意：我们使用应用内部的动态线程池来处理并发任务，而不是多进程
    DEV_MODE = False  # 开发模式：True=热重载, False=正常运行
    
    if DEV_MODE:
        print(f"🔧 开发模式：启用热重载")
        uvicorn.run("ncm.main:app", host="0.0.0.0", port=7997, reload=True, log_level="info")
    else:
        print(f"🚀 生产模式：单进程 + 动态线程池")
        # 使用单个工作进程，依赖应用内部的动态线程池管理并发
        uvicorn.run("ncm.main:app", host="0.0.0.0", port=7997, log_level="info")
