# API 编码规范

## 文件结构与命名

### 文件命名规范
```python
# ✅ 正确示例
app/api/chat_model.py
app/api/user_auth.py
app/api/file_upload.py

# ❌ 错误示例
app/api/ChatModel.py  # 大写字母
app/api/userAuth.py   # 驼峰命名
app/api/user-auth.py  # 连字符
```

### 文件头格式
每个Python文件必须包含标准文件头：
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author   : XXX
# @Time     : 2026/1/6 09:58
# @File     : filename.py
# @Desc     : 文件功能描述
```

---

## 代码格式规范

### 1. 缩进与空格
- 使用4个空格缩进，不使用Tab
- 行长度不超过120个字符
- 运算符两侧加空格：`a + b`, `x == y`

### 2. 函数与类间隔
```python
# 函数/类之间空2行
def function_one():
    pass


def function_two():
    pass


# 方法之间空1行
class ExampleClass:
    def method_one(self):
        pass

    def method_two(self):
        pass
```

---

## 导入规范

### 导入顺序（必须按顺序）
```python
# 1. 标准库导入
import re
import json
from datetime import datetime
from typing import Any

# 2. 第三方库导入
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# 3. 本地应用导入
from app.db.session import get_db
from app.libs.logger import logger
from app.libs.token_auth import get_current_user
from app.models.user import User
```

### 导入最佳实践
- 避免使用 `from fastapi import *`
- 优先使用绝对导入
- 避免循环导入

---

## 路由设计

### 1. URL设计原则
```python
router = APIRouter(prefix="/api/v1/user", tags=["User"])

# ✅ 正确示例
@router.get("/get_user_list")               # 列表查询
@router.get("/get_user_detail/{user_id}")    # 单个资源
@router.post("/create_user")                 # 创建资源
@router.post("/update_user")                 # 更新资源

# ❌ 错误示例
@router.get("/getUsers")                     # URL中避免驼峰
@router.get("/UserInfo")                     # 避免大小写混用
@router.get("/get-user-info")               # 避免连字符
```

### 2. HTTP方法使用规范
- 统一使用两种 HTTP 方法：`GET` 与 `POST`
- 路径前缀统一：`/api/v1/{module}`
- 路径使用动词+对象风格，且与函数名一致
- 推荐命名：
  - `GET /api/v1/user/get_user_list`
  - `GET /api/v1/user/get_user_detail/{user_id}`
  - `POST /api/v1/user/create_user`
  - `POST /api/v1/user/update_user`
  - `POST /api/v1/user/delete_user`
  - `POST /api/v1/user/change_user_status`
  
### GET：用于所有数据查询
- 获取列表数据（支持分页、搜索、过滤）
- 获取单个资源详情
- 获取关联资源数据

### POST：用于所有数据变更
- 创建新资源
- 更新现有资源
- 删除资源（软删除）
- 状态变更操作
- 复杂查询操作


### 3. 路由前缀
- 所有API路由必须以 `/api` 开头
- 版本号可选：`/api/v1/users`

---

## 认证与权限

### 1. 依赖注入认证
```python
from app.libs.token_auth import get_current_user

@router.get("/get_user_info")
async def get_user_info(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """需要认证的接口"""
    user_id = current_user.get("uid")
    return success_response({"user_id": user_id})
```

### 2. 权限控制
```python
from app.libs.scope import is_in_scope
from fastapi import HTTPException, status

def check_permission(scope_name: str, endpoint: str) -> None:
    """检查接口访问权限"""
    if not is_in_scope(scope_name, endpoint):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限访问")
```

---

## 参数验证

### 1. 验证器创建

**验证器定义位置**：直接在API接口文件中定义

**继承基类**：所有验证器必须继承 Pydantic `BaseModel`

**创建方式**：在API接口文件顶部定义验证器类

```python
from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.libs.logger import logger
from app.libs.token_auth import get_current_user


# 验证器定义区域
class ChatModelForm(BaseModel):
    """聊天模型参数验证器"""
    prompt: str = Field(min_length=1, max_length=6000, description="提示词不能为空")
    model_name: str | None = Field(
        default=None, min_length=1, max_length=50, description="模型名称"
    )

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, value: str | None) -> str | None:
        """自定义验证：检查模型名称"""
        if value is not None:
            supported_models = ["deepseek", "gemini_pro", "doubao"]
            if value not in supported_models:
                raise ValueError(f"不支持的模型: {value}")
        return value


