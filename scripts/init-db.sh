#!/bin/bash

# ============================================================
# 数据库初始化脚本 - Database Initialization Script
# ============================================================
#
# 作用：初始化数据库（运行 Alembic 迁移）
#
# 使用方法：
#   chmod +x scripts/init-db.sh
#   ./scripts/init-db.sh

set -e

echo "========================================"
echo "  初始化数据库..."
echo "========================================"

# 检查容器是否运行
if ! docker-compose ps app | grep -q "Up"; then
    echo "❌ 应用容器未运行，请先启动服务"
    echo "   运行: ./scripts/start.sh"
    exit 1
fi

echo ""
echo "📊 检查当前数据库版本..."
docker-compose exec app alembic current

echo ""
echo "🔄 运行数据库迁移..."
docker-compose exec app alembic upgrade head

echo ""
echo "📊 检查迁移后的数据库版本..."
docker-compose exec app alembic current

echo ""
echo "========================================"
echo "  ✅ 数据库初始化完成"
echo "========================================"
echo ""
echo "💡 其他命令："
echo "   查看迁移历史: docker-compose exec app alembic history"
echo "   创建新迁移: docker-compose exec app alembic revision --autogenerate -m '描述'"
echo "   回滚迁移: docker-compose exec app alembic downgrade -1"
echo ""
