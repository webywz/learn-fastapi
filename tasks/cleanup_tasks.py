"""
===========================================
清理和维护任务 (Cleanup Tasks)
===========================================

作用：
  定期清理和维护系统数据

为什么需要清理任务？
  - 删除过期数据（节省空间）
  - 清理缓存
  - 数据库优化
  - 健康检查

使用场景：
  - 每天清理过期 Token
  - 每周清理临时文件
  - 每月归档旧数据
"""

import time
import random
from celery import shared_task
from datetime import datetime, timedelta


# ============================================================
# 数据清理任务
# ============================================================

@shared_task(name="tasks.cleanup_tasks.cleanup_expired_data")
def cleanup_expired_data():
    """
    清理过期数据

    定时任务:
        每天凌晨 2 点执行

    清理内容:
        - 过期的 Token
        - 过期的 Session
        - 临时文件
        - 已删除用户的数据
    """
    print(f"🧹 开始清理过期数据...")

    # 1. 清理过期 Token
    print("   清理过期 Token...")
    # 实际代码:
    # from datetime import datetime, timedelta
    # from models.token import Token
    # expired_date = datetime.now() - timedelta(days=7)
    # await db.execute(
    #     delete(Token).where(Token.created_at < expired_date)
    # )

    time.sleep(1)
    deleted_tokens = random.randint(10, 100)
    print(f"   ✅ 删除 {deleted_tokens} 个过期 Token")

    # 2. 清理过期 Session
    print("   清理过期 Session...")
    time.sleep(1)
    deleted_sessions = random.randint(50, 200)
    print(f"   ✅ 删除 {deleted_sessions} 个过期 Session")

    # 3. 清理临时文件
    print("   清理临时文件...")
    # import os
    # import glob
    # temp_files = glob.glob('/tmp/*.tmp')
    # for file in temp_files:
    #     os.remove(file)

    time.sleep(1)
    deleted_files = random.randint(5, 30)
    print(f"   ✅ 删除 {deleted_files} 个临时文件")

    # 4. 清理 Redis 过期缓存
    print("   清理 Redis 过期缓存...")
    # from core.redis import redis_cache
    # await redis_cache.delete_pattern("temp:*")

    time.sleep(1)

    print(f"✅ 清理完成!")

    return {
        "deleted_tokens": deleted_tokens,
        "deleted_sessions": deleted_sessions,
        "deleted_files": deleted_files
    }


@shared_task(name="tasks.cleanup_tasks.cleanup_old_logs")
def cleanup_old_logs(days_to_keep: int = 30):
    """
    清理旧日志

    参数:
        days_to_keep: 保留天数（默认 30 天）

    定时任务:
        每周日凌晨执行

    调用方式:
        cleanup_old_logs.delay(days_to_keep=30)
    """
    print(f"🧹 清理 {days_to_keep} 天前的日志...")

    cutoff_date = datetime.now() - timedelta(days=days_to_keep)

    print(f"   删除 {cutoff_date.strftime('%Y-%m-%d')} 之前的日志...")

    # 实际代码:
    # import glob
    # import os
    # from datetime import datetime
    #
    # log_files = glob.glob('logs/*.log')
    # for log_file in log_files:
    #     file_time = datetime.fromtimestamp(os.path.getmtime(log_file))
    #     if file_time < cutoff_date:
    #         os.remove(log_file)

    time.sleep(2)

    deleted_logs = random.randint(10, 50)

    print(f"✅ 删除 {deleted_logs} 个日志文件")

    return {"deleted_logs": deleted_logs}


@shared_task(name="tasks.cleanup_tasks.archive_old_data")
def archive_old_data(table_name: str, months_to_keep: int = 6):
    """
    归档旧数据

    参数:
        table_name: 表名
        months_to_keep: 保留月数

    用途:
        - 将旧数据移到归档表
        - 保持主表数据量小
        - 提高查询性能

    调用方式:
        archive_old_data.delay(table_name="orders", months_to_keep=6)
    """
    print(f"🧹 归档 {table_name} 表的旧数据...")
    print(f"   保留最近 {months_to_keep} 个月的数据")

    cutoff_date = datetime.now() - timedelta(days=months_to_keep * 30)

    # 实际代码:
    # 1. 将旧数据复制到归档表
    # await db.execute(
    #     f"INSERT INTO {table_name}_archive SELECT * FROM {table_name} WHERE created_at < :cutoff",
    #     {"cutoff": cutoff_date}
    # )
    #
    # 2. 删除主表中的旧数据
    # await db.execute(
    #     f"DELETE FROM {table_name} WHERE created_at < :cutoff",
    #     {"cutoff": cutoff_date}
    # )

    time.sleep(3)

    archived_records = random.randint(1000, 10000)

    print(f"✅ 归档 {archived_records} 条记录")

    return {
        "table": table_name,
        "archived_records": archived_records,
        "cutoff_date": cutoff_date.strftime("%Y-%m-%d")
    }


# ============================================================
# 系统维护任务
# ============================================================

