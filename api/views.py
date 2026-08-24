import json

from asgiref.sync import sync_to_async
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .agent import run_agent_stream
from .models import Conversation, Message, News, User
from .serializers import MessageSerializer, NewsSerializer, UserSerializer

REGISTER_FIELDS = ['student_id', 'major', 'password', 'class_name', 'name', 'phone', 'campus']


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        for f in REGISTER_FIELDS:
            if not str(data.get(f, '')).strip():
                return Response({'error': f'{f} 不能为空'}, status=400)
        if User.objects.filter(pk=data['student_id'].strip()).exists():
            return Response({'error': '学号已注册'}, status=400)

        user = User.objects.create_user(
            data['student_id'].strip(),
            password=data['password'],
            major=data['major'].strip(),
            class_name=data['class_name'].strip(),
            name=data['name'].strip(),
            phone=data['phone'].strip(),
            campus=data['campus'].strip(),
        )
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user': UserSerializer(user).data}, status=201)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        student_id = str(request.data.get('student_id', '')).strip()
        password = str(request.data.get('password', ''))
        user = User.objects.filter(pk=student_id).first()
        if not user:
            return Response({'error': '学号不存在'}, status=400)
        if not user.check_password(password):
            return Response({'error': '密码错误'}, status=400)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user': UserSerializer(user).data})


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class CreateMessageView(APIView):
    """保存用户消息，返回 {message_id, conversation_id}；conversation_id 为空时新建对话"""

    def post(self, request):
        content = str(request.data.get('content', '')).strip()
        conversation_id = request.data.get('conversation_id')
        if not content:
            return Response({'error': '消息不能为空'}, status=400)

        conv = None
        if conversation_id:
            conv = Conversation.objects.filter(id=conversation_id, user=request.user).first()
            if not conv:
                return Response({'error': '对话不存在'}, status=404)
        if not conv:
            conv = Conversation.objects.create(user=request.user)

        msg = Message.objects.create(conversation=conv, role='user', content=content)
        return Response({'message_id': msg.id, 'conversation_id': conv.id})


@csrf_exempt
async def chat_stream(request):
    """SSE 流式对话。前端先调 CreateMessageView 保存用户消息，再传 conversation_id

    ponytail: 用普通 async 视图而非 DRF APIView —— DRF 的异步 dispatch 里 token
    认证会同步查库触发 SynchronousOnlyOperation，这里手动用 sync_to_async 包裹认证。
    """
    try:
        result = await sync_to_async(TokenAuthentication().authenticate)(request)
    except Exception:
        result = None
    if not result:
        return StreamingHttpResponse(error_stream('未认证'), content_type='text/event-stream', status=401)
    user = result[0]

    try:
        conversation_id = json.loads(request.body).get('conversation_id')
    except (json.JSONDecodeError, AttributeError):
        return StreamingHttpResponse(error_stream('参数错误'), content_type='text/event-stream', status=400)

    # 从数据库取完整历史（含刚保存的用户消息），避免依赖 langgraph 内存
    conv = await sync_to_async(Conversation.objects.filter(id=conversation_id, user=user).first)()
    if not conv:
        return StreamingHttpResponse(error_stream('对话不存在'), content_type='text/event-stream', status=404)
    history = await sync_to_async(list)(conv.messages.all())
    messages = [{'role': m.role, 'content': m.content} for m in history]
    user_info = {'student_id': user.student_id, 'name': user.name}

    async def event_stream():
        assistant_content = ''
        try:
            async for token in run_agent_stream(messages, user_info):
                assistant_content += token
                yield f"data: {token}\n\n".encode('utf-8')
            yield b"data: [DONE]\n\n"
            if assistant_content:
                await sync_to_async(Message.objects.create)(
                    conversation=conv, role='assistant', content=assistant_content)
        except Exception as e:
            yield f"data: {{'error': '{e}'}}\n\n".encode('utf-8')
            yield b"data: [DONE]\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


class ConversationListView(APIView):
    def get(self, request):
        result = []
        for conv in request.user.conversations.all():
            first = conv.messages.filter(role='user').first()
            result.append({
                'id': conv.id,
                'preview': first.content[:80] if first else '',
                'msg_count': conv.messages.count(),
                'updated_at': conv.updated_at.strftime('%m-%d %H:%M'),
            })
        return Response({'conversations': result})


class ConversationMessagesView(APIView):
    def get(self, request, conv_id):
        conv = request.user.conversations.filter(id=conv_id).first()
        if not conv:
            return Response({'error': '对话不存在'}, status=404)
        return Response({'messages': MessageSerializer(conv.messages.all(), many=True).data})


class DeleteConversationView(APIView):
    def delete(self, request, conv_id):
        deleted, _ = request.user.conversations.filter(id=conv_id).delete()
        return Response({'deleted': deleted})


class NewsViewSet(viewsets.ModelViewSet):
    """校园资讯：增删改仅管理员(is_staff)，其余角色只读；列表支持 ?category=&campus= 过滤"""
    queryset = News.objects.all()
    serializer_class = NewsSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get('category')
        campus = self.request.query_params.get('campus')
        if category:
            qs = qs.filter(category=category)
        if campus:
            qs = qs.filter(campus=campus)
        return qs


async def error_stream(msg: str):
    yield f"data: {{'error': '{msg}'}}\n\n".encode('utf-8')
    yield b"data: [DONE]\n\n"
