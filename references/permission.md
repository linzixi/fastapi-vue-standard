# 权限系统规范（通用 RBAC）

## 目标
- 建立可扩展的角色权限模型，实现后端强校验 + 前端可视化控制。

## 数据模型建议
- `users`：用户
- `roles`：角色
- `permissions`：权限点
- `user_roles`：用户与角色关联
- `role_permissions`：角色与权限关联

## 权限点命名
- 推荐格式：`module:resource:action`
- 示例：`system:user:read`、`system:user:create`、`content:article:publish`
- 命名统一小写，使用冒号分隔

## 后端权限校验（FastAPI）

### 基础权限依赖

```python
from fastapi import Depends, HTTPException, status


def require_permission(permission: str):
    def checker(current_user = Depends(get_current_user)):
        if permission not in current_user.permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return current_user
    return checker
```

- 在路由层通过 `Depends(require_permission("module:resource:action"))` 使用
- 超级管理员应通过配置控制，不写死用户名

### 完整权限依赖链

权限校验分三层依赖，逐层收紧：`get_current_user` → `require_permission` → `require_data_scope`。

```python
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """第一层：从 Token 解析并加载用户，附带权限列表"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await user_repo.get_with_permissions(db, user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_permission(permission: str):
    """第二层：校验用户是否持有指定权限码"""
    def checker(current_user=Depends(get_current_user)):
        if current_user.is_superadmin:
            return current_user
        if permission not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {permission}",
            )
        return current_user
    return checker


def require_data_scope(scope: str = "all"):
    """第三层：在权限校验通过后进一步限制数据范围

    scope 取值: 'self' | 'department' | 'all'
    """
    def checker(current_user=Depends(get_current_user)):
        if current_user.is_superadmin:
            current_user.data_scope = "all"
            return current_user
        allowed = current_user.data_scope or "self"
        scope_levels = {"self": 0, "department": 1, "all": 2}
        if scope_levels.get(allowed, 0) < scope_levels.get(scope, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="数据范围不足",
            )
        current_user.data_scope = allowed
        return current_user
    return checker
```

路由中组合使用：

```python
@router.get("/api/v1/user/get_user_list")
async def get_user_list(
    current_user=Depends(require_permission("system:user:read")),
):
    ...


@router.get("/api/v1/order/get_order_list")
async def get_order_list(
    current_user=Depends(require_data_scope("department")),
):
    # current_user.data_scope 可传入 Service 层做数据过滤
    ...
```

### 多权限组合校验（AND / OR）

```python
from typing import List


def require_all_permissions(permissions: List[str]):
    """AND 逻辑：用户必须同时持有所有权限"""
    def checker(current_user=Depends(get_current_user)):
        if current_user.is_superadmin:
            return current_user
        missing = [p for p in permissions if p not in current_user.permissions]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {', '.join(missing)}",
            )
        return current_user
    return checker


def require_any_permission(permissions: List[str]):
    """OR 逻辑：用户持有任一权限即可"""
    def checker(current_user=Depends(get_current_user)):
        if current_user.is_superadmin:
            return current_user
        if not any(p in current_user.permissions for p in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="缺少必要权限",
            )
        return current_user
    return checker
```

使用示例：

```python
@router.post("/api/v1/user/create_user")
async def create_user(
    current_user=Depends(require_all_permissions([
        "system:user:create",
        "system:role:read",
    ])),
):
    ...


@router.get("/api/v1/report/get_report_detail")
async def get_report_detail(
    current_user=Depends(require_any_permission([
        "report:sales:read",
        "report:finance:read",
    ])),
):
    ...
```

### 权限白名单（免认证接口）

在 `app/core/config.py` 中集中管理无需认证的路径：

```python
# app/core/config.py
class Settings:
    ...
    PERMISSION_WHITELIST: list = [
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/register",
        "/api/v1/common/health",
        "/api/v1/common/captcha",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]
```

在认证中间件中跳过白名单路径：

```python
from starlette.middleware.base import BaseHTTPMiddleware


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if any(path.startswith(w) for w in settings.PERMISSION_WHITELIST):
            return await call_next(request)
        # 执行 Token 校验逻辑...
        return await call_next(request)
```

## 前端权限控制（Vue）
- 路由守卫基于用户权限控制可访问页面
- 按钮权限通过 `v-permission` 指令或组合式函数控制
- 禁止把权限码硬编码在多个组件，集中维护常量

## 数据权限（可选）
- 在 Service 层增加数据范围过滤（本人、本部门、全部）
- 避免仅依赖前端参数传递数据范围

## 审计与安全
- 记录权限变更日志（谁在何时改了什么）
- 关键操作要求二次确认或二次认证（可选）
- Token 失效和角色变更后应支持主动刷新权限缓存

## 检查清单
- [ ] 权限模型包含用户、角色、权限三层
- [ ] 后端接口已强制权限校验
- [ ] 前端路由和按钮已做权限显隐
- [ ] 数据权限策略已落地（如有）
- [ ] 权限变更具备审计记录
