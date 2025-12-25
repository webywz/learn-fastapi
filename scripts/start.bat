@echo off
REM ============================================================
REM 启动脚本 - Start Script (Windows)
REM ============================================================
REM
REM 作用：启动所有 Docker 容器
REM
REM 使用方法：
REM   双击运行或在命令行执行: scripts\start.bat

echo ========================================
echo   启动 FastAPI 应用...
echo ========================================

REM 检查 Docker 是否运行
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 未运行，请先启动 Docker Desktop
    pause
    exit /b 1
)

echo.
echo 📦 构建 Docker 镜像...
docker-compose build

echo.
echo 🚀 启动所有服务...
docker-compose up -d

echo.
echo ⏳ 等待服务启动...
timeout /t 5 /nobreak >nul

echo.
echo 📊 查看服务状态...
docker-compose ps

echo.
echo ========================================
echo   ✅ 启动完成！
echo ========================================
echo.
echo 🌐 服务访问地址：
echo    FastAPI 应用: http://localhost:8080
echo    API 文档: http://localhost:8080/docs
echo    ReDoc 文档: http://localhost:8080/redoc
echo    Flower 监控: http://localhost:5555
echo    Nginx 代理: http://localhost
echo.
echo 📝 常用命令：
echo    查看日志: docker-compose logs -f
echo    查看状态: docker-compose ps
echo    停止服务: scripts\stop.bat
echo.
echo ========================================
echo.

pause
