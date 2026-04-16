# 错误码与异常体系规范

## 错误码设计原则

### 格式定义

错误码为 **6 位数字字符串**，结构如下：

```
[MM][NNNN]
 │    └── 具体错误序号（0000 ~ 9999）
 └─────── 模块码（00 ~ 99）
```

- 成功统一使用 `code = 200`，不走错误码体系
- 错误码仅在业务失败时出现，HTTP 状态码与错误码含义对应但**不要求数值相等**
- 错误码在整个系统内全局唯一，禁止跨模块复用

### 模块码段划分

| 模块码 | 模块名称 | 说明 |
|--------|----------|------|
| 00 | 通用 | 参数校验、认证、权限、限流等基础设施错误 |
| 10 | 用户模块 | 用户注册、信息管理、账号状态等 |
| 11 | 认证模块 | 登录、Token、OAuth、验证码等 |
| 12 | 权限模块 | 角色管理、菜单权限、数据权限等 |
| 20 | 内容模块 | 文章、评论、标签等 |
| 21 | 文件模块 | 上传、下载、存储等 |
| 30 | 订单模块 | 订单创建、支付、退款等 |
| 31 | 商品模块 | 商品管理、库存等 |
| 40~89 | 预留 | 按业务扩展自行分配 |
| 90~99 | 第三方集成 | 外部 API 调用、消息推送等 |

> **扩展规则**：新增模块时从预留段中顺序领取，在 `app/core/error_codes.py` 顶部注释区登记。

---

## 通用错误码表

| 错误码 | HTTP 状态码 | 常量名 | 描述 |
|--------|------------|--------|------|
| 000000 | 200 | SUCCESS | 成功 |
| 000001 | 400 | PARAM_VALIDATION_ERROR | 参数校验失败 |
| 000002 | 401 | NOT_AUTHENTICATED | 未认证 |
| 000003 | 403 | PERMISSION_DENIED | 权限不足 |
| 000004 | 404 | RESOURCE_NOT_FOUND | 资源不存在 |
| 000005 | 429 | RATE_LIMIT_EXCEEDED | 请求过于频繁 |
| 000006 | 400 | DUPLICATE_RESOURCE | 资源已存在 |
| 000007 | 405 | METHOD_NOT_ALLOWED | 请求方法不允许 |
| 000099 | 500 | INTERNAL_ERROR | 系统内部错误 |

---

## 自定义异常类层次结构

### 异常基类

```python
# app/core/exceptions.py

from __future__ import annotations


class AppException(Exception):
    """应用异常基类，所有业务异常必须继承此类。"""

    code: str = "000099"
    http_status: int = 500
    message: str = "系统内部错误"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        http_status: int | None = None,
        data: dict | None = None,
    ):
        self.message = message or self.__class__.message
        self.code = code or self.__class__.code
        self.http_status = http_status or self.__class__.http_status
        self.data = data
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "data": self.data,
        }
```

### 具体异常子类

```python
class ValidationError(AppException):
    """参数校验失败。"""
    code = "000001"
    http_status = 400
    message = "参数校验失败"


class AuthenticationError(AppException):
    """未认证或认证失败。"""
    code = "000002"
    http_status = 401
    message = "未认证"


class PermissionDeniedError(AppException):
    """权限不足。"""
    code = "000003"
    http_status = 403
    message = "权限不足"


class NotFoundError(AppException):
    """资源不存在。"""
    code = "000004"
    http_status = 404
    message = "资源不存在"


class RateLimitError(AppException):
    """请求过于频繁。"""
    code = "000005"
    http_status = 429
    message = "请求过于频繁"


class DuplicateError(AppException):
    """资源已存在。"""
    code = "000006"
    http_status = 400
    message = "资源已存在"


class BusinessError(AppException):
    """通用业务异常，用于各模块的业务规则校验失败。"""
    http_status = 400
    message = "业务处理失败"
```

### 使用示例

