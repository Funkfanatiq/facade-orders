#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для настройки PostgreSQL подключения к Render
"""

import os

def create_env_file():
    """Создает файл .env с настройками PostgreSQL для Render"""
    env_content = """# PostgreSQL на Render - данные сохраняются навсегда!
DATABASE_URL=postgresql://facade_user:2BojvrPNG9p65kS6on1dgzu7i2ks1Aq6@dpg-d2vj30ur433s73c09er0-a/facade_orders

# Секретный ключ для Flask
SECRET_KEY=your-super-secret-key-change-in-production

# Окружение
FLASK_ENV=production
"""
    
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("✅ Файл .env создан успешно!")
        print("📋 Содержимое:")
        print(env_content)
        return True
    except Exception as e:
        print(f"❌ Ошибка создания файла .env: {str(e)}")
        return False

def update_app_py():
    """Обновляет app.py для загрузки переменных окружения"""
    try:
        # Читаем текущий файл app.py
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем, есть ли уже импорт dotenv
        if 'from dotenv import load_dotenv' in content:
            print("✅ app.py уже настроен для загрузки .env")
            return True
        
        # Добавляем импорт dotenv после других импортов
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            # Добавляем импорт dotenv после импорта os
            if line.startswith('import os') and i < len(lines) - 1:
                new_lines.append('from dotenv import load_dotenv')
                new_lines.append('')
                new_lines.append('# Загружаем переменные окружения из .env файла')
                new_lines.append('load_dotenv()')
        
        # Записываем обновленный файл
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        
        print("✅ app.py обновлен для загрузки .env файла")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка обновления app.py: {str(e)}")
        return False

def update_requirements():
    """Обновляет requirements.txt для PostgreSQL"""
    try:
        # Читаем текущий файл requirements.txt
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем, есть ли уже python-dotenv
        if 'python-dotenv' in content:
            print("✅ requirements.txt уже содержит python-dotenv")
            return True
        
        # Добавляем python-dotenv
        if not content.endswith('\n'):
            content += '\n'
        content += 'python-dotenv==1.0.0\n'
        
        # Записываем обновленный файл
        with open('requirements.txt', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ requirements.txt обновлен")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка обновления requirements.txt: {str(e)}")
        return False

def test_connection():
    """Тестирует подключение к PostgreSQL"""
    try:
        import os
        from dotenv import load_dotenv
        
        # Загружаем переменные окружения
        load_dotenv()
        
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("❌ Переменная DATABASE_URL не найдена!")
            return False
        
        print("🔍 Тестируем подключение к PostgreSQL на Render...")
        print(f"📡 Хост: {database_url.split('@')[1].split('/')[0]}")
        
        # Импортируем и тестируем подключение
        from app import app, db
        from models import User
        
        with app.app_context():
            # Простой запрос для проверки подключения
            user_count = User.query.count()
            print(f"✅ Подключение успешно!")
            print(f"👥 Пользователей в базе: {user_count}")
            
            # Проверяем информацию о базе данных
            result = db.session.execute("SELECT version();")
            version = result.fetchone()[0]
            print(f"📊 Версия PostgreSQL: {version}")
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка подключения: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 НАСТРОЙКА POSTGRESQL НА RENDER")
    print("=" * 50)
    print("💡 Теперь данные будут сохраняться навсегда!")
    print("=" * 50)
    
    # Создаем файл .env
    if create_env_file():
        print("\n🔧 Обновляем конфигурацию...")
        
        # Обновляем app.py
        if update_app_py():
            print("✅ app.py обновлен")
        
        # Обновляем requirements.txt
        if update_requirements():
            print("✅ requirements.txt обновлен")
        
        print("\n📦 Установите зависимости:")
        print("pip install python-dotenv")
        
        print("\n🚀 Следующие шаги:")
        print("1. Установите зависимости: pip install python-dotenv")
        print("2. Инициализируйте базу: python render_init_db.py")
        print("3. Запустите приложение: python app.py")
        print("4. Проверьте работу - данные должны сохраняться!")
        
        print("\n🌐 Для деплоя на Render:")
        print("1. Добавьте переменную DATABASE_URL в Environment")
        print("2. Перезапустите приложение через Manual Deploy")
        
    else:
        print("\n❌ Не удалось создать файл .env")
