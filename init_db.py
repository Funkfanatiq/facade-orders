#!/usr/bin/env python3
"""
Надежный скрипт инициализации базы данных
"""

import os
import sys

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def init_database():
    """Инициализация базы данных"""
    try:
        print("🚀 Начинаем инициализацию...")
        
        from flask import Flask
        from config import Config
        from models import db, User
        
        print("✅ Импорты успешны")
        
        app = Flask(__name__)
        app.config.from_object(Config)
        
        print(f"📊 DATABASE_URL: {app.config.get('SQLALCHEMY_DATABASE_URI', 'НЕ НАЙДЕН')}")
        
        db.init_app(app)
        
        with app.app_context():
            print("🚀 Создание таблиц...")
            db.create_all()
            print("✅ Таблицы созданы")
            
            # Проверяем количество пользователей
            try:
                user_count = User.query.count()
                print(f"👥 Пользователей в базе: {user_count}")
                
                if user_count == 0:
                    print("👤 Создание пользователей...")
                    
                    # Создаем менеджера
                    manager = User(
                        username='manager',
                        password=User.hash_password('5678'),
                        role='Менеджер'
                    )
                    db.session.add(manager)
                    
                    # Создаем админа
                    admin = User(
                        username='admin',
                        password=User.hash_password('admin123'),
                        role='Админ'
                    )
                    db.session.add(admin)
                    
                    db.session.commit()
                    print("✅ Пользователи созданы")
                else:
                    print("✅ Пользователи уже существуют")
                    
            except Exception as e:
                print(f"⚠️ Ошибка при проверке пользователей: {e}")
                # Продолжаем выполнение
            
            print("🎉 Инициализация завершена!")
            return True
            
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_database()
    if not success:
        print("💥 Инициализация не удалась!")
        sys.exit(1)
    else:
        print("🎉 Инициализация успешна!")