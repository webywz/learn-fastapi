#!/bin/bash

# ============================================================
# 日志查看脚本 - Logs Script
# ============================================================
#
# 作用：查看 Docker 容器日志
#
# 使用方法：
#   chmod +x scripts/logs.sh
#   ./scripts/logs.sh [服务名]
#
# 示例：
#   ./scripts/logs.sh          # 查看所有服务日志
#   ./scripts/logs.sh app      # 只查看 app 服务日志
#   ./scripts/logs.sh redis    # 只查看 redis 服务日志

SERVICE=${1:-""}  # 第一个参数为服务名，默认为空（所有服务）

if [ -z "$SERVICE" ]; then
    echo "========================================"
    echo "  查看所有服务日志"
    echo "========================================"
    echo ""
    echo "💡 提示："
    echo "   按 Ctrl+C 退出"
    echo "   查看单个服务: ./scripts/logs.sh [服务名]"
    echo ""
    echo "可用服务："
    echo "   app, redis, celery_worker, celery_beat, flower, nginx"
    echo ""
    echo "========================================"
    echo ""

    docker-compose logs -f --tail=100
else
    echo "========================================"
    echo "  查看 $SERVICE 服务日志"
    echo "========================================"
    echo ""
    echo "💡 按 Ctrl+C 退出"
    echo ""

    docker-compose logs -f --tail=100 "$SERVICE"
fi
