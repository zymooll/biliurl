#!/bin/bash
# 快速部署脚本 - 在源站服务器上运行

set -e

echo "🚀 开始部署 BiliURL 源站服务..."

# 1. 检查必要依赖
echo "📦 检查依赖..."
command -v python3 >/dev/null 2>&1 || { echo "❌ 需要安装 Python 3"; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo "❌ 需要安装 pip3"; exit 1; }

# 2. 安装Python依赖
echo "📚 安装Python依赖..."
pip3 install -r requirements.txt

# 3. 配置环境变量
echo "⚙️ 配置环境变量..."
read -p "请输入节点名称 (如: changsha-01): " NODE_NAME
read -p "请输入节点区域 (mainland_china/asia/australia): " NODE_REGION

export NODE_NAME="$NODE_NAME"
export NODE_REGION="$NODE_REGION"

# 写入环境变量到配置文件
cat > .env << EOF
NODE_NAME=$NODE_NAME
NODE_REGION=$NODE_REGION
EOF

echo "✅ 环境变量已保存到 .env 文件"

# 4. 检查端口占用
if lsof -Pi :7997 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️ 端口 7997 已被占用"
    read -p "是否停止现有进程? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill $(lsof -t -i:7997) || true
        sleep 2
    fi
fi

# 5. 测试启动
echo "🧪 测试启动服务..."
timeout 5s python3 run_server.py &
PID=$!
sleep 3

# 检查进程是否还在运行
if ps -p $PID > /dev/null; then
    echo "✅ 服务启动成功！"
    kill $PID
else
    echo "❌ 服务启动失败，请检查错误日志"
    exit 1
fi

# 6. 询问是否创建systemd服务
read -p "是否创建systemd服务（开机自启）? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    CURRENT_DIR=$(pwd)
    CURRENT_USER=$(whoami)
    
    sudo tee /etc/systemd/system/biliurl.service > /dev/null << EOF
[Unit]
Description=BiliURL Media Proxy Service
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment="NODE_NAME=$NODE_NAME"
Environment="NODE_REGION=$NODE_REGION"
ExecStart=/usr/bin/python3 $CURRENT_DIR/run_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    echo "✅ systemd服务已创建"
    echo "   启动服务: sudo systemctl start biliurl"
    echo "   开机自启: sudo systemctl enable biliurl"
    echo "   查看状态: sudo systemctl status biliurl"
    echo "   查看日志: sudo journalctl -u biliurl -f"
fi

# 7. 测试健康检查
echo ""
echo "🏥 5秒后测试健康检查..."
python3 run_server.py &
SERVICE_PID=$!
sleep 5

HEALTH_CHECK=$(curl -s http://localhost:7997/health || echo "failed")
if [[ $HEALTH_CHECK == *"healthy"* ]]; then
    echo "✅ 健康检查通过！"
    echo "$HEALTH_CHECK" | python3 -m json.tool
else
    echo "❌ 健康检查失败"
fi

kill $SERVICE_PID 2>/dev/null || true

echo ""
echo "=========================================="
echo "🎉 部署完成！"
echo ""
echo "下一步："
echo "1. 启动服务: python3 run_server.py"
echo "   或使用: sudo systemctl start biliurl"
echo ""
echo "2. 测试访问: curl http://localhost:7997/health"
echo ""
echo "3. 配置Nginx反向代理（参考 nginx.conf.example）"
echo ""
echo "4. 部署Cloudflare Workers（参考 CDN_DEPLOYMENT_GUIDE.md）"
echo "=========================================="
