@echo off
REM ============================================================
REM 重启脚本 - Restart Script (Windows)
REM ============================================================
REM
REM 作用：重启 Docker 容器
REM
REM 使用方法：
REM   scripts\restart.bat [服务名]
REM
REM 示例：
REM   scripts\restart.bat          # 重启所有服务
REM   scripts\restart.bat app      # 只重启 app 服务

echo ========================================
echo   重启服务...
echo ========================================

if "%1"=="" (
    echo.
    echo 🔄 重启所有服务...
    docker-compose restart

    echo.
    echo 📊 查看服务状态...
    docker-compose ps
) else (
    echo.
    echo 🔄 重启 %1 服务...
    docker-compose restart %1

    echo.
    echo 📊 查看服务状态...
    docker-compose ps %1
)

echo.
echo ========================================
echo   ✅ 重启完成
echo ========================================
echo.

pause