@shared_task(name="tasks.cleanup_tasks.health_check")
def health_check():
    """
    系统健康检查

    定时任务:
        每 10 分钟执行一次

    检查项:
        - 数据库连接
        - Redis 连接
        - 磁盘空间
        - 内存使用率
    """
    print(f"🏥 执行健康检查...")

    health_status = {}

    # 1. 检查数据库
    print("   检查数据库连接...")
    try:
        # from core.database import engine
        # async with engine.connect() as conn:
        #     await conn.execute("SELECT 1")
        health_status["database"] = "healthy"
    except Exception as e:
        health_status["database"] = "unhealthy"
        print(f"   ❌ 数据库连接失败: {e}")

    time.sleep(0.5)

    # 2. 检查 Redis
    print("   检查 Redis 连接...")
    try:
        # from core.redis import get_redis
        # redis = await get_redis()
        # await redis.ping()
        health_status["redis"] = "healthy"
    except Exception as e:
        health_status["redis"] = "unhealthy"
        print(f"   ❌ Redis 连接失败: {e}")

    time.sleep(0.5)

    # 3. 检查磁盘空间
    print("   检查磁盘空间...")
    # import shutil
    # total, used, free = shutil.disk_usage("/")
    # disk_usage_percent = (used / total) * 100

    disk_usage_percent = random.uniform(30, 90)
    health_status["disk"] = {
        "usage_percent": round(disk_usage_percent, 2),
        "status": "healthy" if disk_usage_percent < 80 else "warning"
    }

    if disk_usage_percent > 80:
        print(f"   ⚠️  磁盘使用率过高: {disk_usage_percent:.2f}%")
        # 发送告警
        from tasks.email_tasks import send_email
        send_email.delay(
            to="admin@example.com",
            subject="⚠️ 磁盘空间告警",
            body=f"磁盘使用率: {disk_usage_percent:.2f}%"
        )

    time.sleep(0.5)

    # 4. 检查内存
    print("   检查内存使用率...")
    # import psutil
    # memory = psutil.virtual_memory()
    # memory_usage_percent = memory.percent

    memory_usage_percent = random.uniform(40, 90)
    health_status["memory"] = {
        "usage_percent": round(memory_usage_percent, 2),
        "status": "healthy" if memory_usage_percent < 85 else "warning"
    }

    if memory_usage_percent > 85:
        print(f"   ⚠️  内存使用率过高: {memory_usage_percent:.2f}%")

    print(f"✅ 健康检查完成")

    # 所有检查通过
    all_healthy = all(
        status == "healthy" or (isinstance(status, dict) and status["status"] == "healthy")
        for status in health_status.values()
    )

    return {
        "status": "healthy" if all_healthy else "warning",
        "checks": health_status,
        "timestamp": datetime.now().isoformat()
    }


@shared_task(name="tasks.cleanup_tasks.optimize_database")
def optimize_database():
    """
    优化数据库

    定时任务:
        每周日凌晨 3 点执行

    操作:
        - 分析表
        - 优化表
        - 重建索引
        - 更新统计信息
    """
    print(f"🔧 开始优化数据库...")

    tables = ["users", "posts", "comments", "orders"]

    for table in tables:
        print(f"   优化表: {table}...")

        # 实际代码（MySQL）:
        # await db.execute(f"ANALYZE TABLE {table}")
        # await db.execute(f"OPTIMIZE TABLE {table}")

        # PostgreSQL:
        # await db.execute(f"VACUUM ANALYZE {table}")

        time.sleep(2)

    print(f"✅ 数据库优化完成")

    return {"optimized_tables": tables}


@shared_task(name="tasks.cleanup_tasks.backup_database")
def backup_database():
    """
    备份数据库

    定时任务:
        每天凌晨 3 点执行

    操作:
        1. 导出数据库
        2. 压缩备份文件
        3. 上传到 OSS
        4. 删除本地备份
        5. 清理旧备份（保留 7 天）
    """
    print(f"💾 开始备份数据库...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_{timestamp}.sql"

    # 1. 导出数据库
    print(f"   导出数据库到 {backup_file}...")
    # import subprocess
    # subprocess.run([
    #     'mysqldump',
    #     '-u', 'user',
    #     '-p', 'password',
    #     'database_name',
    #     '>', backup_file
    # ])

    time.sleep(5)

    # 2. 压缩
    print(f"   压缩备份文件...")
    # import gzip
    # with open(backup_file, 'rb') as f_in:
    #     with gzip.open(f'{backup_file}.gz', 'wb') as f_out:
    #         f_out.writelines(f_in)

    time.sleep(2)

    # 3. 上传到 OSS
    print(f"   上传到 OSS...")
    # import oss2
    # bucket = oss2.Bucket(auth, endpoint, bucket_name)
    # bucket.put_object_from_file(f'backups/{backup_file}.gz', f'{backup_file}.gz')

    time.sleep(3)

    # 4. 删除本地文件
    print(f"   删除本地文件...")
    # os.remove(backup_file)
    # os.remove(f'{backup_file}.gz')

    # 5. 清理旧备份
    print(f"   清理 7 天前的备份...")
    # 从 OSS 删除旧备份

    time.sleep(1)

    print(f"✅ 备份完成")

    return {
        "backup_file": f"{backup_file}.gz",
        "timestamp": timestamp,
        "status": "success"
    }


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结：

1. 【定时清理的重要性】
   - 节省存储空间
   - 提高查询性能
   - 数据安全合规
   - 系统稳定运行

2. 【清理策略】
   - 软删除 vs 硬删除
   - 归档 vs 删除
   - 保留期限设置
   - 分批删除（避免锁表）

3. 【健康检查】
   - 定期检查系统状态
   - 自动告警
   - 预防性维护
   - 问题早发现

4. 【数据备份】
   - 每日备份
   - 异地存储
   - 定期恢复测试
   - 保留多个版本

5. 【最佳实践】
   - 非高峰期执行（凌晨）
   - 设置超时时间
   - 记录详细日志
   - 失败告警通知

6. 【实际工具】
   - psutil: 系统监控
   - shutil: 文件操作
   - subprocess: 执行系统命令
   - schedule: 定时任务调度
"""
