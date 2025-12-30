"""
===========================================
任务 API (Tasks API)
===========================================

作用：
  提供任务相关的 API 接口

功能：
  - 提交异步任务
  - 查询任务状态
  - 获取任务结果
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# 导入 Celery 任务
from tasks.email_tasks import (
    send_email,
    send_welcome_email,
    send_bulk_emails
)
from tasks.report_tasks import (
    export_users_csv,
    generate_excel_report
)
from core.celery_app import celery_app
from common.response import success, error


# ============================================================
# 路由配置
# ============================================================

router = APIRouter()


# ============================================================
# 请求/响应模型
# ============================================================

class SendEmailRequest(BaseModel):
    """发送邮件请求"""
    to: EmailStr
    subject: str
    body: str


class BulkEmailRequest(BaseModel):
    """批量邮件请求"""
    emails: List[dict]


class ExportRequest(BaseModel):
    """导出请求"""
    filters: Optional[dict] = None


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: str
    message: str


# ============================================================
# 邮件任务 API
# ============================================================

@router.post("/email/send", tags=["任务-邮件"], summary="发送邮件", description="异步发送邮件，立即返回任务ID，不阻塞API响应")
async def send_email_api(request: SendEmailRequest):
    """
    发送邮件（异步）

    功能：
    - 异步发送邮件
    - 立即返回任务 ID
    - 不阻塞 API 响应

    使用示例:
        POST /api/v1/tasks/email/send
        {
            "to": "user@example.com",
            "subject": "Hello",
            "body": "Welcome!"
        }

    响应:
        {
            "code": 0,
            "message": "success",
            "data": {
                "task_id": "abc-123-def",
                "status": "PENDING",
                "message": "邮件正在发送中..."
            }
        }
    """
    # 异步发送邮件
    task = send_email.delay(
        to=request.to,
        subject=request.subject,
        body=request.body
    )

    return success(data={
        "task_id": task.id,
        "status": task.state,
        "message": "邮件正在发送中，请稍后查询状态"
    })


@router.post("/email/welcome/{user_id}", tags=["任务-邮件"], summary="发送欢迎邮件", description="用户注册成功后发送欢迎邮件")
async def send_welcome_email_api(
    user_id: int,
    email: EmailStr,
    username: str
):
    """
    发送欢迎邮件

    用途:
        用户注册成功后调用

    使用示例:
        POST /api/v1/tasks/email/welcome/1?email=alice@example.com&username=Alice
    """
    task = send_welcome_email.delay(
        user_id=user_id,
        email=email,
        username=username
    )

    return success(data={
        "task_id": task.id,
        "message": "欢迎邮件正在发送中"
    })


@router.post("/email/bulk", tags=["任务-邮件"], summary="批量发送邮件", description="批量异步发送多封邮件")
async def send_bulk_emails_api(request: BulkEmailRequest):
    """
    批量发送邮件

    使用示例:
        POST /api/v1/tasks/email/bulk
        {
            "emails": [
                {"to": "user1@example.com", "subject": "Hi", "body": "..."},
                {"to": "user2@example.com", "subject": "Hi", "body": "..."}
            ]
        }
    """
    task = send_bulk_emails.delay(emails=request.emails)

    return success(data={
        "task_id": task.id,
        "email_count": len(request.emails),
        "message": f"正在批量发送 {len(request.emails)} 封邮件"
    })


# ============================================================
# 报表任务 API
# ============================================================

@router.post("/report/export-users", tags=["任务-报表"], summary="导出用户数据", description="异步导出用户数据为CSV文件，上传到OSS并发送下载链接")
async def export_users_api(
    user_id: int,
    request: ExportRequest
):
    """
    导出用户数据（CSV）

    功能：
    - 异步导出数据
    - 生成 CSV 文件
    - 上传到 OSS
    - 发送下载链接

    使用示例:
        POST /api/v1/tasks/report/export-users?user_id=1
        {
            "filters": {"is_active": true}
        }

    流程:
        1. 提交任务，返回 task_id
        2. 前端轮询任务状态
        3. 任务完成后获取下载链接
    """
    task = export_users_csv.delay(
        user_id=user_id,
        filters=request.filters
    )

    return success(data={
        "task_id": task.id,
        "status": task.state,
        "message": "数据导出任务已提交，请稍后查询状态"
    })


@router.post("/report/generate", tags=["任务-报表"], summary="生成Excel报表", description="根据报表类型和日期范围生成Excel报表")
async def generate_report_api(
    report_type: str,
    start_date: str,
    end_date: str
):
    """
    生成 Excel 报表

    参数:
        report_type: 报表类型（sales, users, orders）
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）

    使用示例:
        POST /api/v1/tasks/report/generate?report_type=sales&start_date=2024-01-01&end_date=2024-01-31
    """
    task = generate_excel_report.delay(
        report_type=report_type,
        date_range={"start": start_date, "end": end_date}
    )

    return success(data={
        "task_id": task.id,
        "report_type": report_type,
        "message": "报表生成任务已提交"
    })


# ============================================================
# 任务状态查询 API
# ============================================================

@router.get("/status/{task_id}", tags=["任务-查询"], summary="查询任务状态", description="查询任务执行状态、进度和结果")
async def get_task_status(task_id: str):
    """
    查询任务状态

    功能：
    - 查询任务执行状态
    - 获取任务进度
    - 获取任务结果

    任务状态:
        - PENDING: 等待执行
        - STARTED: 正在执行
        - PROGRESS: 执行中（带进度）
        - SUCCESS: 执行成功
        - FAILURE: 执行失败
        - RETRY: 重试中

    使用示例:
        GET /api/v1/tasks/status/abc-123-def

    响应（执行中）:
        {
            "task_id": "abc-123-def",
            "status": "PROGRESS",
            "progress": {
                "current": 50,
                "total": 100,
                "percent": 50
            }
        }

    响应（成功）:
        {
            "task_id": "abc-123-def",
            "status": "SUCCESS",
            "result": {
                "download_url": "https://..."
            }
        }
    """
    # 从 Celery 获取任务结果
    task_result = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": task_result.state,
    }

    if task_result.state == 'PENDING':
        response["message"] = "任务等待执行中"

    elif task_result.state == 'STARTED':
        response["message"] = "任务正在执行中"

    elif task_result.state == 'PROGRESS':
        # 获取进度信息
        info = task_result.info
        response["progress"] = {
            "current": info.get('current', 0),
            "total": info.get('total', 0),
            "percent": int((info.get('current', 0) / info.get('total', 1)) * 100)
        }
        response["message"] = info.get('status', '处理中...')

    elif task_result.state == 'SUCCESS':
        # 获取任务结果
        response["result"] = task_result.result
        response["message"] = "任务执行成功"

    elif task_result.state == 'FAILURE':
        # 获取错误信息
        response["error"] = str(task_result.info)
        response["message"] = "任务执行失败"

    else:
        response["message"] = task_result.state

    return success(data=response)


@router.delete("/cancel/{task_id}", tags=["任务-查询"], summary="取消任务", description="取消正在执行或等待执行的任务")
async def cancel_task(task_id: str):
    """
    取消任务

    功能:
        取消正在执行或等待执行的任务

    注意:
        - 只能取消未开始或正在执行的任务
        - 已完成的任务无法取消

    使用示例:
        DELETE /api/v1/tasks/cancel/abc-123-def
    """
    task_result = celery_app.AsyncResult(task_id)

    if task_result.state in ['PENDING', 'STARTED', 'PROGRESS']:
        task_result.revoke(terminate=True)
        return success(data={
            "task_id": task_id,
            "message": "任务已取消"
        })
    else:
        return error(message=f"无法取消任务，当前状态: {task_result.state}")


@router.get("/list", tags=["任务-查询"], summary="列出活跃任务", description="查看当前正在执行和等待执行的任务列表")
async def list_tasks():
    """
    列出所有活跃任务

    功能:
        查看当前正在执行和等待执行的任务

    注意:
        需要使用 Celery Inspect 或 Flower 监控工具
        这里返回模拟数据

    使用示例:
        GET /api/v1/tasks/list
    """
    # 实际项目中，使用 Celery Inspect:
    # from core.celery_app import celery_app
    # inspect = celery_app.control.inspect()
    # active_tasks = inspect.active()
    # scheduled_tasks = inspect.scheduled()

    return success(data={
        "message": "请使用 Flower 监控工具查看所有任务",
        "flower_url": "http://localhost:5555"
    })


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结：

1. 【任务提交流程】
   用户请求 → FastAPI 接收 → 提交到 Celery → 立即返回 task_id → Worker 执行任务

2. 【异步 vs 同步】
   # ❌ 同步（阻塞 API）
   result = send_email("user@example.com", "Hi", "Hello")
   return result  # 要等 2-3 秒

   # ✅ 异步（立即返回）
   task = send_email.delay("user@example.com", "Hi", "Hello")
   return {"task_id": task.id}  # 立即返回

3. 【任务状态追踪】
   1. 提交任务，获取 task_id
   2. 前端轮询 /tasks/status/{task_id}
   3. 根据状态显示进度
   4. 任务完成后获取结果

4. 【前端集成示例】
   // 提交任务
   const response = await fetch('/api/v1/tasks/email/send', {
       method: 'POST',
       body: JSON.stringify({to: 'user@example.com', subject: 'Hi', body: 'Hello'})
   });
   const {task_id} = await response.json();

   // 轮询状态
   const timer = setInterval(async () => {
       const status = await fetch(`/api/v1/tasks/status/${task_id}`);
       const data = await status.json();

       if (data.status === 'SUCCESS') {
           clearInterval(timer);
           console.log('任务完成！', data.result);
       } else if (data.status === 'FAILURE') {
           clearInterval(timer);
           console.log('任务失败！', data.error);
       } else {
           console.log('进度：', data.progress);
       }
   }, 2000);  // 每 2 秒查询一次

5. 【最佳实践】
   - 任务要幂等（多次执行结果一样）
   - 设置超时时间
   - 失败自动重试
   - 记录详细日志
   - 结果过期时间

6. 【监控工具】
   - Flower: Web 监控界面
   - Celery Inspect: 命令行监控
   - 自定义监控（记录到数据库）
"""
