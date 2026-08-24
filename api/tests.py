"""API 流程自检：注册/登录/对话历史/SSE 认证。AI 流式需网络，仅测其前置错误路径。"""
import asyncio

from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import Message, News, User
from .tools import _execute

USER = {'student_id': '20240001', 'major': '计算机', 'password': 'abc123',
        'class_name': '计科1班', 'name': '张三', 'phone': '13800000000', 'campus': '本部'}


def _collect(r):
    async def run():
        out = []
        async for ch in r.streaming_content:
            out.append(ch.decode('utf-8', 'ignore'))
        return out
    return asyncio.run(run())


class FlowTests(TestCase):
    def setUp(self):
        self.c = APIClient()

    def test_register_login(self):
        r = self.c.post('/api/register/', USER, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.json()['token'])
        # 重复注册
        self.assertEqual(self.c.post('/api/register/', USER, format='json').status_code, 400)
        # 密码错误 / 正确
        self.assertEqual(self.c.post('/api/login/', {'student_id': '20240001', 'password': 'x'}, format='json').status_code, 400)
        r = self.c.post('/api/login/', {'student_id': '20240001', 'password': 'abc123'}, format='json')
        self.assertEqual(r.status_code, 200)
        # 密码哈希落库
        u = User.objects.get(pk='20240001')
        self.assertTrue(u.check_password('abc123'))

    def test_me_auth(self):
        self.c.post('/api/register/', USER, format='json')
        self.assertEqual(APIClient().get('/api/me/').status_code, 401)
        tok = self.c.post('/api/login/', {'student_id': '20240001', 'password': 'abc123'}, format='json').json()['token']
        self.c.credentials(HTTP_AUTHORIZATION='Token ' + tok)
        self.assertEqual(self.c.get('/api/me/').json()['name'], '张三')

    def test_conversation_flow(self):
        self.c.post('/api/register/', USER, format='json')
        tok = self.c.post('/api/login/', {'student_id': '20240001', 'password': 'abc123'}, format='json').json()['token']
        self.c.credentials(HTTP_AUTHORIZATION='Token ' + tok)

        r = self.c.post('/api/chat/', {'content': '你好'}, format='json')
        cid = r.json()['conversation_id']
        self.assertEqual(Message.objects.get(pk=r.json()['message_id']).role, 'user')

        self.assertEqual(self.c.get('/api/conversations/').json()['conversations'][0]['preview'], '你好')
        msgs = self.c.get(f'/api/conversations/{cid}/messages/').json()['messages']
        self.assertEqual(len(msgs), 1)
        # 删除是级联：conversation + 其中 message 一并删
        self.assertEqual(self.c.delete(f'/api/conversations/{cid}/').json()['deleted'], 2)
        self.assertEqual(self.c.get(f'/api/conversations/{cid}/messages/').status_code, 404)

    def test_news_crud(self):
        news = {'title': '迎新晚会', 'content': '本周五晚举办迎新晚会',
                'category': '活动', 'campus': '本部', 'publish_date': '2026-08-25'}
        # 普通用户：只读，写入返回 403
        self.c.post('/api/register/', USER, format='json')
        tok = self.c.post('/api/login/', {'student_id': '20240001', 'password': 'abc123'}, format='json').json()['token']
        self.c.credentials(HTTP_AUTHORIZATION='Token ' + tok)
        self.assertEqual(self.c.post('/api/news/', news, format='json').status_code, 403)
        self.assertEqual(len(self.c.get('/api/news/').json()), 0)

        # 管理员：完整 CRUD
        admin = User.objects.create_superuser(
            'admin001', password='admin123', major='x', class_name='x', name='管理员', phone='x', campus='x')
        tok_admin, _ = Token.objects.get_or_create(user=admin)
        self.c.credentials(HTTP_AUTHORIZATION='Token ' + tok_admin.key)

        r = self.c.post('/api/news/', news, format='json')
        self.assertEqual(r.status_code, 201)
        nid = r.json()['id']

        # 列表 + 按校区过滤
        self.assertEqual(len(self.c.get('/api/news/').json()), 1)
        self.assertEqual(len(self.c.get('/api/news/', {'campus': '本部'}, format='json').json()), 1)
        self.assertEqual(len(self.c.get('/api/news/', {'campus': '宜宾'}, format='json').json()), 0)

        # 更新 + 详情 + 删除
        self.assertEqual(self.c.patch(f'/api/news/{nid}/', {'title': '迎新晚会改期'}, format='json').json()['title'], '迎新晚会改期')
        self.assertEqual(self.c.get(f'/api/news/{nid}/').json()['title'], '迎新晚会改期')
        self.assertEqual(self.c.delete(f'/api/news/{nid}/').status_code, 204)
        self.assertEqual(len(self.c.get('/api/news/').json()), 0)

    def test_admin_news_page(self):
        # 未登录 -> 重定向到管理登录页
        r = self.client.get('/admin_news/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/admin/login/', r.url)
        # 普通用户 -> 仍重定向（仅管理员）
        normal = User.objects.create_user(USER['student_id'], password=USER['password'],
                                          major='计算机', class_name='测试班', name='测试', phone='1', campus='本部')
        self.client.force_login(normal)
        self.assertEqual(self.client.get('/admin_news/').status_code, 302)
        # 管理员 -> 页面可访问
        admin = User.objects.create_superuser('admin001', password='admin123', major='x',
                                              class_name='x', name='管理员', phone='x', campus='x')
        self.client.force_login(admin)
        r = self.client.get('/admin_news/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '资讯管理')
        self.assertContains(r, 'vue.global.prod.js')
        # 管理员 session 直接调用资讯 API 增删改查
        self.assertEqual(self.client.post('/api/news/', {'title': 't', 'content': 'c', 'category': 'a',
                                                          'campus': 'b', 'publish_date': '2026-08-25'},
                                          content_type='application/json').status_code, 201)

    def test_query_news_tool(self):
        News.objects.create(title='迎新晚会', content='周五晚', category='活动', campus='本部', publish_date='2026-08-25')
        # 安全查询
        out = _execute("SELECT title FROM api_news WHERE campus='本部' LIMIT 5")
        self.assertIn('迎新晚会', out)
        # 非 SELECT / DDL / 多语句 / 越权表
        self.assertIn('被拒绝', _execute('DELETE FROM api_news'))
        self.assertIn('被拒绝', _execute("SELECT title FROM api_news; DROP TABLE api_news"))
        self.assertIn('被拒绝', _execute("SELECT * FROM auth_user"))
        self.assertIn('被拒绝', _execute('PRAGMA table_info(api_news)'))
        # 数据未被破坏
        self.assertEqual(News.objects.count(), 1)

    def test_stream_auth(self):
        self.c.post('/api/register/', USER, format='json')
        # 未带 token -> 401
        r = APIClient().post('/api/chat/stream/', {'conversation_id': 1}, format='json')
        self.assertEqual(r.status_code, 401)
        self.assertIn('未认证', _collect(r)[0])
        # 带 token 但对话不存在 -> 404
        tok = self.c.post('/api/login/', {'student_id': '20240001', 'password': 'abc123'}, format='json').json()['token']
        self.c.credentials(HTTP_AUTHORIZATION='Token ' + tok)
        r = self.c.post('/api/chat/stream/', {'conversation_id': 999}, format='json')
        self.assertEqual(r.status_code, 404)
        self.assertIn('对话不存在', _collect(r)[0])
