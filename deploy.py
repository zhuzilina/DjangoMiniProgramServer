#!/usr/bin/env python3
"""
自动部署脚本：创建虚拟环境、换清华镜像装依赖、初始化数据库、植入测试用户。
Windows / Linux 通用，用当前系统 Python 运行：python deploy.py
"""
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
IS_WINDOWS = os.name == 'nt'
VENV_PY = BASE_DIR / '.venv' / ('Scripts/python.exe' if IS_WINDOWS else 'bin/python')
MIRROR = 'https://pypi.tuna.tsinghua.edu.cn/simple'

# 测试用户
TEST_USER = {
    'pk': '20240001',
    'name': '测试用户', 'major': '计算机', 'class_name': '测试班',
    'phone': '13800000000', 'campus': '本部', 'password': 'abc123',
}
# 测试管理员
TEST_ADMIN = {
    'pk': 'admin001',
    'name': '管理员', 'major': '管理', 'class_name': '管理员',
    'phone': '00000000000', 'campus': '本部', 'password': 'admin123',
}


def run(cmd, check=True):
    print(f'\n>>> {" ".join(str(c) for c in cmd)}')
    r = subprocess.run([str(c) for c in cmd])
    if check and r.returncode != 0:
        sys.exit(f'命令失败：{" ".join(str(c) for c in cmd)}')
    return r


def create_venv():
    if VENV_PY.exists():
        print(f'\n.venv 已存在，跳过创建：{VENV_PY}')
        return
    print('\n>>> 创建虚拟环境 .venv')
    run([sys.executable, '-m', 'venv', str(BASE_DIR / '.venv')])


def install_deps():
    print(f'\n>>> 使用清华源安装依赖（{MIRROR}）')
    run([VENV_PY, '-m', 'pip', 'install', '-i', MIRROR,
         '-r', str(BASE_DIR / 'requirements.txt')])


def init_db():
    print('\n>>> 运行 Django 数据库初始化（migrate）')
    run([VENV_PY, str(BASE_DIR / 'manage.py'), 'migrate'])
    seed = f'''
from api.models import User

def seed_user(pk, name, major, class_name, phone, campus, password, superuser=False):
    u, created = User.objects.get_or_create(
        pk=pk,
        defaults={{"name": name, "major": major, "class_name": class_name,
                   "phone": phone, "campus": campus}},
    )
    if created:
        u.set_password(password)
        u.is_staff = superuser
        u.is_superuser = superuser
        u.save()
        print("已创建：" + pk + " / " + password)
    else:
        print("已存在，跳过：" + pk)

# 测试普通用户
seed_user({TEST_USER['pk']!r}, {TEST_USER['name']!r}, {TEST_USER['major']!r},
          {TEST_USER['class_name']!r}, {TEST_USER['phone']!r}, {TEST_USER['campus']!r},
          {TEST_USER['password']!r})
# 测试管理员
seed_user({TEST_ADMIN['pk']!r}, {TEST_ADMIN['name']!r}, {TEST_ADMIN['major']!r},
          {TEST_ADMIN['class_name']!r}, {TEST_ADMIN['phone']!r}, {TEST_ADMIN['campus']!r},
          {TEST_ADMIN['password']!r}, True)
'''
    r = subprocess.run([str(VENV_PY), str(BASE_DIR / 'manage.py'), 'shell'],
                       input=seed, text=True, cwd=str(BASE_DIR))
    if r.returncode != 0:
        sys.exit('测试账号植入失败')


def main():
    print(f'检测到系统：{"Windows" if IS_WINDOWS else "Linux"}')
    create_venv()
    install_deps()
    init_db()

    cmd = 'set QWEN_TOKEN=你的APIKey' if IS_WINDOWS else 'export QWEN_TOKEN=你的APIKey'
    print(f'''
部署完成！

已植入测试账号：
  普通用户：{TEST_USER['pk']} / {TEST_USER['password']}
  管理员：  {TEST_ADMIN['pk']} / {TEST_ADMIN['password']}   （资讯管理后台：/admin_news/）

请设置阿里云百炼 API Key 环境变量后启动服务：
  {cmd}

（Windows 也可在 系统设置 > 环境变量 中永久添加 QWEN_TOKEN）
启动：{VENV_PY} manage.py runserver
''')


if __name__ == '__main__':
    main()
