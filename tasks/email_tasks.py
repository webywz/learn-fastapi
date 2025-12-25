"""
===========================================
邮件任务 (Email Tasks)
===========================================

作用：
  处理所有邮件相关的异步任务

为什么发邮件要用异步？
  - 发邮件很慢（1-3 秒）
  - 如果同步发送，API 会阻塞
  - 用户体验差

使用场景：
  - 用户注册欢迎邮件
  - 密码重置邮件
  - 订单通知邮件
  - 营销邮件

类比前端：
  - 类似后台发送通知
  - 用户不需要等待
"""

import time
from celery import shared_task
from typing import List


# ============================================================
# 基础邮件任务
# ============================================================

@shared_task(
    bind=True,
    name="tasks.email_tasks.send_email",
    max_retries=3,
    default_retry_delay=60
)
def send_email(self, to: str, subject: str, body: str):
    """
    发送单个邮件（异步任务）

    参数:
        to: 收件人邮箱
        subject: 邮件主题
        body: 邮件内容

    装饰器参数说明:
        bind=True: 绑定任务实例（可以使用 self）
        name: 任务名称（用于监控）
        max_retries: 最大重试次数
        default_retry_delay: 重试延迟（秒）

    使用示例（在 API 中）:
        # 异步发送（立即返回）
        send_email.delay("user@example.com", "Welcome", "Hello!")

        # 延迟 60 秒后发送
        send_email.apply_async(
            args=["user@example.com", "Welcome", "Hello!"],
            countdown=60
        )

        # 指定时间发送
        send_email.apply_async(
            args=["user@example.com", "Welcome", "Hello!"],
            eta=datetime(2024, 1, 1, 0, 0, 0)
        )
    """
    try:
        print(f"📧 开始发送邮件...")
        print(f"   收件人: {to}")
        print(f"   主题: {subject}")
        print(f"   内容: {body}")

        # 模拟发送邮件（实际项目中调用 SMTP 或邮件服务 API）
        time.sleep(2)  # 模拟网络延迟

        # 实际发送邮件的代码（示例）:
        # import smtplib
        # from email.mime.text import MIMEText
        #
        # msg = MIMEText(body)
        # msg['Subject'] = subject
        # msg['From'] = 'noreply@example.com'
        # msg['To'] = to
        #
        # with smtplib.SMTP('smtp.gmail.com', 587) as server:
        #     server.starttls()
        #     server.login('your_email@gmail.com', 'your_password')
        #     server.send_message(msg)

        print(f"✅ 邮件发送成功!")
        return {"status": "success", "to": to}

    except Exception as exc:
        print(f"❌ 邮件发送失败: {exc}")

        # 任务失败，自动重试
        raise self.retry(exc=exc)


@shared_task(name="tasks.email_tasks.send_welcome_email")
def send_welcome_email(user_id: int, email: str, username: str):
    """
    发送欢迎邮件

    参数:
        user_id: 用户 ID
        email: 用户邮箱
        username: 用户名

    使用场景:
        用户注册成功后发送

    调用方式:
        send_welcome_email.delay(1, "alice@example.com", "Alice")
    """
    print(f"📧 发送欢迎邮件给 {username} ({email})")

    subject = f"欢迎加入，{username}！"
    body = f"""
    亲爱的 {username}，

    欢迎加入我们的平台！

    您的账号已经创建成功。

    如有任何问题，请随时联系我们。

    祝好！
    团队
    """

    # 模拟发送
    time.sleep(1)

    print(f"✅ 欢迎邮件已发送给 {email}")
    return {"user_id": user_id, "status": "sent"}


@shared_task(name="tasks.email_tasks.send_password_reset_email")
def send_password_reset_email(email: str, reset_token: str):
    """
    发送密码重置邮件

    参数:
        email: 用户邮箱
        reset_token: 重置令牌

    使用场景:
        用户忘记密码

    调用方式:
        send_password_reset_email.delay("user@example.com", "abc123")
    """
    print(f"📧 发送密码重置邮件给 {email}")

    reset_url = f"https://example.com/reset-password?token={reset_token}"

    subject = "重置您的密码"
    body = f"""
    您好，

    我们收到了重置密码的请求。

    请点击以下链接重置密码：
    {reset_url}

    如果您没有请求重置密码，请忽略此邮件。

    此链接将在 1 小时后失效。
    """

    # 模拟发送
    time.sleep(1)

    print(f"✅ 密码重置邮件已发送")
    return {"email": email, "status": "sent"}


