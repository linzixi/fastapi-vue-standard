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

## Base 基类设计

### 推荐的 Base 类实现

所有模型继承统一的 `Base` 基类，内置公共字段和通用方法，减少重复代码。

```python
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """全局基类，内置 id / created_at / updated_at 公共字段。"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_dict(self, exclude: set[str] | None = None) -> dict[str, Any]:
        """通用序列化：遍历列属性，自动处理 datetime → ISO 格式。"""
        exclude = exclude or set()
        result: dict[str, Any] = {}
        for col in self.__table__.columns:
            if col.name in exclude:
                continue
            value = getattr(self, col.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[col.name] = value
        return result
```

> **约定**：业务模型不再重复声明 `id` / `created_at` / `updated_at`，直接继承即可。

### 软删除 Mixin

需要软删除的表混入 `SoftDeleteMixin`，配合查询过滤即可。

```python
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


class SoftDeleteMixin:
    """软删除 Mixin：deleted_at 为 NULL 表示未删除。"""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True, index=True
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

使用示例：

```python
class Article(SoftDeleteMixin, Base):
    __tablename__ = "article"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
```

查询时统一追加过滤条件：

```python
stmt = select(Article).where(Article.deleted_at.is_(None))
```

---

## 字段类型最佳实践

### 常用字段类型对照表

| Python 类型 | SQLAlchemy 类型 | MySQL 类型 | 适用场景 |
|---|---|---|---|
| `int` | `Integer` | `INT` | 主键、计数、状态码 |
| `int` | `BigInteger` | `BIGINT` | 雪花 ID、超大计数 |
| `str` | `String(n)` | `VARCHAR(n)` | 短文本（用户名、标题） |
| `str` | `Text` | `TEXT` | 长文本（正文、备注） |
| `bool` | `Boolean` | `TINYINT(1)` | 开关、标记 |
| `float` | `Float` | `FLOAT` | 非精确浮点 |
| `Decimal` | `Numeric(10, 2)` | `DECIMAL(10,2)` | 金额、比率（需精确） |
| `datetime` | `DateTime(timezone=True)` | `DATETIME` | 时间戳 |
| `date` | `Date` | `DATE` | 仅日期 |
| `dict` / `list` | `JSON` | `JSON` | 动态结构数据 |

### 枚举字段处理

推荐使用 Python `enum.IntEnum` + `Integer` 存储，而非数据库原生 `ENUM`（方便扩展，避免 DDL 变更）。

```python
import enum

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class OrderStatus(enum.IntEnum):
    PENDING = 0
    PAID = 1
    SHIPPED = 2
    COMPLETED = 3
    CANCELLED = -1


class Order(Base):
    __tablename__ = "order"

    order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[int] = mapped_column(
        Integer, default=OrderStatus.PENDING, nullable=False, comment="订单状态"
    )
```

> **原则**：枚举值与含义在代码层维护，数据库只存整数，降低迁移成本。

### JSON 字段使用

**适用场景**：非结构化扩展属性、用户偏好设置、第三方回调原始数据。

**注意事项**：
- JSON 字段**不可建普通索引**（MySQL 需虚拟列 + 索引）
- 不要用 JSON 代替正常的关系建模
- 读取后为 `dict` / `list`，注意做空值防御

```python
from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column


class UserProfile(Base):
    __tablename__ = "user_profile"

    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    extra: Mapped[dict | None] = mapped_column(JSON, default=None, comment="扩展配置")
```

### Text vs String 的选择

| 场景 | 推荐类型 | 原因 |
|---|---|---|
| 长度可预期 ≤ 500 字符 | `String(n)` | 可加索引，存储更紧凑 |
| 长度不可预期（正文/HTML） | `Text` | 无长度限制 |
| 需要按内容模糊搜索 | `String(n)` 或全文索引 | `Text` 默认不可索引 |

---

## 索引策略

### 单列索引 vs 复合索引

- **单列索引**：适用于单条件查询或低基数过滤（如 `status`）
- **复合索引**：适用于固定组合的多条件查询，遵循**最左前缀**原则

```python
from sqlalchemy import Index, String, Integer
from sqlalchemy.orm import Mapped, mapped_column


