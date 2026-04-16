---
name: fastapi-vue-standard
description: 为项目提供通用的 FastAPI + Vue 全栈开发编码规范，覆盖数据建模、业务实现、API设计、前端开发、权限控制、安全、测试、部署与 Git 协作。
---

# FastAPI + Vue 编码规范 Skill

## 概述

此技能用于指导通用后台管理或业务系统的全栈开发，目标是让后端（FastAPI）和前端（Vue）在目录结构、分层设计、接口协议、权限方案和交付质量上保持一致。

## 文件结构

```text
fastapi-vue-standard/
├── SKILL.md                            # 本文件（技能包核心配置）
├── references/                         # 规范参考文档
│   ├── datatable.md                    # 数据模型与数据库规范
│   ├── business.md                     # 业务分层规范
│   ├── api.md                          # API 编码规范
│   ├── frontend.md                     # Vue 前端开发规范
│   ├── permission.md                   # 权限系统规范
│   ├── git.md                          # Git 与分支管理规范
│   ├── testing.md                      # 测试规范
│   ├── security.md                     # 安全编码规范
│   ├── deployment.md                   # 部署与运维规范
│   └── error-codes.md                  # 错误码与异常体系规范
└── examples/                           # 编写代码示例
    ├── datatable_example.py            # 数据模型示例
    ├── business_example.py             # 业务层示例
    └── api_example.py                  # API 接口示例
```

## 何时使用此技能

在以下场景中使用此技能：
- 新建 FastAPI + Vue 项目
- 为现有系统新增业务模块
- 统一团队编码风格和分层架构
- 设计可维护的 RBAC 权限体系
- 建立可持续的测试与发布流程
- 配置 CI/CD 与部署方案
- 进行安全审查与加固


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
    │   ├── hooks/
    │   ├── layouts/
    │   ├── pages/
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
6. Git 与分支管理规范（约定式提交 + Code Review）
7. 测试规范（pytest + Vitest）
8. 安全编码规范（认证、接口、数据、文件上传）
9. 错误码与异常体系规范（统一错误码 + 全局异常处理）
10. 部署与运维规范（Docker + CI/CD + 健康检查）

## 执行流程

### 第一步：需求拆解
- 明确业务边界、核心实体、角色与权限范围
- 输出实体关系、接口清单、页面清单

### 第二步：数据库与模型设计
- 读取 `references/datatable.md`（详细参考文档）
- 读取 `examples/datatable_example.py`（脚本参考案例）
- 先确定表结构、索引、约束，再实现 SQLAlchemy 模型
- 通过 Alembic 生成并执行迁移

### 第三步：后端业务与 API 实现
- 读取 `references/business.md`（详细参考文档）
- 读取 `examples/business_example.py`（脚本参考案例）
- 按 `Endpoint -> Service -> Repository` 分层落地
- 使用 Pydantic Schema 做输入输出校验

### 第四步：API 接口设计和实现
- 根据业务逻辑功能，设计新的 API 接口
- 读取 `references/api.md`（详细参考文档）
- 读取 `examples/api_example.py`（脚本参考案例）
- 读取 `references/error-codes.md`（错误码与异常体系）

### 第五步：前端页面实现
- 读取 `references/frontend.md`（详细参考文档）
- 按页面职责拆分视图、组件、状态与 API 调用
- 统一错误处理、加载态、空态和权限显隐

### 第六步：权限接入与联调
- 读取 `references/permission.md`（详细参考文档）
- 完成后端权限校验依赖和前端路由/按钮控制
- 联调验证角色隔离、数据权限、审计日志

### 第七步：测试与质量保障
- 读取 `references/testing.md`（详细参考文档）
- 按规范编写单元测试与集成测试
- 确保覆盖率达到门禁要求

### 第八步：安全审查
- 读取 `references/security.md`（详细参考文档）
- 检查认证、接口、数据、文件上传等安全项
- 确保敏感数据脱敏与配置安全

### 第九步：部署与发布
- 读取 `references/deployment.md`（详细参考文档）
- 读取 `references/git.md`（Git 与分支管理规范）
- 配置 Docker、CI/CD、健康检查
- 按规范流程完成数据库迁移与应用发布

## 命名规范

### 后端文件命名
- 模型文件：`app/models/{模块名}.py`（如 `app/models/user.py`）
- 业务服务：`app/services/{模块名}.py`（如 `app/services/user.py`）
- 数据访问：`app/repositories/{模块名}.py`（如 `app/repositories/user.py`）
- API 路由：`app/api/v1/endpoints/{模块名}.py`（如 `app/api/v1/endpoints/user.py`）
- Schema：`app/schemas/{模块名}.py`（如 `app/schemas/user.py`）

### 前端文件命名
- 页面组件：`pages/{ModuleName}.vue`（PascalCase）
- 公共组件：`components/{ComponentName}.vue`（PascalCase）
- API 文件：`api/{moduleName}.js`（camelCase）
- Store 文件：`store/{moduleName}.js`（camelCase）
- 工具函数：`utils/{moduleName}.js`（camelCase）
- 组合式函数：`hooks/use{Xxx}.js`（camelCase）

### 变量命名
- Python：使用 `snake_case`（如 `user_list`、`is_active`）
- JavaScript：使用 `camelCase`（如 `userList`、`isActive`）

### API 路由命名
- 路径前缀：`/api/v1/{module}`
- 列表查询：`GET /api/v1/user/get_user_list`
- 详情查询：`GET /api/v1/user/get_user_detail/{user_id}`
- 创建操作：`POST /api/v1/user/create_user`
- 更新操作：`POST /api/v1/user/update_user`
- 删除操作：`POST /api/v1/user/delete_user`
- 状态变更：`POST /api/v1/user/change_user_status`

## 默认编码
- 源码与配置文件统一使用 `UTF-8 without BOM`

## 注意
- 优先保证可维护性和一致性，再考虑局部"快捷写法"
- 业务逻辑避免写入路由层和 Vue 视图层
- 所有接口与页面变更都应包含最小测试验证
