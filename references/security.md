# 安全编码规范

## 1. 认证安全

### 1.1 JWT 规范

| 配置项 | 要求 | 说明 |
|--------|------|------|
| 算法 | `HS256` | 对称签名，禁止使用 `none` 算法 |
| Access Token 过期时间 | ≤ 2 小时 | 生产环境推荐 30 分钟 |
| Refresh Token 过期时间 | ≤ 7 天 | 用于静默续签 |
| Payload 标准字段 | `uid`, `scope`, `exp`, `iat` | 禁止在 Payload 中存放密码、手机号等敏感信息 |
| SECRET_KEY 长度 | ≥ 32 字符 | 使用 `secrets.token_urlsafe(32)` 生成 |

```python
# app/libs/token_auth.py

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

security = HTTPBearer()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(uid: int, scope: str | None = None) -> str:
    """生成访问令牌。"""
    payload = {
        "uid": uid,
        "scope": scope or "user",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(uid: int) -> str:
    """生成刷新令牌。"""
    payload = {
        "uid": uid,
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """解析并验证令牌。"""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 无效")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """从请求头中提取并验证当前用户。"""
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 类型错误")
    return payload
```

### 1.2 密码存储

| 规则 | 说明 |
|------|------|
| 哈希库 | 使用 `passlib[bcrypt]` |
| 禁止方式 | 明文存储、MD5、SHA-1、SHA-256 单次哈希 |
| bcrypt rounds | 默认 12（passlib 默认值） |

```python
# app/libs/password.py

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """对明文密码进行 bcrypt 哈希。"""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码与哈希值是否匹配。"""
    return pwd_context.verify(plain, hashed)
```

### 1.3 Token 传输

- 所有需要认证的接口通过 `Authorization` 请求头传递 Token
- 格式：`Authorization: Bearer <token>`
- 禁止将 Token 放在 URL 查询参数中
- 禁止将 Token 放在 Cookie 中（除非有完整的 CSRF 防护方案）

### 1.4 登录安全

| 策略 | 配置 |
|------|------|
| 最大失败次数 | 5 次（可按账号或 IP 维度） |
| 锁定时长 | 15 分钟 |
| 锁定方式 | Redis 计数器，Key 格式 `login_fail:{username}` |
| 解锁方式 | 超时自动解锁，管理员手动解锁 |

```python
# app/services/login.py

import redis.asyncio as redis
from fastapi import HTTPException, status

LOGIN_FAIL_PREFIX = "login_fail:"
MAX_ATTEMPTS = 5
LOCK_SECONDS = 900  # 15 分钟


async def check_login_attempts(rd: redis.Redis, username: str) -> None:
    """检查登录失败次数，超限则拒绝。"""
    key = f"{LOGIN_FAIL_PREFIX}{username}"
    attempts = await rd.get(key)
    if attempts and int(attempts) >= MAX_ATTEMPTS:
        ttl = await rd.ttl(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"登录失败次数过多，请 {ttl // 60 + 1} 分钟后重试",
        )


async def record_login_failure(rd: redis.Redis, username: str) -> None:
    """记录一次登录失败。"""
    key = f"{LOGIN_FAIL_PREFIX}{username}"
    pipe = rd.pipeline()
    pipe.incr(key)
    pipe.expire(key, LOCK_SECONDS)
    await pipe.execute()


async def clear_login_failures(rd: redis.Redis, username: str) -> None:
    """登录成功后清除失败计数。"""
    await rd.delete(f"{LOGIN_FAIL_PREFIX}{username}")
```

---

## 2. 接口安全

### 2.1 CORS 配置

| 环境 | 规则 |
|------|------|
| 开发环境 | 允许 `allow_origins=["*"]` |
| 生产环境 | **禁止** `allow_origins=["*"]`，必须指定具体域名 |

