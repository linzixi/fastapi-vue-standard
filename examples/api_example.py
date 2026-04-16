#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author   : ****
# @Time     : 2026/1/6 10:00
# @File     : user_api.py
# @Desc     : 用户管理API接口（FastAPI示例，仅GET/POST）

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.libs.logger import logger
from app.libs.token_auth import get_current_user
from app.models.user import User


class UserCreate(BaseModel):
    """创建用户请求参数。"""

    username: str = Field(min_length=3, max_length=20, description="用户名")
    email: EmailStr
    password: str = Field(min_length=6, max_length=32, description="密码")

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", value):
            raise ValueError("用户名只能包含字母、数字和下划线")
        return value


class UserUpdate(BaseModel):
    """更新用户请求参数。"""

    user_id: int = Field(gt=0)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6, max_length=32)


class UserDelete(BaseModel):
    """软删除请求参数。"""

    user_id: int = Field(gt=0)


class UserStatusChange(BaseModel):
    """状态变更请求参数。"""

    user_id: int = Field(gt=0)
    status: bool


class UserComplexQuery(BaseModel):
    """复杂查询请求参数（POST查询示例）。"""

    keywords: list[str] = Field(default_factory=list)
    email_domain: str | None = None
    created_after: datetime | None = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class UserRead(BaseModel):
    """用户响应模型。"""

    id: int
    username: str
    email: EmailStr
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserListData(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[UserRead]


class ApiResponse(BaseModel):
    code: int
    message: str
    data: Any = None


class EmptyData(BaseModel):
    pass


def success_response(data: Any = None, message: str = "成功", code: int = 200) -> dict[str, Any]:
    return {"code": code, "message": message, "data": data}


def _apply_soft_delete(user: User) -> None:
    """对不同模型字段做兼容软删除。"""

    if hasattr(user, "is_deleted"):
        setattr(user, "is_deleted", True)
    elif hasattr(user, "deleted_at"):
        setattr(user, "deleted_at", datetime.utcnow())
    elif hasattr(user, "status"):
        setattr(user, "status", False)


router = APIRouter(prefix="/api/v1/user", tags=["User"])


@router.get("/get_user_list", response_model=ApiResponse)
async def get_user_list(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: str = Query("", description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """获取用户列表（GET 查询）。"""

    try:
        logger.info(
            "[API] 获取用户列表 - 页码: %s, 每页: %s, 关键词: %s, 操作人: %s",
            page,
            per_page,
            keyword,
            current_user.get("uid"),
        )

        stmt = select(User)
        if keyword.strip():
            stmt = stmt.where(User.username.like(f"%{keyword.strip()}%"))

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(total_stmt)
        total = total_result.scalar_one()

        result = await db.execute(stmt.offset((page - 1) * per_page).limit(per_page))
        users = result.scalars().all()

        data = UserListData(
            total=total,
            page=page,
            per_page=per_page,
            items=[UserRead.model_validate(user) for user in users],
        )
        return success_response(data.model_dump())
    except Exception as exc:
        logger.error("[API] 获取用户列表失败: %s", str(exc), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取用户列表失败")


@router.get("/get_user_detail/{user_id}", response_model=ApiResponse)
async def get_user_detail(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """获取用户详情（GET 查询）。"""

    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            logger.warning("[API] 用户不存在 - ID: %s, 操作人: %s", user_id, current_user.get("uid"))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

        return success_response(UserRead.model_validate(user).model_dump())
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[API] 获取用户详情失败: %s", str(exc), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取用户详情失败")


@router.post("/create_user", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """创建用户（POST 变更）。"""

    try:
        exists_result = await db.execute(select(User).where(User.username == payload.username))
        if exists_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")

        user = User(username=payload.username, email=payload.email)
        user.set_password(payload.password)

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info("[API] 创建用户成功 - 用户名: %s, 操作人: %s", payload.username, current_user.get("uid"))
        return success_response(UserRead.model_validate(user).model_dump(), "创建成功", 201)
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.error("[API] 创建用户失败: %s", str(exc), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="创建用户失败")


@router.post("/update_user", response_model=ApiResponse)
async def update_user(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """更新用户（POST 变更）。"""

    try:
        result = await db.execute(select(User).where(User.id == payload.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

        if payload.email is not None:
            user.email = payload.email
        if payload.password:
            user.set_password(payload.password)

        await db.commit()
        await db.refresh(user)

        logger.info("[API] 更新用户成功 - ID: %s, 操作人: %s", payload.user_id, current_user.get("uid"))
        return success_response(UserRead.model_validate(user).model_dump(), "更新成功")
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.error("[API] 更新用户失败: %s", str(exc), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新用户失败")


@router.post("/delete_user", response_model=ApiResponse)
async def delete_user(
    payload: UserDelete,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """删除用户（POST 软删除）。"""

    try:
        result = await db.execute(select(User).where(User.id == payload.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

        _apply_soft_delete(user)
        await db.commit()

        logger.info("[API] 删除用户成功(软删除) - ID: %s, 操作人: %s", payload.user_id, current_user.get("uid"))
        return success_response(None, "删除成功")
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.error("[API] 删除用户失败: %s", str(exc), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="删除用户失败")


@router.post("/change_user_status", response_model=ApiResponse)
async def change_user_status(
    payload: UserStatusChange,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """状态变更（POST 变更）。"""

    try:
        result = await db.execute(select(User).where(User.id == payload.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

        if not hasattr(user, "status"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户模型无 status 字段")

        user.status = payload.status
        await db.commit()
        await db.refresh(user)

        logger.info(
            "[API] 用户状态变更成功 - ID: %s, 状态: %s, 操作人: %s",
            payload.user_id,
            payload.status,
            current_user.get("uid"),
        )
        return success_response(UserRead.model_validate(user).model_dump(), "状态变更成功")
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.error("[API] 用户状态变更失败: %s", str(exc), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="状态变更失败")


@router.post("/query_users_complex", response_model=ApiResponse)
async def query_users_complex(
    payload: UserComplexQuery,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """复杂查询（POST 查询场景）。"""

    try:
        stmt = select(User)

        if payload.keywords:
            keyword_conditions = [User.username.like(f"%{kw.strip()}%") for kw in payload.keywords if kw.strip()]
            if keyword_conditions:
                stmt = stmt.where(*keyword_conditions)

        if payload.email_domain:
            stmt = stmt.where(User.email.like(f"%@{payload.email_domain}"))

        if payload.created_after and hasattr(User, "created_at"):
            stmt = stmt.where(User.created_at >= payload.created_after)

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(total_stmt)
        total = total_result.scalar_one()

        result = await db.execute(
            stmt.offset((payload.page - 1) * payload.per_page).limit(payload.per_page)
        )
        users = result.scalars().all()

        logger.info("[API] 复杂查询成功 - 操作人: %s", current_user.get("uid"))

        data = UserListData(
            total=total,
            page=payload.page,
            per_page=payload.per_page,
            items=[UserRead.model_validate(user) for user in users],
        )
        return success_response(data.model_dump())
    except Exception as exc:
        logger.error("[API] 复杂查询失败: %s", str(exc), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="复杂查询失败")
