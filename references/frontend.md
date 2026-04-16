# VUE 前端开发规范

---

## 1. 开发环境

```bash
# Node 版本要求
>= 18.0.0

# 包管理器
pnpm (推荐)
```

---

## 2. 技术栈规范

### 2.1 必须使用的技术

✅ **框架和库**
- Vue 3 Composition API（禁止使用 Options API）
- Pinia（禁止使用 Vuex）
- Element Plus（UI 组件优先使用项目封装的 `fs-*` 组件）
- 使用 SCSS 编写样式
- 禁止使用 ts

✅ **工具链**
- Vite（构建工具）
- ESLint + Stylelint + Prettier（代码规范）
- unplugin-auto-import（自动导入 API）
- unplugin-vue-components（自动导入组件）

### 2.2 图标实现
- 使用 `svg-icon` 组件实现图标
- 未找到的图标，优先从 [yesicon](https://yesicon.app/) 和 [iconfont](https://www.iconfont.cn/) 搜索并下载保存到 `assets/icons` 目录下
- 如果未找到符合条件的图标，使用 svg 实现，并将 svg 代码保存到 `assets/icons` 目录下
- 不要直接在代码中添加 svg 源代码

---

## 3. 目录结构规范

| 目录 | 职责 | 命名规范 |
|------|------|----------|
| `api/` | HTTP 接口定义，按业务模块划分 | `pascalCase.js` |
| `assets/` | 静态资源（图标、图片等） | `product_cover.jpg` |
| `components/` | 可复用组件 | `PascalCase.vue` |
| `hooks/` | Composition API 逻辑复用 | `useXxx.js` |
| `layouts/` | 布局组件 | `PascalCase.vue` |
| `pages/` | 页面组件（与路由对应） | `PascalCase.vue` |
| `router/` | 路由配置 | `kebab-case.js` |
| `store/` | Pinia 状态管理 | `pascalCase.js` |
| `utils/` | 工具函数 | `pascalCase.js` |

### 文件创建规则
✅ **创建文件的场景**
- 新增页面/路由组件
- 新增可复用组件
- 新增业务模块 API
- 新增 Composition Hook

⚠️ **最小化原则**
- 优先编辑现有文件，而非创建新文件
- 创建文件前，先搜索是否已有类似功能
- 避免创建一次性文件，优先抽象为可复用模块

---

## 4. 代码规范

### 4.1 代码组织顺序
Vue 文件内部按以下顺序组织：

```vue
<template>
  <!-- 模板 -->
</template>

<script setup>
// 1. import 语句（按类型分组）
// 2. 组件定义（自动导入可省略）
// 3. Props / Emits / Model 定义
// 4. Composables / Hooks
// 5. 响应式数据
// 6. 计算属性
// 7. 侦听器
// 8. 生命周期钩子
// 9. 方法定义
// 10. defineExpose（仅在需要暴露给父组件时）
</script>

<style scoped lang="scss">
/* 样式 */
</style>
```

### 4.2 注释规范

```javascript
/**
 * 函数功能说明（必须）
 * @param {Object} params - 参数说明
 * @param {string} params.id - 用户 ID
 * @returns {Promise<Object>} 返回值说明
 * @example
 * const user = await getUserInfo({ id: '123' })
 */
async function getUserInfo(params) {
  // 实现逻辑
}
```

✅ 必须添加注释的场景
- 复杂的业务逻辑
- 公共函数和工具函数
- 不明显的代码实现
- 临时解决方案（TODO、FIXME、HACK）

### 4.3 调试日志规范
- 调试日志需带清晰前缀（模块名/页面名），便于排查问题
- 提交前移除无意义日志，保留必要错误日志

---

## 5. API 调用规范

### 5.1 axios 封装规范

在 `utils/request.js` 中统一封装 axios 实例：

```javascript
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'
import router from '@/router'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
})

// 请求拦截器：注入 token、显示 loading
service.interceptors.request.use(
  (config) => {
    const userStore = useUserStore()
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// 响应拦截器：统一错误处理
service.interceptors.response.use(
  (response) => {
    const { code, message, data } = response.data
    if (code === 200) return data
    ElMessage.error(message || '请求失败')
    return Promise.reject(new Error(message))
  },
  (error) => {
    const status = error.response?.status
    const handlers = {
      401: () => {
        const userStore = useUserStore()
        userStore.logout()
        router.push('/login')
        ElMessage.error('登录已过期，请重新登录')
      },
      403: () => ElMessage.error('没有权限访问'),
      500: () => ElMessage.error('服务器内部错误'),
    }
    const handler = handlers[status]
    if (handler) {
      handler()
    } else {
      ElMessage.error(error.message || '网络异常')
    }
    return Promise.reject(error)
  },
)

export default service
```

### 5.2 API 文件按模块组织

按业务模块拆分，每个模块一个文件：

```
api/
├── user.js       # 用户相关
├── role.js       # 角色相关
├── order.js      # 订单相关
├── product.js    # 商品相关
└── upload.js     # 文件上传
```

单个 API 文件示例（`api/user.js`）：

```javascript
import request from '@/utils/request'

/** 获取用户列表 */
export function getUserList(params) {
  return request({ url: '/users', method: 'get', params })
}

/** 获取用户详情 */
export function getUserDetail(id) {
  return request({ url: `/users/${id}`, method: 'get' })
}

/** 创建用户 */
export function createUser(data) {
  return request({ url: '/users', method: 'post', data })
}

/** 更新用户 */
export function updateUser(id, data) {
  return request({ url: `/users/${id}`, method: 'put', data })
}

/** 删除用户 */
export function deleteUser(id) {
  return request({ url: `/users/${id}`, method: 'delete' })
}
```

### 5.3 请求函数命名规范

| 操作 | 命名模式 | 示例 |
|------|----------|------|
| 列表查询 | `getXxxList` | `getUserList`、`getOrderList` |
| 详情查询 | `getXxxDetail` | `getUserDetail` |
| 创建 | `createXxx` | `createUser` |
| 更新 | `updateXxx` | `updateUser` |
| 删除 | `deleteXxx` | `deleteUser` |
| 批量删除 | `batchDeleteXxx` | `batchDeleteUser` |
| 导出 | `exportXxx` | `exportUserList` |
| 上传 | `uploadXxx` | `uploadAvatar` |

---

## 6. 状态管理规范（Pinia）

### 6.1 Store 文件命名

- 文件名：`store/user.js`、`store/app.js`（小驼峰）
- 导出函数名：`useXxxStore`（如 `useUserStore`、`useAppStore`）

### 6.2 Setup Store 写法

项目统一使用 **Setup Store** 写法（禁止 Options Store）：

```javascript
// store/user.js
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { getUserDetail } from '@/api/user'
import router from '@/router'

export const useUserStore = defineStore('user', () => {
  // -------- state --------
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)

  // -------- getters --------
  const isLoggedIn = computed(() => !!token.value)
  const userName = computed(() => userInfo.value?.name ?? '')
  const permissions = computed(() => userInfo.value?.permissions ?? [])

  // -------- actions --------
  function setToken(val) {
    token.value = val
    localStorage.setItem('token', val)
  }

  async function fetchUserInfo() {
    const data = await getUserDetail('me')
    userInfo.value = data
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    router.push('/login')
  }

  return { token, userInfo, isLoggedIn, userName, permissions, setToken, fetchUserInfo, logout }
})
```

### 6.3 state / getters / actions 组织规则

| 类型 | 用途 | 写法 |
|------|------|------|
| state | 响应式数据 | `ref()` / `reactive()` |
| getters | 派生计算 | `computed()` |
| actions | 异步请求、修改 state | 普通函数 / `async` 函数 |

> 在 `return` 中按 **state → getters → actions** 的顺序导出，保持一致性。

---

## 7. 路由规范

### 7.1 路由配置示例（含权限 meta）

```javascript
// router/modules/system.js
export default {
  path: '/system',
  name: 'System',
  component: () => import('@/layouts/MainLayout.vue'),
  meta: { title: '系统管理', icon: 'setting' },
  children: [
    {
      path: 'user',
      name: 'SystemUser',
      component: () => import('@/pages/system/UserList.vue'),
      meta: {
        title: '用户管理',
        permission: 'system:user:list',
        keepAlive: true,
      },
    },
    {
      path: 'role',
      name: 'SystemRole',
      component: () => import('@/pages/system/RoleList.vue'),
      meta: {
        title: '角色管理',
        permission: 'system:role:list',
      },
    },
  ],
}
```

`meta` 常用字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | `string` | 页面标题 / 面包屑文本 |
| `permission` | `string` | 所需权限标识 |
| `icon` | `string` | 菜单图标 |
| `keepAlive` | `boolean` | 是否缓存页面 |
| `hidden` | `boolean` | 是否在菜单中隐藏 |

### 7.2 路由守卫规范

```javascript
// router/guard.js
import { useUserStore } from '@/store/user'

const WHITE_LIST = ['/login', '/404', '/403']

export function setupRouterGuard(router) {
  router.beforeEach(async (to, from, next) => {
    const userStore = useUserStore()
    const hasToken = !!userStore.token

    if (hasToken) {
      if (to.path === '/login') {
        next('/')
      } else {
        if (!userStore.userInfo) {
          await userStore.fetchUserInfo()
        }
        next()
      }
    } else {
      if (WHITE_LIST.includes(to.path)) {
        next()
      } else {
        next(`/login?redirect=${to.fullPath}`)
      }
    }
  })
}
```

### 7.3 路由懒加载

所有页面组件必须使用动态 `import()` 实现懒加载：

```javascript
// ✅ 正确：懒加载
component: () => import('@/pages/system/UserList.vue')

// ❌ 错误：静态导入
import UserList from '@/pages/system/UserList.vue'
component: UserList
```

---

## 8. CRUD 页面模板

### 8.1 标准列表页模板

```vue
<template>
  <div class="page-container">
    <!-- 搜索栏 -->
    <el-card shadow="never" class="search-card">
      <el-form :model="queryParams" inline>
        <el-form-item label="用户名">
          <el-input v-model="queryParams.username" placeholder="请输入用户名" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryParams.status" placeholder="请选择" clearable>
            <el-option label="启用" :value="1" />
            <el-option label="禁用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 操作栏 + 表格 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <el-button type="primary" @click="handleAdd">新增</el-button>
        <el-button type="danger" :disabled="!selectedIds.length" @click="handleBatchDelete">
          批量删除
        </el-button>
      </template>

      <el-table
        v-loading="loading"
        :data="tableData"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="queryParams.page"
        v-model:page-size="queryParams.pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        class="pagination"
        @size-change="fetchList"
        @current-change="fetchList"
      />
    </el-card>

    <!-- 表单弹窗 -->
    <UserFormDialog ref="formDialogRef" @success="fetchList" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUserList, deleteUser, batchDeleteUser } from '@/api/user'
import UserFormDialog from './components/UserFormDialog.vue'

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const selectedIds = ref([])
const formDialogRef = ref(null)

const queryParams = reactive({
  username: '',
  status: undefined,
  page: 1,
  pageSize: 10,
})

async function fetchList() {
  loading.value = true
  try {
    const { list, total: t } = await getUserList(queryParams)
    tableData.value = list
    total.value = t
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  queryParams.page = 1
  fetchList()
}

function handleReset() {
  Object.assign(queryParams, { username: '', status: undefined, page: 1 })
  fetchList()
}

function handleSelectionChange(rows) {
  selectedIds.value = rows.map((r) => r.id)
}

function handleAdd() {
  formDialogRef.value.open()
}

function handleEdit(row) {
  formDialogRef.value.open(row.id)
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确认删除该用户吗？', '提示', { type: 'warning' })
  await deleteUser(row.id)
  ElMessage.success('删除成功')
  fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条数据吗？`, '提示', {
    type: 'warning',
  })
  await batchDeleteUser(selectedIds.value)
  ElMessage.success('删除成功')
  fetchList()
}

