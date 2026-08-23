"""URL configuration for djangominiprogramserver project."""
from django.contrib import admin
from django.urls import path

from api import views

urlpatterns = [
    path('admin/', admin.site.urls),
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
]
