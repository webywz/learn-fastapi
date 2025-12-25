#!/bin/bash

# ============================================================
# 重启脚本 - Restart Script
# ============================================================
#
# 作用：重启 Docker 容器
#
# 使用方法：
#   chmod +x scripts/restart.sh
#   ./scripts/restart.sh [服务名]
#
# 示例：
#   ./scripts/restart.sh          # 重启所有服务
#   ./scripts/restart.sh app      # 只重启 app 服务

SERVICE=${1:-""}

echo "========================================"
echo "  重启服务..."
echo "========================================"

if [ -z "$SERVICE" ]; then
    echo ""
    echo "🔄 重启所有服务..."
    docker-compose restart

    echo ""
    echo "📊 查看服务状态..."
    docker-compose ps
else
    echo ""
    echo "🔄 重启 $SERVICE 服务..."
    docker-compose restart "$SERVICE"

    echo ""
    echo "📊 查看服务状态..."
    docker-compose ps "$SERVICE"
fi

echo ""
echo "========================================"
echo "  ✅ 重启完成"
echo "========================================"
echo ""
