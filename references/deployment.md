# 部署与运维规范

---

## 1. 环境分层

### 1.1 环境定义

| 环境 | 标识 | 用途 | 访问范围 |
|------|------|------|----------|
| 开发环境 | `dev` | 本地开发与联调，允许频繁重启和调试 | 开发人员 |
| 预发布环境 | `staging` | 与生产环境配置一致，用于上线前验收测试 | 开发 + 测试人员 |
| 生产环境 | `production` | 对外提供服务，稳定性优先 | 全部用户 |

### 1.2 环境标识管理

- 通过环境变量 `APP_ENV` 统一标识当前环境
- 所有与环境相关的行为（日志级别、DEBUG 开关、数据库连接等）必须通过环境变量驱动，禁止在代码中硬编码环境判断

```python
# ✅ 正确：通过配置驱动
logger.setLevel(settings.LOG_LEVEL)

# ❌ 错误：硬编码环境判断
if os.getenv("APP_ENV") == "dev":
    logger.setLevel("DEBUG")
```

---

## 2. 环境变量管理

### 2.1 .env 文件规范

| 文件 | 是否入库 | 说明 |
|------|----------|------|
| `.env.example` | ✅ 入库 | 变量名 + 占位值，供团队成员拷贝使用 |
| `.env` | ❌ 不入库 | 本地实际配置，加入 `.gitignore` |
| `.env.staging` | ❌ 不入库 | 预发布环境配置，由 CI/CD 或运维管理 |
| `.env.production` | ❌ 不入库 | 生产环境配置，由 CI/CD 或运维管理 |

`.env.example` 示例：

```dotenv
# ========== 应用 ==========
APP_ENV=dev
APP_NAME=my-project
APP_HOST=0.0.0.0
APP_PORT=8000
SECRET_KEY=change-me

# ========== 数据库 ==========
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=change-me
DB_NAME=my_project

# ========== Redis ==========
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# ========== 日志 ==========
LOG_LEVEL=DEBUG
```

### 2.2 FastAPI BaseSettings 分层配置

```python
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """所有环境共享的基础配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "my-project"
    APP_ENV: str = "dev"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    SECRET_KEY: str = Field(..., min_length=16)

    # 数据库
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "my_project"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # 日志
    LOG_LEVEL: str = "DEBUG"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+asyncmy://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def REDIS_URL(self) -> str:
        password_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


class DevSettings(BaseAppSettings):
    """开发环境特有配置。"""

    APP_ENV: str = "dev"
    LOG_LEVEL: str = "DEBUG"


class StagingSettings(BaseAppSettings):
    """预发布环境特有配置。"""

    APP_ENV: str = "staging"
    LOG_LEVEL: str = "INFO"


class ProductionSettings(BaseAppSettings):
    """生产环境特有配置。"""

    APP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"


_env_map: dict[str, type[BaseAppSettings]] = {
    "dev": DevSettings,
    "staging": StagingSettings,
    "production": ProductionSettings,
}


@lru_cache
def get_settings() -> BaseAppSettings:
    env = BaseAppSettings().APP_ENV
    settings_cls = _env_map.get(env, DevSettings)
    return settings_cls()


settings = get_settings()
```

### 2.3 必需环境变量清单模板

在 `app/core/config.py` 中为关键字段设置 `Field(...)`，应用启动时若缺失将立即报错：

```python
SECRET_KEY: str = Field(..., min_length=16)
DB_PASSWORD: str = Field(...)
```

推荐在启动脚本或 CI 中增加前置校验：

```python
REQUIRED_VARS = ["SECRET_KEY", "DB_HOST", "DB_PASSWORD", "REDIS_HOST"]

def check_env():
    import os
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        raise RuntimeError(f"缺少必需环境变量: {', '.join(missing)}")
```

---

## 3. Docker 标准化

### 3.1 后端 Dockerfile

采用多阶段构建，使用非 root 用户运行：

```dockerfile
# ---- 构建阶段 ----
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- 运行阶段 ----
FROM python:3.12-slim

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.2 前端 Dockerfile

构建产物 + Nginx 静态托管：

```dockerfile
# ---- 构建阶段 ----
FROM node:20-alpine AS builder

WORKDIR /build
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

# ---- 运行阶段 ----
FROM nginx:1.27-alpine

