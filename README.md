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

> Token 从登录/注册响应的 `token` 字段获取，请求时放 `Authorization: Token <token>` 头。
> 对话流程：先调接口 3 保存用户消息拿到 `conversation_id`，再调接口 4 传 `conversation_id` 流式收 AI 回复。

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
