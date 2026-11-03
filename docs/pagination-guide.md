# 分页学习指南

> 中文讲解为主，关键术语保留中英对照，方便对照官方文档和面试表达。

配套代码：`core/pagination.py`  
接到的真实接口：`GET /api/v1/files/list`、`GET /api/v1/users`  
配套测试：`tests/test_pagination.py`、`tests/test_api_pagination.py`

---

## 1. 为什么列表必须分页？

一次把几千条记录全部返回会同时打到三头：

- 数据库：扫全表、占连接
- 网络：响应体巨大
- 前端：表格 / 列表渲染卡顿

分页就是「每次只要一页」。后台表格用页码，信息流用「加载更多」。

---

## 2. 两种分页

| | 页码分页 offset / limit | 游标分页 cursor / keyset |
|--|--------------------------|---------------------------|
| 用户看到的 | 第 1 / 2 / 3 页 | 下一页按钮、无限滚动 |
| SQL | `OFFSET 20 LIMIT 10` | `WHERE (created_at, id) < (?, ?) LIMIT 10` |
| 能不能跳页 | 能 | 一般不能 |
| 翻到很后面 | OFFSET 越大越慢 | 几乎一样快 |
| 插入/删除时 | 可能漏行或重复 | 相对稳定 |
| 要不要总数 | 通常要 `COUNT(*)` | 通常只要 `has_next` |

记忆口诀：

- **后台表格、要跳页、要「共 N 条」**：offset
- **信息流、加载更多、数据还在涨**：cursor

本项目两种都实现了，由同一个 `get_list_params` 切换：

- 不传 `cursor` → offset（`page` + `page_size`）
- 传了 `cursor` → cursor（忽略 `page`）

---

## 3. 页码怎么换算

用户说「第 3 页，每页 10 条」，数据库要的是：

```text
offset = (page - 1) * page_size   # 20
limit  = page_size                # 10
```

空列表的总页数是 **0**，不是 1。  
页码超出最后一页：返回空数组，不要 404（用户改筛选项时很常见）。

`page < 1` 或 `page_size` 超范围由 FastAPI `Query(ge=1, le=100)` 拦住，走统一的 `PARAMS_INVALID`。

---

## 4. 游标怎么做

游标不是「假装成页码的 page=2」，而是「上一页最后一条的位置」。

本项目约定：

```text
payload = {"id": 12, "created_at": "2024-01-01T12:00:00+00:00"}
cursor  = urlsafe_b64(json)     # 去掉末尾 =
```

本仓库的文件 / 用户列表按 **自增 id 降序**，游标通常只有 `{"id": 12}`。

如果按 `created_at` 排序，游标就要带两个字段，否则同一秒插入的两行可能漏掉。  
教学库用 SQLite 时不要这么做：DateTime 是字符串，isoformat 和驱动绑定格式对不齐，`<` / `=` 会整页重复。生产环境请用 PostgreSQL 的 `timestamptz`。

判断还有没有下一页，用 **+1 技巧**：`LIMIT page_size + 1`。  
多取到的那一条只用来设 `has_next`，不返回给前端。

无效游标（乱码、缺 id、不是 JSON）返回业务错误码 `40103 INVALID_CURSOR`，不是 500。

---

## 5. 总数 COUNT(*) 的取舍

| 场景 | 要不要 COUNT |
|------|----------------|
| 后台用户表、文件管理 | 要。表格要「共 12 页」 |
| 朋友圈、通知、动态 | 不要。只要 `has_next` |
| 百万行大表 | 慎重。COUNT 可能比列表还慢 |

助手里 `include_total` 控制这件事。  
文件列表为了兼容旧客户端，**两种模式都还算 total**（`data.files` / `data.total` 保持原样）。

---

## 6. 本仓库接到了哪些接口

| 方法 | 路径 | 列表字段 | 说明 |
|------|------|----------|------|
| GET | `/api/v1/files/list` | `files` | 旧字段全部保留，新增 `has_next` / `next_cursor` / `mode` |
| GET | `/api/v1/users` | `items` | 新接口，走 `success_with_page` |
| GET | `/api/v1/files/shares` | `shares` | 仍用 page / page_size，内部改走 `apply_offset` |
| GET | `/api/v1/files/audit` | `logs` | 同上 |

文件列表响应（默认，不传 cursor）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "files": [],
    "total": 0,
    "page": 1,
    "page_size": 10,
    "total_pages": 0,
    "has_next": false,
    "has_prev": false,
    "next_cursor": null,
    "mode": "offset"
  }
}
```

**形状变化**：只新增字段，旧客户端继续读 `files` / `total` 即可。

```text
GET /api/v1/files/list?page=1&page_size=10
GET /api/v1/files/list?page_size=2&cursor=<上一页的 next_cursor>
GET /api/v1/users?page=1&page_size=10
```

offset 首页如果还有下一页，也会带上 `next_cursor`。  
前端可以第 1 页用页码，之后改成「加载更多」。

---

## 7. 查询优化（点到为止）

本模块不做成完整 Query Builder，只记住四条就够用：

1. **深分页**不要靠巨大 `OFFSET`，改游标。
2. **索引**要覆盖过滤 + 排序。文件列表常见组合是 `(owner_id, created_at, id)`。
3. **N+1**：循环里不要再查关联。分享列表已经用 `selectinload(FileShare.file)`。
4. **少取字段**：`select(User)` 对小表没问题；真要减载荷再用 `load_only`，并保证序列化字段还在。

---

## 8. 前端怎么接

页码表格（Element Plus）：

```javascript
const { data } = await axios.get('/api/v1/files/list', {
  params: { page: 1, page_size: 10 },
});
// data.files / data.total / data.page
```

加载更多：

```javascript
let cursor = null;
const loadMore = async () => {
  const { data } = await axios.get('/api/v1/files/list', {
    params: { page_size: 10, cursor },
  });
  items.push(...data.files);
  cursor = data.next_cursor;
  if (!data.has_next) {
    // 没有更多了
  }
};
```

---

## 9. 怎么测

```bash
pytest tests/test_pagination.py tests/test_api_pagination.py
```

覆盖：

- 页码换算、空列表、超出最后一页
- 无效游标（`40103`）
- `page=0` 被校验拦住
- 文件列表旧字段仍然在
- 用 `next_cursor` 一页页走完

---

## 10. 常见问题

**Q: 为什么文件列表不改成 `items`？**  
A: 旧测试和旧客户端已经在用 `data.files`。教学项目也要练习「增量加字段，不随便改名字」。

**Q: 游标能往回翻吗？**  
A: 可以再做 `prev_cursor`（把比较符反过来）。本模块先把下一页做稳。

**Q: 游标会不会泄露自增 id？**  
A: Base64 不是加密，只能防瞎改。生产环境若不能暴露内部 id，换成 UUID 排序键。

**Q: SQLite 和 PostgreSQL 写法一样吗？**  
A: 助手用 `OR / AND` 比较，不依赖 `tuple_()`，两种库都能用。