```python
# app/core/cors.py

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.core.config import settings


def setup_cors(app: FastAPI) -> None:
    """根据环境配置 CORS 中间件。"""
    if settings.ENV == "production":
        origins = settings.ALLOWED_ORIGINS  # 如 ["https://admin.example.com"]
    else:
        origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
```

### 2.2 接口限流

使用 `slowapi` 实现接口级限流：

```python
# app/core/rate_limit.py

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

```python
# app/api/v1/endpoints/auth.py

from fastapi import APIRouter, Request
from app.core.rate_limit import limiter

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, payload: LoginForm):
    """登录接口，每个 IP 每分钟最多 5 次。"""
    # 业务逻辑...
```

**限流推荐阈值**：

| 接口类型 | 限流规则 |
|----------|----------|
| 登录 / 注册 | 5 次/分钟 |
| 短信验证码 | 1 次/60 秒 |
| 普通查询接口 | 60 次/分钟 |
| 文件上传 | 10 次/分钟 |

### 2.3 请求体大小限制

在反向代理（Nginx）和应用层同时限制：

```python
# Nginx 配置
# client_max_body_size 10m;

# FastAPI 层面限制
from fastapi import Request, HTTPException, status


async def limit_request_body(request: Request, max_size: int = 10 * 1024 * 1024):
    """限制请求体大小，默认 10MB。"""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="请求体过大",
        )
```

---

## 3. 数据安全

### 3.1 SQL 注入防护

| 规则 | 说明 |
|------|------|
| **必须** | 使用 SQLAlchemy ORM 或 `text()` 参数化查询 |
| **禁止** | 字符串拼接 SQL 语句 |

```python
from sqlalchemy import select, text
from app.models.user import User

# ✅ 正确：ORM 查询
stmt = select(User).where(User.username == keyword)

# ✅ 正确：参数化原生 SQL
stmt = text("SELECT * FROM users WHERE username = :name")
result = await db.execute(stmt, {"name": keyword})

# ❌ 禁止：字符串拼接
sql = f"SELECT * FROM users WHERE username = '{keyword}'"
```

### 3.2 XSS 防护

**后端**：
- 对用户输入进行转义后再存储或返回
- 富文本字段使用白名单过滤（如 `bleach`）

```python
import bleach

ALLOWED_TAGS = ["p", "br", "strong", "em", "ul", "ol", "li", "a", "img"]
ALLOWED_ATTRS = {"a": ["href", "title"], "img": ["src", "alt"]}


def sanitize_html(raw: str) -> str:
    """过滤富文本中的危险标签。"""
    return bleach.clean(raw, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
```

**前端**：
- 禁止使用 `v-html` 渲染不可信内容
- 必须使用 `v-html` 时，先通过 `DOMPurify` 过滤

```javascript
// utils/sanitize.js

import DOMPurify from 'dompurify'

export function sanitizeHtml(raw) {
  return DOMPurify.sanitize(raw, {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'img'],
    ALLOWED_ATTR: ['href', 'src', 'alt', 'title'],
  })
}
```

```html
<!-- ✅ 正确：过滤后再渲染 -->
<div v-html="sanitizeHtml(content)"></div>

<!-- ❌ 禁止：直接渲染不可信内容 -->
<div v-html="userInput"></div>
```

### 3.3 敏感数据脱敏规则

| 数据类型 | 原始值 | 脱敏后 | 规则 |
|----------|--------|--------|------|
| 手机号 | `13812345678` | `138****5678` | 保留前 3 后 4 |
| 身份证 | `110101199001011234` | `110101****1234` | 保留前 6 后 4 |
| 邮箱 | `zhangsan@example.com` | `zha****@example.com` | 用户名保留前 3，其余替换 |
| 银行卡 | `6222021234567890123` | `6222****0123` | 保留前 4 后 4 |
| 姓名 | `张三丰` | `张*丰` | 保留首尾，中间替换 |
| 地址 | `北京市朝阳区XX路XX号` | `北京市朝阳区****` | 保留省市区，其余替换 |

```python
# app/libs/masking.py

import re


