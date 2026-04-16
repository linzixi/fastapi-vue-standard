---
type: "manual"
---

# API 编码规范

## 文件结构与命名

### 文件命名规范
```python
# ✅ 正确示例
app/api/chat_model.py
app/api/user_auth.py
app/api/file_upload.py

# ❌ 错误示例
app/api/ChatModel.py  # 大写字母
app/api/userAuth.py   # 驼峰命名
app/api/user-auth.py  # 连字符
```

### 文件头格式
每个Python文件必须包含标准文件头：
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author   : XXX
# @Time     : 2026/1/6 09:58
# @File     : filename.py
# @Desc     : 文件功能描述
```

---

## 代码格式规范

### 1. 缩进与空格
- 使用4个空格缩进，不使用Tab
- 行长度不超过120个字符
- 运算符两侧加空格：`a + b`, `x == y`

### 2. 函数与类间隔
```python
# 函数/类之间空2行
def function_one():
    pass


def function_two():
    pass


# 方法之间空1行
class ExampleClass:
    def method_one(self):
        pass

    def method_two(self):
        pass
```

---

## 导入规范

### 导入顺序（必须按顺序）
```python
# 1. 标准库导入
import time
import json

# 2. 第三方库导入
from flask import request, jsonify, g
from wtforms import StringField, IntegerField
from wtforms.validators import DataRequired, Length

# 3. 本地应用导入
from app.api import api
from app.libs.logger import logger
from app.libs.token_auth import auth
from app.validators.chat_model import ChatModelForm
```

### 导入最佳实践
- 避免使用 `from flask import *`
- 优先使用绝对导入
- 避免循环导入

---

## 路由设计

### 1. URL设计原则
```python
# ✅ 正确示例
@api.route('/api/users')                          # 资源集合
@api.route('/api/users/<int:user_id>')            # 单个资源
@api.route('/api/chat_model', methods=['POST'])   # 指定方法
@api.route('/api/files/<path:file_path>')         # 路径参数

# ❌ 错误示例
@api.route('/api/getUsers')                       # URL中避免动词
@api.route('/api/UserInfo')                       # 避免大小写混用
@api.route('/api/get-user-info')                  # 避免连字符
```

### 2. HTTP方法使用规范
- 统一使用两种 HTTP 方法：`GET` 与 `POST`
- 路径前缀统一：`/api/v1/{module}`
- 路径使用动词+对象风格，且与函数名一致
- 推荐命名：
  - `GET /api/v1/user/get_user_list`
  - `GET /api/v1/user/get_user_detail/{user_id}`
  - `POST /api/v1/user/create_user`
  - `POST /api/v1/user/update_user`
  - `POST /api/v1/user/delete_user`
  - `POST /api/v1/user/change_user_status`
  
### GET：用于所有数据查询
- 获取列表数据（支持分页、搜索、过滤）
- 获取单个资源详情
- 获取关联资源数据

### POST：用于所有数据变更
- 创建新资源
- 更新现有资源
- 删除资源（软删除）
- 状态变更操作
- 复杂查询操作


### 3. 路由前缀
- 所有API路由必须以 `/api` 开头
- 版本号可选：`/api/v1/users`

---

## 认证与权限

### 1. 认证装饰器使用
```python
from app.libs.token_auth import auth

@api.route('/api/user/info')
@auth.login_required
def get_user_info():
    """需要认证的接口"""
    user_id = g.client.uid
    return jsonify(user_id=user_id)
```

### 2. 权限控制
```python
from app.libs.scope import is_in_scope
from app.libs.error_code import Forbidden

def check_permission(scope_name, endpoint):
    """检查接口访问权限"""
    if not is_in_scope(scope_name, endpoint):
        raise Forbidden(msg="无权限访问")
```

---

## 参数验证

### 1. 验证器创建

**验证器定义位置**：直接在API接口文件中定义

**继承基类**：所有验证器必须继承 `BaseForm`

**创建方式**：在API接口文件顶部定义验证器类

```python

from flask import request, jsonify, g
from wtforms import StringField, IntegerField
from wtforms.validators import DataRequired, Length, ValidationError
from app.api import api
from app.libs.logger import logger
from app.libs.token_auth import auth
from app.validators.base_form import BaseForm


