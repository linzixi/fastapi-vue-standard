# 测试规范

## 1. 测试目录结构

```text
backend/tests/
├── conftest.py          # 全局 fixture（数据库 session、测试用户、app 实例等）
├── unit/                # 单元测试
│   ├── services/        # Service 层测试
│   └── repositories/    # Repository 层测试
├── integration/         # 集成测试
│   └── api/             # API 端点测试
└── fixtures/            # 测试数据（JSON / 工厂函数）

frontend/tests/
├── setup.js             # Vitest 全局 setup
├── components/          # 组件测试
└── utils/               # 工具函数测试
```

---

## 2. 后端测试规范（pytest）

### 2.1 pytest 配置

在 `pyproject.toml` 中统一配置：

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers -p no:warnings"
markers = [
    "slow: 耗时较长的测试",
    "integration: 集成测试",
]
filterwarnings = [
    "ignore::DeprecationWarning",
]
```

### 2.2 Fixture 管理规范

全局 fixture 统一放在 `tests/conftest.py`，子目录可追加局部 `conftest.py`。

```python
import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base_class import Base
from app.main import app


TEST_DATABASE_URL = settings.TEST_DATABASE_URL  # 使用独立的测试库


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db) -> AsyncGenerator[AsyncClient, None]:
    """提供绑定了测试数据库的 httpx.AsyncClient"""
    from app.core.deps import get_db

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db: AsyncSession):
    """创建并返回一个测试用户"""
    from app.models.user import User

    user = User(username="testuser", email="test@example.com")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def auth_client(client: AsyncClient, test_user):
    """携带认证 Token 的测试客户端"""
    from app.core.security import create_access_token

    token = create_access_token(subject=test_user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return client
```

**Fixture 原则：**
- `scope="session"`：数据库引擎、event loop 等重量级资源
- `scope="function"`（默认）：db session、测试数据，每个用例结束后自动回滚
- 禁止在 fixture 中硬编码密码、Token 等敏感信息，统一从配置或工厂函数获取

### 2.3 异步测试写法

使用 `pytest-asyncio`，配合 `asyncio_mode = "auto"` 后无需手动标记 `@pytest.mark.asyncio`：

```python
async def test_should_return_user_when_valid_id(db: AsyncSession):
    repo = UserRepository()
    user = await repo.get_by_id(db, user_id=1)
    assert user is not None
    assert user.id == 1
```

### 2.4 测试命名规范

格式：`test_should_{预期行为}_when_{条件}`

```python
# ✅ 正确示例
def test_should_create_order_when_valid_payload():
    ...

def test_should_raise_not_found_when_order_id_invalid():
    ...

def test_should_return_empty_list_when_no_orders_exist():
    ...

# ❌ 错误示例
def test_order():          # 含义不清
    ...

def test_create():         # 无法区分成功还是失败用例
    ...

def test_1():              # 毫无语义
    ...
```

### 2.5 测试结构：Arrange / Act / Assert

每个测试用例严格按三段式组织，段之间用空行分隔：

```python
async def test_should_calculate_total_when_items_provided(db: AsyncSession):
    # Arrange
    service = OrderService()
    order = await create_test_order(db, items=[
        {"product_id": 1, "quantity": 2, "price": 100},
        {"product_id": 2, "quantity": 1, "price": 50},
    ])

    # Act
    total = await service.calculate_total(db, order_id=order.id)

    # Assert
    assert total == 250
```

### 2.6 Service 层单元测试示例

```python
from unittest.mock import AsyncMock

from app.services.order import OrderService
from app.schemas.order import OrderCreate


async def test_should_create_order_when_valid_payload():
    # Arrange
    mock_repo = AsyncMock()
    mock_repo.create.return_value = {"id": 1, "status": "pending"}
    service = OrderService(repo=mock_repo)
    payload = OrderCreate(product_id=1, quantity=2)

    # Act
    result = await service.create_order(db=AsyncMock(), payload=payload, operator_id=1)

    # Assert
    mock_repo.create.assert_called_once()
    assert result["status"] == "pending"


async def test_should_raise_error_when_stock_insufficient():
    # Arrange
    mock_repo = AsyncMock()
    mock_repo.check_stock.return_value = 0
    service = OrderService(repo=mock_repo)
    payload = OrderCreate(product_id=1, quantity=100)

    # Act & Assert
    with pytest.raises(BusinessException, match="库存不足"):
        await service.create_order(db=AsyncMock(), payload=payload, operator_id=1)
```

### 2.7 API 集成测试示例

```python
import pytest
from httpx import AsyncClient


async def test_should_return_order_list_when_authenticated(auth_client: AsyncClient):
    # Act
    response = await auth_client.get("/api/v1/orders", params={"page": 1, "page_size": 10})

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert "items" in body["data"]


async def test_should_return_401_when_no_token(client: AsyncClient):
    # Act
    response = await client.get("/api/v1/orders")

    # Assert
    assert response.status_code == 401


async def test_should_return_403_when_no_permission(auth_client: AsyncClient):
    # Act（test_user 不具备 admin 权限）
    response = await auth_client.post("/api/v1/users/delete", json={"ids": [999]})

    # Assert
    assert response.status_code == 403


async def test_should_create_order_when_valid_data(auth_client: AsyncClient):
    # Arrange
    payload = {"product_id": 1, "quantity": 2}

    # Act
    response = await auth_client.post("/api/v1/orders", json=payload)

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["id"] is not None
```

---

## 3. Mock 策略

### 3.1 数据库 Mock

**推荐方案：使用独立的测试数据库**

- 开发环境使用 PostgreSQL / MySQL 作为测试库，通过 `TEST_DATABASE_URL` 配置
- 每个测试用例通过事务回滚隔离数据，无需清表
- 简单场景可使用 SQLite 异步驱动 `aiosqlite`（注意 SQLite 不支持部分 PostgreSQL 特性）

```python
# .env.test
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app_test
# 或轻量方案
TEST_DATABASE_URL=sqlite+aiosqlite:///./test.db
```

### 3.2 外部服务 Mock

使用 `unittest.mock` 或 `pytest-mock` 对外部服务调用进行 Mock：

```python
from unittest.mock import AsyncMock, patch


async def test_should_send_notification_when_order_created():
    # Arrange
    with patch("app.services.notification.NotificationClient.send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"status": "sent"}
        service = OrderService()

        # Act
        await service.create_and_notify(db=AsyncMock(), payload=payload, operator_id=1)

        # Assert
        mock_send.assert_called_once()
```

**pytest-mock 写法（更简洁）：**

```python
async def test_should_send_sms_when_order_paid(mocker):
    mock_sms = mocker.patch("app.services.sms.SmsClient.send", new_callable=AsyncMock)
    mock_sms.return_value = True

    service = PaymentService()
    await service.process_payment(db=AsyncMock(), order_id=1)

    mock_sms.assert_called_once()
```

### 3.3 Redis Mock

使用 `fakeredis` 库替换真实 Redis 连接：

```python
import fakeredis.aioredis


@pytest.fixture
async def redis():
    return fakeredis.aioredis.FakeRedis()


async def test_should_cache_user_info(redis):
    from app.services.cache import CacheService

    service = CacheService(redis=redis)
    await service.set_user_cache(user_id=1, data={"name": "test"})

    cached = await service.get_user_cache(user_id=1)
    assert cached["name"] == "test"
```

### 3.4 何时用 Mock、何时用真实依赖

| 场景 | 策略 | 理由 |
|------|------|------|
| 数据库操作 | 真实测试库 + 事务回滚 | 验证 SQL / ORM 的真实行为 |
| 外部 HTTP 调用（短信、支付等） | Mock | 不可控、有费用、不稳定 |
| Redis 缓存 | fakeredis 或真实 Redis | 简单场景用 fakeredis，复杂 Lua 脚本用真实 Redis |
| 文件系统 | `tmp_path` fixture | pytest 内置支持，自动清理 |
| 时间相关 | `freezegun` 或 `time-machine` | 保证测试确定性 |
| Service 依赖的 Repository | Mock（单元测试）/ 真实（集成测试） | 单元测试隔离依赖，集成测试验证串联 |

---

## 4. 前端测试规范（Vitest）

### 4.1 基本配置

```javascript
// vite.config.js（追加 test 配置）
export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.js'],
    include: ['tests/**/*.test.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{js,vue}'],
      exclude: ['src/main.js', 'src/router/**'],
    },
  },
})
```

```javascript
// tests/setup.js
import { config } from '@vue/test-utils'
import ElementPlus from 'element-plus'

