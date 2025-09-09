#!/usr/bin/env python3
"""
Скрипт для диагностики конфигурации на Render.com
"""

import os
import sys

def debug_render_config():
    print("🔍 ДИАГНОСТИКА КОНФИГУРАЦИИ RENDER")
    print("=" * 50)
    
    # Проверяем переменные окружения
    print("📋 Переменные окружения:")
    print(f"  DATABASE_URL: {os.environ.get('DATABASE_URL', 'НЕ УСТАНОВЛЕНА')}")
    print(f"  SECRET_KEY: {os.environ.get('SECRET_KEY', 'НЕ УСТАНОВЛЕНА')}")
    print(f"  FLASK_ENV: {os.environ.get('FLASK_ENV', 'НЕ УСТАНОВЛЕНА')}")
    print(f"  RENDER: {os.environ.get('RENDER', 'НЕ УСТАНОВЛЕНА')}")
    
    # Проверяем конфигурацию
    print("\n🔧 Конфигурация базы данных:")
    try:
        from config import Config
        print(f"  SQLALCHEMY_DATABASE_URI: {Config.SQLALCHEMY_DATABASE_URI}")
        
        # Проверяем валидность URL
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            if database_url.startswith('postgres://'):
                print("  ⚠️  Обнаружен старый формат postgres://")
                fixed_url = database_url.replace('postgres://', 'postgresql://', 1)
                print(f"  ✅ Исправленный URL: {fixed_url}")
            elif database_url.startswith('postgresql://'):
                print("  ✅ Формат postgresql:// корректен")
            else:
                print(f"  ❌ Неизвестный формат URL: {database_url[:20]}...")
        else:
            print("  ⚠️  DATABASE_URL не установлена, используется SQLite")
            
    except Exception as e:
        print(f"  ❌ Ошибка загрузки конфигурации: {e}")
    
    # Проверяем подключение к базе данных
    print("\n🔌 Тест подключения к базе данных:")
    try:
        from app import app, db
        with app.app_context():
            # Пробуем выполнить простой запрос
            result = db.session.execute(db.text("SELECT 1")).scalar()
            print(f"  ✅ Подключение успешно: {result}")
    except Exception as e:
        print(f"  ❌ Ошибка подключения: {e}")
        print(f"  Тип ошибки: {type(e).__name__}")
    
    print("\n" + "=" * 50)
    print("🏁 Диагностика завершена")

if __name__ == "__main__":
    debug_render_config()
