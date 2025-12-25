"""
===========================================
统一响应格式模块 (Response Module)
===========================================

作用：
  前端开发最需要的就是统一的API响应格式！
  这个模块定义了所有接口的统一返回格式，让前端能够统一处理响应。

为什么需要统一响应格式？
  1. 前端可以写一个通用的请求拦截器，统一处理成功和失败
  2. 减少前端的判断逻辑，提高开发效率
  3. 让接口更规范，团队协作更顺畅

响应格式说明：
  成功：{ "code": 0, "message": "success", "data": {...} }
  失败：{ "code": 40001, "message": "错误信息", "data": null }
"""

from typing import Optional, Any, Generic, TypeVar
from pydantic import BaseModel, Field


# ============================================================
# 泛型类型变量 (Generic Type Variable)
# ============================================================
# 这是 Python 的泛型，可以让我们的响应模型支持不同类型的data
# 比如：ResponseModel[User] 或 ResponseModel[List[User]]
T = TypeVar('T')


# ============================================================
# 统一响应模型 (Unified Response Model)
# ============================================================
class ResponseModel(BaseModel, Generic[T]):
    """
    统一响应模型 - 所有接口都返回这个结构

    作为前端开发，你一定很熟悉这种格式！
    这就像 Axios 拦截器里统一处理的那个 response.data 一样

    字段说明:
        code (int): 业务状态码
            - 0: 表示成功
            - 非0: 表示各种业务错误（比如 40001=用户名已存在）

        message (str): 提示信息
            - 可以直接展示给用户的文字
            - 比如 "操作成功"、"用户名已存在" 等

        data (T | None): 实际业务数据
            - 成功时：包含实际数据（用户信息、列表等）
            - 失败时：通常为 None

    前端使用示例 (TypeScript):
        interface Response<T> {
          code: number;
          message: string;
          data: T | null;
        }

        // 在 axios 拦截器中
        axios.interceptors.response.use(
          response => {
            if (response.data.code === 0) {
              return response.data.data;  // 返回实际数据
            } else {
              // 统一错误提示
              message.error(response.data.message);
              return Promise.reject(response.data);
            }
          }
        );

    后端使用示例:
        # 成功响应
        return ResponseModel(code=0, message="操作成功", data=user)

        # 失败响应
        return ResponseModel(code=40001, message="用户名已存在", data=None)
    """

    code: int = Field(
        default=0,
        description="业务状态码，0表示成功，非0表示失败"
    )

    message: str = Field(
        default="success",
        description="提示信息，可直接展示给用户"
    )

    data: Optional[T] = Field(
        default=None,
        description="实际业务数据"
    )

    class Config:
        """
        Pydantic 配置类
        json_schema_extra: 在 OpenAPI 文档中显示示例
        """
        json_schema_extra = {
            "example": {
                "code": 0,
                "message": "success",
                "data": {"id": 1, "username": "zhangsan"}
            }
        }


# ============================================================
# 分页数据模型 (Pagination Model)
# ============================================================
class PageData(BaseModel, Generic[T]):
    """
    分页数据模型 - 前端分页组件需要的数据结构

    为什么需要分页？
        当数据量很大时（比如有1000个用户），一次性返回所有数据会：
        1. 接口响应慢（数据量大）
        2. 前端渲染慢（DOM节点太多）
        3. 浪费带宽（用户可能只看前几页）

    前端分页组件通常需要这些数据：
        - items: 当前页的数据
        - total: 总共有多少条数据（用于计算总页数）
        - page: 当前是第几页
        - page_size: 每页显示多少条
        - total_pages: 总共有多少页

    字段说明:
        items: 当前页的数据列表（比如第1页的10个用户）
        total: 总记录数（比如总共有100个用户）
        page: 当前页码（从1开始）
        page_size: 每页大小（比如每页10条）
        total_pages: 总页数（自动计算：total / page_size 向上取整）

    前端使用示例 (Element Plus):
        <el-table :data="pageData.items">
          ...
        </el-table>

        <el-pagination
          :current-page="pageData.page"
          :page-size="pageData.page_size"
          :total="pageData.total"
          @current-change="handlePageChange"
        />
    """

    items: list[T] = Field(
        description="当前页的数据列表"
    )

    total: int = Field(
        description="总记录数"
    )

    page: int = Field(
        default=1,
        description="当前页码（从1开始）"
    )

    page_size: int = Field(
        default=10,
        description="每页大小"
    )

    total_pages: int = Field(
        description="总页数"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {"id": 1, "username": "user1"},
                    {"id": 2, "username": "user2"}
                ],
                "total": 100,
                "page": 1,
                "page_size": 10,
                "total_pages": 10
            }
        }