onMounted(() => fetchList())
</script>

<style scoped lang="scss">
.page-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
```

### 8.2 表单弹窗模板

```vue
<template>
  <el-dialog v-model="visible" :title="isEdit ? '编辑用户' : '新增用户'" width="500px">
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="80px">
      <el-form-item label="用户名" prop="username">
        <el-input v-model="formData.username" placeholder="请输入用户名" />
      </el-form-item>
      <el-form-item label="邮箱" prop="email">
        <el-input v-model="formData.email" placeholder="请输入邮箱" />
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-radio-group v-model="formData.status">
          <el-radio :value="1">启用</el-radio>
          <el-radio :value="0">禁用</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { getUserDetail, createUser, updateUser } from '@/api/user'

const emit = defineEmits(['success'])

const visible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref(null)
let editId = null

const initialForm = { username: '', email: '', status: 1 }
const formData = reactive({ ...initialForm })

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
}

async function open(id) {
  visible.value = true
  isEdit.value = !!id
  editId = id || null
  Object.assign(formData, { ...initialForm })
  await nextTick()
  formRef.value?.clearValidate()
  if (id) {
    const data = await getUserDetail(id)
    Object.assign(formData, data)
  }
}

async function handleSubmit() {
  await formRef.value.validate()
  submitLoading.value = true
  try {
    if (isEdit.value) {
      await updateUser(editId, formData)
      ElMessage.success('更新成功')
    } else {
      await createUser(formData)
      ElMessage.success('创建成功')
    }
    visible.value = false
    emit('success')
  } finally {
    submitLoading.value = false
  }
}

