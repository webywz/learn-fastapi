# Pydantic 方法和用法完全手册

## 📚 目录
1. [Field 验证参数](#field-验证参数)
2. [数据类型](#数据类型)
3. [模型配置](#模型配置)
4. [数据转换方法](#数据转换方法)
5. [自定义验证器](#自定义验证器)
6. [实用示例](#实用示例)

---

## Field 验证参数

### 基础参数

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    # ===== 必填 vs 可选 =====
    username: str = Field(...)              # 必填（... 表示必须提供）
    nickname: Optional[str] = Field(None)   # 可选（默认 None）
    age: int = Field(default=18)            # 可选（默认 18）

    # ===== 字符串长度验证 =====
    password: str = Field(
        ...,
        min_length=6,      # 最小长度
        max_length=20      # 最大长度
    )
    # 用户输入 "12345" → ❌ 验证失败（太短）
    # 用户输入 "123456" → ✅ 通过

    # ===== 数字范围验证 =====
    age: int = Field(
        ...,
        ge=0,    # greater than or equal（大于等于）
        le=150   # less than or equal（小于等于）
    )
    # 用户输入 -1 → ❌ 验证失败
    # 用户输入 25 → ✅ 通过

    score: float = Field(
        ...,
        gt=0,    # greater than（严格大于）
        lt=100   # less than（严格小于）
    )
    # 用户输入 0 → ❌ 验证失败（需要 > 0）
    # 用户输入 50.5 → ✅ 通过

    # ===== 正则表达式验证 =====
    phone: str = Field(
        ...,
        pattern=r"^1[3-9]\d{9}$"  # 中国手机号格式
    )
    # 用户输入 "12345678901" → ❌ 验证失败
    # 用户输入 "13812345678" → ✅ 通过

    # ===== 列表验证 =====
    tags: list[str] = Field(
        default=[],
        min_items=0,      # 最少元素数量
        max_items=10      # 最多元素数量
    )

    # ===== 文档相关 =====
    email: str = Field(
        ...,
        description="用户邮箱",           # 字段说明（显示在 API 文档）
        examples=["alice@example.com"]  # 示例值
    )
```

---

### Field 参数完整列表

| 参数 | 类型 | 作用 | 示例 |
|------|------|------|------|
| `default` | Any | 默认值 | `Field(default="guest")` |
| `default_factory` | Callable | 默认值工厂函数 | `Field(default_factory=list)` |
| `...` | - | 必填标记 | `Field(...)` |
| `min_length` | int | 最小长度 | `Field(min_length=3)` |
| `max_length` | int | 最大长度 | `Field(max_length=50)` |
| `ge` | float | 大于等于 | `Field(ge=0)` |
| `gt` | float | 严格大于 | `Field(gt=0)` |
| `le` | float | 小于等于 | `Field(le=100)` |
| `lt` | float | 严格小于 | `Field(lt=100)` |
| `pattern` | str | 正则表达式 | `Field(pattern=r"^\d{6}$")` |
| `min_items` | int | 列表最少元素 | `Field(min_items=1)` |
| `max_items` | int | 列表最多元素 | `Field(max_items=10)` |
| `description` | str | 字段说明 | `Field(description="用户名")` |
| `examples` | list | 示例值 | `Field(examples=["alice"])` |
| `alias` | str | 别名 | `Field(alias="userName")` |

---

## 数据类型

### 基础类型

```python
from pydantic import BaseModel
from typing import Optional

class Example(BaseModel):
    # ===== 字符串 =====
    name: str                    # 字符串
    # 输入: "alice" → ✅
    # 输入: 123 → ❌

    # ===== 整数 =====
    age: int                     # 整数
    # 输入: 25 → ✅
    # 输入: "25" → ✅（自动转换）
    # 输入: 25.5 → ❌

    # ===== 浮点数 =====
    price: float                 # 浮点数
    # 输入: 9.99 → ✅
    # 输入: 10 → ✅（自动转为 10.0）
    # 输入: "9.99" → ✅（自动转换）

    # ===== 布尔值 =====
    is_active: bool              # 布尔值
    # 输入: true → ✅
    # 输入: "true" → ✅（自动转换）
    # 输入: 1 → ✅（转为 True）
    # 输入: 0 → ✅（转为 False）

    # ===== 可选类型 =====
    nickname: Optional[str]      # 可以是 str 或 None
    # 输入: "Alice" → ✅
    # 输入: null → ✅
    # 不传: ✅（默认 None）
```

---

### 特殊类型

```python
from pydantic import BaseModel, EmailStr, HttpUrl, constr, conint, conlist
from datetime import datetime, date
from typing import Optional

class SpecialTypes(BaseModel):
    # ===== EmailStr - 邮箱验证 =====
    email: EmailStr
    # 输入: "alice@example.com" → ✅
    # 输入: "invalid-email" → ❌（自动验证邮箱格式）

    # ===== HttpUrl - URL 验证 =====
    website: HttpUrl
    # 输入: "https://example.com" → ✅
    # 输入: "example.com" → ❌（必须包含协议）

    # ===== datetime - 日期时间 =====
    created_at: datetime
    # 输入: "2024-01-01T12:00:00" → ✅（自动转换）
    # 输入: "2024-01-01 12:00:00" → ✅
    # 返回: datetime 对象

    # ===== date - 日期 =====
    birth_date: date
    # 输入: "2000-01-01" → ✅
    # 返回: date 对象

    # ===== constr - 受限字符串 =====
    username: constr(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    # 等同于:
    # username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")

    # ===== conint - 受限整数 =====
    age: conint(ge=0, le=150)
    # 等同于:
    # age: int = Field(ge=0, le=150)

    # ===== conlist - 受限列表 =====
    tags: conlist(str, min_items=1, max_items=5)
    # 等同于:
    # tags: list[str] = Field(min_items=1, max_items=5)
```

---

### 复杂类型

```python
from pydantic import BaseModel
from typing import List, Dict, Optional, Union

class ComplexTypes(BaseModel):
    # ===== 列表 =====
    tags: List[str]              # 字符串列表
    # 输入: ["python", "fastapi"] → ✅
    # 输入: ["python", 123] → ❌（元素类型不对）

    numbers: List[int]           # 整数列表
    # 输入: [1, 2, 3] → ✅

    # ===== 字典 =====
    metadata: Dict[str, str]     # 键值都是字符串
    # 输入: {"key": "value"} → ✅

    settings: Dict[str, int]     # 键是字符串，值是整数
    # 输入: {"timeout": 30} → ✅

    # ===== Union - 多种类型之一 =====
    value: Union[int, str]       # 可以是 int 或 str
    # 输入: 123 → ✅
    # 输入: "abc" → ✅
    # 输入: 1.5 → ❌

    # ===== 嵌套模型 =====
    address: Optional["Address"] # 嵌套的 Address 模型

class Address(BaseModel):
    city: str
    street: str
    zipcode: str

# 使用示例：
data = {
    "tags": ["python"],
    "metadata": {"version": "1.0"},
    "value": 123,
    "address": {
        "city": "北京",
        "street": "中关村大街",
        "zipcode": "100000"
    }
}
obj = ComplexTypes(**data)
```

---

## 模型配置

### `model_config` 配置选项

```python
from pydantic import BaseModel, ConfigDict

class User(BaseModel):
    id: int
    username: str

    # Pydantic V2 的配置方式
    model_config = ConfigDict(
        # ===== 1. from_attributes - 从 ORM 对象创建 =====
        from_attributes=True,  # 允许 User.from_orm(db_user)

        # ===== 2. str_strip_whitespace - 自动去除空格 =====
        str_strip_whitespace=True,
        # 输入: "  alice  " → 转换为 "alice"

        # ===== 3. validate_assignment - 赋值时验证 =====
        validate_assignment=True,
        # user.age = -1  → 抛出验证错误（如果 age 有 ge=0 限制）

        # ===== 4. frozen - 不可变（冻结） =====
        frozen=True,
        # user.username = "new"  → 抛出错误（对象不可修改）

        # ===== 5. use_enum_values - 使用枚举值 =====
        use_enum_values=True,
        # 枚举类型直接返回值而不是枚举对象

        # ===== 6. json_schema_extra - 添加示例 =====
        json_schema_extra={
            "example": {
                "id": 1,
                "username": "alice"
            }
        }
    )
```

---

### 常用配置场景

```python
# ===== 场景1: API 响应模型 =====
class UserResponse(BaseModel):
    id: int
    username: str
    email: str

    model_config = ConfigDict(
        from_attributes=True,  # 从 ORM 转换
        json_schema_extra={    # API 文档示例
            "example": {
                "id": 1,
                "username": "alice",
                "email": "alice@example.com"
            }
        }
    )

# 使用：
db_user = User(id=1, username="alice", email="alice@example.com")
response = UserResponse.from_orm(db_user)


# ===== 场景2: 请求模型 =====
class UserCreate(BaseModel):
    username: str = Field(min_length=3)
    email: EmailStr
    password: str = Field(min_length=6)

    model_config = ConfigDict(
        str_strip_whitespace=True,  # 自动去除首尾空格
    )

# 用户输入: "  alice  " → 自动转为 "alice"


# ===== 场景3: 配置对象 =====
class AppConfig(BaseModel):
    app_name: str
    debug: bool
    port: int

    model_config = ConfigDict(
        frozen=True,  # 配置不可修改
    )

config = AppConfig(app_name="MyApp", debug=True, port=8000)
# config.port = 9000  # ❌ 错误！frozen=True 不允许修改
```

---

## 数据转换方法

### `.dict()` / `.model_dump()` - 转为字典

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    username: str
    email: str
    password: str

user = User(id=1, username="alice", email="alice@example.com", password="secret")

# Pydantic V2 推荐用法
data = user.model_dump()
# {'id': 1, 'username': 'alice', 'email': 'alice@example.com', 'password': 'secret'}

# 排除某些字段
data = user.model_dump(exclude={"password"})
# {'id': 1, 'username': 'alice', 'email': 'alice@example.com'}

# 只包含某些字段
data = user.model_dump(include={"id", "username"})
# {'id': 1, 'username': 'alice'}

# 排除未设置的字段
data = user.model_dump(exclude_unset=True)

# 排除 None 值
data = user.model_dump(exclude_none=True)
```

---

### `.json()` / `.model_dump_json()` - 转为 JSON 字符串

```python
user = User(id=1, username="alice", email="alice@example.com")

# 转为 JSON 字符串
json_str = user.model_dump_json()
# '{"id":1,"username":"alice","email":"alice@example.com"}'

# 格式化输出
json_str = user.model_dump_json(indent=2)
# {
#   "id": 1,
#   "username": "alice",
#   "email": "alice@example.com"
# }
```

---

### `.parse_obj()` / `.model_validate()` - 从字典创建

```python
# 从字典创建对象
data = {
    "id": 1,
    "username": "alice",
    "email": "alice@example.com"
}

# Pydantic V2
user = User.model_validate(data)

# 或者直接用 **data 解包
user = User(**data)
```

---

### `.from_orm()` - 从 ORM 对象创建

```python
from models.user import User as DBUser  # ORM 模型
from schemas.user import User as UserSchema  # Pydantic 模型

# 从数据库查询
db_user = await get_user_by_id(db, 1)  # DBUser 对象

# 转换为 Pydantic 模型
user_schema = UserSchema.from_orm(db_user)

# 前提：需要配置 from_attributes=True
class UserSchema(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)
```

---

## 自定义验证器

### `@field_validator` - 字段验证器

```python
from pydantic import BaseModel, field_validator

class User(BaseModel):
    username: str
    password: str
    age: int

    # ===== 验证单个字段 =====
    @field_validator('username')
    @classmethod
    def username_must_be_alphanumeric(cls, v: str) -> str:
        """用户名只能包含字母和数字"""
        if not v.isalnum():
            raise ValueError('用户名只能包含字母和数字')
        return v

    # ===== 验证前转换（mode='before'）=====
    @field_validator('username', mode='before')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """去除首尾空格"""
        if isinstance(v, str):
            return v.strip()
        return v

    # ===== 验证多个字段 =====
    @field_validator('username', 'password')
    @classmethod
    def check_not_empty(cls, v: str) -> str:
        """检查不能为空"""
        if not v or not v.strip():
            raise ValueError('不能为空')
        return v

    # ===== 复杂验证逻辑 =====
    @field_validator('age')
    @classmethod
    def check_age(cls, v: int) -> int:
        """检查年龄合法性"""
        if v < 0:
            raise ValueError('年龄不能为负数')
        if v > 150:
            raise ValueError('年龄不能超过150岁')
        return v
```

---

### `@model_validator` - 模型验证器

```python
from pydantic import BaseModel, model_validator

class PasswordChange(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str

    # ===== 验证整个模型 =====
    @model_validator(mode='after')
    def check_passwords_match(self):
        """检查两次密码输入是否一致"""
        if self.new_password != self.confirm_password:
            raise ValueError('两次密码输入不一致')

        if self.old_password == self.new_password:
            raise ValueError('新密码不能与旧密码相同')

        return self

# 使用：
data = {
    "old_password": "old123",
    "new_password": "new456",
    "confirm_password": "new456"
}
password_change = PasswordChange(**data)  # ✅ 验证通过

data_error = {
    "old_password": "old123",
    "new_password": "new456",
    "confirm_password": "different"
}
# PasswordChange(**data_error)  # ❌ 抛出 ValueError: 两次密码输入不一致
```

---

## 实用示例

### 1. 用户注册验证

```python
from pydantic import BaseModel, EmailStr, field_validator, Field
import re

class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    email: EmailStr
    password: str = Field(min_length=8)
    phone: str

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        """用户名只能包含字母、数字和下划线"""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        """密码必须包含大小写字母和数字"""
        if not re.search(r'[A-Z]', v):
            raise ValueError('密码必须包含大写字母')
        if not re.search(r'[a-z]', v):
            raise ValueError('密码必须包含小写字母')
        if not re.search(r'\d', v):
            raise ValueError('密码必须包含数字')
        return v

    @field_validator('phone')
    @classmethod
    def phone_format(cls, v: str) -> str:
        """验证中国手机号"""
        if not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('手机号格式不正确')
        return v
```

---

### 2. 分页参数

```python
from pydantic import BaseModel, Field, field_validator

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)

    @field_validator('page_size')
    @classmethod
    def limit_page_size(cls, v: int) -> int:
        """限制单页最大数量"""
        if v > 100:
            return 100  # 强制限制为100
        return v

# 使用：
params = PaginationParams(page=2, page_size=20)
params = PaginationParams(page=1, page_size=200)  # page_size 会被限制为 100
```

---

### 3. 动态字段

```python
from pydantic import BaseModel, Field
from typing import Optional

class UserUpdate(BaseModel):
    """用户更新 - 所有字段可选"""
    username: Optional[str] = Field(None, min_length=3)
    email: Optional[EmailStr] = None
    age: Optional[int] = Field(None, ge=0, le=150)

# 使用：
# 只更新邮箱
update_data = UserUpdate(email="new@example.com")

# 更新多个字段
update_data = UserUpdate(
    username="newname",
    email="new@example.com",
    age=26
)

# 获取实际设置的字段
set_fields = update_data.model_dump(exclude_unset=True)
# 只包含用户实际提供的字段
```

---

## 常见错误和解决方案

### 错误1: ValidationError

```python
from pydantic import BaseModel, ValidationError

class User(BaseModel):
    username: str
    age: int

try:
    user = User(username="alice", age="not a number")
except ValidationError as e:
    print(e.errors())
    # [
    #   {
    #     'type': 'int_parsing',
    #     'loc': ('age',),
    #     'msg': 'Input should be a valid integer',
    #     'input': 'not a number'
    #   }
    # ]
```

---

### 错误2: 字段名冲突

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    # ❌ 前端字段名是 userName（驼峰），但 Python 惯用 user_name（下划线）
    # 使用 alias 解决
    user_name: str = Field(alias="userName")

# 前端发送：
data = {"userName": "alice"}
user = User(**data)  # ✅ 成功

# 获取值：
print(user.user_name)  # "alice"
```

---

## 方法速查表

| 方法/参数 | 作用 | 示例 |
|-----------|------|------|
| `Field(...)` | 必填字段 | `Field(...)` |
| `Field(default=x)` | 默认值 | `Field(default=0)` |
| `Field(min_length=n)` | 最小长度 | `Field(min_length=3)` |
| `Field(max_length=n)` | 最大长度 | `Field(max_length=50)` |
| `Field(ge=n)` | 大于等于 | `Field(ge=0)` |
| `Field(le=n)` | 小于等于 | `Field(le=100)` |
| `Field(pattern=r"...")` | 正则验证 | `Field(pattern=r"^\d+$")` |
| `EmailStr` | 邮箱类型 | `email: EmailStr` |
| `HttpUrl` | URL类型 | `website: HttpUrl` |
| `model_dump()` | 转字典 | `user.model_dump()` |
| `model_dump_json()` | 转JSON | `user.model_dump_json()` |
| `model_validate()` | 从字典创建 | `User.model_validate(data)` |
| `from_orm()` | 从ORM创建 | `UserSchema.from_orm(db_user)` |
| `@field_validator` | 字段验证器 | 自定义验证逻辑 |
| `@model_validator` | 模型验证器 | 验证多个字段关系 |
