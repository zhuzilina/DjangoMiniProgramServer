from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Django 6.1 的默认 UserManager 硬编码 username=，自定义以适配学号作主键"""
    use_in_migrations = True

    def create_user(self, student_id, password=None, **extra_fields):
        if not student_id:
            raise ValueError('学号必须设置')
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        user = self.model(student_id=student_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, student_id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(student_id, password, **extra_fields)


class User(AbstractUser):
    """学生用户，学号作主键"""
    student_id = models.CharField('学号', max_length=20, primary_key=True)
    username = None  # 用学号代替 username
    major = models.CharField('专业', max_length=100)
    class_name = models.CharField('班级', max_length=50)
    name = models.CharField('姓名', max_length=50)
    phone = models.CharField('电话', max_length=20)
    campus = models.CharField('校区', max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'student_id'
    REQUIRED_FIELDS = ['major', 'class_name', 'name', 'phone', 'campus']

    def __str__(self):
        return self.student_id


class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']


class Message(models.Model):
    """对话消息"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20)  # user / assistant
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
