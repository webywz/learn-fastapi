"""
===========================================
报表任务 (Report Tasks)
===========================================

作用：
  处理报表生成相关的异步任务

为什么报表要异步？
  - 生成报表很慢（数分钟到数小时）
  - 涉及大量数据查询和计算
  - 不能阻塞 API

使用场景：
  - 用户数据导出（CSV, Excel）
  - 统计报表生成
  - 数据分析报告
"""

import time
import random
from celery import shared_task
from datetime import datetime, timedelta


# ============================================================
# 数据导出任务
# ============================================================

@shared_task(
    bind=True,
    name="tasks.report_tasks.export_users_csv",
    max_retries=2
)
def export_users_csv(self, user_id: int, filters: dict = None):
    """
    导出用户列表为 CSV

    参数:
        user_id: 请求导出的用户 ID
        filters: 筛选条件

    流程:
        1. 从数据库查询数据
        2. 生成 CSV 文件
        3. 上传到对象存储（OSS）
        4. 发送下载链接给用户

    调用方式:
        task = export_users_csv.delay(user_id=1, filters={"is_active": True})
        # 返回任务 ID，前端可以轮询状态
    """
    try:
        print(f"📊 开始导出用户数据...")
        print(f"   请求用户: {user_id}")
        print(f"   筛选条件: {filters}")

        # 1. 模拟查询数据库
        print("   查询数据库...")
        time.sleep(2)

        # 实际项目中的代码示例:
        # from sqlalchemy import select
        # from models.user import User
        # from core.database import AsyncSessionLocal
        #
        # async with AsyncSessionLocal() as db:
        #     query = select(User)
        #     if filters:
        #         if "is_active" in filters:
        #             query = query.where(User.is_active == filters["is_active"])
        #     result = await db.execute(query)
        #     users = result.scalars().all()

        # 2. 模拟生成 CSV
        print("   生成 CSV 文件...")
        time.sleep(3)

        # 实际代码:
        # import csv
        # with open('users.csv', 'w', newline='') as csvfile:
        #     writer = csv.writer(csvfile)
        #     writer.writerow(['ID', 'Username', 'Email', 'Created At'])
        #     for user in users:
        #         writer.writerow([user.id, user.username, user.email, user.created_at])

        # 3. 模拟上传到 OSS
        print("   上传到 OSS...")
        time.sleep(2)

        download_url = f"https://example.com/downloads/users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        print(f"✅ 导出完成!")
        print(f"   下载链接: {download_url}")

        # 4. 发送邮件通知用户
        from tasks.email_tasks import send_email
        send_email.delay(
            to="user@example.com",
            subject="用户数据导出完成",
            body=f"您的数据导出已完成，请访问：{download_url}"
        )

        return {
            "status": "success",
            "download_url": download_url,
            "record_count": 1000  # 模拟数据
        }

    except Exception as exc:
        print(f"❌ 导出失败: {exc}")
        raise self.retry(exc=exc)


@shared_task(name="tasks.report_tasks.generate_excel_report")
def generate_excel_report(report_type: str, date_range: dict):
    """
    生成 Excel 报表

    参数:
        report_type: 报表类型（sales, users, orders）
        date_range: 日期范围 {"start": "2024-01-01", "end": "2024-01-31"}

    调用方式:
        generate_excel_report.delay(
            report_type="sales",
            date_range={"start": "2024-01-01", "end": "2024-01-31"}
        )
    """
    print(f"📊 生成 {report_type} Excel 报表...")
    print(f"   日期范围: {date_range['start']} 到 {date_range['end']}")

    # 模拟数据处理
    print("   查询数据...")
    time.sleep(3)

    print("   生成 Excel...")
    time.sleep(2)

    # 实际代码（使用 openpyxl 或 pandas）:
    # import pandas as pd
    #
    # df = pd.DataFrame(data)
    # df.to_excel('report.xlsx', index=False)

    report_url = f"https://example.com/reports/{report_type}_{datetime.now().strftime('%Y%m%d')}.xlsx"

    print(f"✅ 报表生成完成: {report_url}")

    return {
        "status": "success",
        "report_url": report_url,
        "report_type": report_type
    }


# ============================================================
# 统计任务
# ============================================================

@shared_task(name="tasks.report_tasks.generate_daily_stats")
def generate_daily_stats(date: str = None):
    """
    生成每日统计数据

    参数:
        date: 日期（YYYY-MM-DD），默认昨天

    定时任务:
        每天凌晨 1 点自动执行

    调用方式:
        generate_daily_stats.delay(date="2024-01-15")
    """
    if date is None:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"📊 生成 {date} 的每日统计...")

    # 模拟统计各种指标
    stats = {
        "date": date,
        "new_users": random.randint(10, 100),
        "active_users": random.randint(500, 1000),
        "orders": random.randint(50, 200),
        "revenue": round(random.uniform(1000, 10000), 2)
    }

    print(f"   新增用户: {stats['new_users']}")
    print(f"   活跃用户: {stats['active_users']}")
    print(f"   订单数: {stats['orders']}")
    print(f"   收入: ¥{stats['revenue']}")

    # 实际项目中：
    # 1. 查询数据库统计
    # 2. 存入统计表
    # 3. 更新缓存
    # 4. 发送日报给管理员

    time.sleep(2)

    print(f"✅ 每日统计完成")

    return stats


