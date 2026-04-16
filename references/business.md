# 业务层编码规范（FastAPI）

## 分层原则
- Router 层：参数接收、权限依赖、调用 Service、返回响应
- Service 层：业务编排、事务控制、跨仓储协作
- Repository 层：数据库读写细节封装
- Model 层：实体定义，不承载复杂业务流程

## 目录建议
- `backend/app/api/v1/endpoints/`：路由
- `backend/app/services/`：业务服务
- `backend/app/repositories/`：数据访问

## Router 层规范
- 路由函数应保持轻量，不直接写复杂 SQL
- 通过 `Depends` 注入 `db session`、当前用户、权限检查
- 使用 `response_model` 明确定义返回结构

### 路由文件组织
- 一个文件对应一个业务模块，如 `endpoints/user.py`、`endpoints/order.py`
- 每个文件内创建独立的 `APIRouter` 实例，统一在 `api/v1/__init__.py` 中汇总注册
- 文件内路由按 CRUD 顺序排列：list → get → create → update → delete

### APIRouter 前缀与 tags 命名
```python
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["用户管理"])
```
- `prefix` 使用复数名词小写，如 `/users`、`/orders`、`/wx-img-texts`
- `tags` 使用中文业务名称，便于 Swagger 文档可读性
- 汇总注册示例：

```python
# api/v1/__init__.py
from fastapi import APIRouter

from app.api.v1.endpoints import user, order, wx_img_text

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(user.router)
v1_router.include_router(order.router)
v1_router.include_router(wx_img_text.router)
```

### 完整路由函数示例

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user, require_permissions
from app.models.user import User
from app.schemas.order import OrderCreate, OrderUpdate, OrderRead, OrderListData
from app.schemas.response import ApiResponse
from app.services.order import OrderService

router = APIRouter(prefix="/orders", tags=["订单管理"])


def get_order_service() -> OrderService:
    return OrderService()


@router.get("", response_model=ApiResponse[OrderListData])
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions("order:list")),
    service: OrderService = Depends(get_order_service),
):
    data = await service.list_orders(
        db, page=page, page_size=page_size, status=status
    )
    return ApiResponse(data=data)


@router.get("/{order_id}", response_model=ApiResponse[OrderRead])
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions("order:read")),
    service: OrderService = Depends(get_order_service),
):
    item = await service.get_order(db, order_id=order_id)
    return ApiResponse(data=item)


@router.post("", response_model=ApiResponse[OrderRead])
async def create_order(
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions("order:create")),
    service: OrderService = Depends(get_order_service),
):
    item = await service.create_order(db, payload=payload, operator_id=current_user.id)
    return ApiResponse(data=item)


@router.post("/{order_id}", response_model=ApiResponse[OrderRead])
async def update_order(
    order_id: int,
    payload: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions("order:update")),
    service: OrderService = Depends(get_order_service),
):
    item = await service.update_order(
        db, order_id=order_id, payload=payload, operator_id=current_user.id
    )
    return ApiResponse(data=item)


@router.post("/delete", response_model=ApiResponse)
async def delete_orders(
    ids: list[int],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions("order:delete")),
    service: OrderService = Depends(get_order_service),
):
    await service.delete_orders(db, order_ids=ids)
    return ApiResponse(message="删除成功")
```

## Service 层规范
- 使用清晰的方法名：`create_xxx`、`update_xxx`、`delete_xxx`、`list_xxx`
- 跨表操作必须使用事务
- 对业务异常抛出明确的自定义异常

### Service 类标准结构模板

```python
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessException
from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreate, OrderUpdate

logger = logging.getLogger(__name__)


class OrderService:
    """订单业务服务。"""

    def __init__(
        self,
        repo: OrderRepository | None = None,
    ):
        self.repo = repo or OrderRepository()

    async def list_orders(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> dict[str, Any]:
        items, total = await self.repo.list(
            db, page=page, page_size=page_size, status=status
        )
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [item.to_dict() for item in items],
        }

    async def get_order(self, db: AsyncSession, *, order_id: int) -> dict[str, Any]:
        item = await self.repo.get_by_id(db, order_id)
        if not item:
            raise BusinessException("订单不存在", code=404)
        return item.to_dict()

    async def create_order(
        self,
        db: AsyncSession,
        *,
        payload: OrderCreate,
        operator_id: int,
    ) -> dict[str, Any]:
        data = payload.model_dump()
        data["created_by"] = operator_id

        async with db.begin():
            item = await self.repo.create(db, data)

        await db.refresh(item)
        logger.info("订单创建成功: id=%s, operator=%s", item.id, operator_id)
        return item.to_dict()

    async def update_order(
        self,
        db: AsyncSession,
        *,
        order_id: int,
        payload: OrderUpdate,
        operator_id: int,
    ) -> dict[str, Any]:
        item = await self.repo.get_by_id(db, order_id)
        if not item:
            raise BusinessException("订单不存在", code=404)

        data = payload.model_dump(exclude_unset=True)
        data["updated_by"] = operator_id

        async with db.begin():
            item = await self.repo.update(db, item, data)

        await db.refresh(item)
        return item.to_dict()

    async def delete_orders(
        self, db: AsyncSession, *, order_ids: list[int]
    ) -> None:
        if not order_ids:
            raise BusinessException("删除ID不能为空", code=400)

        targets = []
        for oid in order_ids:
            item = await self.repo.get_by_id(db, oid)
            if not item:
                raise BusinessException(f"订单不存在: {oid}", code=404)
            targets.append(item)

        async with db.begin():
            await self.repo.delete_many(db, targets)

        logger.info("订单批量删除: ids=%s", order_ids)
