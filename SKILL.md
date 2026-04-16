---
name: fastapi-vue-standard
description: 为项目提供通用的 FastAPI + Vue 全栈开发编码规范，覆盖数据建模、业务实现、API设计、前端开发与权限控制。
---

# FastAPI + Vue 编码规范 Skill

## 概述

此技能用于指导通用后台管理或业务系统的全栈开发，目标是让后端（FastAPI）和前端（Vue）在目录结构、分层设计、接口协议、权限方案和交付质量上保持一致。

## 文件结构

    .claude/skills/fastapi-vue-standard/
    ├── SKILL.md                        # 本文件（技能包核心配置）
    ├── templates/                      # 文档结构模板（通用）
    └── examples/                       # 编写代码示例

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
- 读取 `examples/datatable_example.py` (脚本参考案例)
- 先确定表结构、索引、约束，再实现 SQLAlchemy 模型
- 通过 Alembic 生成并执行迁移

### 第三步：后端业务与 API 实现
- 读取 `references/business.md`（详细参考文档）
- 读取 `examples/business_example.py` (脚本参考案例)
- 按 `Endpoint -> Service -> Repository` 分层落地
- 使用 Pydantic Schema 做输入输出校验

### 第四步：前端页面实现
- 读取 `references/frontend.md`
- 按页面职责拆分视图、组件、状态与 API 调用
- 统一错误处理、加载态、空态和权限显隐

### 第五步：权限接入与联调
- 读取 `references/permission.md`（详细参考文档）
- 读取 `assets/setup_permission.py` (参考设置权限脚本)
- 完成后端权限校验依赖和前端路由/按钮控制
- 联调验证角色隔离、数据权限、审计日志

### 第六步：测试与质量保障
- 读取 `references/testing.md`（详细参考文档）
- 按规范编写单元测试与集成测试
- 确保覆盖率达到门禁要求

### API接口设计和实现
**API接口设计和实现阶段**：
- 根据业务逻辑功能，设计新的API接口
- 读取 `references/api.md`（详细参考文档）
- 读取 `examples/api_example.py` (脚本参考案例)

## 命名规范

### 文件命名
- 模型文件：`app/models/{功能名}.py`
- 业务逻辑：`app/admin/{功能名}.py`
- 模板目录：`app/templates/admin/{功能名}/`

### 变量命名
- 使用小写字母+下划线
- 模型实例：`mdb = globals()['ModelName']`
- 列表数据：`list = mdb.query.all()`

### 路由命名
- 列表页面：`/{功能名}/index`
- 添加页面：`/{功能名}/add`
- 编辑页面：`/{功能名}/edit`
- 删除操作：`/{功能名}/delete`

## 默认编码
- 源码与配置文件统一使用 `UTF-8 without BOM`

## 注意
- 优先保证可维护性和一致性，再考虑局部“快捷写法”
- 业务逻辑避免写入路由层和 Vue 视图层
- 所有接口与页面变更都应包含最小测试验证