defineExpose({ open })
</script>
```

---

## 9. 样式规范

### 9.1 SCSS 变量与 mixin

在 `styles/variables.scss` 中统一定义设计变量，`vite.config.js` 中全局注入：

```scss
// styles/variables.scss

// 颜色
$primary-color: #409eff;
$success-color: #67c23a;
$warning-color: #e6a23c;
$danger-color: #f56c6c;
$text-primary: #303133;
$text-regular: #606266;
$text-secondary: #909399;
$border-color: #dcdfe6;
$bg-color: #f5f7fa;

// 间距
$spacing-xs: 4px;
$spacing-sm: 8px;
$spacing-md: 16px;
$spacing-lg: 24px;
$spacing-xl: 32px;

// 圆角
$radius-sm: 4px;
$radius-md: 8px;
$radius-lg: 12px;
```

常用 mixin：

```scss
// styles/mixins.scss

@mixin flex-center {
  display: flex;
  align-items: center;
  justify-content: center;
}

@mixin flex-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

@mixin text-ellipsis($lines: 1) {
  overflow: hidden;
  text-overflow: ellipsis;
  @if $lines == 1 {
    white-space: nowrap;
  } @else {
    display: -webkit-box;
    -webkit-line-clamp: $lines;
    -webkit-box-orient: vertical;
  }
}