config.global.plugins = [ElementPlus]
```

### 4.2 组件测试基本要求

- 每个可复用组件（`components/` 下）应有对应测试文件
- 页面组件优先测试关键交互流程，无需覆盖所有 UI 细节
- 测试文件放在 `frontend/tests/components/` 下，与源文件同名

```javascript
// tests/components/UserCard.test.js
import { mount } from '@vue/test-utils'
import UserCard from '@/components/UserCard.vue'

describe('UserCard', () => {
  it('should render username when props provided', () => {
    const wrapper = mount(UserCard, {
      props: { username: '张三', role: 'admin' },
    })

    expect(wrapper.text()).toContain('张三')
    expect(wrapper.text()).toContain('admin')
  })

  it('should emit edit event when edit button clicked', async () => {
    const wrapper = mount(UserCard, {
      props: { username: '张三', role: 'admin' },
    })

    await wrapper.find('[data-test="edit-btn"]').trigger('click')

    expect(wrapper.emitted('edit')).toHaveLength(1)
  })
})
```

### 4.3 API Mock

**方案一：vi.mock（简单场景）**

```javascript
import { vi } from 'vitest'

vi.mock('@/api/user', () => ({
  getUserList: vi.fn().mockResolvedValue({
    code: 200,
    data: { items: [{ id: 1, name: '张三' }], total: 1 },
  }),
}))
```

**方案二：MSW（需要验证请求细节时）**

```javascript
// tests/mocks/handlers.js
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/v1/users', () => {
    return HttpResponse.json({
      code: 200,
      data: { items: [{ id: 1, name: '张三' }], total: 1 },
    })
  }),
]
```

### 4.4 测试命名规范

- 使用 `describe` 按组件 / 模块分组
- 使用 `it('should ... when ...')` 描述预期行为

```javascript
describe('OrderList', () => {
  it('should display loading state when fetching data', () => { ... })
  it('should render order items when data loaded', () => { ... })
  it('should show empty state when no orders', () => { ... })
})
```

---

## 5. 测试覆盖率要求

| 层级 | 最低覆盖率 | 说明 |
|------|-----------|------|
| Service 层 | >= 80% | 核心业务逻辑，必须高覆盖 |
| Repository 层 | >= 70% | 重点覆盖复杂查询与边界条件 |
| API 端点 | >= 60% | 至少覆盖成功用例 + 主要失败用例（401/403/400） |
| 工具函数 | >= 90% | 纯函数，易测试，应尽量全覆盖 |
| 前端组件 | >= 50% | 可复用组件优先，页面组件覆盖关键交互 |

**运行覆盖率报告：**

```bash
# 后端
pytest --cov=app --cov-report=term-missing --cov-report=html:htmlcov