class Product(Base):
    __tablename__ = "product"

    __table_args__ = (
        Index("ix_product_category_status", "category_id", "status"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
```

### 唯一索引

- 业务唯一字段必须添加唯一索引（如手机号、订单号、邀请码）
- 软删除场景下，唯一索引需包含 `deleted_at` 避免冲突

```python
from sqlalchemy import UniqueConstraint

class Invitation(Base):
    __tablename__ = "invitation"

    __table_args__ = (
        UniqueConstraint("code", "deleted_at", name="uq_invitation_code"),
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False)
```

### 索引命名规范

| 类型 | 格式 | 示例 |
|---|---|---|
| 普通索引 | `ix_{table}_{col}` | `ix_product_category_id` |
| 复合索引 | `ix_{table}_{col1}_{col2}` | `ix_product_category_status` |
| 唯一索引 | `uq_{table}_{col}` | `uq_user_email` |

### 避免过度索引

- 写多读少的表（如日志表）控制索引数量 ≤ 3
- 不要对低基数列（如 `gender`）单独建索引
- 定期审查慢查询日志，按需增删索引

---

## 查询性能优化

### offset 分页 vs 游标分页

| 方式 | 优点 | 缺点 | 适用场景 |
|---|---|---|---|
| offset 分页 | 实现简单，支持跳页 | 深页性能差（`OFFSET 10000`） | 后台管理、数据量 < 10 万 |
| 游标分页 | 性能稳定，不受深度影响 | 不支持跳页 | C 端列表、无限滚动、大数据量 |

**offset 分页**（后台管理推荐）：

```python
from sqlalchemy import select

async def paginate_offset(session, page: int = 1, size: int = 20):
    stmt = (
        select(Article)
        .where(Article.deleted_at.is_(None))
        .order_by(Article.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await session.execute(stmt)
    return result.scalars().all()
```

**游标分页**（C 端推荐）：

```python
async def paginate_cursor(session, cursor: int | None = None, size: int = 20):
    stmt = (
        select(Article)
        .where(Article.deleted_at.is_(None))
        .order_by(Article.id.desc())
        .limit(size)
    )
    if cursor is not None:
        stmt = stmt.where(Article.id < cursor)
    result = await session.execute(stmt)
    items = result.scalars().all()
    next_cursor = items[-1].id if items else None
    return items, next_cursor
```

### 批量插入 / 更新

避免循环逐条操作，使用批量 API：

```python
from sqlalchemy import insert, update

# 批量插入
async def bulk_create(session, records: list[dict]):
    stmt = insert(Article).values(records)
    await session.execute(stmt)
    await session.commit()

# 批量更新（按条件）
async def bulk_update_status(session, ids: list[int], status: int):
    stmt = (
        update(Article)
        .where(Article.id.in_(ids))
        .values(status=status)
    )
    await session.execute(stmt)
    await session.commit()
```

> **注意**：单次批量操作建议控制在 500 ~ 1000 条，过大可能锁表或超时。

### N+1 查询的识别和解决

**症状**：查询列表时，每条记录额外触发一次关联查询，导致 SQL 数量 = 1 + N。

**解决方案**：使用 `selectinload` 或 `joinedload` 预加载关联数据。

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

# selectinload：用 IN 子查询加载（推荐，适合一对多）
stmt = (
    select(Article)
    .options(selectinload(Article.comments))
    .order_by(Article.id.desc())
)

# joinedload：用 JOIN 一次加载（适合多对一、一对一）
stmt = (
    select(Comment)
    .options(joinedload(Comment.author))
    .order_by(Comment.id.desc())
)
```

### selectinload vs joinedload 选择

| 策略 | SQL 方式 | 适用关系 | 注意 |
|---|---|---|---|
| `selectinload` | `SELECT ... WHERE id IN (...)` | 一对多、多对多 | 避免笛卡尔积，分页友好 |
| `joinedload` | `LEFT JOIN` | 多对一、一对一 | 一对多时会产生重复行，影响分页 |

> **原则**：默认用 `selectinload`，仅在多对一 / 一对一且需要过滤关联字段时用 `joinedload`。

---

## 数据库连接配置

### 连接池参数建议

| 参数 | 建议值 | 说明 |
|---|---|---|
| `pool_size` | 10 ~ 20 | 常驻连接数，按并发量调整 |
| `max_overflow` | 10 | 超出 pool_size 后的最大临时连接 |
| `pool_timeout` | 30 | 获取连接的最大等待秒数 |
| `pool_recycle` | 1800 | 连接回收时间（秒），避免 MySQL `wait_timeout` 断连 |
| `pool_pre_ping` | True | 每次取连接前发 ping，剔除死连接 |

### 异步引擎配置示例

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "mysql+aiomysql://user:password@127.0.0.1:3306/mydb?charset=utf8mb4"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=10,
    max_overflow=10,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=False,  # 生产环境关闭 SQL 日志
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """FastAPI 依赖注入：获取异步数据库会话。"""
    async with AsyncSessionLocal() as session:
        yield session
```

> **生产建议**：`echo=False`，`pool_size` 根据服务实例数 × 并发估算，总连接数不超过数据库 `max_connections` 的 80%。

---

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
- [ ] 模型继承自统一 Base 基类，未重复声明公共字段
- [ ] 软删除表已混入 SoftDeleteMixin，查询统一过滤 deleted_at
- [ ] 枚举字段使用 IntEnum + Integer 存储，未使用数据库原生 ENUM
- [ ] JSON 字段仅用于非结构化扩展数据，未替代关系建模
- [ ] 索引命名遵循 `ix_` / `uq_` 前缀规范
- [ ] 写多读少的表索引数量 ≤ 3
- [ ] 列表查询已处理 N+1 问题（selectinload / joinedload）
- [ ] 大数据量分页已评估是否需要游标分页
- [ ] 批量操作使用 bulk API，单次不超过 1000 条
- [ ] 数据库连接池参数已按部署环境调优