```

### 复杂业务编排示例（跨多个 Repository 协作）

当一个业务操作涉及多张表时，在 Service 内统一编排，所有写操作放在同一事务中：

```python
from app.repositories.order import OrderRepository
from app.repositories.inventory import InventoryRepository
from app.repositories.order_log import OrderLogRepository


class OrderService:
    def __init__(self):
        self.order_repo = OrderRepository()
        self.inventory_repo = InventoryRepository()
        self.log_repo = OrderLogRepository()

    async def confirm_order(
        self, db: AsyncSession, *, order_id: int, operator_id: int
    ) -> dict[str, Any]:
        order = await self.order_repo.get_by_id(db, order_id)
        if not order:
            raise BusinessException("订单不存在", code=404)
        if order.status != "pending":
            raise BusinessException("订单状态不允许确认", code=400)

        async with db.begin():
            # 1. 扣减库存
            await self.inventory_repo.deduct(
                db, product_id=order.product_id, quantity=order.quantity
            )
            # 2. 更新订单状态
            await self.order_repo.update(db, order, {"status": "confirmed"})
            # 3. 写入操作日志
            await self.log_repo.create(db, {
                "order_id": order_id,
                "action": "confirm",
                "operator_id": operator_id,
            })

        await db.refresh(order)
        return order.to_dict()
```

### 数据转换（Entity → DTO）位置
- **推荐在 Service 层完成**：调用 `entity.to_dict()` 或手动组装返回字典
- Repository 返回 ORM 实体（Model），不做格式转换
- Router 层不直接访问实体属性，只处理 Service 返回的 dict/Schema
- 如果转换逻辑复杂，可在 `schemas/` 下创建 `from_orm` 类方法：

```python
# schemas/order.py
class OrderRead(BaseModel):
    id: int
    order_no: str
    status: str
    total_amount: float
    created_at: datetime

    @classmethod
    def from_entity(cls, entity) -> "OrderRead":
        return cls(
            id=entity.id,
            order_no=entity.order_no,
            status=entity.status,
            total_amount=float(entity.total_amount),
            created_at=entity.created_at,
        )
```

### 缓存使用策略

对于高频读取、低频变更的数据，使用 Redis 缓存减轻数据库压力：

```python
import json
import functools
from typing import Callable

from app.core.redis import redis_client


def cache_result(prefix: str, ttl: int = 300):
    """Service 方法级别的缓存装饰器。"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{prefix}:{json.dumps(kwargs, sort_keys=True, default=str)}"
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            result = await func(*args, **kwargs)
            await redis_client.set(cache_key, json.dumps(result, default=str), ex=ttl)
            return result
        return wrapper
    return decorator


class ConfigService:
    @cache_result(prefix="config:list", ttl=600)
    async def list_configs(self, db: AsyncSession, **kwargs) -> dict:
        ...

    async def update_config(self, db: AsyncSession, config_id: int, payload):
        ...
        # 变更后主动清除相关缓存
        await redis_client.delete("config:list:*")
```

缓存使用原则：
- 仅缓存读操作，写操作后主动清除关联缓存
- 缓存键需包含足够的区分度（查询参数、用户维度等）
- 设置合理的 TTL，避免缓存雪崩
- 不要缓存包含敏感信息的数据

## Repository 层规范
- 只处理数据访问与查询拼装
- 避免泄露 ORM 细节到上层
- 高频查询提供分页和筛选接口

## 事务与异常处理

```python
from sqlalchemy.ext.asyncio import AsyncSession


class UserService:
    def __init__(self, repo):
        self.repo = repo

    async def create_user(self, db: AsyncSession, payload):
        async with db.begin():
            user = await self.repo.create(db, payload)
        return user
```

## 日志规范
- 关键操作必须记录：创建、更新、删除、权限拒绝、外部调用失败
- 日志应包含上下文：`trace_id`、`user_id`、接口路径
- 禁止输出敏感信息（密码、完整 token、身份证号）

## 测试要求
- Service 层必须有单元测试
- Endpoint 层至少覆盖成功和失败用例
- 涉及权限的功能必须覆盖越权访问测试

## 检查清单
- [ ] Router/Service/Repository 职责清晰
- [ ] 事务边界明确
- [ ] 异常已分层处理
- [ ] 日志可追踪且已脱敏
- [ ] 关键业务路径有测试覆盖