# 前端
npx vitest run --coverage
```

---

## 6. CI 集成

### 6.1 测试命令标准化

```bash
# 后端测试
cd backend
pytest                                     # 运行全部测试
pytest tests/unit/                         # 只运行单元测试
pytest tests/integration/                  # 只运行集成测试
pytest -m "not slow"                       # 排除耗时测试
pytest --cov=app --cov-fail-under=70       # 覆盖率门禁

# 前端测试
cd frontend
npx vitest run                             # 运行全部测试
npx vitest run --coverage                  # 带覆盖率
```

### 6.2 覆盖率报告生成

```yaml
# .github/workflows/test.yml（参考片段）
jobs:
  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: app_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r backend/requirements.txt
      - run: |
          cd backend
          pytest --cov=app --cov-report=xml:coverage.xml --cov-fail-under=70
      - uses: codecov/codecov-action@v4
        with:
          files: backend/coverage.xml

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "18"
      - run: cd frontend && pnpm install
      - run: cd frontend && npx vitest run --coverage
```

### 6.3 测试失败阻断合并

- CI 流水线中后端测试或前端测试任一失败，**必须阻断 PR 合并**
- 在 GitHub 仓库 Settings → Branches → Branch protection rules 中，将 `backend-test` 和 `frontend-test` 设为 required status checks
- 覆盖率低于阈值同样视为失败（通过 `--cov-fail-under` 控制）

---

## 7. 检查清单

### 测试编写
- [ ] 测试命名遵循 `test_should_{预期行为}_when_{条件}` 格式
- [ ] 测试结构遵循 Arrange / Act / Assert 三段式
- [ ] 每个 Service 公开方法至少有成功和失败两个测试用例
- [ ] API 端点至少覆盖 200 成功、参数校验失败（400）、未认证（401）用例

### Fixture 与 Mock
- [ ] 全局 fixture 放在 `tests/conftest.py`，避免重复创建
- [ ] 数据库测试使用事务回滚隔离，不依赖执行顺序
- [ ] 外部服务调用已 Mock，测试不依赖网络
- [ ] Mock 的返回值贴近真实数据结构

### 覆盖率与 CI
- [ ] 本地可通过 `pytest --cov` 和 `vitest --coverage` 生成报告
- [ ] CI 流水线配置了测试步骤和覆盖率门禁
- [ ] 测试失败或覆盖率不达标时 PR 无法合并

### 前端测试
- [ ] 可复用组件有对应的测试文件
- [ ] API 调用已通过 `vi.mock` 或 MSW 隔离
- [ ] 测试使用 `data-test` 属性选取元素，不依赖 CSS 类名