@mixin scrollbar {
  &::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }
  &::-webkit-scrollbar-thumb {
    border-radius: 3px;
    background: #c0c4cc;
  }
}
```

`vite.config.js` 全局注入：

```javascript
// vite.config.js
css: {
  preprocessorOptions: {
    scss: {
      additionalData: `
        @use "@/styles/variables.scss" as *;
        @use "@/styles/mixins.scss" as *;
      `,
    },
  },
}
```

### 9.2 命名规范

项目采用 **BEM** 命名约定：

```scss
.user-card {                     // Block
  &__header {                    // Element
    font-size: 16px;
  }
  &__body {
    padding: $spacing-md;
  }
  &--active {                    // Modifier
    border-color: $primary-color;
  }
}
```

命名规则：
- Block：小写字母，多词用 `-` 连接（`user-card`）
- Element：双下划线 `__`（`user-card__header`）
- Modifier：双中划线 `--`（`user-card--active`）

### 9.3 scoped 样式

所有组件样式必须添加 `scoped`，需覆盖 Element Plus 样式时使用 `:deep()`：

```vue
<style scoped lang="scss">
.my-table {
  :deep(.el-table__header) {
    background: $bg-color;
  }
  :deep(.el-pagination) {
    margin-top: $spacing-md;
  }
}
</style>
```

> 禁止在 `scoped` 外写全局样式。全局样式统一放在 `styles/global.scss`。

---

## 10. 错误处理与用户体验

### 10.1 全局错误捕获

在 `main.js` 中注册全局错误处理：

```javascript
// main.js
app.config.errorHandler = (err, instance, info) => {
  console.error(`[GlobalError] ${info}:`, err)
  ElMessage.error('系统异常，请稍后重试')
}

