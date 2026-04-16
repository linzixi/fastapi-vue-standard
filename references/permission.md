---
type: "manual"
---

# 权限系统规范（通用 RBAC）

## 目标
- 建立可扩展的角色权限模型，实现后端强校验 + 前端可视化控制。

## 数据模型建议
- `users`：用户
- `roles`：角色
- `permissions`：权限点
- `user_roles`：用户与角色关联
- `role_permissions`：角色与权限关联

## 权限点命名
- 推荐格式：`module:resource:action`
- 示例：`system:user:read`、`system:user:create`、`content:article:publish`
- 命名统一小写，使用冒号分隔

## 后端权限校验（FastAPI）

```python
from fastapi import Depends, HTTPException, status


def require_permission(permission: str):
    def checker(current_user = Depends(get_current_user)):
        if permission not in current_user.permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return current_user
    return checker
```

- 在路由层通过 `Depends(require_permission("module:resource:action"))` 使用
- 超级管理员应通过配置控制，不写死用户名

## 前端权限控制（Vue）
- 路由守卫基于用户权限控制可访问页面
- 按钮权限通过 `v-permission` 指令或组合式函数控制
- 禁止把权限码硬编码在多个组件，集中维护常量

## 数据权限（可选）
- 在 Service 层增加数据范围过滤（本人、本部门、全部）
- 避免仅依赖前端参数传递数据范围

## 审计与安全
- 记录权限变更日志（谁在何时改了什么）
- 关键操作要求二次确认或二次认证（可选）
- Token 失效和角色变更后应支持主动刷新权限缓存

## 检查清单
- [ ] 权限模型包含用户、角色、权限三层
- [ ] 后端接口已强制权限校验
- [ ] 前端路由和按钮已做权限显隐
- [ ] 数据权限策略已落地（如有）
- [ ] 权限变更具备审计记录
