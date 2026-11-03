"""
===========================================
邮件 Pydantic 模型 (Email Schemas)
===========================================

作用：
  给邮件教学接口提供请求体。
  真正组 MIME / 渲染模板在 services/email_service.py，
  这里只负责「前端能传什么、自动校验邮箱格式」。
"""

from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class EmailSendRequest(BaseModel):
    """直接发一封自定义邮件（不走模板）。"""

    to: EmailStr = Field(..., description="收件人", examples=["alice@example.com"])
    subject: str = Field(..., min_length=1, max_length=200, description="主题")
    text: Optional[str] = Field(None, description="纯文本正文")
    html: Optional[str] = Field(None, description="HTML 正文（可选）")
    use_queue: bool = Field(
        False,
        description="True 时尝试丢给 Celery；Broker 挂了会回退同步发送",
    )


class WelcomeEmailRequest(BaseModel):
    """欢迎邮件演示。"""

    to: EmailStr = Field(..., examples=["alice@example.com"])
    username: str = Field(..., min_length=1, max_length=50, examples=["alice"])
    use_queue: bool = False


class VerifyEmailRequest(BaseModel):
    """注册验证邮件演示（不会改数据库里的用户状态）。"""

    to: EmailStr = Field(..., examples=["alice@example.com"])
    username: str = Field(..., min_length=1, max_length=50, examples=["alice"])
    verify_token: Optional[str] = Field(
        None,
        description="不传则现场生成一个教学用 token",
    )
    use_queue: bool = False


class PasswordResetEmailRequest(BaseModel):
    """密码重置邮件演示（不会真的改密码）。"""

    to: EmailStr = Field(..., examples=["alice@example.com"])
    username: Optional[str] = Field(None, max_length=50, examples=["alice"])
    reset_token: Optional[str] = Field(
        None,
        description="不传则现场生成一个教学用 token",
    )
    use_queue: bool = False


class AttachmentEmailRequest(BaseModel):
    """附件演示：运行时生成很小的 txt / pdf，不写磁盘。"""

    to: EmailStr = Field(..., examples=["alice@example.com"])
    kind: Literal["text", "pdf"] = Field(
        "text",
        description="text=演示 txt；pdf=最小 PDF 头，用来看 MIME 附件",
    )
    use_queue: bool = False