def mask_phone(phone: str) -> str:
    """手机号脱敏：保留前 3 后 4。"""
    if len(phone) != 11:
        return phone
    return f"{phone[:3]}****{phone[7:]}"


def mask_id_card(id_card: str) -> str:
    """身份证脱敏：保留前 6 后 4。"""
    if len(id_card) not in (15, 18):
        return id_card
    return f"{id_card[:6]}{'*' * (len(id_card) - 10)}{id_card[-4:]}"


def mask_email(email: str) -> str:
    """邮箱脱敏：用户名保留前 3 位。"""
    parts = email.split("@")
    if len(parts) != 2:
        return email
    name = parts[0]
    masked_name = name[:3] + "****" if len(name) > 3 else name[0] + "****"
    return f"{masked_name}@{parts[1]}"


def mask_bank_card(card: str) -> str:
    """银行卡脱敏：保留前 4 后 4。"""
    if len(card) < 8:
        return card
    return f"{card[:4]}****{card[-4:]}"


def mask_name(name: str) -> str:
    """姓名脱敏：保留首尾字符。"""
    if len(name) <= 1:
        return name
    return f"{name[0]}{'*' * (len(name) - 2)}{name[-1]}"
```

### 3.4 日志脱敏

日志中禁止出现明文敏感数据，输出前必须调用脱敏函数：

```python
from app.libs.masking import mask_phone, mask_id_card
from app.libs.logger import logger

# ✅ 正确：脱敏后记录
logger.info("[User] 手机号: %s 验证通过", mask_phone(phone))

# ❌ 禁止：明文记录
logger.info("[User] 手机号: %s 验证通过", phone)
```

**禁止出现在日志中的字段**：
- 密码（明文或哈希值）
- 完整 Token
- 身份证号
- 银行卡号
- 完整手机号

---

## 4. 文件上传安全

### 4.1 安全规则

| 规则 | 配置 |
|------|------|
| 类型白名单 | 仅允许 `.jpg`, `.jpeg`, `.png`, `.gif`, `.pdf`, `.xlsx`, `.xls`, `.doc`, `.docx` |
| 大小限制 | 图片 ≤ 5MB，文档 ≤ 20MB |
| 文件重命名 | UUID4 重命名，禁止使用原始文件名 |
| 存储路径 | 按日期分目录：`uploads/{type}/{YYYY-MM}/{uuid}.ext` |
| magic bytes 校验 | 读取文件头字节验证真实类型，防止伪造扩展名 |

### 4.2 代码示例

```python
# app/libs/file_upload.py

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

ALLOWED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".gif"}
ALLOWED_DOC_TYPES = {".pdf", ".xlsx", ".xls", ".doc", ".docx"}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_TYPES | ALLOWED_DOC_TYPES

IMAGE_MAX_SIZE = 5 * 1024 * 1024    # 5MB
DOC_MAX_SIZE = 20 * 1024 * 1024     # 20MB

MAGIC_BYTES = {
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".gif": [b"GIF87a", b"GIF89a"],
    ".pdf": [b"%PDF"],
    ".xlsx": [b"PK\x03\x04"],
    ".xls": [b"\xd0\xcf\x11\xe0"],
    ".doc": [b"\xd0\xcf\x11\xe0"],
    ".docx": [b"PK\x03\x04"],
}


async def validate_and_save(
    file: UploadFile,
    upload_type: str = "general",
    base_dir: str = "uploads",
) -> str:
    """验证并保存上传文件，返回相对存储路径。"""
    # 1. 扩展名检查
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {ext}",
        )

    # 2. 读取内容并检查大小
    content = await file.read()
    max_size = IMAGE_MAX_SIZE if ext in ALLOWED_IMAGE_TYPES else DOC_MAX_SIZE
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过限制（{max_size // 1024 // 1024}MB）",
        )

    # 3. magic bytes 校验
    magic_list = MAGIC_BYTES.get(ext, [])
    if magic_list and not any(content.startswith(m) for m in magic_list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件内容与扩展名不匹配",
        )

    # 4. UUID 重命名 + 按日期存储
    new_filename = f"{uuid.uuid4().hex}{ext}"
    date_dir = datetime.now().strftime("%Y-%m")
    save_dir = Path(base_dir) / upload_type / date_dir
    save_dir.mkdir(parents=True, exist_ok=True)

    save_path = save_dir / new_filename
    save_path.write_bytes(content)

    return str(save_path)
