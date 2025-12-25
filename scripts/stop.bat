@echo off
REM ============================================================
REM 停止脚本 - Stop Script (Windows)
REM ============================================================
REM
REM 作用：停止所有 Docker 容器
REM
REM 使用方法：
REM   双击运行或在命令行执行: scripts\stop.bat

echo ========================================
echo   停止 FastAPI 应用...
echo ========================================

echo.
echo 🛑 停止所有服务...
docker-compose down

echo.
echo ========================================
echo   ✅ 所有服务已停止
echo ========================================
echo.
echo 💡 提示：
echo    重新启动: scripts\start.bat
echo    删除数据: docker-compose down -v
echo.

pause