# 验证器定义区域
class ChatModelForm(BaseForm):
    """聊天模型参数验证器"""
    prompt = StringField(validators=[
        DataRequired(message='提示词不能为空'),
        Length(min=1, max=6000, message='提示词长度应在1-6000个字符之间')
    ])
    model_name = StringField(validators=[
        Length(min=1, max=50, message='模型名称长度应在1-50个字符之间')
    ])

    def validate_model_name(self, field):
        """自定义验证：检查模型名称"""
        if field.data:
            supported_models = ['deepseek', 'gemini_pro', 'doubao']
            if field.data not in supported_models:
                raise ValidationError(f'不支持的模型: {field.data}')


# API接口定义区域
@api.route('/api/chat_model', methods=['POST'])
@auth.login_required
def api_chat_model():
    """聊天模型接口"""
    # 接口实现...
```

### 2. 验证器使用

**四步验证流程**：

```python
@api.route('/api/chat_model', methods=['POST'])
@auth.login_required
def api_chat_model():
    """聊天模型接口"""
    try:
        # 第一步：创建验证器实例
        form = ChatModelForm()

        # 第二步：执行验证
        if not form.validate():
            # 第三步：提取第一个错误信息
            error_msg = list(form.errors.values())[0][0] if form.errors else '参数错误'
            return jsonify({
                "code": 400,
                "message": error_msg,
                "data": None
            }), 400

        # 第四步：获取验证后的参数
        prompt = form.prompt.data
        model_name = form.model_name.data or 'deepseek'

        # 业务逻辑处理
        logger.info(f"调用模型: {model_name}, 提示词: {prompt[:20]}...")
        # 执行业务逻辑...

        return jsonify({
            "code": 200,
            "message": "成功",
            "data": result
        })
    except ValueError as e:
        logger.warning(f"参数验证失败: {str(e)}")
        return jsonify({
            "code": 400,
            "message": str(e),
            "data": None
        }), 400
    except Exception as e:
        logger.error(f"接口错误: {str(e)}")
        return jsonify({
            "code": 500,
            "message": "服务内部错误",
            "data": None
        }), 500
```

### 3. 常用验证规则

| 验证器 | 用途 | 示例 |
|--------|------|------|
| DataRequired | 必填验证 | `DataRequired(message='字段不能为空')` |
| Length | 长度验证 | `Length(min=1, max=100, message='长度应在1-100之间')` |
| Email | 邮箱验证 | `Email(message='邮箱格式不正确')` |
| Regexp | 正则验证 | `Regexp(r'^[a-zA-Z0-9]+$', message='只能包含字母和数字')` |
| NumberRange | 数值范围 | `NumberRange(min=1, max=100, message='数值应在1-100之间')` |
| 自定义验证 | validate_字段名 | `def validate_username(self, field)` |

### 4. 自定义验证方法示例

```python
class MemberForm(BaseForm):
    """会员参数验证器"""
    account = StringField(validators=[
        DataRequired(message='账号不允许为空'),
        Length(min=5, max=32, message='账号长度应在5-32个字符之间')
    ])
    type = IntegerField(validators=[DataRequired(message='类型不能为空')])

    def validate_type(self, field):
        """自定义验证：验证会员类型枚举"""
        try:
            member_type = MemberTypeEnum(field.data)
            # 验证通过后可以转换数据类型
            self.type.data = member_type
        except ValueError as e:
            raise ValidationError(f'无效的会员类型: {field.data}')


class CreateUserForm(BaseForm):
    """创建用户验证器"""
    username = StringField(validators=[
        DataRequired(message='用户名不能为空'),
        Length(min=3, max=20, message='用户名长度应在3-20个字符之间')
    ])
    email = StringField(validators=[
        DataRequired(message='邮箱不能为空'),
        Email(message='邮箱格式不正确')
    ])
    password = StringField(validators=[
        DataRequired(message='密码不能为空'),
        Length(min=6, max=32, message='密码长度应在6-32个字符之间')
    ])

    def validate_username(self, field):
        """自定义验证：检查用户名格式"""
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', field.data):
            raise ValidationError('用户名只能包含字母、数字和下划线')
```

### 5. 文件组织结构

**推荐的API文件结构**：

```python

# ========== 第一部分：导入区域 ==========
from flask import request, jsonify, g
from wtforms import StringField
from wtforms.validators import DataRequired, Length, Email
from app.api import api
from app.libs.logger import logger
from app.libs.token_auth import auth
from app.validators.base_form import BaseForm
from app.models.user import User

