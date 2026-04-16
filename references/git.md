# Git 与分支管理规范

---

## 1. 分支策略

### 1.1 分支类型

| 分支类型 | 命名格式 | 说明 | 生命周期 |
|----------|----------|------|----------|
| 主分支 | `main` | 生产环境代码，始终保持可发布状态 | 永久 |
| 开发分支 | `develop` | 日常开发集成分支，最新开发进度 | 永久 |
| 功能分支 | `feature/模块名-简述` | 新功能开发 | 合并后删除 |
| 修复分支 | `fix/模块名-简述` | 非紧急 Bug 修复 | 合并后删除 |
| 发布分支 | `release/vX.Y.Z` | 版本发布准备、最终测试与修复 | 合并后删除 |
| 热修复分支 | `hotfix/简述` | 生产环境紧急修复 | 合并后删除 |

### 1.2 命名规则

- 分支名**必须小写**，单词之间使用**连字符** `-` 分隔
- 禁止使用中文、空格、下划线或大写字母
- 功能/修复分支需包含模块名以便追溯

```bash
# ✅ 正确示例
feature/user-auth
feature/order-export
fix/user-login-error
fix/order-amount-calc
release/v1.2.0
hotfix/token-expire

# ❌ 错误示例
feature/UserAuth          # 包含大写
feature/user_auth         # 使用下划线
fix/修复登录问题           # 包含中文
Feature/order-export      # 类型前缀大写
```

### 1.3 分支工作流

```text
main ─────────────────────────────────────────── 生产
 │                          ▲            ▲
 │                          │            │
 └─► develop ──────────────►├── release ─┘
      │        ▲             │
      │        │             │
      └─► feature/xxx ──────┘
           fix/xxx ─────────┘

hotfix ──► main + cherry-pick 回 develop
```

1. 从 `develop` 创建 `feature/*` 或 `fix/*` 分支
2. 开发完成后提交 PR，合并回 `develop`
3. 需要发布时从 `develop` 创建 `release/vX.Y.Z`
4. `release` 分支测试通过后合并到 `main`，同时合并回 `develop`
5. 生产紧急问题从 `main` 创建 `hotfix/*`，修复后合并到 `main` 并 cherry-pick 回 `develop`

---

## 2. Commit 规范

### 2.1 格式

