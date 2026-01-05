import uvicorn
import logging

if __name__ == "__main__":
    # 过滤 uvicorn 的无效请求警告
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
    
    # 启动 API 服务
    uvicorn.run("ncm.main:app", host="0.0.0.0", port=7997, reload=True, log_level="info")