# ========== 第二部分：验证器定义区域 ==========
class CreateUserForm(BaseForm):
    """创建用户验证器"""
    username = StringField(validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField(validators=[DataRequired(), Email()])
    password = StringField(validators=[DataRequired(), Length(min=6, max=32)])

# ========== 第三部分：辅助函数区域 ==========
def success_response(data=None, message="成功"):
    """统一成功响应"""
    return jsonify({"code": 200, "message": message, "data": data})

# ========== 第四部分：API路由区域 ==========
@api.route('/api/users', methods=['GET'])
@auth.login_required
def get_users():
    """获取用户列表"""
    # 实现代码...

@api.route('/api/users', methods=['POST'])
@auth.login_required
def create_user():
    """创建新用户"""
    form = CreateUserForm()
    # 实现代码...
```

---

## 错误处理

### 1. 异常捕获层次

**三层异常处理结构**：

```python
@api.route('/api/chat_model', methods=['POST'])
@auth.login_required
def api_chat_model():
    try:
        # 业务逻辑
        form = ChatModelForm()

        if not form.validate():
            error_msg = list(form.errors.values())[0][0] if form.errors else '参数错误'
            return jsonify({
                "code": 400,
                "message": error_msg,
                "data": None
            }), 400

        # 执行业务逻辑
        result = process_business_logic()

        return jsonify({
            "code": 200,
            "message": "成功",
            "data": result
        })

    # 第一层：参数验证错误
    except ValueError as e:
        logger.warning(f"参数验证失败: {str(e)}")
        return jsonify({
            "code": 400,
            "message": str(e),
            "data": None
        }), 400

    # 第二层：业务逻辑错误
    except BusinessException as e:
        logger.warning(f"业务异常: {str(e)}")
        return jsonify({
            "code": e.code,
            "message": e.message,
            "data": None
        }), e.code

    # 第三层：系统异常
    except Exception as e:
        logger.error(f"系统错误: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": "服务内部错误",
            "data": None
        }), 500
```

### 2. HTTP状态码使用规范

| 状态码 | 场景 | 返回示例 |
|--------|------|---------|
| 200 | 请求成功 | `return jsonify({...})` |
| 201 | 创建成功 | `return jsonify({...}), 201` |
| 400 | 参数错误 | `return jsonify({...}), 400` |
| 401 | 未认证 | `return jsonify({...}), 401` |
| 403 | 权限不足 | `return jsonify({...}), 403` |
| 404 | 资源不存在 | `return jsonify({...}), 404` |
| 500 | 服务器错误 | `return jsonify({...}), 500` |

### 3. 自定义异常类

```python
# app/libs/error_code.py
class APIException(Exception):
    """API异常基类"""
    code = 500
    msg = '服务器异常'

    def __init__(self, msg=None, code=None):
        if msg:
            self.msg = msg
        if code:
            self.code = code

class ParameterException(APIException):
    """参数异常"""
    code = 400
    msg = '参数错误'

class AuthFailed(APIException):
    """认证失败"""
    code = 401
    msg = '认证失败'

class Forbidden(APIException):
    """权限不足"""
    code = 403
    msg = '权限不足'

class NotFound(APIException):
    """资源不存在"""
    code = 404
    msg = '资源不存在'
```

---

## 响应格式

### 1. 成功响应标准格式

**单条数据响应**：
```python
return jsonify({
    "code": 200,
    "message": "成功",
    "data": {
        "content": "你好！有什么我可以帮助你的吗？",
        "model_name": "deepseek",
        "finish_reason": "stop",
        "input_tokens": 10,
        "output_tokens": 15
    }
})
```

**列表数据响应**：
```python
return jsonify({
    "code": 200,
    "message": "成功",
    "data": {
        "total": 100,
        "page": 1,
        "per_page": 20,
        "items": [
            {"id": 1, "name": "item1"},
            {"id": 2, "name": "item2"}
        ]
    }
})
```

**无返回数据响应**：
```python
return jsonify({
    "code": 200,
    "message": "操作成功",
    "data": None
})
```

### 2. 错误响应标准格式

```python
return jsonify({
    "code": 400,
    "message": "参数验证失败：提示词不能为空",
    "data": None
}), 400
```

### 3. 响应格式规范要点

- **必须字段**：`code`、`message`、`data`
- **code 字段**：与 HTTP 状态码保持一致
- **message 字段**：清晰描述操作结果或错误原因
- **data 字段**：成功时返回数据对象，失败时返回 `None`

---

## 日志记录

### 1. 日志级别使用规范

```python
from app.libs.logger import logger