# ============================================================
# 快捷响应函数 (Helper Functions)
# ============================================================
# 这些函数让你的代码更简洁，不用每次都写完整的 ResponseModel

def success(data: Any = None, message: str = "success") -> ResponseModel:
    """
    成功响应的快捷方法

    使用场景：
        任何操作成功时都可以用这个函数快速返回

    参数:
        data: 要返回的业务数据（可以是对象、列表、字典等）
        message: 提示信息（默认是 "success"）

    返回:
        ResponseModel: 统一的响应对象

    使用示例:
        # 1. 只返回成功，不需要数据
        return success()

        # 2. 返回成功 + 数据
        return success(data=user, message="用户创建成功")

        # 3. 返回成功 + 列表数据
        return success(data=users, message="查询成功")
    """
    return ResponseModel(code=0, message=message, data=data)


def error(code: int, message: str, data: Any = None) -> ResponseModel:
    """
    错误响应的快捷方法

    使用场景：
        业务逻辑出现错误时（比如用户名重复、权限不足等）

    参数:
        code: 错误码（必须非0，通常是 40001、50001 这种）
        message: 错误提示信息
        data: 额外的错误信息（通常为None）

    返回:
        ResponseModel: 统一的响应对象

    使用示例:
        # 1. 用户名已存在
        return error(code=40001, message="用户名已存在")

        # 2. 权限不足
        return error(code=40301, message="权限不足，无法访问")

        # 3. 带额外信息的错误
        return error(
            code=40002,
            message="参数验证失败",
            data={"errors": ["用户名不能为空", "密码长度不够"]}
        )
    """
    return ResponseModel(code=code, message=message, data=data)


def success_with_page(
    items: list,
    total: int,
    page: int = 1,
    page_size: int = 10,
    message: str = "success"
) -> ResponseModel[PageData]:
    """
    分页成功响应的快捷方法

    使用场景：
        返回列表数据，并且需要分页时

    参数:
        items: 当前页的数据列表
        total: 总记录数（需要从数据库查询 count）
        page: 当前页码（默认第1页）
        page_size: 每页大小（默认10条）
        message: 提示信息（默认 "success"）

    返回:
        ResponseModel[PageData]: 包含分页信息的统一响应

    使用示例:
        # 从数据库查询
        users = await db.query(User).offset(0).limit(10).all()  # 当前页数据
        total = await db.query(User).count()  # 总数

        # 返回分页响应
        return success_with_page(
            items=users,
            total=total,
            page=1,
            page_size=10
        )

    前端如何调用：
        // GET /api/v1/users?page=1&page_size=10
        const response = await axios.get('/api/v1/users', {
          params: { page: 1, page_size: 10 }
        });

        // response.data 就是：
        // {
        //   code: 0,
        //   message: "success",
        //   data: {
        //     items: [...],
        //     total: 100,
        //     page: 1,
        //     page_size: 10,
        //     total_pages: 10
        //   }
        // }
    """
    # 计算总页数（向上取整）
    # 比如：total=95, page_size=10 => total_pages=10
    total_pages = (total + page_size - 1) // page_size

    # 构建分页数据对象
    page_data = PageData(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

    # 返回包含分页数据的响应
    return ResponseModel(code=0, message=message, data=page_data)


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结（给前端开发的你）：

1. 【统一响应格式】
   - 就像前端的 Axios 拦截器，后端也需要统一的响应结构
   - 让前端不用判断各种不同的返回格式

2. 【泛型 Generic[T]】
   - 类似 TypeScript 的泛型 <T>
   - ResponseModel[User] 表示 data 是 User 类型
   - ResponseModel[List[User]] 表示 data 是用户列表

3. 【Pydantic 模型】
   - FastAPI 用 Pydantic 做数据验证和序列化
   - 类似前端的 Zod 或 Joi
   - 自动生成 OpenAPI 文档

4. 【分页设计】
   - offset/limit 分页（数据库层面）
   - page/page_size 分页（用户层面）
   - 转换：offset = (page - 1) * page_size

5. 【快捷函数】
   - success() 和 error() 让代码更简洁
   - 类似前端的工具函数封装
"""
