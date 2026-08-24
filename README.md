# 652学长 — 校园 AI 学长 API 服务

基于 Django + Django REST Framework 的纯接口服务，对接微信小程序。
数据库使用 SQLite，Token 认证。

## 快速开始

```bash
pip install -r requirements.txt
set QWEN_TOKEN=百炼APIKey    # 未设置时 AI 流式接口会返回错误帧，其余接口不受影响
python manage.py runserver
```

## 接口总览

| # | 接口 | 方法 | 路径 | 认证 | 请求体 / 说明 |
| --- | ------ | ------ | ------ | ------ | --------------- |
| 1 | 登录 | POST | `/api/login/` | 无 | `{"student_id", "password"}` |
| 2 | 当前用户 | GET | `/api/me/` | Token | — |
| 3 | 保存用户消息 | POST | `/api/chat/` | Token | `{"content"}` → 返回 `message_id` + `conversation_id` |
| 4 | AI 流式对话 | POST | `/api/chat/stream/` | Token | `{"conversation_id"}`（SSE 流式返回） |
| 5 | 对话历史列表 | GET | `/api/conversations/` | Token | — |
| 6 | 单个对话消息 | GET | `/api/conversations/<id>/messages/` | Token | — |
| 7 | 删除对话 | DELETE | `/api/conversations/<id>/` | Token | — |
| 8 | 注册 | POST | `/api/register/` | 无 | 见下表 |
| 9 | 资讯列表 | GET | `/api/news/` | Token | 支持 `?category=` `?campus=` 过滤 |
| 10 | 资讯详情 | GET | `/api/news/<id>/` | Token | — |
| 11 | 新增资讯 | POST | `/api/news/` | Token(管理员) | 见下表 |
| 12 | 更新资讯 | PUT/PATCH | `/api/news/<id>/` | Token(管理员) | 见下表 |
| 13 | 删除资讯 | DELETE | `/api/news/<id>/` | Token(管理员) | — |

> Token 从登录/注册响应的 `token` 字段获取，请求时放 `Authorization: Token <token>` 头。
> 对话流程：先调接口 3 保存用户消息拿到 `conversation_id`，再调接口 4 传 `conversation_id` 流式收 AI 回复。
> 资讯写操作（新增/更新/删除）仅管理员（`is_staff`）可用，其余角色只读。

## 注册字段

| 字段 | 说明 | 约束 |
| ------ | ------ | ------ |
| `student_id` | 学号 | 主键，必填，唯一 |
| `name` | 姓名 | 必填 |
| `major` | 专业 | 必填 |
| `class_name` | 班级 | 必填 |
| `phone` | 电话 | 必填 |
| `campus` | 校区 | 必填 |
| `password` | 密码 | 必填，哈希存储 |

## 资讯字段

| 字段 | 说明 | 约束 |
| ------ | ------ | ------ |
| `title` | 标题 | 必填 |
| `content` | 内容（纯文本） | 必填 |
| `category` | 类别 | 必填 |
| `campus` | 校区 | 必填 |
| `publish_date` | 发布日期 | 必填，格式 `YYYY-MM-DD` |

## 请求/响应示例

### 注册

```json
POST /api/register/
{
    "student_id": "123456789",
    "major": "计算机科学与技术",
    "class_name": "2023级5班",
    "phone": "12312345678",
    "campus": "宜宾",
    "password": "qwer1234",
    "name": "张三"
}
```

### 登录

```json
POST /api/login/
{ "student_id": "20240001", "password": "abc123" }
```

### 流式对话

```json
POST /api/chat/stream/
Authorization: Token <token>
{ "conversation_id": 6 }
```

SSE 响应：`data: {token}\n\n` 逐块返回 AI 内容，以 `data: [DONE]` 结束。

### 新增资讯（管理员）

```json
POST /api/news/
Authorization: Token <token>
{
    "title": "迎新晚会",
    "content": "本周五晚 7 点在礼堂举办迎新晚会，欢迎参加。",
    "category": "活动",
    "campus": "本部",
    "publish_date": "2026-08-25"
}
```

普通用户调用返回 `403`。管理员可通过 `manage.py shell` 创建或把现有用户 `is_staff` 设为 `True`。
