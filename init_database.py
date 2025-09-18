#!/usr/bin/env python3
"""
Надежный скрипт для инициализации базы данных на Render
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from models import db, User, Order, Employee, SalaryPeriod

def init_database():
    """Инициализация базы данных с обработкой ошибок"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    
    with app.app_context():
        try:
            print("🚀 Начинаем инициализацию базы данных...")
            
            # Создаем все таблицы
            print("📊 Создание таблиц...")
            db.create_all()
            print("✅ Таблицы созданы успешно!")
            
            # Проверяем подключение
            result = db.session.execute(db.text("SELECT 1"))
            print("✅ Подключение к базе данных работает!")
            
            # Проверяем, есть ли пользователи
            user_count = User.query.count()
            print(f"👥 Найдено пользователей: {user_count}")
            
            if user_count == 0:
                print("👤 Создание пользователей...")
                
                # Создаем менеджера
                manager = User(
                    username='manager',
                    password=User.hash_password('5678'),
                    role='Менеджер'
                )
                db.session.add(manager)
                print("✅ Менеджер создан: manager / 5678")
                
                # Создаем админа
                admin = User(
                    username='admin',
                    password=User.hash_password('admin123'),
                    role='Админ'
                )
                db.session.add(admin)
                print("✅ Админ создан: admin / admin123")
                
                # Создаем других пользователей
                users_data = [
                    ('worker', '0000', 'Производство'),
                    ('cutter', '7777', 'Фрезеровка'),
                    ('polisher', '8888', 'Шлифовка'),
                    ('monitor', '9999', 'Монитор')
                ]
                
                for username, password, role in users_data:
                    user = User(
                        username=username,
                        password=User.hash_password(password),
                        role=role
                    )
                    db.session.add(user)
                    print(f"✅ Пользователь создан: {username} / {password}")
                
                db.session.commit()
                print("🎉 Все пользователи созданы успешно!")
            else:
                print("✅ Пользователи уже существуют!")
            
            # Проверяем таблицы
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📋 Созданные таблицы: {tables}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при инициализации: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("🔧 Инициализация базы данных...")
    success = init_database()
    if success:
        print("🎉 База данных успешно инициализирована!")
    else:
        print("💥 Ошибка при инициализации!")
        sys.exit(1)
