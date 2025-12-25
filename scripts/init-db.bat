@echo off
REM ============================================================
REM 数据库初始化脚本 - Database Initialization Script (Windows)
REM ============================================================
REM
REM 作用：初始化数据库（运行 Alembic 迁移）
REM
REM 使用方法：
REM   双击运行或在命令行执行: scripts\init-db.bat

echo ========================================
echo   初始化数据库...
echo ========================================

REM 检查容器是否运行
docker-compose ps app | findstr "Up" >nul 2>&1
if errorlevel 1 (
    echo ❌ 应用容器未运行，请先启动服务
    echo    运行: scripts\start.bat
    pause
    exit /b 1
)

echo.
echo 📊 检查当前数据库版本...
docker-compose exec app alembic current

echo.
echo 🔄 运行数据库迁移...
docker-compose exec app alembic upgrade head

echo.
echo 📊 检查迁移后的数据库版本...
docker-compose exec app alembic current

echo.
echo ========================================
echo   ✅ 数据库初始化完成
echo ========================================
echo.
echo 💡 其他命令：
echo    查看迁移历史: docker-compose exec app alembic history
echo    创建新迁移: docker-compose exec app alembic revision --autogenerate -m "描述"
echo    回滚迁移: docker-compose exec app alembic downgrade -1
echo.

pause