COPY --from=builder /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 3.3 docker-compose.yml 示例

```yaml
version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
      MYSQL_DATABASE: ${DB_NAME}
      MYSQL_USER: ${DB_USER}
      MYSQL_PASSWORD: ${DB_PASSWORD}
    ports:
      - "3306:3306"
    volumes:
      - db_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  db_data:
  redis_data:
```

### 3.4 .dockerignore

后端和前端各自维护 `.dockerignore`，避免将无关文件打入镜像：

```
# backend/.dockerignore
__pycache__
*.pyc
.env
.env.*
.git
.vscode
tests/
*.md

# frontend/.dockerignore
node_modules
.env
.env.*
.git
.vscode
tests/
*.md
dist
```

---

## 4. CI/CD 流水线

### 4.1 标准阶段

```
┌───────┐    ┌───────┐    ┌───────┐    ┌────────┐
│ Lint  │ →  │ Test  │ →  │ Build │ →  │ Deploy │
└───────┘    └───────┘    └───────┘    └────────┘
```

| 阶段 | 后端 | 前端 |
|------|------|------|
| Lint | `ruff check .` + `ruff format --check .` | `eslint . --max-warnings 0` |
| Test | `pytest --cov --cov-fail-under=80` | `vitest run --coverage` |
| Build | `docker build -t backend:$TAG .` | `docker build -t frontend:$TAG .` |
| Deploy | 推送镜像 → 更新服务 | 推送镜像 → 更新服务 |

### 4.2 GitHub Actions 示例

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_PREFIX: ${{ github.repository }}

jobs:
  # ---------- 后端 ----------
  backend-lint:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: ruff check .
      - run: ruff format --check .

  backend-test:
    runs-on: ubuntu-latest
    needs: backend-lint
    defaults:
      run:
        working-directory: backend
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: test_root
          MYSQL_DATABASE: test_db
        ports:
          - 3306:3306
        options: >-
          --health-cmd="mysqladmin ping -h localhost"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd="redis-cli ping"
          --health-interval=10s
          --health-timeout=3s
          --health-retries=5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pytest --cov --cov-fail-under=80
        env:
          DB_HOST: 127.0.0.1
          DB_PORT: 3306
          DB_USER: root
          DB_PASSWORD: test_root
          DB_NAME: test_db
          REDIS_HOST: 127.0.0.1

  # ---------- 前端 ----------
  frontend-lint:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: corepack enable && pnpm install --frozen-lockfile
      - run: pnpm lint

  frontend-test:
    runs-on: ubuntu-latest
    needs: frontend-lint
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: corepack enable && pnpm install --frozen-lockfile
      - run: pnpm test:ci

  # ---------- 构建与推送镜像 ----------
  build-and-push:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    needs: [backend-test, frontend-test]
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_PREFIX }}/backend:${{ github.sha }}
      - uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_PREFIX }}/frontend:${{ github.sha }}
```

### 4.3 自动化检查项

每次 PR 合并前必须通过以下检查：

- [ ] Lint 无错误（后端 ruff + 前端 ESLint）
- [ ] 单元测试全部通过
- [ ] 测试覆盖率 ≥ 80%
- [ ] Docker 镜像构建成功
- [ ] 无新增的安全漏洞（依赖扫描）

---

## 5. 数据库迁移发布

### 5.1 迁移脚本审核

- 每次 PR 包含的 Alembic 迁移文件必须经过至少一人 Code Review
- 审核要点：
  - 是否包含不可逆操作（`DROP TABLE`、`DROP COLUMN`）
  - 大表 `ALTER` 是否会锁表，是否需要 `pt-online-schema-change` 等工具
  - 迁移脚本的 `upgrade()` 和 `downgrade()` 是否对称

### 5.2 发布顺序

严格遵循**先迁移、再部署**的顺序，避免新代码访问尚未变更的数据库结构：

```
1. 备份数据库
2. 执行 alembic upgrade head
3. 验证迁移结果（表结构、数据完整性）
4. 部署新版本后端服务
5. 部署新版本前端服务
6. 执行冒烟测试
```

### 5.3 回滚策略

| 场景 | 回滚操作 |
|------|----------|
| 迁移执行失败 | `alembic downgrade -1` 回退到上一版本 |
| 部署后发现业务异常 | 先回滚应用到上一镜像版本，再评估是否需要回退迁移 |
| 数据损坏 | 从备份恢复，禁止直接手动修改生产数据 |

> **注意**：包含不可逆操作（如删列、删表）的迁移，必须在发布计划中标注"不可回滚"，并在上线前做充分验证。

### 5.4 备份规范

- 生产环境数据库必须配置每日自动备份，保留周期 ≥ 7 天
- 每次发布前手动触发一次全量备份
- 备份文件命名格式：`{db_name}_{YYYYMMDD_HHmmss}.sql.gz`
- 定期验证备份可恢复性（至少每月一次）

---

## 6. 健康检查

### 6.1 /health 接口

每个后端服务必须提供 `/health` 端点，供负载均衡器和容器编排工具探测：

```python
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=["健康检查"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    checks: dict[str, str] = {}
    healthy = True

    # 数据库连接检查
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"
        healthy = False

    # Redis 连接检查
    try:
        from app.core.redis import redis_client
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"
        healthy = False

    status_code = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={"status": "healthy" if healthy else "unhealthy", "checks": checks},
    )
