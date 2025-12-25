@echo off
REM ============================================================
REM 日志查看脚本 - Logs Script (Windows)
REM ============================================================
REM
REM 作用：查看 Docker 容器日志
REM
REM 使用方法：
REM   scripts\logs.bat [服务名]
REM
REM 示例：
REM   scripts\logs.bat          # 查看所有服务日志
REM   scripts\logs.bat app      # 只查看 app 服务日志
REM   scripts\logs.bat redis    # 只查看 redis 服务日志

if "%1"=="" (
    echo ========================================
    echo   查看所有服务日志
    echo ========================================
    echo.
    echo 💡 提示：
    echo    按 Ctrl+C 退出
    echo    查看单个服务: scripts\logs.bat [服务名]
    echo.
    echo 可用服务：
    echo    app, redis, celery_worker, celery_beat, flower, nginx
    echo.
    echo ========================================
    echo.

    docker-compose logs -f --tail=100
) else (
    echo ========================================
    echo   查看 %1 服务日志
    echo ========================================
    echo.
    echo 💡 按 Ctrl+C 退出
    echo.

    docker-compose logs -f --tail=100 %1
)
