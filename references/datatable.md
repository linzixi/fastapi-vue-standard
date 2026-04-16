---
type: "manual"
---

# 数据模型与数据库规范（FastAPI）

## 目标
- 统一数据库建模风格，保证模型可维护、迁移可回滚、性能可预期。

## 文件与目录
- 模型文件放在 `backend/app/models/`
- Schema 文件放在 `backend/app/schemas/`
- 迁移文件放在 `backend/alembic/versions/`

## 建模规范

### 表命名
- 使用 `snake_case`
- 使用语义清晰的名词（如 `user_account`、`order_item`）
- 避免与数据库关键字冲突

### 字段命名
- 主键统一使用 `id`
- 时间字段统一使用 `created_at`、`updated_at`
- 布尔字段使用 `is_` 前缀（如 `is_active`）
- 枚举字段建议使用 `status` + Enum

### 数据类型与约束
- 必填字段显式 `nullable=False`
- 对高频查询字段建立索引
- 对业务唯一字段添加 `UniqueConstraint`
- 绝对禁止使用外键!!!

### 公共字段建议
- `id`: 主键
- `created_at`: 创建时间
- `updated_at`: 更新时间
- `deleted_at`: 软删除时间（可选）

## SQLAlchemy 2.0 推荐写法

```python
from datetime import datetime
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

## 迁移规范（Alembic）
- 变更模型后必须生成迁移脚本
- 每个迁移脚本只做一类变更（建表/加列/索引）
- 必须可回滚（`upgrade` 与 `downgrade` 对应）

```bash
cd backend
alembic revision --autogenerate -m "add user table"
alembic upgrade head
```

## 反模式
- 在模型层写复杂业务逻辑
- 不经迁移直接改线上数据库
- 查询字段无索引导致全表扫描
- 把 JSON 大字段当关系数据滥用

## 检查清单
- [ ] 表与字段命名符合规范
- [ ] 索引与唯一约束已覆盖核心查询场景
- [ ] 外键关系与删除策略明确
- [ ] Alembic 迁移已生成并验证
- [ ] 模型对应 Schema 已同步更新