```

---

## 5. 环境与配置安全

### 5.1 .env 文件管理

| 规则 | 说明 |
|------|------|
| `.env` 不入库 | `.gitignore` 必须包含 `.env*`（`.env.example` 除外） |
| 提供示例文件 | 仓库中保留 `.env.example`，包含所有配置项但不含真实值 |
| 分环境配置 | `.env.development`、`.env.production` 分开管理 |

```text
# .gitignore
.env
.env.*
!.env.example
```

```text
# .env.example
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
REDIS_URL=redis://localhost:6379/0
ALLOWED_ORIGINS=["http://localhost:5173"]
ENV=development
```

### 5.2 生产环境配置

| 配置项 | 生产值 | 说明 |
|--------|--------|------|
| `DEBUG` | `False` | 关闭调试模式 |
| `docs_url` | `None` | 关闭 Swagger UI |
| `redoc_url` | `None` | 关闭 ReDoc |
| `openapi_url` | `None` | 关闭 OpenAPI schema |

```python
# app/main.py

from app.core.config import settings

if settings.ENV == "production":
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
else:
    app = FastAPI(title="项目名称", version="1.0.0")
```

### 5.3 SECRET_KEY 生成规范

```python
# 生成安全的 SECRET_KEY（在终端执行一次即可）
import secrets
print(secrets.token_urlsafe(32))
# 示例输出: "dG9wLXNlY3JldC1rZXktZm9yLXByb2R1Y3Rpb24"
```

- 长度：≥ 32 字符
- 禁止使用默认值、简单字符串（如 `"secret"`, `"123456"`）
- 每个环境使用不同的 SECRET_KEY
- 定期轮换（推荐每 90 天）

### 5.4 第三方密钥管理

| 规则 | 说明 |
|------|------|
| 存储位置 | 环境变量或密钥管理服务（如 Vault），**禁止硬编码** |
| 代码中引用 | 仅通过 `settings.XXX_API_KEY` 引用 |
| 日志中禁止输出 | 第三方 API Key、Secret 禁止出现在日志中 |

```python
# ✅ 正确：从配置中读取
from app.core.config import settings

api_key = settings.OPENAI_API_KEY

# ❌ 禁止：硬编码
api_key = "sk-xxxxxxxxxxxxxxxxxxxx"
```

---

## 6. 前端安全

### 6.1 敏感信息存储

| 规则 | 说明 |
|------|------|
| `localStorage` | 仅存 Token（不可避免时） |
| 禁止存储 | 密码、身份证、银行卡、手机号等敏感信息 |
| Token 过期 | 前端定时检查并清除过期 Token |

```javascript
// store/user.js

import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: {},  // 仅存非敏感信息：uid、username、avatar
  }),

  actions: {
    setToken(token) {
      this.token = token
      localStorage.setItem('token', token)
    },

    logout() {
      this.token = ''
      this.userInfo = {}
      localStorage.removeItem('token')
    },
  },
})
```

### 6.2 CSRF 防护

当使用 Cookie 传递认证信息时，必须启用 CSRF 防护：

```javascript
// utils/request.js

import axios from 'axios'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
  withCredentials: true,
})

// 从 Cookie 中读取 CSRF Token 并附加到请求头
service.interceptors.request.use((config) => {
  const csrfToken = document.cookie
    .split('; ')
    .find((row) => row.startsWith('csrftoken='))
    ?.split('=')[1]

  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken
  }
  return config
})
```

> **推荐方案**：使用 `Authorization: Bearer` 方式传递 Token，天然免疫 CSRF 攻击，无需额外防护。

### 6.3 路由权限防越权

前端路由守卫结合后端权限数据，防止用户通过直接输入 URL 越权访问：

```javascript
// router/index.js