# API接口定义区域
router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


@router.post("/chat_model")
async def api_chat_model(
    payload: ChatModelForm,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """聊天模型接口"""
    # 接口实现...
```

### 2. 验证器使用

**Pydantic 自动验证**：参数通过函数签名声明，FastAPI 自动完成校验，无需手动调用 `validate()`。

```python
@router.post("/chat_model")
async def api_chat_model(
    payload: ChatModelForm,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """聊天模型接口"""
    try:
        # Pydantic 已自动验证，直接获取字段值
        prompt = payload.prompt
        model_name = payload.model_name or "deepseek"

        # 业务逻辑处理
        logger.info(f"调用模型: {model_name}, 提示词: {prompt[:20]}...")
        # 执行业务逻辑...

        return success_response(data=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"接口错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务内部错误",
        )
```

### 3. 常用验证规则

| 验证方式 | 用途 | 示例 |
|--------|------|------|
| `Field(min_length=, max_length=)` | 字符串长度验证 | `Field(min_length=1, max_length=100)` |
| `Field(ge=, le=)` | 数值范围验证 | `Field(ge=1, le=100)` |
| `Field(gt=0)` | 必须大于零 | `user_id: int = Field(gt=0)` |
| `EmailStr` | 邮箱格式验证 | `email: EmailStr` |
| `field_validator` | 自定义验证 | `@field_validator("username")` |
| `Field(pattern=...)` | 正则验证 | `Field(pattern=r"^[a-zA-Z0-9]+$")` |

### 4. 自定义验证方法示例

```python
from enum import IntEnum

from pydantic import BaseModel, EmailStr, Field, field_validator


class MemberTypeEnum(IntEnum):
    NORMAL = 1
    VIP = 2
    SVIP = 3


class MemberForm(BaseModel):
    """会员参数验证器"""
    account: str = Field(min_length=5, max_length=32, description="账号不允许为空")
    type: int = Field(description="类型不能为空")

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: int) -> int:
        """自定义验证：验证会员类型枚举"""
        try:
            MemberTypeEnum(value)
        except ValueError:
            raise ValueError(f"无效的会员类型: {value}")
        return value


class CreateUserForm(BaseModel):
    """创建用户验证器"""
    username: str = Field(min_length=3, max_length=20, description="用户名不能为空")
    email: EmailStr
    password: str = Field(min_length=6, max_length=32, description="密码不能为空")

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        """自定义验证：检查用户名格式"""
        import re
        if not re.match(r"^[a-zA-Z0-9_]+$", value):
            raise ValueError("用户名只能包含字母、数字和下划线")
        return value
```

### 5. 文件组织结构

**推荐的API文件结构**：

```python
# ========== 第一部分：导入区域 ==========
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.libs.logger import logger
from app.libs.token_auth import get_current_user
from app.models.user import User

# ========== 第二部分：验证器定义区域 ==========
class CreateUserForm(BaseModel):
    """创建用户验证器"""
    username: str = Field(min_length=3, max_length=20)
    email: EmailStr
    password: str = Field(min_length=6, max_length=32)

# ========== 第三部分：响应模型与辅助函数区域 ==========
class UserRead(BaseModel):
    """用户响应模型"""
    id: int
    username: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)

def success_response(data: Any = None, message: str = "成功", code: int = 200) -> dict[str, Any]:
    """统一成功响应"""
    return {"code": code, "message": message, "data": data}

# ========== 第四部分：路由与接口区域 ==========
router = APIRouter(prefix="/api/v1/user", tags=["User"])

