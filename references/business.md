---
type: "manual"
---

# 业务层编码规范（FastAPI）

## 分层原则
- Router 层：参数接收、权限依赖、调用 Service、返回响应
- Service 层：业务编排、事务控制、跨仓储协作
- Repository 层：数据库读写细节封装
- Model 层：实体定义，不承载复杂业务流程

## 目录建议
- `backend/app/api/v1/endpoints/`：路由
- `backend/app/services/`：业务服务
- `backend/app/repositories/`：数据访问

## Router 层规范
- 路由函数应保持轻量，不直接写复杂 SQL
- 通过 `Depends` 注入 `db session`、当前用户、权限检查
- 使用 `response_model` 明确定义返回结构

## Service 层规范
- 使用清晰的方法名：`create_xxx`、`update_xxx`、`delete_xxx`、`list_xxx`
- 跨表操作必须使用事务
- 对业务异常抛出明确的自定义异常

## Repository 层规范
- 只处理数据访问与查询拼装
- 避免泄露 ORM 细节到上层
- 高频查询提供分页和筛选接口

## 事务与异常处理

```python
from sqlalchemy.ext.asyncio import AsyncSession


class UserService:
    def __init__(self, repo):
        self.repo = repo

    async def create_user(self, db: AsyncSession, payload):
        async with db.begin():
            user = await self.repo.create(db, payload)
        return user
```

## 日志规范
- 关键操作必须记录：创建、更新、删除、权限拒绝、外部调用失败
- 日志应包含上下文：`trace_id`、`user_id`、接口路径
- 禁止输出敏感信息（密码、完整 token、身份证号）

## 测试要求
- Service 层必须有单元测试
- Endpoint 层至少覆盖成功和失败用例
- 涉及权限的功能必须覆盖越权访问测试

## 检查清单
- [ ] Router/Service/Repository 职责清晰
- [ ] 事务边界明确
- [ ] 异常已分层处理
- [ ] 日志可追踪且已脱敏
- [ ] 关键业务路径有测试覆盖