# ============================================================
# 批量邮件任务
# ============================================================

@shared_task(name="tasks.email_tasks.send_bulk_emails")
def send_bulk_emails(emails: List[dict]):
    """
    批量发送邮件

    参数:
        emails: 邮件列表
            [
                {"to": "user1@example.com", "subject": "Hello", "body": "..."},
                {"to": "user2@example.com", "subject": "Hello", "body": "..."},
            ]

    使用场景:
        - 营销邮件
        - 系统通知

    调用方式:
        send_bulk_emails.delay([
            {"to": "user1@example.com", "subject": "Hi", "body": "..."},
            {"to": "user2@example.com", "subject": "Hi", "body": "..."},
        ])

    注意:
        - 大量邮件建议分批发送
        - 避免被标记为垃圾邮件
    """
    print(f"📧 开始批量发送 {len(emails)} 封邮件...")

    success_count = 0
    failed_count = 0

    for email_data in emails:
        try:
            to = email_data["to"]
            subject = email_data["subject"]
            body = email_data["body"]

            # 发送邮件
            print(f"   发送给 {to}...")
            time.sleep(0.5)  # 模拟发送

            success_count += 1

        except Exception as e:
            print(f"   ❌ 发送给 {to} 失败: {e}")
            failed_count += 1

    print(f"✅ 批量发送完成!")
    print(f"   成功: {success_count}")
    print(f"   失败: {failed_count}")

    return {
        "total": len(emails),
        "success": success_count,
        "failed": failed_count
    }


@shared_task(name="tasks.email_tasks.send_newsletter")
def send_newsletter(subject: str, content: str, user_ids: List[int]):
    """
    发送新闻通讯

    参数:
        subject: 邮件主题
        content: 邮件内容
        user_ids: 用户 ID 列表

    使用场景:
        定期发送新闻、更新

    调用方式:
        send_newsletter.delay("本周更新", "内容...", [1, 2, 3])

    优化:
        - 分批发送（每批 100 个）
        - 使用邮件服务 API（SendGrid, Mailgun）
    """
    print(f"📧 发送新闻通讯给 {len(user_ids)} 个用户...")

    # 实际项目中，这里会：
    # 1. 从数据库查询用户邮箱
    # 2. 使用模板渲染邮件内容
    # 3. 调用邮件服务 API 批量发送

    # 模拟发送
    batch_size = 100
    for i in range(0, len(user_ids), batch_size):
        batch = user_ids[i:i + batch_size]
        print(f"   发送第 {i//batch_size + 1} 批 ({len(batch)} 个用户)...")
        time.sleep(1)

    print(f"✅ 新闻通讯发送完成!")
    return {"user_count": len(user_ids), "status": "sent"}


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结：

1. 【@shared_task 装饰器】
   - 将函数转换为 Celery 任务
   - 可以异步执行
   - 支持重试、延迟等功能

2. 【任务调用方式】
   # 同步调用（阻塞）
   result = send_email("user@example.com", "Hi", "Hello")

   # 异步调用（立即返回）
   task = send_email.delay("user@example.com", "Hi", "Hello")

   # 异步调用（带参数）
   task = send_email.apply_async(
       args=["user@example.com", "Hi", "Hello"],
       countdown=60,  # 延迟 60 秒
       expires=3600,  # 1 小时后过期
   )

3. 【获取任务结果】
   task = send_email.delay("user@example.com", "Hi", "Hello")

   # 检查任务状态
   print(task.state)  # PENDING, STARTED, SUCCESS, FAILURE

   # 获取结果（阻塞）
   result = task.get(timeout=10)

   # 异步检查
   if task.ready():
       result = task.result

4. 【任务重试】
   try:
       # 执行任务
       pass
   except Exception as exc:
       # 失败后重试
       raise self.retry(exc=exc, countdown=60, max_retries=3)

5. 【实际项目中的邮件发送】
   # 使用 SMTP
   import smtplib

   # 使用邮件服务（推荐）
   # SendGrid, Mailgun, AWS SES, 阿里云邮件推送

6. 【性能优化】
   - 批量发送（每批 100-1000）
   - 使用专业邮件服务
   - 异步发送（不阻塞 API）
   - 失败重试
"""