# INFO - 重要业务操作
logger.info(f"[API] 调用模型: {model_name}, 用户: {user_id}, 提示词长度: {len(prompt)}")

# WARNING - 警告信息（可预期的异常）
logger.warning(f"[Validation] 参数验证失败: {error_msg}, 用户: {user_id}")

# ERROR - 错误信息（系统异常）
logger.error(f"[System] 接口异常: {str(e)}, 路径: {request.path}", exc_info=True)
```

### 2. 日志格式规范

**推荐格式**：`[模块] 操作描述: 详细信息 - 上下文信息`

```python
# ✅ 正确示例
logger.info(f"[API] {request.method} {request.path} - 用户: {user_id} - 耗时: {elapsed}ms")
logger.error(f"[DB] 数据库查询失败 - SQL: {sql} - 错误: {error}")
logger.warning(f"[Auth] Token验证失败 - Token: {token[:10]}... - IP: {request.remote_addr}")

# ❌ 错误示例
logger.info("error")              # 信息不明确
logger.error(user_id)             # 缺少上下文
logger.warning("失败")            # 没有详细信息
```

### 3. 日志记录最佳实践

- **关键操作必记**：API调用、数据库操作、外部服务调用
- **敏感信息脱敏**：密码、Token完整内容、身份证号等
- **包含上下文**：用户ID、请求路径、IP地址等
- **使用 exc_info**：记录异常堆栈时添加 `exc_info=True`

---

## 文档注释

### 1. 接口文档标准格式

使用 `@@@` 包裹的 Markdown 格式文档：

```python
@api.route('/api/chat_model', methods=['POST'])
@auth.login_required
def api_chat_model():
    """
    聊天模型接口
    @@@
    #### 接口说明
    调用指定的聊天模型进行对话，支持多种模型切换。

    #### 认证方式
    - 需要在请求头中携带 Token
    - Header: `Authorization: Bearer <token>`

    #### 请求参数

    | 参数 | 是否必填 | 类型 | 说明 | 示例 |
    |------|---------|------|------|------|
    | prompt | 是 | String | 用户输入的提示词 | "你好" |
    | model_name | 否 | String | 模型名称，默认为 deepseek | "deepseek" |

    #### 返回数据

    ```json
    {
        "code": 200,
        "message": "成功",
        "data": {
            "content": "你好！有什么我可以帮助你的吗？",
            "model_name": "deepseek",
            "finish_reason": "stop",
            "input_tokens": 10,
            "output_tokens": 15
        }
    }
    ```

    #### 备注
    - 请求方式：POST Raw JSON
    - 接口地址：http://127.0.0.1:5000/api/v1/chat_model
    - 超时时间：30秒
    @@@
    """
    # 接口实现代码...
```

### 2. 函数注释规范

```python
def generate_auth_token(uid, scope=None, expiration=7200):
    """生成认证令牌

    为用户生成用于API认证的JWT令牌。

    :param uid: 用户ID
    :type uid: int
    :param scope: 权限范围，默认为None表示继承用户权限
    :type scope: str, optional
    :param expiration: 过期时间（秒），默认7200秒（2小时）
    :type expiration: int, optional
    :return: 加密后的token字符串
    :rtype: str
    :raises ValueError: 如果uid无效或为空

    示例:
        >>> token = generate_auth_token(123, scope='user', expiration=3600)
        >>> print(token)
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    """
    pass
```

---

## 最佳实践

### 1. 接口设计原则

#### SOLID 原则应用

**单一职责（Single Responsibility）**：
```python
# ✅ 正确：每个接口只负责一个功能
@api.route('/api/users', methods=['GET'])
def get_users():
    """获取用户列表"""
    pass

@api.route('/api/users', methods=['POST'])
def create_user():
    """创建新用户"""
    pass

# ❌ 错误：一个接口承担多个职责
@api.route('/api/users', methods=['GET', 'POST', 'DELETE'])
def handle_users():
    """处理所有用户操作"""
    pass
