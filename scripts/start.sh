#!/bin/bash

# ============================================================
# 启动脚本 - Start Script
# ============================================================
#
# 作用：启动所有 Docker 容器
#
# 使用方法：
#   chmod +x scripts/start.sh
#   ./scripts/start.sh

set -e  # 遇到错误立即退出

echo "========================================"
echo "  启动 FastAPI 应用..."
echo "========================================"

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker"
    exit 1
fi

echo ""
echo "📦 构建 Docker 镜像..."
docker-compose build

echo ""
echo "🚀 启动所有服务..."
docker-compose up -d

echo ""
echo "⏳ 等待服务启动..."
sleep 5

echo ""
echo "📊 查看服务状态..."
docker-compose ps

echo ""
echo "========================================"
echo "  ✅ 启动完成！"
echo "========================================"
echo ""
echo "🌐 服务访问地址："
echo "   FastAPI 应用: http://localhost:8080"
echo "   API 文档: http://localhost:8080/docs"
echo "   ReDoc 文档: http://localhost:8080/redoc"
echo "   Flower 监控: http://localhost:5555"
echo "   Nginx 代理: http://localhost"
echo ""
echo "📝 常用命令："
echo "   查看日志: docker-compose logs -f"
echo "   查看状态: docker-compose ps"
echo "   停止服务: ./scripts/stop.sh"
echo ""
echo "========================================"