@shared_task(name="tasks.report_tasks.generate_hourly_report")
def generate_hourly_report():
    """
    生成每小时报表

    定时任务:
        每小时执行一次

    用途:
        - 实时监控
        - 异常检测
        - 趋势分析
    """
    current_hour = datetime.now().strftime("%Y-%m-%d %H:00")

    print(f"📊 生成 {current_hour} 的小时报表...")

    # 模拟统计
    report = {
        "hour": current_hour,
        "requests": random.randint(1000, 5000),
        "errors": random.randint(0, 10),
        "avg_response_time": round(random.uniform(0.1, 1.0), 3)
    }

    print(f"   请求数: {report['requests']}")
    print(f"   错误数: {report['errors']}")
    print(f"   平均响应时间: {report['avg_response_time']}s")

    time.sleep(1)

    # 如果错误率过高，发送告警
    error_rate = report['errors'] / report['requests']
    if error_rate > 0.01:  # 错误率 > 1%
        print(f"⚠️  错误率过高: {error_rate:.2%}")
        # 发送告警邮件
        from tasks.email_tasks import send_email
        send_email.delay(
            to="admin@example.com",
            subject="⚠️ 错误率告警",
            body=f"当前错误率: {error_rate:.2%}"
        )

    print(f"✅ 小时报表完成")

    return report


# ============================================================
# 数据分析任务
# ============================================================

@shared_task(
    bind=True,
    name="tasks.report_tasks.analyze_user_behavior",
    time_limit=1800  # 30 分钟超时
)
def analyze_user_behavior(self, user_ids: list = None):
    """
    分析用户行为

    参数:
        user_ids: 用户 ID 列表（None 表示分析所有用户）

    使用场景:
        - 用户画像分析
        - 推荐系统
        - 个性化服务

    调用方式:
        analyze_user_behavior.delay(user_ids=[1, 2, 3])

    注意:
        - 大数据分析，可能很耗时
        - 设置了 30 分钟超时
    """
    print(f"📊 开始分析用户行为...")

    if user_ids:
        print(f"   分析 {len(user_ids)} 个用户")
    else:
        print(f"   分析所有用户")

    # 模拟数据分析
    steps = [
        "加载用户数据",
        "分析浏览记录",
        "分析购买行为",
        "生成用户画像",
        "计算推荐分数",
        "存储分析结果"
    ]

    for i, step in enumerate(steps, 1):
        print(f"   [{i}/{len(steps)}] {step}...")
        time.sleep(3)

        # 更新任务进度
        self.update_state(
            state='PROGRESS',
            meta={'current': i, 'total': len(steps), 'status': step}
        )

    print(f"✅ 用户行为分析完成")

    return {
        "status": "success",
        "analyzed_users": len(user_ids) if user_ids else 1000,
        "insights": {
            "avg_session_time": 25.5,
            "conversion_rate": 0.15,
            "popular_categories": ["电子产品", "图书", "服装"]
        }
    }


@shared_task(name="tasks.report_tasks.generate_dashboard_data")
def generate_dashboard_data():
    """
    生成仪表板数据

    定时任务:
        每 5 分钟执行一次

    用途:
        - 实时仪表板
        - 管理后台首页数据
        - KPI 监控
    """
    print(f"📊 生成仪表板数据...")

    # 模拟查询各种指标
    dashboard_data = {
        "timestamp": datetime.now().isoformat(),
        "users": {
            "total": random.randint(10000, 20000),
            "online": random.randint(100, 500),
            "new_today": random.randint(10, 50)
        },
        "orders": {
            "total_today": random.randint(50, 200),
            "revenue_today": round(random.uniform(5000, 20000), 2),
            "pending": random.randint(5, 20)
        },
        "system": {
            "cpu_usage": round(random.uniform(20, 80), 2),
            "memory_usage": round(random.uniform(40, 90), 2),
            "disk_usage": round(random.uniform(30, 70), 2)
        }
    }

    time.sleep(1)

    # 存入 Redis 缓存（供前端实时读取）
    # from core.redis import redis_cache
    # await redis_cache.set("dashboard:data", dashboard_data, ttl=300)

    print(f"✅ 仪表板数据已更新")

    return dashboard_data


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结：

1. 【长任务处理】
   - 设置 time_limit（超时时间）
   - 分批处理（避免内存溢出）
   - 更新进度（self.update_state）

2. 【任务进度追踪】
   @shared_task(bind=True)
   def my_task(self):
       for i in range(100):
           self.update_state(
               state='PROGRESS',
               meta={'current': i, 'total': 100}
           )

   # 前端查询进度
   task = my_task.delay()
   print(task.state)  # PROGRESS
   print(task.info)   # {'current': 50, 'total': 100}

3. 【文件导出最佳实践】
   1. 生成文件
   2. 上传到对象存储（OSS）
   3. 返回下载链接
   4. 发邮件通知用户
   5. 定期清理过期文件

4. 【定时统计任务】
   - 每日统计: 凌晨执行
   - 每小时统计: 实时监控
   - 按需统计: 用户触发

5. 【性能优化】
   - 使用数据库索引
   - 分批查询（避免一次加载太多）
   - 结果缓存
   - 异步执行

6. 【实际工具库】
   - pandas: 数据分析
   - openpyxl: Excel 操作
   - csv: CSV 操作
   - matplotlib: 图表生成
"""