使用 [约定式提交（Conventional Commits）](https://www.conventionalcommits.org/zh-hans/) 规范：

```
<type>(<scope>): <description>

[可选的正文]

[可选的脚注]
```

- `type`：必填，变更类型
- `scope`：可选，影响的模块名
- `description`：必填，简明描述本次变更

### 2.2 类型说明

| 类型 | 说明 | 示例场景 |
|------|------|----------|
| `feat` | 新功能 | 新增用户注册接口 |
| `fix` | Bug 修复 | 修复订单金额计算错误 |
| `docs` | 文档变更 | 更新 API 文档 |
| `style` | 代码格式调整（不影响逻辑） | 调整缩进、删除多余空行 |
| `refactor` | 重构（不新增功能也不修复 Bug） | 重构用户服务层 |
| `perf` | 性能优化 | 优化列表查询加索引 |
| `test` | 测试相关 | 补充用户模块单元测试 |
| `chore` | 构建/工具变更 | 更新依赖版本 |
| `ci` | CI/CD 配置变更 | 修改 GitHub Actions 配置 |
| `build` | 构建系统变更 | 修改 Dockerfile |

### 2.3 描述要求

- 使用中文或英文均可，但**团队内必须统一**
- 首字母小写（英文），不加句号结尾
- 简明扼要，说清楚「做了什么」而非「怎么做的」
- 单次提交只做一件事，避免混合多个变更

### 2.4 示例

```bash
# ✅ 正确示例
feat(user): 新增用户注册接口
fix(order): 修复订单金额小数精度丢失问题
docs: 更新部署文档
refactor(auth): 将 JWT 逻辑抽取到独立模块
perf(query): 为 order 表 status 字段添加索引
test(user): 补充用户服务层单元测试
chore: 升级 FastAPI 到 0.115.0
ci: 添加 lint 检查步骤到 CI 流水线

# ❌ 错误示例
update code                  # 无类型前缀，描述模糊
feat: 改了一些东西            # 描述不清晰
fix(order): 修复bug。        # 不要加句号
feat(user): 新增注册+修复登录  # 混合多个变更
```

### 2.5 Breaking Change

不向下兼容的变更必须在类型后加 `!` 或在脚注中标注：

```bash
feat(api)!: 用户接口响应结构调整为统一格式

BREAKING CHANGE: /api/v1/users 返回结构从数组改为分页对象
```

---

## 3. 合并策略

### 3.1 合并方式

| 场景 | 合并方式 | 原因 |
|------|----------|------|
| `feature/*` → `develop` | **Squash Merge** | 将多次零碎提交压缩为一条，保持 develop 历史清晰 |
| `fix/*` → `develop` | **Squash Merge** | 同上 |
| `develop` → `main` | **Merge Commit** | 保留完整的开发历史和合并节点 |
| `release/*` → `main` | **Merge Commit** | 保留发布记录 |
| `hotfix/*` → `main` | **Merge Commit** | 保留热修复记录，之后 cherry-pick 回 `develop` |

### 3.2 禁止操作

- ❌ 禁止对 `main` 和 `develop` 执行 `force push`
- ❌ 禁止直接向 `main` 提交代码（必须通过 PR）
- ❌ 禁止在 `develop` 上直接开发功能（必须拉分支）
- ❌ 禁止使用 `rebase` 合并到 `main`（会丢失合并节点）

### 3.3 合并前检查

```bash
# 合并前确保本地分支与远程同步
git fetch origin
git rebase origin/develop   # 功能分支同步最新 develop

# 合并前解决所有冲突
# 合并前确保 CI 检查通过
# 合并前确保至少 1 人 Approve
```

---

## 4. Code Review 规范

### 4.1 PR 基本要求

- 每个 PR 只做**一件事**（一个功能/一个修复）
- PR 标题遵循 Commit 规范格式：`type(scope): description`
- PR 创建后必须至少 **1 人 Approve** 方可合并
- CI 检查全部通过后方可合并

### 4.2 PR 模板

```markdown
## 改动描述
<!-- 简要说明本次改动的内容和目的 -->


## 改动类型
- [ ] 新功能（feat）
- [ ] Bug 修复（fix）
- [ ] 重构（refactor）
- [ ] 文档（docs）
- [ ] 其他：______

## 影响范围
<!-- 列出受影响的模块、页面或接口 -->
-

## 测试说明
<!-- 说明如何验证本次改动 -->
- [ ] 已通过本地测试
- [ ] 已补充/更新单元测试
- [ ] 已在开发环境验证

## 关联
<!-- 关联的 Issue 或任务编号 -->
- closes #

## 截图（如有 UI 变更）
<!-- 贴上变更前后的截图对比 -->
```

### 4.3 Review 关注点

✅ **必须检查**
- 代码是否符合项目编码规范
- 是否有明显的逻辑错误或边界问题
- 是否有安全隐患（SQL 注入、XSS、敏感信息泄露）
- 是否有性能问题（N+1 查询、大循环、无分页）
- 测试是否充分覆盖

⚠️ **建议检查**
- 命名是否清晰、一致
- 是否有重复代码可抽取
- 注释是否准确反映代码意图
- 错误处理是否完善

---

## 5. Tag 与版本管理

### 5.1 版本号规范

使用 [语义化版本（Semantic Versioning）](https://semver.org/lang/zh-CN/)：

```
vMAJOR.MINOR.PATCH
```

| 版本段 | 递增时机 | 示例 |
|--------|----------|------|
| MAJOR | 不向下兼容的 API 变更 | v1.0.0 → v2.0.0 |
| MINOR | 向下兼容的功能新增 | v1.0.0 → v1.1.0 |
| PATCH | 向下兼容的 Bug 修复 | v1.0.0 → v1.0.1 |

### 5.2 打 Tag 规则

- Tag 格式：`vX.Y.Z`，如 `v1.2.3`
- 仅在 `main` 分支上打 Tag
- 打 Tag 时机：`release/*` 或 `hotfix/*` 合并到 `main` 之后
- Tag 必须附带 annotation（使用 `-a` 参数）

```bash
# 打 Tag
git tag -a v1.2.0 -m "release: v1.2.0 - 新增订单导出功能"
git push origin v1.2.0

# 查看所有 Tag
git tag -l "v*"
```

### 5.3 CHANGELOG 维护

- 项目根目录维护 `CHANGELOG.md`
- 每次发版时更新，格式如下：

```markdown
# Changelog

## [v1.2.0] - 2026-04-16

### 新增
- 新增订单导出功能（#123）
- 新增用户批量导入接口（#130）

### 修复
- 修复登录页面验证码刷新失败（#125）

### 变更
- 用户列表接口响应结构调整（#128）

## [v1.1.0] - 2026-03-20

### 新增
- 新增用户角色管理模块
```

---

## 6. .gitignore 标准模板

```gitignore
# ===== Python 后端 =====
__pycache__/
*.py[cod]
*$py.class
*.so
*.egg-info/
dist/
build/
*.egg
.pytest_cache/
htmlcov/
.coverage
.mypy_cache/
.ruff_cache/

# 虚拟环境
venv/
.venv/
env/

# Alembic
alembic/versions/__pycache__/

# ===== Vue 前端 =====
node_modules/
dist/
.nuxt/
*.local

# ===== IDE =====
.idea/
.vscode/
*.swp
*.swo
*~
.DS_Store
Thumbs.db

# ===== 环境变量与机密文件 =====
.env
.env.*
!.env.example
*.pem
*.key
credentials.json

# ===== 日志 =====
logs/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# ===== 操作系统 =====
.DS_Store
Thumbs.db
Desktop.ini
```

---

## 7. 检查清单

### 分支管理
- [ ] 从 `develop` 创建功能/修复分支
- [ ] 分支命名符合规范（小写、连字符、含模块名）
- [ ] 开发完成后及时提交 PR
- [ ] 合并后删除已完成的分支

### 提交规范
- [ ] Commit 消息符合约定式提交格式
- [ ] 每次提交只包含一个逻辑变更
- [ ] 不提交临时文件、调试代码或敏感信息
- [ ] `.gitignore` 已正确配置

### 合并与发布
- [ ] PR 已通过 Code Review（至少 1 人 Approve）
- [ ] CI 检查全部通过
- [ ] 合并方式正确（feature → develop 用 Squash，develop → main 用 Merge Commit）
- [ ] 发布时已在 `main` 上打 Tag 并更新 CHANGELOG

### Code Review
- [ ] PR 描述完整（改动描述、测试说明、影响范围）
- [ ] 代码符合项目编码规范
- [ ] 无安全隐患和明显性能问题
- [ ] 测试覆盖充分