```python
from app.core.exceptions import NotFoundError, BusinessError

# 使用默认消息
raise NotFoundError()

# 自定义消息
raise NotFoundError("用户不存在")

# 携带业务错误码
raise BusinessError("订单已取消，无法重复操作", code="300001")

# 携带附加数据
raise ValidationError("参数校验失败", data={"fields": ["email", "phone"]})
```

---

## 全局异常处理器

在 `app/core/exception_handlers.py` 中注册全局异常处理器，确保所有异常返回统一格式。

### 统一响应格式

无论成功或失败，响应体结构保持一致：

```json
{
    "code": "000001",
    "message": "参数校验失败",
    "data": null
}
```

成功时 `code` 为 `200`（整数），失败时 `code` 为 6 位错误码字符串。

### 异常处理器实现

```python
# app/core/exception_handlers.py

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """捕获所有自定义业务异常。"""
        logger.warning(
            "[BizError] %s %s - code=%s message=%s",
            request.method,
            request.url.path,
            exc.code,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """捕获 Pydantic / FastAPI 参数校验错误。"""
        errors = exc.errors()
        first_error = errors[0] if errors else {}
        field = " -> ".join(str(loc) for loc in first_error.get("loc", []))
        detail = first_error.get("msg", "参数校验失败")
        message = f"{field}: {detail}" if field else detail

        logger.warning(
            "[ValidationError] %s %s - %s",
            request.method,
            request.url.path,
            message,
        )
        return JSONResponse(
            status_code=400,
            content={
                "code": "000001",
                "message": message,
                "data": None,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ):
        """捕获框架级 HTTP 异常（404、405 等）。"""
        status_map = {
            401: ("000002", "未认证"),
            403: ("000003", "权限不足"),
            404: ("000004", "资源不存在"),
            405: ("000007", "请求方法不允许"),
            429: ("000005", "请求过于频繁"),
        }
        code, message = status_map.get(
            exc.status_code, ("000099", exc.detail or "请求失败")
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": code,
                "message": message,
                "data": None,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """兜底：捕获所有未处理的异常，避免返回原始堆栈。"""
        logger.error(
            "[UnhandledError] %s %s - %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": "000099",
                "message": "系统内部错误",
                "data": None,
            },
        )
```

### 注册到 FastAPI 应用

```python
# app/main.py

from fastapi import FastAPI
from app.core.exception_handlers import register_exception_handlers

app = FastAPI()
register_exception_handlers(app)
```

### 异常处理器优先级

处理器按以下顺序尝试匹配（越具体越优先）：

1. `RequestValidationError` — 参数校验失败
2. `AppException`（及其子类） — 业务异常
3. `StarletteHTTPException` — 框架 HTTP 异常
4. `Exception` — 兜底捕获

---

## 业务模块错误码注册

### 错误码常量文件组织

```
backend/app/core/
├── exceptions.py          # 异常基类与通用异常
├── exception_handlers.py  # 全局异常处理器
└── error_codes/
    ├── __init__.py        # 汇总导出所有错误码
    ├── common.py          # 通用错误码（00 段）
    ├── user.py            # 用户模块错误码（10 段）
    ├── auth.py            # 认证模块错误码（11 段）
    └── order.py           # 订单模块错误码（30 段）
```

### 通用错误码定义

```python
# app/core/error_codes/common.py

SUCCESS = "000000"
PARAM_VALIDATION_ERROR = "000001"
NOT_AUTHENTICATED = "000002"
PERMISSION_DENIED = "000003"
RESOURCE_NOT_FOUND = "000004"
RATE_LIMIT_EXCEEDED = "000005"
DUPLICATE_RESOURCE = "000006"
METHOD_NOT_ALLOWED = "000007"
INTERNAL_ERROR = "000099"
```

### 用户模块错误码