window.addEventListener('unhandledrejection', (event) => {
  console.error('[UnhandledRejection]', event.reason)
  event.preventDefault()
})
```

### 10.2 loading / 空态 / 异常态

列表页必须处理三种状态：

```vue
<template>
  <!-- 加载态 -->
  <el-table v-loading="loading" :data="tableData">
    <!-- columns -->
  </el-table>

  <!-- 空态 -->
  <el-empty v-if="!loading && tableData.length === 0" description="暂无数据" />

  <!-- 异常态 -->
  <el-result v-if="loadError" icon="error" title="加载失败">
    <template #extra>
      <el-button type="primary" @click="fetchList">重新加载</el-button>
    </template>
  </el-result>
</template>
```

按钮提交时禁用防止重复操作：

```vue
<el-button type="primary" :loading="submitLoading" @click="handleSubmit">提交</el-button>
```

### 10.3 ElMessage / ElMessageBox 使用规范

| 场景 | 组件 | 示例 |
|------|------|------|
| 操作成功 | `ElMessage.success()` | `ElMessage.success('保存成功')` |
| 操作警告 | `ElMessage.warning()` | `ElMessage.warning('请先选择数据')` |
| 操作失败 | `ElMessage.error()` | `ElMessage.error('保存失败')` |
| 删除确认 | `ElMessageBox.confirm()` | 见下方示例 |
| 信息提示 | `ElMessageBox.alert()` | 纯信息展示 |

### 10.4 删除前确认

所有删除操作必须弹出确认框：

```javascript
import { ElMessage, ElMessageBox } from 'element-plus'

async function handleDelete(row) {
  await ElMessageBox.confirm(
    `确认删除「${row.name}」吗？删除后不可恢复。`,
    '删除确认',
    { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' },
  )
  await deleteXxx(row.id)
  ElMessage.success('删除成功')
  fetchList()
}
```

> 批量删除需在确认文案中显示选中数量。

---

## 11. 性能优化

### 11.1 路由懒加载

所有页面必须使用动态 `import()` 实现按需加载（见 7.3）。可结合 Vite 的 `rollupOptions.output.manualChunks` 进一步拆分：

```javascript
// vite.config.js
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        'element-plus': ['element-plus'],
        'vue-vendor': ['vue', 'vue-router', 'pinia'],
      },
    },
  },
}
```

### 11.2 虚拟滚动

当列表数据量超过 **500 条**时，使用虚拟滚动避免 DOM 性能瓶颈：

```vue
<template>
  <el-table-v2
    :columns="columns"
    :data="largeList"
    :width="tableWidth"
    :height="500"
    :row-height="48"
    fixed
  />
</template>

<script setup>
import { ref } from 'vue'

const tableWidth = ref(800)
const columns = [
  { key: 'id', dataKey: 'id', title: 'ID', width: 80 },
  { key: 'name', dataKey: 'name', title: '名称', width: 200 },
  { key: 'email', dataKey: 'email', title: '邮箱', width: 260 },
  { key: 'status', dataKey: 'status', title: '状态', width: 120 },
]
const largeList = ref([]) // 大数据量列表
</script>
```

> Element Plus 提供 `el-table-v2`（虚拟化表格），适合万级数据渲染。

### 11.3 图片懒加载

使用 `v-lazy` 指令或 Element Plus 的 `el-image` 内置懒加载：

```vue
<template>
  <!-- Element Plus el-image 内置 lazy -->
  <el-image :src="imgUrl" lazy fit="cover" />

  <!-- 列表场景 -->
  <div v-for="item in productList" :key="item.id" class="product-item">
    <el-image :src="item.cover" lazy fit="cover" class="product-cover" />
    <span>{{ item.name }}</span>
  </div>
</template>
```

大量静态图片资源建议开启 CDN 或使用 `srcset` 提供多尺寸：

```vue
<img
  :src="item.cover"
  :srcset="`${item.cover}?w=200 200w, ${item.cover}?w=400 400w`"
  sizes="(max-width: 768px) 200px, 400px"
  loading="lazy"
  alt=""
/>
```

---

## 附录

### A. 参考资源
- [Vue 3 官方文档](https://cn.vuejs.org/)
- [Vite 官方文档](https://cn.vitejs.dev/)
- [Element Plus 文档](https://element-plus.org/zh-CN/)
- [Pinia 文档](https://pinia.vuejs.org/zh/)
- [ESLint 文档](https://eslint.org/)
- [约定式提交规范](https://www.conventionalcommits.org/zh-hans/)