@router.get("/get_user_list")
async def get_user_list(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """获取用户列表"""
    # 实现代码...

@router.post("/create_user")
async def create_user(
    payload: CreateUserForm,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """创建新用户"""
    # 实现代码...
```

---

## 错误处理

### 1. 异常捕获层次

**三层异常处理结构**：

```python
@router.post("/chat_model")
async def api_chat_model(
    payload: ChatModelForm,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    try:
        # 执行业务逻辑
        result = await process_business_logic(payload, db)

        return success_response(data=result)

    # 第一层：FastAPI HTTP 异常（参数错误、资源不存在等）
    except HTTPException:
        raise

    # 第二层：业务逻辑异常
    except BusinessException as e:
        logger.warning(f"业务异常: {str(e)}")
        raise HTTPException(status_code=e.code, detail=e.message)

    # 第三层：系统异常
    except Exception as e:
        logger.error(f"系统错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务内部错误",
        )
```

### 2. HTTP状态码使用规范

| 状态码 | 场景 | 返回方式 |
|--------|------|---------|
| 200 | 请求成功 | `return success_response(data)` |
| 201 | 创建成功 | `return success_response(data, "创建成功", 201)` |
| 400 | 参数错误 | `raise HTTPException(status_code=400, detail="参数错误")` |
| 401 | 未认证 | `raise HTTPException(status_code=401, detail="未认证")` |
| 403 | 权限不足 | `raise HTTPException(status_code=403, detail="权限不足")` |
| 404 | 资源不存在 | `raise HTTPException(status_code=404, detail="资源不存在")` |
| 500 | 服务器错误 | `raise HTTPException(status_code=500, detail="服务内部错误")` |

### 3. 自定义异常类

```python
# app/libs/error_code.py
from fastapi import HTTPException, status


class APIException(HTTPException):
    """API异常基类"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "服务器异常"

    def __init__(self, detail: str | None = None, status_code: int | None = None):
        super().__init__(
            status_code=status_code or self.__class__.status_code,
            detail=detail or self.__class__.detail,
        )


class ParameterException(APIException):
    """参数异常"""
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "参数错误"


class AuthFailed(APIException):
    """认证失败"""
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "认证失败"


class Forbidden(APIException):
    """权限不足"""
    status_code = status.HTTP_403_FORBIDDEN
    detail = "权限不足"


class NotFound(APIException):
    """资源不存在"""
    status_code = status.HTTP_404_NOT_FOUND
    detail = "资源不存在"
```

---

## 响应格式

### 1. 成功响应标准格式

**单条数据响应**：
```python
return success_response({
    "content": "你好！有什么我可以帮助你的吗？",
    "model_name": "deepseek",
    "finish_reason": "stop",
    "input_tokens": 10,
    "output_tokens": 15,
})
```

**列表数据响应**：
```python
return success_response({
    "total": 100,
    "page": 1,
    "per_page": 20,
    "items": [
        {"id": 1, "name": "item1"},
        {"id": 2, "name": "item2"},
    ],
})
```

**无返回数据响应**：
```python
return success_response(None, "操作成功")
```

### 2. 错误响应标准格式

```python
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="参数验证失败：提示词不能为空",
)
```

### 3. 响应格式规范要点

- **必须字段**：`code`、`message`、`data`
- **code 字段**：与 HTTP 状态码保持一致
- **message 字段**：清晰描述操作结果或错误原因
- **data 字段**：成功时返回数据对象，失败时返回 `None`

---

## 日志记录

### 1. 日志级别使用规范

```python
from app.libs.logger import logger

# INFO - 重要业务操作
logger.info("[API] 调用模型: %s, 用户: %s, 提示词长度: %s", model_name, user_id, len(prompt))

# WARNING - 警告信息（可预期的异常）
logger.warning("[Validation] 参数验证失败: %s, 用户: %s", error_msg, user_id)

# ERROR - 错误信息（系统异常）
logger.error("[System] 接口异常: %s", str(e), exc_info=True)
```

### 2. 日志格式规范

**推荐格式**：`[模块] 操作描述: 详细信息 - 上下文信息`

```python
# ✅ 正确示例
logger.info("[API] GET /api/v1/user/get_user_list - 用户: %s - 耗时: %sms", user_id, elapsed)
logger.error("[DB] 数据库查询失败 - SQL: %s - 错误: %s", sql, error)
logger.warning("[Auth] Token验证失败 - Token: %s... - IP: %s", token[:10], client_ip)

# ❌ 错误示例
logger.info("error")              # 信息不明确
logger.error(user_id)             # 缺少上下文
logger.warning("失败")            # 没有详细信息
```

### 3. 日志记录最佳实践

- **关键操作必记**：API调用、数据库操作、外部服务调用
- **敏感信息脱敏**：密码、Token完整内容、身份证号等
- **包含上下文**：用户ID、请求路径、IP地址等
- **使用 exc_info**：记录异常堆栈时添加 `exc_info=True`

---

## 文档注释

### 1. 接口文档标准格式

使用 `@@@` 包裹的 Markdown 格式文档：

```python
@router.post("/chat_model")
async def api_chat_model(
    payload: ChatModelForm,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """
    聊天模型接口
    @@@
    #### 接口说明
    调用指定的聊天模型进行对话，支持多种模型切换。

    #### 认证方式
    - 需要在请求头中携带 Token
    - Header: `Authorization: Bearer <token>`

    #### 请求参数

    | 参数 | 是否必填 | 类型 | 说明 | 示例 |
    |------|---------|------|------|------|
    | prompt | 是 | String | 用户输入的提示词 | "你好" |
    | model_name | 否 | String | 模型名称，默认为 deepseek | "deepseek" |

    #### 返回数据

    ```json
    {
        "code": 200,
        "message": "成功",
        "data": {
            "content": "你好！有什么我可以帮助你的吗？",
            "model_name": "deepseek",
            "finish_reason": "stop",
            "input_tokens": 10,
            "output_tokens": 15
        }
    }
    ```

    #### 备注
    - 请求方式：POST Raw JSON
    - 接口地址：http://127.0.0.1:8000/api/v1/chat/chat_model
    - 超时时间：30秒
    @@@
    """
    # 接口实现代码...
```

### 2. 函数注释规范

```python
def generate_auth_token(uid: int, scope: str | None = None, expiration: int = 7200) -> str:
    """生成认证令牌

    为用户生成用于API认证的JWT令牌。

    :param uid: 用户ID
    :type uid: int
    :param scope: 权限范围，默认为None表示继承用户权限
    :type scope: str, optional
    :param expiration: 过期时间（秒），默认7200秒（2小时）
    :type expiration: int, optional
    :return: 加密后的token字符串
    :rtype: str
    :raises ValueError: 如果uid无效或为空

    示例:
        >>> token = generate_auth_token(123, scope='user', expiration=3600)
        >>> print(token)
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    """
    pass
```

---

## 最佳实践

### 1. 接口设计原则

#### SOLID 原则应用

**单一职责（Single Responsibility）**：
```python
# ✅ 正确：每个接口只负责一个功能
@router.get("/get_user_list")
async def get_user_list():
    """获取用户列表"""
    pass

@router.post("/create_user")
async def create_user():
    """创建新用户"""
    pass

# ❌ 错误：一个接口承担多个职责
@router.api_route("/users", methods=["GET", "POST", "DELETE"])
async def handle_users():
    """处理所有用户操作"""
    pass
```

**接口隔离（Interface Segregation）**：
```python
# ✅ 正确：精确的接口定义
@router.get("/get_user_profile")
async def get_user_profile():
    """获取用户资料"""
    pass

@router.get("/get_user_settings")
async def get_user_settings():
    """获取用户设置"""
    pass

# ❌ 错误：返回过多不必要的数据
@router.get("/get_user_all_data")
async def get_user_all_data():
    """返回用户所有数据（包括不需要的）"""
    pass
```

### 2. 响应模型与ORM转换

**使用 `ConfigDict(from_attributes=True)` 支持 ORM 对象直接转换**：
```python
from pydantic import BaseModel, ConfigDict

class UserRead(BaseModel):
    """用户响应模型"""
    id: int
    username: str
    email: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


@router.get("/get_user_detail/{user_id}")
async def get_user_detail(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """获取用户详情"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return success_response(UserRead.model_validate(user).model_dump())
```

### 3. 性能优化

**使用分页**：
```python
@router.get("/get_user_list")
async def get_user_list(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: str = Query("", description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """获取用户列表（分页）"""
    stmt = select(User)
    if keyword.strip():
        stmt = stmt.where(User.username.like(f"%{keyword.strip()}%"))

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(total_stmt)
    total = total_result.scalar_one()

    result = await db.execute(stmt.offset((page - 1) * per_page).limit(per_page))
    users = result.scalars().all()

    return success_response({
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [UserRead.model_validate(u).model_dump() for u in users],
    })
```

**避免 N+1 查询**：
```python
from sqlalchemy.orm import selectinload

# ✅ 正确：使用 selectinload
@router.get("/get_article_list")
async def get_article_list(db: AsyncSession = Depends(get_db)):
    """获取文章列表（包含作者信息）"""
    stmt = select(Article).options(selectinload(Article.author))
    result = await db.execute(stmt)
    articles = result.scalars().all()
    return success_response([a.to_dict() for a in articles])

# ❌ 错误：N+1 查询
@router.get("/get_article_list_bad")
async def get_article_list_bad(db: AsyncSession = Depends(get_db)):
    """获取文章列表（N+1问题）"""
    result = await db.execute(select(Article))
    articles = result.scalars().all()
    # 每次循环都会触发一次数据库查询
    return success_response([
        {**a.to_dict(), "author": a.author.to_dict()}
        for a in articles
    ])
```

### 4. 安全性

**SQL注入防护**：
```python
# ✅ 正确：使用 SQLAlchemy ORM 参数化查询
@router.get("/search_users")
async def search_users(
    keyword: str = Query("", description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.name.like(f"%{keyword}%"))
    result = await db.execute(stmt)
    users = result.scalars().all()
    return success_response([u.to_dict() for u in users])

# ❌ 错误：直接拼接SQL
@router.get("/search_users_unsafe")
async def search_users_unsafe(
    keyword: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    sql = f"SELECT * FROM users WHERE name LIKE '%{keyword}%'"
    result = await db.execute(text(sql))
    users = result.fetchall()
    return success_response(users)
```

---

## 规范检查清单

在提交代码前，请对照以下清单进行检查：

### 基础规范
- [ ] 文件头信息完整（Shebang、编码、作者、描述）
- [ ] 导入语句按标准库、第三方库、本地模块分组排序
- [ ] 代码格式符合 PEP 8 规范
- [ ] 函数和类之间有适当的空行

### 接口设计
- [ ] URL命名符合规范（小写、下划线、动词+对象风格）
- [ ] HTTP方法使用正确（GET查询、POST变更）
- [ ] 所有API路由以 `/api/v1` 开头，通过 `APIRouter(prefix=...)` 配置

### 参数验证
- [ ] 在API文件顶部创建了对应的 Pydantic 验证器（继承 `BaseModel`）
- [ ] 验证器定义在导入区域之后、路由定义之前
- [ ] 所有必填参数使用了 `Field(...)` 约束
- [ ] GET 查询参数使用 `Query(...)` 声明
- [ ] POST 请求体使用 Pydantic 模型声明（`payload: XxxForm`）
- [ ] 验证错误信息清晰明确
- [ ] 文件结构清晰：导入→验证器→响应模型→辅助函数→路由

### 认证与权限
- [ ] 需要认证的接口添加了 `Depends(get_current_user)` 依赖
- [ ] 权限检查逻辑正确实现

### 错误处理
- [ ] 实现了三层异常捕获（HTTPException、BusinessException、Exception）
- [ ] HTTP状态码使用正确（200/400/401/403/404/500）
- [ ] 错误信息对用户友好且不泄露敏感信息
- [ ] 异常统一通过 `raise HTTPException(...)` 抛出

### 响应格式
- [ ] 所有响应包含 `code`、`message`、`data` 三个字段
- [ ] 成功响应 code 为 200
- [ ] 错误响应 code 与 HTTP 状态码一致

### 日志记录
- [ ] 关键操作有日志记录（API调用、数据库操作、异常）
- [ ] 日志包含足够的上下文信息（用户ID、请求路径等）
- [ ] 日志级别使用正确（INFO/WARNING/ERROR）
- [ ] 敏感信息已脱敏处理

### 文档注释
- [ ] 接口有完整的文档注释（使用 `@@@` 格式）
- [ ] 文档包含：接口说明、参数表格、返回示例、错误码说明
- [ ] 函数有清晰的docstring

### 性能与安全
- [ ] 使用了参数化查询，避免SQL注入
- [ ] 列表接口实现了分页

---

## 注意
- 不要生成单独的接口文档及API 使用指南
