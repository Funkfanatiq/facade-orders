#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для автоматизации развертывания на Render.com
"""

import os
import subprocess
import sys
import webbrowser
from pathlib import Path

def check_git():
    """Проверяем, установлен ли Git"""
    try:
        subprocess.run(['git', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_files():
    """Проверяем наличие необходимых файлов"""
    required_files = [
        'app.py',
        'models.py', 
        'config.py',
        'requirements.txt',
        'Procfile',
        'init_db.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    return missing_files

def init_git():
    """Инициализируем Git репозиторий"""
    print("🔧 Инициализируем Git репозиторий...")
    
    try:
        # Проверяем, уже ли это Git репозиторий
        subprocess.run(['git', 'status'], capture_output=True, check=True)
        print("✅ Git репозиторий уже инициализирован")
        return True
    except subprocess.CalledProcessError:
        # Инициализируем новый репозиторий
        subprocess.run(['git', 'init'], check=True)
        print("✅ Git репозиторий инициализирован")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации Git: {e}")
        return False

def create_gitignore():
    """Создаем .gitignore файл"""
    gitignore_content = """# Конфиденциальные файлы
yandex_token.txt
sync_info.json
token.pickle
credentials.json

# База данных (только для локальной разработки)
database.db
*.db
*.sqlite
*.sqlite3
/instance/
/migrations/versions/

# Загруженные файлы
uploads/

# Локальные резервные копии
/backups/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
"""
    
    with open('.gitignore', 'w', encoding='utf-8') as f:
        f.write(gitignore_content)
    print("✅ Создан .gitignore файл")

def add_files_to_git():
    """Добавляем файлы в Git"""
    print("📁 Добавляем файлы в Git...")
    
    try:
        subprocess.run(['git', 'add', '.'], check=True)
        print("✅ Файлы добавлены в Git")
        return True
    except Exception as e:
        print(f"❌ Ошибка добавления файлов: {e}")
        return False

def make_commit():
    """Делаем коммит"""
    print("💾 Создаем коммит...")
    
    try:
        subprocess.run(['git', 'commit', '-m', 'Initial commit: Facade Orders app for Render deployment'], check=True)
        print("✅ Коммит создан")
        return True
    except Exception as e:
        print(f"❌ Ошибка создания коммита: {e}")
        return False

def open_github():
    """Открываем GitHub для создания репозитория"""
    print("🌐 Открываем GitHub для создания репозитория...")
    webbrowser.open('https://github.com/new')
    print("✅ GitHub открыт в браузере")
    print("📋 Создайте репозиторий с именем 'facade-orders' и сделайте его публичным")

def open_render():
    """Открываем Render для развертывания"""
    print("🚀 Открываем Render для развертывания...")
    webbrowser.open('https://render.com')
    print("✅ Render открыт в браузере")

def main():
    """Основная функция"""
    print("🚀 АВТОМАТИЗАЦИЯ РАЗВЕРТЫВАНИЯ НА RENDER.COM")
    print("=" * 50)
    
    # Проверяем Git
    if not check_git():
        print("❌ Git не установлен. Установите Git с https://git-scm.com/")
        return
    
    # Проверяем файлы
    missing_files = check_files()
    if missing_files:
        print(f"❌ Отсутствуют файлы: {', '.join(missing_files)}")
        return
    
    print("✅ Все необходимые файлы найдены")
    
    # Инициализируем Git
    if not init_git():
        return
    
    # Создаем .gitignore
    create_gitignore()
    
    # Добавляем файлы
    if not add_files_to_git():
        return
    
    # Делаем коммит
    if not make_commit():
        return
    
    print("\n🎉 ПОДГОТОВКА ЗАВЕРШЕНА!")
    print("=" * 50)
    print("📋 Следующие шаги:")
    print("1. Создайте репозиторий на GitHub")
    print("2. Подключите локальный репозиторий к GitHub")
    print("3. Разверните на Render.com")
    print()
    
    # Открываем GitHub
    response = input("Открыть GitHub для создания репозитория? (y/n): ")
    if response.lower() in ['y', 'yes', 'да', 'д']:
        open_github()
    
    print("\n📖 Подробные инструкции:")
    print("- RENDER_QUICK_START.md - Быстрый старт")
    print("- RENDER_DEPLOY.md - Полное руководство")
    
    # Открываем Render
    response = input("\nОткрыть Render для развертывания? (y/n): ")
    if response.lower() in ['y', 'yes', 'да', 'д']:
        open_render()

if __name__ == "__main__":
    main()



