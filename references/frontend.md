---
type: "manual"
---

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

## 附录

### A. 参考资源
- [Vue 3 官方文档](https://cn.vuejs.org/)
- [Vite 官方文档](https://cn.vitejs.dev/)
- [Element Plus 文档](https://element-plus.org/zh-CN/)
- [Pinia 文档](https://pinia.vuejs.org/zh/)
- [ESLint 文档](https://eslint.org/)
- [约定式提交规范](https://www.conventionalcommits.org/zh-hans/)
