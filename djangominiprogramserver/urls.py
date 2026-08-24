"""URL configuration for djangominiprogramserver project."""
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api import views

router = DefaultRouter()
router.register('news', views.NewsViewSet, basename='news')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin_news/', views.admin_news_page),
    # 用户
    path('api/register/', views.RegisterView.as_view()),
    path('api/login/', views.LoginView.as_view()),
    path('api/me/', views.MeView.as_view()),
    # AI 对话
    path('api/chat/', views.CreateMessageView.as_view()),
    path('api/chat/stream/', views.chat_stream),
    path('api/conversations/', views.ConversationListView.as_view()),
    path('api/conversations/<int:conv_id>/messages/', views.ConversationMessagesView.as_view()),
    path('api/conversations/<int:conv_id>/', views.DeleteConversationView.as_view()),
    # 校园资讯（ModelViewSet 增删改查）
    path('api/', include(router.urls)),
]