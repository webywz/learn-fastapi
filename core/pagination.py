"""
===========================================
分页助手 (Pagination Helpers)
===========================================

作用：
  给列表接口提供一套可复用的分页组件，覆盖两种最常见的做法：
  1. offset / limit（页码分页，也叫 page / page_size）
  2. cursor（游标分页，也叫 keyset pagination）

为什么单独封装？
  - 文件列表、分享列表、用户列表都在重复 offset 计算
  - 游标编解码、+1 探测是否有下一页，很容易写错
  - 教学时希望「先看这一份」，再去对照业务路由

两种分页怎么选（面试常问）：

  ┌────────────┬─────────────────────┬──────────────────────────┐
  │            │ offset / limit      │ cursor                   │
  ├────────────┼─────────────────────┼──────────────────────────┤
  │ 前端形态   │ 页码 1 / 2 / 3      │ 「加载更多」无限滚动     │
  │ 跳页       │ 能直接跳到第 N 页   │ 只能顺着下一页走         │
  │ 深分页     │ OFFSET 越大越慢     │ 始终只看「这条之后」     │
  │ 数据变动   │ 翻页时可能漏/重复   │ 相对稳定                 │
  │ 总条数     │ 后台表格通常要      │ 信息流通常不要           │
  │ 实现成本   │ 低                  │ 中（要编码游标）         │
  └────────────┴─────────────────────┴──────────────────────────┘

类比前端：
  - offset 分页 ≈ Element Plus / Ant Design 的 <Pagination>
  - cursor 分页 ≈ 朋友圈、Twitter 的 infinite scroll（next_cursor）

总数 COUNT(*) 的代价：
  - 小表（几百、几千行）：随便 COUNT，用户体验更好
  - 大表（百万行）：COUNT 可能比列表本身还慢
  - 游标接口默认可以不算总数；本项目文件列表为了兼容旧客户端仍返回 total

查询优化小抄（本模块只点到为止，不做成完整 Query Builder）：
  1. 深分页不要用巨大的 OFFSET，改游标
  2. 列表按 (owner_id, created_at, id) 过滤排序时，给这组字段建索引
  3. 循环里不要再查关联（N+1）；分享列表已经用了 selectinload
  4. 真要减载荷可以用 load_only / with_only_columns，但序列化字段要对齐
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, Optional, Sequence, TypeVar

from fastapi import Query
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.error_codes import ErrorCode
from common.exceptions import ValidationException


# ============================================================
# 默认值（和现有文件列表接口保持一致，避免破坏旧客户端）
# ============================================================

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100
CURSOR_FETCH_EXTRA = 1  # 多取 1 条，用来判断有没有下一页


T = TypeVar("T")


# ============================================================
# 页码 / 游标参数
# ============================================================

@dataclass(frozen=True)
class ListParams:
    """
    列表接口的查询参数。

    设计原则（兼容旧客户端）：
      - page / page_size 继续能用，默认 page=1、page_size=10
      - cursor 是新增的可选参数：没传就走 offset，传了就走游标
      - 传了 cursor 时忽略 page（游标本身已经定位到「上一页最后一条」）
    """

    page: int = DEFAULT_PAGE
    page_size: int = DEFAULT_PAGE_SIZE
    cursor: Optional[str] = None

    @property
    def mode(self) -> str:
        return "cursor" if self.cursor else "offset"

    @property
    def offset(self) -> int:
        return compute_offset(self.page, self.page_size)


def get_list_params(
    page: int = Query(
        DEFAULT_PAGE,
        ge=1,
        description="页码，从 1 开始。传入 cursor 时忽略",
    ),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=f"每页条数，默认 {DEFAULT_PAGE_SIZE}，最大 {MAX_PAGE_SIZE}",
    ),
    cursor: Optional[str] = Query(
        None,
        description="游标。有值时改为游标分页，不再使用 page",
    ),
) -> ListParams:
    """
    FastAPI 依赖：从 Query 收集分页参数。

    路由里这样用：
        params: ListParams = Depends(get_list_params)
    """
    if cursor is not None:
        cursor = cursor.strip() or None
    return ListParams(page=page, page_size=page_size, cursor=cursor)


# ============================================================
# 分页结果（业务层拿 ORM，路由层再序列化）
# ============================================================

@dataclass
class PaginatedPage(Generic[T]):
    """
    统一的分页结果。

    items 里可以是 ORM 对象，所以不用 Pydantic 硬序列化。
    路由层调用 as_dict(items=已序列化列表, items_key="files") 即可。
    """

    items: list[T]
    page: int
    page_size: int
    total: Optional[int]
    total_pages: int
    has_next: bool
    has_prev: bool
    next_cursor: Optional[str]
    mode: str

    def as_dict(
        self,
        items: Optional[list[Any]] = None,
        items_key: str = "items",
    ) -> dict[str, Any]:
        """
        转成统一响应里的 data 字典。

        items_key:
          - 新接口建议用 "items"（和 common.response.PageData 对齐）
          - 文件列表沿用 "files"，避免破坏已经在用的前端
        """
        return {
            items_key: self.items if items is None else items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
            "next_cursor": self.next_cursor,
            "mode": self.mode,
        }


# ============================================================
# 纯计算（方便单测，不碰数据库）
# ============================================================

def compute_offset(page: int, page_size: int) -> int:
    """
    page/page_size → SQL OFFSET

    例：第 3 页、每页 10 条 → 跳过前 20 条
        offset = (3 - 1) * 10 = 20
    """
    if page < 1:
        raise ValidationException(
            ErrorCode.PARAMS_INVALID,
            message="页码必须从 1 开始",
        )
    if page_size < 1:
        raise ValidationException(
            ErrorCode.PARAMS_INVALID,
            message="每页条数必须大于 0",
        )
    return (page - 1) * page_size


def compute_total_pages(total: int, page_size: int) -> int:
    """总页数（向上取整）。空列表返回 0，而不是 1。"""
    if total <= 0 or page_size <= 0:
        return 0
    return (total + page_size - 1) // page_size


def compute_has_next_offset(page: int, page_size: int, total: int) -> bool:
    """offset 模式：当前页之后还有没有数据。"""
    return page * page_size < total


def compute_has_prev_offset(page: int) -> bool:
    return page > 1


# ============================================================
# 游标编解码
# ============================================================
#
# 游标不要用「页码」假装游标，也不要把内部自增 id 明文暴露成
# ?after_id=12（能用，但不方便以后改成复合排序）。
#
# 本项目的约定：
#   payload = {"id": 12, "created_at": "2024-01-01T12:00:00+00:00"}
#   cursor  = urlsafe_b64(json)   # 去掉末尾 =，URL 更干净
#
# 本仓库的列表按自增 id 降序，游标通常只有 {"id": 12}。
# 如果你在 PostgreSQL 上按 created_at 排序，可以再带上时间做成复合游标：
#   payload = {"id": 12, "created_at": "2024-01-01T12:00:00+00:00"}
#   WHERE created_at < ? OR (created_at = ? AND id < ?)
# 注意：SQLite 的 DateTime 是字符串，格式对不齐时比较会错，教学环境不要这么用。
#

def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"游标不支持的类型: {type(value)!r}")


def encode_cursor(payload: dict[str, Any]) -> str:
    """把定位信息编码成 URL 安全的游标字符串。"""
    raw = json.dumps(payload, separators=(",", ":"), default=_json_default)
    token = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")
    return token.rstrip("=")


def decode_cursor(cursor: str) -> dict[str, Any]:
    """
    解码游标。

    任何格式错误都当成客户端参数问题（INVALID_CURSOR），
    不要返回 500，也不要泄露解码细节。
    """
    if cursor is None or not str(cursor).strip():
        raise ValidationException(
            ErrorCode.INVALID_CURSOR,
            message="分页游标无效",
        )

    try:
        padded = str(cursor).strip() + "=" * (-len(str(cursor).strip()) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValidationException(
            ErrorCode.INVALID_CURSOR,
            message="分页游标无效",
        ) from exc

    if not isinstance(payload, dict) or "id" not in payload:
        raise ValidationException(
            ErrorCode.INVALID_CURSOR,
            message="分页游标无效",
        )

    try:
        payload["id"] = int(payload["id"])
    except (TypeError, ValueError) as exc:
        raise ValidationException(
            ErrorCode.INVALID_CURSOR,
            message="分页游标无效",
        ) from exc

    return payload


def cursor_from_item(item: Any, sort_field: str = "created_at") -> str:
    """从当前页最后一条记录生成 next_cursor。"""
    payload: dict[str, Any] = {"id": item.id}
    sort_value = getattr(item, sort_field, None)
    if sort_value is not None and sort_field != "id":
        payload[sort_field] = sort_value
    return encode_cursor(payload)


def _parse_cursor_sort(raw: Any) -> Any:
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return raw
    return raw


def apply_cursor_filter(
    stmt: Select,
    *,
    id_column: Any,
    sort_column: Any,
    payload: dict[str, Any],
    descending: bool = True,
) -> Select:
    """
    把「这条之后」翻译成 WHERE。

    降序（最新的在前面，列表接口最常见）：
        created_at < 游标时间
        或 created_at 相同且 id < 游标 id

    升序把 < 换成 > 即可。
    如果游标里没有排序字段，就退化为只比 id（适合按主键列用户）。
    """
    cursor_id = payload["id"]
    sort_key = getattr(sort_column, "key", None) or getattr(sort_column, "name", None)
    raw_sort = payload.get(sort_key) if sort_key else None

    if raw_sort is None or sort_column is id_column:
        cmp = id_column < cursor_id if descending else id_column > cursor_id
        return stmt.where(cmp)

    cursor_sort = _parse_cursor_sort(raw_sort)
    if descending:
        return stmt.where(
            or_(
                sort_column < cursor_sort,
                and_(sort_column == cursor_sort, id_column < cursor_id),
            )
        )
    return stmt.where(
        or_(
            sort_column > cursor_sort,
            and_(sort_column == cursor_sort, id_column > cursor_id),
        )
    )


def apply_offset(stmt: Select, offset: int, limit: int) -> Select:
    """给已有查询加上 OFFSET / LIMIT。调用方负责 order_by。"""
    return stmt.offset(offset).limit(limit)


# ============================================================
# 真正查库的封装
# ============================================================

async def paginate_offset(
    db: AsyncSession,
    stmt: Select,
    *,
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    include_total: bool = True,
    sort_field: str = "created_at",
) -> PaginatedPage:
    """
    offset / limit 分页。

    include_total=False 时跳过 COUNT(*)：
      适合内部批处理，不适合后台表格（表格要总页数）。

    即便走页码，只要还有下一页也会带上 next_cursor。
    这样前端可以第 1 页用 page，之后改成「加载更多」而不用重查。
    """
    total: Optional[int] = None
    if include_total:
        # 去掉 ORDER BY 再 COUNT，避免数据库为了计数还去做排序
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = await db.scalar(count_stmt) or 0

    result = await db.execute(apply_offset(stmt, compute_offset(page, page_size), page_size))
    items = list(result.scalars().unique().all())

    total_for_meta = total if total is not None else 0
    has_next = (
        compute_has_next_offset(page, page_size, total_for_meta)
        if total is not None
        else len(items) == page_size
    )
    return PaginatedPage(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=compute_total_pages(total_for_meta, page_size),
        has_next=has_next,
        has_prev=compute_has_prev_offset(page),
        next_cursor=cursor_from_item(items[-1], sort_field=sort_field) if has_next and items else None,
        mode="offset",
    )


async def paginate_cursor(
    db: AsyncSession,
    stmt: Select,
    *,
    cursor: Optional[str],
    page_size: int = DEFAULT_PAGE_SIZE,
    id_column: Any,
    sort_column: Any = None,
    sort_field: str = "created_at",
    descending: bool = True,
    include_total: bool = False,
) -> PaginatedPage:
    """
    游标分页。

    步骤：
      1. 解码 cursor（第一页 cursor=None，不加 WHERE）
      2. LIMIT page_size + 1，多出来的那条只用来判断 has_next
      3. 用当前页最后一条生成 next_cursor

    include_total 默认 False：信息流不需要「共 N 条」。
    文件列表为了兼容旧字段，调用时会显式传 True。
    """
    sort_column = id_column if sort_column is None else sort_column
    payload = decode_cursor(cursor) if cursor else None
    filtered = (
        apply_cursor_filter(
            stmt,
            id_column=id_column,
            sort_column=sort_column,
            payload=payload,
            descending=descending,
        )
        if payload
        else stmt
    )

    total: Optional[int] = None
    if include_total:
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = await db.scalar(count_stmt) or 0

    result = await db.execute(filtered.limit(page_size + CURSOR_FETCH_EXTRA))
    fetched: Sequence[Any] = list(result.scalars().unique().all())
    has_next = len(fetched) > page_size
    items = list(fetched[:page_size])
    next_cursor = (
        cursor_from_item(items[-1], sort_field=sort_field) if has_next and items else None
    )

    return PaginatedPage(
        items=items,
        page=DEFAULT_PAGE,
        page_size=page_size,
        total=total,
        total_pages=compute_total_pages(total or 0, page_size),
        has_next=has_next,
        has_prev=payload is not None,
        next_cursor=next_cursor,
        mode="cursor",
    )


async def paginate(
    db: AsyncSession,
    stmt: Select,
    *,
    params: ListParams,
    id_column: Any,
    sort_column: Any = None,
    sort_field: str = "created_at",
    descending: bool = True,
    include_total: bool = True,
) -> PaginatedPage:
    """
    路由层最常用的入口：有 cursor 走游标，否则走页码。

    include_total 对两种模式都生效。
    文件 / 用户列表默认 True，保证响应里始终有 total。
    """
    if params.mode == "cursor":
        return await paginate_cursor(
            db,
            stmt,
            cursor=params.cursor,
            page_size=params.page_size,
            id_column=id_column,
            sort_column=sort_column,
            sort_field=sort_field,
            descending=descending,
            include_total=include_total,
        )
    return await paginate_offset(
        db,
        stmt,
        page=params.page,
        page_size=params.page_size,
        include_total=include_total,
        sort_field=sort_field,
    )


# ============================================================
# 学习笔记
# ============================================================
"""
1. 【page 和 offset 的换算】
   用户看到的是页码，数据库看到的是「跳过多少条」。
   offset = (page - 1) * page_size
   limit  = page_size

2. 【为什么深分页慢】
   SELECT ... OFFSET 100000 LIMIT 10
   数据库仍然要扫过前 10 万行再丢掉。数据越多越明显。
   游标变成：WHERE (created_at, id) < (?, ?) LIMIT 10
   走索引就能定位，和已经翻了多少页无关。

3. 【+1 技巧】
   想知道「还有没有下一页」，不要再 COUNT。
   多取 1 条：取到 11 条说明还有，只返回前 10 条。

4. 【总数的取舍】
   后台表格：要 total，用来算「共 12 页」。
   信息流：不要 total，「加载更多」只看 has_next / next_cursor。

5. 【不要把 page 当游标】
   ?page=2 在数据插入/删除后，第 2 页内容会漂。
   游标钉在「上一页最后一条」的主键（和排序键）上，更稳。
"""