```

**接口隔离（Interface Segregation）**：
```python
# ✅ 正确：精确的接口定义
@api.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    """获取用户资料"""
    pass

@api.route('/api/user/settings', methods=['GET'])
def get_user_settings():
    """获取用户设置"""
    pass

# ❌ 错误：返回过多不必要的数据
@api.route('/api/user/all', methods=['GET'])
def get_user_all_data():
    """返回用户所有数据（包括不需要的）"""
    pass
```

### 3. 性能优化

**使用分页**：
```python
@api.route('/api/users', methods=['GET'])
def get_users():
    """获取用户列表（分页）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    pagination = User.query.paginate(page=page, per_page=per_page)

    return success_response({
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "items": [u.to_dict() for u in pagination.items]
    })
```

**避免 N+1 查询**：
```python
# ✅ 正确：使用 joinedload
from sqlalchemy.orm import joinedload

@api.route('/api/articles', methods=['GET'])
def get_articles():
    """获取文章列表（包含作者信息）"""
    articles = Article.query.options(joinedload(Article.author)).all()
    return success_response([a.to_dict() for a in articles])

# ❌ 错误：N+1 查询
@api.route('/api/articles', methods=['GET'])
def get_articles_with_n_plus_one():
    """获取文章列表（N+1问题）"""
    articles = Article.query.all()
    # 每次循环都会触发一次数据库查询
    return success_response([
        {**a.to_dict(), "author": a.author.to_dict()}
        for a in articles
    ])
```

### 4. 安全性

**SQL注入防护**：
```python
# ✅ 正确：使用参数化查询
@api.route('/api/users/search', methods=['GET'])
def search_users():
    keyword = request.args.get('keyword', '')
    users = User.query.filter(User.name.like(f'%{keyword}%')).all()
    return success_response([u.to_dict() for u in users])

# ❌ 错误：直接拼接SQL
@api.route('/api/users/search', methods=['GET'])
def search_users_unsafe():
    keyword = request.args.get('keyword', '')
    sql = f"SELECT * FROM users WHERE name LIKE '%{keyword}%'"
    users = db.session.execute(sql).fetchall()
    return success_response(users)
```

---

## 规范检查清单

在提交代码前，请对照以下清单进行检查：

### 基础规范
- [ ] 文件头信息完整（Shebang、编码、作者、描述）
- [ ] 导入语句按标准库、第三方库、本地模块分组排序
- [ ] 代码格式符合 PEP 8 规范
- [ ] 函数和类之间有适当的空行

### 接口设计
- [ ] URL命名符合RESTful规范（小写、下划线、无动词）
- [ ] HTTP方法使用正确（GET查询、POST创建、PUT更新、DELETE删除）
- [ ] 所有API路由以 `/api` 开头

### 参数验证
- [ ] 在API文件顶部创建了对应的Form验证器（继承BaseForm）
- [ ] 验证器定义在导入区域之后、接口定义之前
- [ ] 所有必填参数使用了 `DataRequired` 验证器
- [ ] 验证错误信息清晰明确
- [ ] 文件结构清晰：导入→验证器→辅助函数→API路由

### 认证与权限
- [ ] 需要认证的接口添加了 `@auth.login_required` 装饰器
- [ ] 权限检查逻辑正确实现

### 错误处理
- [ ] 实现了三层异常捕获（ValueError、BusinessException、Exception）
- [ ] HTTP状态码使用正确（200/400/401/403/404/500）
- [ ] 错误信息对用户友好且不泄露敏感信息

### 响应格式
- [ ] 所有响应包含 `code`、`message`、`data` 三个字段
- [ ] 成功响应 code 为 200
- [ ] 错误响应 code 与 HTTP 状态码一致

### 日志记录
- [ ] 关键操作有日志记录（API调用、数据库操作、异常）
- [ ] 日志包含足够的上下文信息（用户ID、请求路径等）
- [ ] 日志级别使用正确（INFO/WARNING/ERROR）
- [ ] 敏感信息已脱敏处理

### 文档注释
- [ ] 接口有完整的文档注释（使用 `@@@` 格式）
- [ ] 文档包含：接口说明、参数表格、返回示例、错误码说明
- [ ] 函数有清晰的docstring

### 性能与安全
- [ ] 使用了参数化查询，避免SQL注入
- [ ] 列表接口实现了分页
---


## 注意
- 不要生成单独的接口文档及API 使用指南