```python
# app/core/error_codes/user.py

# 10 段：用户模块
USER_NOT_FOUND = "100001"          # 用户不存在
USER_ALREADY_EXISTS = "100002"     # 用户已存在
USER_DISABLED = "100003"           # 用户已被禁用
USER_EMAIL_EXISTS = "100004"       # 邮箱已被注册
USER_PHONE_EXISTS = "100005"       # 手机号已被注册
USER_PASSWORD_WRONG = "100006"     # 密码错误
USER_PASSWORD_EXPIRED = "100007"   # 密码已过期
USER_PROFILE_INCOMPLETE = "100008" # 用户资料不完整
```

### 认证模块错误码

```python
# app/core/error_codes/auth.py

# 11 段：认证模块
TOKEN_EXPIRED = "110001"           # Token 已过期
TOKEN_INVALID = "110002"           # Token 无效
TOKEN_REVOKED = "110003"           # Token 已被吊销
REFRESH_TOKEN_EXPIRED = "110004"   # Refresh Token 已过期
CAPTCHA_ERROR = "110005"           # 验证码错误
CAPTCHA_EXPIRED = "110006"         # 验证码已过期
LOGIN_ATTEMPTS_EXCEEDED = "110007" # 登录尝试次数超限
OAUTH_AUTH_FAILED = "110008"       # 第三方认证失败
```

### 业务模块中使用错误码

```python
# app/services/user.py

from app.core.exceptions import NotFoundError, DuplicateError, BusinessError
from app.core.error_codes import user as user_codes


class UserService:
    async def get_user(self, db, *, user_id: int):
        user = await self.repo.get_by_id(db, user_id)
        if not user:
            raise NotFoundError("用户不存在", code=user_codes.USER_NOT_FOUND)
        return user.to_dict()

    async def create_user(self, db, *, payload):
        existing = await self.repo.get_by_email(db, payload.email)
        if existing:
            raise DuplicateError("邮箱已被注册", code=user_codes.USER_EMAIL_EXISTS)
        # ...

    async def login(self, db, *, username: str, password: str):
        user = await self.repo.get_by_username(db, username)
        if not user:
            raise NotFoundError("用户不存在", code=user_codes.USER_NOT_FOUND)
        if user.is_disabled:
            raise BusinessError("用户已被禁用", code=user_codes.USER_DISABLED)
        if not verify_password(password, user.hashed_password):
            raise BusinessError("密码错误", code=user_codes.USER_PASSWORD_WRONG)
        # ...
```

### 新增模块错误码步骤

1. 在 `app/core/error_codes/` 下新建模块文件（如 `order.py`）
2. 按模块码段定义常量，格式为 `{MODULE_CODE}{SEQUENCE}`
3. 在 `__init__.py` 中导入新模块
4. 在业务 Service 中引用错误码常量，配合异常类抛出

---

## 前端错误处理

### 响应拦截器

在 Axios 响应拦截器中统一处理后端返回的错误码：

```javascript
// utils/request.js

import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/store/user'
import { refreshToken } from '@/api/auth'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
})

let isRefreshing = false
let pendingRequests = []

service.interceptors.response.use(
  (response) => {
    const res = response.data

    // code === 200 表示业务成功
    if (res.code === 200) {
      return res
    }

    // 业务失败，按错误码分流处理
    handleBusinessError(res)
    return Promise.reject(res)
  },
  (error) => {
    // 网络层错误（超时、断网等）
    if (!error.response) {
      ElMessage.error('网络连接异常，请检查网络设置')
      return Promise.reject(error)
    }

    const status = error.response.status
    handleHttpError(status)
    return Promise.reject(error)
  }
)

function handleBusinessError(res) {
  const code = String(res.code)

  // Token 过期 → 尝试静默刷新
  if (code === '110001') {
    return handleTokenExpired(res)
  }

  // 未认证 / Token 无效 → 强制登出
  if (['000002', '110002', '110003'].includes(code)) {
    forceLogout('登录已失效，请重新登录')
    return
  }

  // 权限不足 → 提示但不登出
  if (code === '000003') {
    ElMessage.warning('权限不足，无法执行此操作')
    return
  }

  // 请求过于频繁
  if (code === '000005') {
    ElMessage.warning('操作过于频繁，请稍后再试')
    return
  }

  // 其他业务错误 → 展示后端返回的 message
  ElMessage.error(res.message || '操作失败')
}

function handleHttpError(status) {
  const messages = {
    400: '请求参数错误',
    401: '登录已失效，请重新登录',
    403: '权限不足',
    404: '请求的资源不存在',
    500: '服务器内部错误，请稍后重试',
    502: '网关错误',
    503: '服务暂不可用',
  }
  ElMessage.error(messages[status] || `请求失败（${status}）`)

  if (status === 401) {
    forceLogout()
  }
}
```

