#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2026/04/16 1012
# @Author  : xx
# @File    : business_example.py
# @Desc    : 图文回复业务层示例（Repository + Service）

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wx_imgtext import WxImgText


class BusinessException(Exception):
    """业务异常。"""

    def __init__(self, message: str, code: int = 400):
        self.message = message
        self.code = code
        super().__init__(message)


class WxImgTextRepository:
    """图文回复数据访问层。"""

    async def list(
        self,
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
        keyword: str | None = None,
    ) -> tuple[list[WxImgText], int]:
        stmt = select(WxImgText).order_by(WxImgText.sort.asc(), WxImgText.id.desc())
        if keyword:
            stmt = stmt.where(WxImgText.keyword.like(f"%{keyword}%"))

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(total_stmt)
        total = total_result.scalar_one()

        result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
        return result.scalars().all(), total

    async def get_by_id(self, db: AsyncSession, item_id: int) -> WxImgText | None:
        result = await db.execute(select(WxImgText).where(WxImgText.id == item_id))
        return result.scalar_one_or_none()

    async def get_by_keyword_and_title(self, db: AsyncSession, keyword: str, title: str) -> WxImgText | None:
        result = await db.execute(
            select(WxImgText).where(WxImgText.keyword == keyword, WxImgText.title == title)
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: dict[str, Any]) -> WxImgText:
        item = WxImgText(**data)
        db.add(item)
        await db.flush()
        return item

    async def update(self, db: AsyncSession, item: WxImgText, data: dict[str, Any]) -> WxImgText:
        for key, value in data.items():
            setattr(item, key, value)
        await db.flush()
        return item

    async def delete_many(self, db: AsyncSession, items: list[WxImgText]) -> None:
        for item in items:
            await db.delete(item)


class WxImgTextService:
    """图文回复业务层。"""

    def __init__(self, repo: WxImgTextRepository | None = None):
        self.repo = repo or WxImgTextRepository()

    async def list_items(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
    ) -> dict[str, Any]:
        items, total = await self.repo.list(db, page=page, page_size=page_size, keyword=keyword)
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [item.to_dict() for item in items],
        }

    async def create_item(self, db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
        exists = await self.repo.get_by_keyword_and_title(db, payload["keyword"], payload["title"])
        if exists:
            raise BusinessException("关键词和标题组合已存在", code=400)

        async with db.begin():
            item = await self.repo.create(db, payload)

        await db.refresh(item)
        return item.to_dict()

    async def update_item(self, db: AsyncSession, item_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        item = await self.repo.get_by_id(db, item_id)
        if not item:
            raise BusinessException("图文记录不存在", code=404)

        async with db.begin():
            item = await self.repo.update(db, item, payload)

        await db.refresh(item)
        return item.to_dict()

    async def delete_items(self, db: AsyncSession, item_ids: list[int]) -> None:
        if not item_ids:
            raise BusinessException("删除ID不能为空", code=400)

        targets: list[WxImgText] = []
        for item_id in item_ids:
            item = await self.repo.get_by_id(db, item_id)
            if not item:
                raise BusinessException(f"图文记录不存在: {item_id}", code=404)
            targets.append(item)

        async with db.begin():
            await self.repo.delete_many(db, targets)
