"""API 流程自检：注册/登录/对话历史/SSE 认证。AI 流式需网络，仅测其前置错误路径。"""
import asyncio

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Message, User

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