```

响应示例：

```json
// 正常
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "redis": "ok"
  }
}

// 异常
{
  "status": "unhealthy",
  "checks": {
    "database": "ok",
    "redis": "unavailable"
  }
}
```

### 6.2 Docker 健康检查配置

在 `docker-compose.yml` 或 Dockerfile 中配置健康检查（参见 3.3 节示例），确保容器编排工具能自动重启不健康的实例。

---

## 7. 日志与监控

### 7.1 JSON 结构化日志

生产环境日志必须使用 JSON 格式输出，便于日志收集系统解析：

```python
import logging
import json
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(log_level: str = "INFO"):
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)
```

日志输出示例：

```json
{
  "timestamp": "2026-04-16T08:30:00+00:00",
  "level": "INFO",
  "logger": "app.services.order",
  "message": "订单创建成功",
  "module": "order",
  "function": "create_order",
  "line": 42,
  "request_id": "req-abc123"
}
```

### 7.2 日志级别

| 环境 | 日志级别 | 说明 |
|------|----------|------|
| `dev` | `DEBUG` | 输出所有日志，便于本地调试 |
| `staging` | `INFO` | 关闭 DEBUG，减少噪音 |
| `production` | `INFO` | 仅记录 INFO 及以上，WARNING/ERROR 需重点关注 |

- 开发环境可使用可读的文本格式，生产环境必须使用 JSON 格式
- 禁止在日志中输出密码、Token、身份证号等敏感信息

### 7.3 日志收集方案

推荐采用 ELK 或轻量级替代方案：

```
应用 (JSON stdout) → Filebeat / Fluentd → Elasticsearch → Kibana
```

| 组件 | 职责 |
|------|------|
| 应用 | 日志输出到 stdout/stderr（容器标准实践） |
| Filebeat / Fluentd | 日志采集与转发 |
| Elasticsearch | 日志存储与索引 |
| Kibana | 日志查询与可视化 |

- 容器环境下应用**只输出到 stdout/stderr**，不写本地文件
- 通过 Docker 日志驱动或 sidecar 方式采集
- 生产环境日志保留周期 ≥ 30 天

---

## 8. 上线检查清单

每次发布前，由负责人逐项确认：

### 8.1 发布前

- [ ] 所有 CI 检查通过（Lint + Test + Build）
- [ ] 数据库迁移脚本已审核
- [ ] 数据库已完成备份
- [ ] 环境变量已更新（新增变量已同步到目标环境）
- [ ] `.env.example` 已同步更新
- [ ] Docker 镜像已构建并推送到镜像仓库
- [ ] 发布顺序已确认（迁移 → 后端 → 前端）

### 8.2 发布中

- [ ] 数据库迁移执行成功
- [ ] 后端服务启动正常，`/health` 返回 200
- [ ] 前端页面可正常访问
- [ ] 核心业务流程冒烟测试通过

### 8.3 发布后

- [ ] 监控面板无异常告警
- [ ] 日志中无非预期的 ERROR 级别输出
- [ ] 回滚方案已就绪（镜像 tag、迁移版本已记录）
- [ ] 发布记录已归档（包含版本号、变更摘要、发布人、时间）
