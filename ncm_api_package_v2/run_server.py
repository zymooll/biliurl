import uvicorn
import logging
import multiprocessing

if __name__ == "__main__":
    # 过滤 uvicorn 的无效请求警告
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
    
    # 多线程配置
    DEV_MODE = False  # 开发模式：True=热重载, False=多进程
    WORKERS = multiprocessing.cpu_count()  # 工作进程数
    
    if DEV_MODE:
        print(f"🔧 开发模式：启用热重载")
        uvicorn.run("ncm.main:app", host="0.0.0.0", port=7997, reload=True, log_level="info")
    else:
        print(f"🚀 生产模式：{WORKERS} 个工作进程")
        uvicorn.run("ncm.main:app", host="0.0.0.0", port=7997, workers=WORKERS, log_level="info")
