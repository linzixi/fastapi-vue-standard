---
type: "manual"
description: "为项目提供通用的 FastAPI + Vue 全栈开发编码规范，覆盖数据建模、业务实现、API设计、前端开发与权限控制。"
---

# FastAPI + Vue 编码规范 Skill

## 概述

此技能用于指导通用后台管理或业务系统的全栈开发，目标是让后端（FastAPI）和前端（Vue）在目录结构、分层设计、接口协议、权限方案和交付质量上保持一致。

## 文件结构

    fastapi-vue-standard/
    ├── SKILL.md                        # 本文件（技能包核心配置）
    ├── references/                     # 各层详细规范文档
    │   ├── api.md                      # API 接口设计规范
    │   ├── business.md                 # 业务层分层规范
    │   ├── datatable.md                # 数据模型与数据库规范
    │   ├── frontend.md                 # Vue 前端开发规范
    │   └── permission.md              # 权限系统规范
    └── examples/                       # 可运行代码示例
        ├── api_example.py              # API 接口示例
        ├── business_example.py         # 业务层示例
        └── datatable_example.py        # 数据模型示例

## 何时使用此技能

在以下场景中使用此技能：
- 新建 FastAPI + Vue 项目
- 为现有系统新增业务模块
- 统一团队编码风格和分层架构
- 设计可维护的 RBAC 权限体系
- 建立可持续的测试与发布流程


## 推荐目录结构

```text
project/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/endpoints/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   └── services/
│   ├── alembic/
│   └── tests/
└── frontend/
    ├── src/
    │   ├── api/
    │   ├── components/
    │   ├── router/
    │   ├── store/
    │   ├── utils/
    │   └── views/
    └── tests/
```

## 核心能力

1. 数据建模规范（SQLAlchemy 2 + Alembic）
2. 业务分层规范（Router / Service / Repository）
3. API 设计规范（简化 RESTful：GET/POST + Pydantic）
4. Vue 页面与状态管理规范（Vue 3 + JavaScript）
5. 权限系统规范（RBAC + 前后端联动）
6. 质量门禁规范（Lint、测试、类型检查）

## 执行流程

### 第一步：需求拆解
- 明确业务边界、核心实体、角色与权限范围
- 输出实体关系、接口清单、页面清单

### 第二步：数据库与模型设计
- 读取 `references/datatable.md`（详细参考文档）
- 读取 `examples/datatable_example.py`（代码示例）
- 先确定表结构、索引、约束，再实现 SQLAlchemy 模型
- 通过 Alembic 生成并执行迁移

### 第三步：后端业务与 API 实现
- 读取 `references/business.md`（业务分层规范）
- 读取 `references/api.md`（接口设计规范）
- 读取 `examples/business_example.py`（业务层示例）
- 读取 `examples/api_example.py`（接口示例）
- 按 `Endpoint -> Service -> Repository` 分层落地
- 使用 Pydantic Schema 做输入输出校验
- 路由命名遵循 `/api/v1/{module}/action_noun` 格式

### 第四步：前端页面实现
- 读取 `references/frontend.md`
- 按页面职责拆分视图、组件、状态与 API 调用
- 统一错误处理、加载态、空态和权限显隐

### 第五步：权限接入与联调
- 读取 `references/permission.md`（详细参考文档）
- 完成后端权限校验依赖（`Depends(require_permission(...))`）和前端路由/按钮控制
- 联调验证角色隔离、数据权限、审计日志

## 命名规范

### 文件命名
- 数据模型：`backend/app/models/{功能名}.py`
- 数据访问：`backend/app/repositories/{功能名}.py`
- 业务逻辑：`backend/app/services/{功能名}.py`
- 接口路由：`backend/app/api/v1/endpoints/{功能名}.py`
- 前端页面：`frontend/src/pages/{功能名}/`
- 前端组件：`frontend/src/components/{功能名}/`
- 前端接口：`frontend/src/api/{功能名}.js`

### 变量命名
- 使用小写字母+下划线（snake_case）
- 模型实例：直接使用类名导入，如 `from app.models.user import User`
- 数据库会话：统一命名为 `db: AsyncSession`
- 仓储实例：统一命名为 `repo`，如 `self.repo = UserRepository()`

### 路由命名（与 references/api.md 保持一致）
- 查询列表：`GET  /api/v1/{module}/get_{resource}_list`
- 查询详情：`GET  /api/v1/{module}/get_{resource}_detail/{id}`
- 创建资源：`POST /api/v1/{module}/create_{resource}`
- 更新资源：`POST /api/v1/{module}/update_{resource}`
- 删除资源：`POST /api/v1/{module}/delete_{resource}`
- 状态变更：`POST /api/v1/{module}/change_{resource}_status`

## 默认编码
- 源码与配置文件统一使用 `UTF-8 without BOM`

## 质量门禁

### 后端
- 代码格式：`ruff format .` / `ruff check .`
- 类型检查：`mypy app/`
- 单元测试：`pytest tests/ -v`（Service 层必须覆盖正常 + 异常两条路径）

### 前端
- 代码格式：`eslint src/ --fix` / `stylelint "src/**/*.scss"`
- 构建验证：`pnpm build`（确保无 TS/类型错误）

## 注意
- 优先保证可维护性和一致性，再考虑局部“快捷写法”
- 业务逻辑避免写入路由层和 Vue 视图层
- 所有接口与页面变更都应包含最小测试验证
- Router 层只做参数接收和响应组装，不写 SQL 和业务判断
- 禁止在模型层（models/）写复杂业务流程
