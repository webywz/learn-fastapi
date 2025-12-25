"""
===========================================
错误码定义模块 (Error Codes Module)
===========================================

作用：
  定义所有业务错误码，让前端可以根据错误码做不同的处理

为什么需要错误码？
  1. 前端可以根据错误码做国际化（不同语言显示不同文字）
  2. 前端可以根据错误码做特殊处理（比如 token 过期自动跳转登录页）
  3. 方便调试和日志追踪
  4. 规范团队开发，避免重复定义

错误码设计规范：
  - 0: 成功
  - 400xx: 客户端错误（参数错误、业务逻辑错误）
  - 401xx: 认证相关错误（未登录、token 过期）
  - 403xx: 权限相关错误（无权访问）
  - 404xx: 资源不存在错误
  - 500xx: 服务器错误（系统异常）

类比前端：
  就像前端定义的错误常量，避免魔法数字
  const ERROR_CODES = { USER_NOT_FOUND: 40401, ... }
"""

from enum import Enum


class ErrorCode(Enum):
    """
    错误码枚举类

    为什么用枚举（Enum）？
      1. 避免硬编码（写死的数字），代码更易读
      2. IDE 有自动提示，不容易写错
      3. 集中管理，方便修改和维护

    使用方式：
      # 获取错误码的值
      ErrorCode.USER_ALREADY_EXISTS.value  # 40001

      # 获取错误码的名称
      ErrorCode.USER_ALREADY_EXISTS.name   # "USER_ALREADY_EXISTS"

    每个错误码格式：
      错误名 = (错误码值, "错误描述")
    """

    # =========================================
    # 成功状态码
    # =========================================
    SUCCESS = (0, "success")

    # =========================================
    # 400xx - 客户端错误（用户输入错误、业务规则错误）
    # =========================================

    # 用户相关错误 (400xx)
    USER_ALREADY_EXISTS = (40001, "用户名已存在")
    EMAIL_ALREADY_EXISTS = (40002, "邮箱已存在")
    INVALID_USERNAME_OR_PASSWORD = (40003, "用户名或密码错误")
    PASSWORD_TOO_SHORT = (40004, "密码长度不能少于6位")
    INVALID_EMAIL_FORMAT = (40005, "邮箱格式不正确")
    USER_DISABLED = (40006, "用户已被禁用")

    # 参数验证错误 (401xx)
    PARAMS_INVALID = (40100, "参数验证失败")
    PARAMS_MISSING = (40101, "缺少必需参数")
    PARAMS_TYPE_ERROR = (40102, "参数类型错误")

    # 业务逻辑错误 (402xx)
    OPERATION_FAILED = (40200, "操作失败")
    DUPLICATE_OPERATION = (40201, "重复操作")

    # =========================================
    # 401xx - 认证相关错误（登录、token）
    # =========================================
    # 这里的 401xx 是业务错误码，不是 HTTP 401
    # 业务错误码从 41000 开始，避免与上面的 401xx 冲突

    UNAUTHORIZED = (41000, "未登录或登录已过期")
    TOKEN_EXPIRED = (41001, "Token 已过期")
    TOKEN_INVALID = (41002, "Token 无效")
    TOKEN_MISSING = (41003, "缺少 Token")

    # =========================================
    # 403xx - 权限相关错误
    # =========================================
    FORBIDDEN = (40300, "无权访问")
    PERMISSION_DENIED = (40301, "权限不足")
    RESOURCE_ACCESS_DENIED = (40302, "无权访问此资源")

    # =========================================
    # 404xx - 资源不存在错误
    # =========================================
    USER_NOT_FOUND = (40401, "用户不存在")
    RESOURCE_NOT_FOUND = (40402, "资源不存在")

    # =========================================
    # 500xx - 服务器内部错误
    # =========================================
    INTERNAL_ERROR = (50000, "服务器内部错误")
    DATABASE_ERROR = (50001, "数据库错误")
    NETWORK_ERROR = (50002, "网络错误")
    THIRD_PARTY_ERROR = (50003, "第三方服务错误")

    def __init__(self, code: int, message: str):
        """
        初始化方法

        参数:
            code: 错误码数字
            message: 错误描述文字
        """
        self._code = code
        self._message = message

    @property
    def code(self) -> int:
        """
        获取错误码

        返回:
            int: 错误码数字

        使用示例:
            error_code = ErrorCode.USER_ALREADY_EXISTS
            print(error_code.code)  # 输出: 40001
        """
        return self._code

    @property
    def message(self) -> str:
        """
        获取错误描述

        返回:
            str: 错误描述文字

        使用示例:
            error_code = ErrorCode.USER_ALREADY_EXISTS
            print(error_code.message)  # 输出: "用户名已存在"
        """
        return self._message


# ============================================================
# 快捷获取方法（可选）
# ============================================================

def get_error_code(error_enum: ErrorCode) -> int:
    """
    快捷获取错误码数字

    参数:
        error_enum: 错误码枚举

    返回:
        int: 错误码数字

    使用示例:
        code = get_error_code(ErrorCode.USER_ALREADY_EXISTS)
        # code = 40001
    """
    return error_enum.code


def get_error_message(error_enum: ErrorCode) -> str:
    """
    快捷获取错误描述

    参数:
        error_enum: 错误码枚举

    返回:
        str: 错误描述文字

    使用示例:
        msg = get_error_message(ErrorCode.USER_ALREADY_EXISTS)
        # msg = "用户名已存在"
    """
    return error_enum.message


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结（给前端开发的你）：

1. 【错误码设计】
   - 类似前端的状态码常量定义
   - 统一管理，避免魔法数字
   - 方便前端做国际化和特殊处理

2. 【枚举 (Enum)】
   - Python 的枚举类似 TypeScript 的 enum
   - 提供类型安全和 IDE 提示
   - 避免硬编码

3. 【错误码规范】
   - 0: 成功
   - 4xxxx: 客户端错误
   - 5xxxx: 服务器错误
   - 详细分类方便定位问题

4. 【前端如何使用】
   前端可以根据错误码做不同处理：

   // TypeScript 示例
   axios.interceptors.response.use(
     response => response,
     error => {
       const code = error.response.data.code;

       switch(code) {
         case 41000: // 未登录
         case 41001: // Token 过期
           // 跳转到登录页
           router.push('/login');
           break;

         case 40300: // 无权访问
           message.error('您没有权限访问此资源');
           break;

         case 40001: // 用户名已存在
           // 在表单中显示错误
           formErrors.username = '用户名已存在';
           break;

         default:
           message.error(error.response.data.message);
       }

       return Promise.reject(error);
     }
   );

5. 【HTTP 状态码 vs 业务错误码】
   - HTTP 状态码：200, 404, 500（传输层）
   - 业务错误码：40001, 50000（业务层）

   即使 HTTP 返回 200，业务也可能失败（code != 0）

   示例：
   HTTP 200 OK
   {
     "code": 40001,    // 业务失败
     "message": "用户名已存在",
     "data": null
   }

6. 【扩展性】
   需要新增错误码时，直接在这个文件里添加即可：
   NEW_ERROR = (40007, "新的错误描述")
"""