import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'
import { usePermissionStore } from '@/store/permission'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'Login', component: () => import('@/views/login/index.vue') },
    // 其他路由通过 addRoute 动态加载
  ],
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  const permissionStore = usePermissionStore()

  // 无 Token → 跳转登录（白名单页面除外）
  if (!userStore.token) {
    if (to.path === '/login') {
      return next()
    }
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }

  // 已有 Token 访问登录页 → 跳转首页
  if (to.path === '/login') {
    return next({ path: '/' })
  }

  // 动态路由未加载 → 拉取权限并注册路由
  if (!permissionStore.isRoutesLoaded) {
    try {
      const routes = await permissionStore.loadRoutes()
      routes.forEach((route) => router.addRoute(route))
      return next({ ...to, replace: true })
    } catch {
      userStore.logout()
      return next({ path: '/login' })
    }
  }

  next()
})

export default router
```

### 6.4 依赖安全审计

| 操作 | 命令 | 频率 |
|------|------|------|
| 检查已知漏洞 | `npm audit` | 每次 CI 构建 |
| 自动修复 | `npm audit fix` | 手动确认后执行 |
| 锁定依赖版本 | 提交 `package-lock.json` | 每次变更依赖 |
| 检查过期依赖 | `npm outdated` | 每月一次 |

```json
// package.json - scripts 中集成审计
{
  "scripts": {
    "audit": "npm audit --audit-level=high",
    "audit:fix": "npm audit fix"
  }
}
```

---

## 7. 检查清单

### 认证安全
- [ ] JWT 使用 HS256 算法，Payload 不含敏感数据
- [ ] Access Token 过期时间 ≤ 2 小时
- [ ] 密码使用 `passlib` + `bcrypt` 哈希存储
- [ ] 禁止明文、MD5、SHA 单次哈希存储密码
- [ ] Token 通过 `Authorization: Bearer` 传输
- [ ] 登录失败计数 + 账号锁定策略已实现

### 接口安全
- [ ] 生产环境 CORS `allow_origins` 配置了具体域名
- [ ] 敏感接口（登录、注册、短信）已配置限流
- [ ] 请求体大小限制已在 Nginx 和应用层双重配置

### 数据安全
- [ ] 所有数据库查询使用 ORM 或参数化 SQL
- [ ] 用户输入的富文本经过白名单过滤
- [ ] 前端不可信内容使用 `DOMPurify` 过滤后再 `v-html` 渲染
- [ ] 手机号、身份证、邮箱等敏感字段已按规则脱敏
- [ ] 日志中不包含明文密码、完整 Token、身份证号等敏感信息

### 文件上传安全
- [ ] 仅允许白名单内的文件扩展名
- [ ] 图片 ≤ 5MB，文档 ≤ 20MB
- [ ] 文件使用 UUID 重命名，不保留原始文件名
- [ ] 存储路径按类型和日期隔离
- [ ] 上传时校验文件头 magic bytes

### 环境与配置安全
- [ ] `.env` 文件已加入 `.gitignore`
- [ ] 仓库中提供了 `.env.example` 示例文件
- [ ] 生产环境关闭了 `DEBUG`、`docs_url`、`redoc_url`、`openapi_url`
- [ ] `SECRET_KEY` 使用 `secrets.token_urlsafe(32)` 生成，≥ 32 字符
- [ ] 第三方密钥通过环境变量管理，禁止硬编码

### 前端安全
- [ ] `localStorage` 中不存储密码、身份证等敏感信息
- [ ] 使用 `Authorization: Bearer` 方案或已配置 CSRF 防护
- [ ] 前端路由守卫已实现，动态路由按权限加载
- [ ] CI 流程中集成了 `npm audit`
- [ ] `package-lock.json` 已提交至版本库
