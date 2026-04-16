#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2026/04/16 1010
# @Author  : xx
# @File    : datatable_example.py
# @Desc    : 图文回复数据模型示例（SQLAlchemy 2.0）

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class WxImgText(Base):
    """微信公众号图文回复模型示例。"""

    __tablename__ = "wx_imgtext"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(50), index=True, nullable=False, comment="关键词")
    title: Mapped[str] = mapped_column(String(60), nullable=False, comment="图文标题")
    intro: Mapped[str | None] = mapped_column(String(300), comment="图文简介")
    img_url: Mapped[str | None] = mapped_column(String(300), comment="封面链接")
    content_url: Mapped[str | None] = mapped_column(String(300), comment="正文链接")
    content: Mapped[str | None] = mapped_column(Text, comment="回复内容")
    is_img: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否显示封面")
    status: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="状态")
    match_type: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="1完全匹配 2模糊匹配")
    read_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="阅读量")
    praise_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="点赞量")
    sort: Mapped[int] = mapped_column(Integer, default=100, nullable=False, comment="排序")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "keyword": self.keyword,
            "title": self.title,
            "intro": self.intro,
            "img_url": self.img_url,
            "content_url": self.content_url,
            "content": self.content,
            "is_img": self.is_img,
            "status": self.status,
            "match_type": self.match_type,
            "read_count": self.read_count,
            "praise_count": self.praise_count,
            "sort": self.sort,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
