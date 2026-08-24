from rest_framework import serializers

from .models import Message, News, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['student_id', 'major', 'class_name', 'name', 'phone', 'campus', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'role', 'content', 'created_at']


class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = ['id', 'title', 'content', 'category', 'campus', 'publish_date', 'created_at', 'updated_at']
