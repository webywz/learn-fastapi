"""
===========================================
自定义异常类模块 (Custom Exceptions Module)
===========================================

作用：
  定义业务异常类，让错误处理更规范和优雅

为什么需要自定义异常？
  1. 区分业务异常和系统异常
  2. 携带错误码和错误信息，方便统一处理
  3. 让代码更清晰，一眼就知道是什么错误
  4. 配合全局异常处理器，自动返回统一格式

类比前端：
  就像前端抛出自定义错误
  throw new BusinessError('用户名已存在', 40001)

  然后在错误边界（Error Boundary）中统一捕获处理
"""

from typing import Any, Optional
from .error_codes import ErrorCode


# ============================================================
# 基础业务异常类
# ============================================================

class BusinessException(Exception):
    """
    业务异常基类

    这是所有业务异常的父类。
    业务异常指的是：用户操作导致的可预期的错误
    比如：用户名已存在、密码错误、权限不足等

    为什么要继承 Exception？
      - Exception 是 Python 所有异常的基类
      - 继承它才能使用 try-except 捕获
      - 可以自定义携带的信息

    属性说明:
        error_code (ErrorCode): 错误码枚举
        message (str): 错误信息（可选，默认使用错误码的message）
        data (Any): 额外的错误数据（可选）

    使用示例:
        # 方式1：只传错误码
        raise BusinessException(ErrorCode.USER_ALREADY_EXISTS)

        # 方式2：传错误码 + 自定义消息
        raise BusinessException(
            ErrorCode.USER_ALREADY_EXISTS,
            message="用户名 'zhangsan' 已经被注册了"
        )

        # 方式3：传错误码 + 自定义消息 + 额外数据
        raise BusinessException(
            ErrorCode.PARAMS_INVALID,
            message="参数验证失败",
            data={"errors": ["用户名不能为空", "密码长度不够"]}
        )

    捕获示例:
        try:
            # 业务逻辑
            if user_exists:
                raise BusinessException(ErrorCode.USER_ALREADY_EXISTS)
        except BusinessException as e:
            # 获取错误码
            print(e.code)  # 40001
            # 获取错误信息
            print(e.message)  # "用户名已存在"
            # 获取额外数据
            print(e.data)  # None 或其他数据
    """

    def __init__(
        self,
        error_code: ErrorCode,
        message: Optional[str] = None,
        data: Any = None
    ):
        """
        初始化业务异常

        参数:
            error_code: 错误码枚举（必传）
            message: 自定义错误信息（可选，不传则使用错误码的默认信息）
            data: 额外的错误数据（可选）
        """
        self.error_code = error_code
        self.code = error_code.code  # 错误码数字
        self.message = message or error_code.message  # 错误信息
        self.data = data  # 额外数据

        # 调用父类的初始化方法
        # 这样在打印异常时会显示错误信息
        super().__init__(self.message)

    def __str__(self) -> str:
        """
        字符串表示

        当你 print(exception) 时会调用这个方法

        返回:
            str: 格式化的错误信息

        示例:
            e = BusinessException(ErrorCode.USER_ALREADY_EXISTS)
            print(e)  # 输出: [40001] 用户名已存在
        """
        return f"[{self.code}] {self.message}"

    def __repr__(self) -> str:
        """
        开发者友好的表示

        在调试时（比如 REPL 中）显示

        返回:
            str: 详细的异常信息
        """
        return (
            f"BusinessException(code={self.code}, "
            f"message='{self.message}', data={self.data})"
        )


# ============================================================
# 具体的业务异常类（可选，根据需要定义）
# ============================================================

class AuthenticationException(BusinessException):
    """
    认证异常

    专门用于处理认证相关的错误
    比如：未登录、token 过期、token 无效等

    为什么要单独定义？
      - 让代码更语义化（一看就知道是认证错误）
      - 方便统一处理（比如自动跳转登录页）
      - 可以在这里添加认证相关的特殊逻辑

    使用示例:
        # 检查用户登录状态
        if not current_user:
            raise AuthenticationException(ErrorCode.UNAUTHORIZED)

        # 检查 token 是否过期
        if token_expired:
            raise AuthenticationException(ErrorCode.TOKEN_EXPIRED)
    """

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.UNAUTHORIZED,
        message: Optional[str] = None,
        data: Any = None
    ):
        """
        初始化认证异常

        参数:
            error_code: 错误码（默认是 UNAUTHORIZED）
            message: 自定义错误信息
            data: 额外数据
        """
        super().__init__(error_code, message, data)


class PermissionException(BusinessException):
    """
    权限异常

    专门用于处理权限相关的错误
    比如：无权访问、权限不足等

    为什么要单独定义？
      - 让代码更语义化
      - 方便统一处理（比如显示 403 页面）
      - 可以添加权限相关的特殊逻辑

    使用示例:
        # 检查用户权限
        if not user.is_admin:
            raise PermissionException(ErrorCode.PERMISSION_DENIED)

        # 检查资源访问权限
        if resource.owner_id != current_user.id:
            raise PermissionException(
                ErrorCode.RESOURCE_ACCESS_DENIED,
                message="您不能访问其他用户的资源"
            )
    """

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.FORBIDDEN,
        message: Optional[str] = None,
        data: Any = None
    ):
        """
        初始化权限异常

        参数:
            error_code: 错误码（默认是 FORBIDDEN）
            message: 自定义错误信息
            data: 额外数据
        """
        super().__init__(error_code, message, data)


