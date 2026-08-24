"""校园资讯库只读查询工具：AI 自主写 SQL，执行前校验安全性"""
import json
import re

from asgiref.sync import sync_to_async
from django.db import connection
from langchain_core.tools import tool

# 允许访问的表（Django 默认表名：app_模型）
ALLOWED_TABLES = frozenset({'api_news'})

# 危险关键字（移除注释/字符串后全表扫描）
_DANGEROUS = re.compile(
    r'\b(?:INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|GRANT|REVOKE|TRUNCATE|'
    r'VACUUM|REINDEX|ANALYZE|ATTACH|DETACH|PRAGMA|BEGIN|COMMIT|ROLLBACK|'
    r'LOAD_EXTENSION|WRITEFILE|READFILE|EXEC|CALL|MERGE|RENAME|USING|WITH)\b',
    re.IGNORECASE,
)
_TABLE_REF_RE = re.compile(r'(?:FROM|JOIN)\s+[`"\']?(\w+)[`"\']?', re.IGNORECASE)

MAX_ROWS = 100


def _strip_literals(sql: str) -> str:
    """移除注释和字符串字面量，避免其中关键字/分号误判"""
    sql = re.sub(r'--[^\n]*', '', sql)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    return re.sub(r"'[^']*'|\"[^\"]*\"", '', sql)


def _validate_sql(sql: str):
    """返回 None 表示安全，否则返回错误原因"""
    cleaned = _strip_literals(sql).strip()
    if not cleaned.upper().startswith('SELECT'):
        return '只允许 SELECT 查询'
    if _DANGEROUS.search(cleaned):
        return '包含不允许的操作关键字'
    if ';' in cleaned:
        return '不允许多条语句'
    for tbl in _TABLE_REF_RE.findall(cleaned):
        if tbl.lower() not in ALLOWED_TABLES:
            return f'不允许访问表：{tbl}'
    return None


def _execute(sql: str) -> str:
    err = _validate_sql(sql)
    if err:
        return f'SQL 被拒绝：{err}'
    try:
        with connection.cursor() as cur:
            cur.execute(sql)
            cols = [c[0] for c in cur.description] if cur.description else []
            rows = []
            for i, row in enumerate(cur):
                if i >= MAX_ROWS:
                    return json.dumps(rows, ensure_ascii=False, default=str) + f'\n…（超过 {MAX_ROWS} 条，仅显示前 {MAX_ROWS} 条）'
                rows.append(dict(zip(cols, row)))
            return json.dumps(rows, ensure_ascii=False, default=str)
    except Exception as e:
        return f'SQL 执行出错：{e}'


@tool
async def query_news(sql: str) -> str:
    """查询校园资讯数据库（只读）。

    请用 SQLite SELECT 语句查询，返回 JSON 数组。表名必须是 `api_news`，字段：
    id, title(标题), content(正文), category(类别), campus(校区), publish_date(发布日期, YYYY-MM-DD), created_at, updated_at。
    建议加 LIMIT 控制返回行数。

    示例：
    SELECT title, category, campus, publish_date FROM api_news ORDER BY publish_date DESC LIMIT 10
    SELECT title, content FROM api_news WHERE category='活动' AND campus='本部' LIMIT 5
    """
    return await sync_to_async(_execute)(sql)