### Token 过期自动刷新

```javascript
function handleTokenExpired(originalRes) {
  if (isRefreshing) {
    // 正在刷新中，将当前请求加入等待队列
    return new Promise((resolve) => {
      pendingRequests.push(() => resolve(service(originalRes.config)))
    })
  }

  isRefreshing = true

  return refreshToken()
    .then((res) => {
      const userStore = useUserStore()
      userStore.setToken(res.data.access_token)

      // 重发等待队列中的请求
      pendingRequests.forEach((cb) => cb())
      pendingRequests = []

      // 重发当前请求
      return service(originalRes.config)
    })
    .catch(() => {
      forceLogout('登录已过期，请重新登录')
      return Promise.reject(originalRes)
    })
    .finally(() => {
      isRefreshing = false
    })
}

function forceLogout(message) {
  const userStore = useUserStore()

  ElMessageBox.confirm(message || '登录已失效，请重新登录', '提示', {
    confirmButtonText: '重新登录',
    showCancelButton: false,
    type: 'warning',
  }).then(() => {
    userStore.logout()
    window.location.href = '/login'
  })
}
```

### 错误提示展示策略

| 错误类型 | 提示方式 | 说明 |
|----------|----------|------|
| 参数校验失败 | `ElMessage.error` | 展示后端返回的具体字段错误信息 |
| 权限不足 | `ElMessage.warning` | 警告提示，不阻断页面 |
| 资源不存在 | `ElMessage.error` | 可配合路由跳转到 404 页面 |
| Token 过期 | 静默刷新 | 用户无感知，刷新失败才弹窗 |
| Token 无效 / 已吊销 | `ElMessageBox` 弹窗 | 强制登出并跳转登录页 |
| 请求频繁 | `ElMessage.warning` | 提示稍后重试 |
| 网络异常 | `ElMessage.error` | 检查网络连接 |
| 服务器错误 | `ElMessage.error` | 提示稍后重试，不暴露技术细节 |

### 页面级错误处理

对于表单提交等场景，在页面层面可进一步细化：

```javascript
async function handleSubmit() {
  try {
    await createUser(formData)
    ElMessage.success('创建成功')
    router.push('/users')
  } catch (err) {
    // 拦截器已处理通用提示，此处仅做页面特殊逻辑
    if (err.code === '100004') {
      // 邮箱已存在 → 聚焦到邮箱输入框
      emailInputRef.value?.focus()
    }
  }
}
```

---

## 检查清单

### 后端
- [ ] 错误码为 6 位数字字符串，按模块码段分配
- [ ] 异常类继承 `AppException`，不直接 `raise Exception`
- [ ] 全局异常处理器已注册（`AppException` / `RequestValidationError` / `Exception`）
- [ ] Service 层抛出异常时携带明确的错误码和消息
- [ ] 兜底处理器不向客户端暴露堆栈信息
- [ ] 异常日志包含请求上下文（路径、方法、用户信息）
- [ ] 新增模块错误码已在 `error_codes/` 下登记

### 前端
- [ ] 响应拦截器统一处理错误码分流
- [ ] Token 过期实现静默刷新机制
- [ ] 未认证 / Token 无效时强制登出
- [ ] 错误提示对用户友好，不暴露技术细节
- [ ] 页面级特殊错误码有针对性处理