class ResourceNotFoundException(BusinessException):
    """
    资源不存在异常

    专门用于处理资源不存在的错误
    比如：用户不存在、文章不存在等

    使用示例:
        # 查询用户
        user = await get_user(user_id)
        if not user:
            raise ResourceNotFoundException(
                ErrorCode.USER_NOT_FOUND,
                message=f"用户 ID {user_id} 不存在"
            )
    """

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.RESOURCE_NOT_FOUND,
        message: Optional[str] = None,
        data: Any = None
    ):
        """
        初始化资源不存在异常

        参数:
            error_code: 错误码（默认是 RESOURCE_NOT_FOUND）
            message: 自定义错误信息
            data: 额外数据
        """
        super().__init__(error_code, message, data)


class ValidationException(BusinessException):
    """
    参数验证异常

    专门用于处理参数验证失败的错误
    比如：参数缺失、参数类型错误、参数格式不对等

    使用示例:
        # 验证参数
        if not username:
            raise ValidationException(
                ErrorCode.PARAMS_MISSING,
                message="用户名不能为空"
            )

        # 验证邮箱格式
        if not is_valid_email(email):
            raise ValidationException(
                ErrorCode.INVALID_EMAIL_FORMAT,
                message=f"邮箱格式不正确: {email}"
            )

        # 多个验证错误
        errors = []
        if not username:
            errors.append("用户名不能为空")
        if len(password) < 6:
            errors.append("密码长度不能少于6位")

        if errors:
            raise ValidationException(
                ErrorCode.PARAMS_INVALID,
                message="参数验证失败",
                data={"errors": errors}
            )
    """

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.PARAMS_INVALID,
        message: Optional[str] = None,
        data: Any = None
    ):
        """
        初始化参数验证异常

        参数:
            error_code: 错误码（默认是 PARAMS_INVALID）
            message: 自定义错误信息
            data: 额外数据（可以包含具体的验证错误列表）
        """
        super().__init__(error_code, message, data)


# ============================================================
# 快捷抛出异常的函数（可选）
# ============================================================

def raise_user_not_found(user_id: Any = None):
    """
    快捷抛出用户不存在异常

    使用示例:
        user = await get_user(123)
        if not user:
            raise_user_not_found(123)
    """
    message = f"用户不存在" if user_id is None else f"用户 ID {user_id} 不存在"
    raise ResourceNotFoundException(
        ErrorCode.USER_NOT_FOUND,
        message=message
    )


def raise_unauthorized(message: str = "未登录或登录已过期"):
    """
    快捷抛出未授权异常

    使用示例:
        if not current_user:
            raise_unauthorized()
    """
    raise AuthenticationException(
        ErrorCode.UNAUTHORIZED,
        message=message
    )


def raise_permission_denied(message: str = "权限不足"):
    """
    快捷抛出权限不足异常

    使用示例:
        if not user.is_admin:
            raise_permission_denied("只有管理员才能执行此操作")
    """
    raise PermissionException(
        ErrorCode.PERMISSION_DENIED,
        message=message
    )


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结（给前端开发的你）：

1. 【异常 vs 错误码】
   - 异常（Exception）：Python 的错误处理机制（类似 try-catch）
   - 错误码（ErrorCode）：业务层面的错误标识

   异常携带错误码，两者结合使用：
   raise BusinessException(ErrorCode.USER_ALREADY_EXISTS)

2. 【业务异常 vs 系统异常】
   - 业务异常：用户操作导致的可预期错误（自定义异常）
     例如：用户名重复、权限不足、资源不存在

   - 系统异常：程序bug或环境问题导致的不可预期错误
     例如：数据库连接失败、内存不足、网络超时

3. 【异常的继承体系】
   Exception (Python 内置)
     └── BusinessException (自定义基类)
           ├── AuthenticationException (认证异常)
           ├── PermissionException (权限异常)
           ├── ResourceNotFoundException (资源不存在)
           └── ValidationException (参数验证异常)

4. 【异常处理流程】
   业务代码 → 抛出异常 → 全局异常处理器 → 返回统一格式

   try:
       if user_exists:
           raise BusinessException(ErrorCode.USER_ALREADY_EXISTS)
   except BusinessException as e:
       # 全局异常处理器会捕获并转换为统一响应格式
       return ResponseModel(
           code=e.code,
           message=e.message,
           data=e.data
       )

5. 【与前端的对应关系】
   后端抛异常    →    前端捕获错误
   ↓                 ↓
   全局异常处理器  →   Axios 拦截器
   ↓                 ↓
   统一响应格式    →   统一错误处理

6. 【最佳实践】
   - 使用具体的异常类（AuthenticationException 而不是 Exception）
   - 提供清晰的错误信息（让用户知道怎么解决）
   - 不要吞掉异常（要么处理，要么向上抛）
   - 记录日志（方便排查问题）

7. 【实际使用示例】
   # 在业务逻辑中
   async def create_user(username: str, email: str):
       # 检查用户名
       if await user_exists(username):
           raise BusinessException(ErrorCode.USER_ALREADY_EXISTS)

       # 检查邮箱
       if await email_exists(email):
           raise BusinessException(ErrorCode.EMAIL_ALREADY_EXISTS)

       # 创建用户
       user = await User.create(username=username, email=email)
       return user

   # FastAPI 路由中
   @router.post("/users")
   async def create_user_api(user_data: UserCreate):
       try:
           user = await create_user(
               username=user_data.username,
               email=user_data.email
           )
           return success(data=user, message="用户创建成功")
       except BusinessException as e:
           # 返回错误响应
           return error(code=e.code, message=e.message, data=e.data)

   注意：实际项目中不需要在每个路由都写 try-except
   我们会用全局异常处理器自动捕获！
"""
