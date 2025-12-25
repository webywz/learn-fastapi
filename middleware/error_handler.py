"""
===========================================
全局异常处理器 (Global Exception Handler)
===========================================

作用：
  统一捕获和处理所有异常，返回统一格式的错误响应

为什么需要？
  1. 避免在每个路由都写 try-except
  2. 确保所有错误都返回统一格式
  3. 记录错误日志，方便排查问题

类比前端：
  - 类似 Axios 的响应拦截器
  - 或者 React 的 Error Boundary
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError

from common.exceptions import BusinessException
from common.error_codes import ErrorCode
from common.response import ResponseModel
from utils.logger import get_logger

logger = get_logger(__name__)


async def business_exception_handler(request: Request, exc: BusinessException) -> JSONResponse:
    """
    处理业务异常

    业务异常是我们主动抛出的，都有明确的错误码和消息
    直接返回给前端即可

    参数:
        request: 请求对象
        exc: 业务异常

    返回:
        JSONResponse: 统一格式的错误响应
    """
    logger.warning(
        f"Business exception: {exc.code} - {exc.message} | "
        f"Path: {request.url.path} | "
        f"Method: {request.method}"
    )

    response = ResponseModel(
        code=exc.code,
        message=exc.message,
        data=exc.data
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,  # 业务错误也返回 200
        content=response.dict()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    处理参数验证异常

    当 Pydantic 验证失败时（比如缺少必填字段、类型错误）

    参数:
        request: 请求对象
        exc: 验证异常

    返回:
        JSONResponse: 统一格式的错误响应
    """
    # 提取错误信息
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:])  # 字段名
        message = error["msg"]  # 错误消息
        errors.append(f"{field}: {message}")

    logger.warning(
        f"Validation error: {errors} | "
        f"Path: {request.url.path} | "
        f"Method: {request.method}"
    )

    response = ResponseModel(
        code=ErrorCode.PARAMS_INVALID.code,
        message="参数验证失败",
        data={"errors": errors}
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response.dict()
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    处理 HTTP 异常

    比如 404 Not Found, 405 Method Not Allowed 等

    参数:
        request: 请求对象
        exc: HTTP 异常

    返回:
        JSONResponse: 统一格式的错误响应
    """
    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail} | "
        f"Path: {request.url.path} | "
        f"Method: {request.method}"
    )

    # 根据 HTTP 状态码映射业务错误码
    error_code_map = {
        404: ErrorCode.RESOURCE_NOT_FOUND,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
    }

    error_code = error_code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)

    response = ResponseModel(
        code=error_code.code,
        message=str(exc.detail),
        data=None
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response.dict()
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    处理数据库异常

    比如连接失败、查询错误等

    参数:
        request: 请求对象
        exc: 数据库异常

    返回:
        JSONResponse: 统一格式的错误响应
    """
    logger.error(
        f"Database error: {str(exc)} | "
        f"Path: {request.url.path} | "
        f"Method: {request.method}",
        exc_info=True  # 记录完整堆栈
    )

    response = ResponseModel(
        code=ErrorCode.DATABASE_ERROR.code,
        message="数据库错误" if not logger.level == "DEBUG" else str(exc),
        data=None
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response.dict()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    处理所有未捕获的异常

    这是最后的兜底，防止程序崩溃

    参数:
        request: 请求对象
        exc: 异常

    返回:
        JSONResponse: 统一格式的错误响应
    """
    logger.error(
        f"Unexpected error: {str(exc)} | "
        f"Path: {request.url.path} | "
        f"Method: {request.method}",
        exc_info=True  # 记录完整堆栈
    )

    response = ResponseModel(
        code=ErrorCode.INTERNAL_ERROR.code,
        message="服务器内部错误",
        data=None
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response.dict()
    )


def register_exception_handlers(app):
    """
    注册所有异常处理器

    在 main.py 中调用

    使用示例:
        from middleware.error_handler import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)
    """
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
