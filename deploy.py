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
    run([VENV_PY, 'manage.py', 'migrate'])
    seed = f'''
from api.models import User
u, created = User.objects.get_or_create(
    pk="{TEST_USER['pk']}",
    defaults={{"name": "{TEST_USER['name']}", "major": "{TEST_USER['major']}",
               "class_name": "{TEST_USER['class_name']}", "phone": "{TEST_USER['phone']}",
               "campus": "{TEST_USER['campus']}"}},
)
if created:
    u.set_password("{TEST_USER['password']}")
    u.save()
    print("测试用户已创建：{TEST_USER['pk']} / {TEST_USER['password']}")
else:
    print("测试用户已存在，跳过")
'''
    run([VENV_PY, 'manage.py', 'shell', '-c', seed])


def main():
    print(f'检测到系统：{"Windows" if IS_WINDOWS else "Linux"}')
    create_venv()
    install_deps()
    init_db()

    cmd = 'set QWEN_TOKEN=你的APIKey' if IS_WINDOWS else 'export QWEN_TOKEN=你的APIKey'
    print(f'''
部署完成！

请设置阿里云百炼 API Key 环境变量后启动服务：
  {cmd}

（Windows 也可在 系统设置 > 环境变量 中永久添加 QWEN_TOKEN）
启动：{VENV_PY} manage.py runserver
''')


if __name__ == '__main__':
    main()
