#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных на Render.com
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from models import db, User, Order, Employee, SalaryPeriod

def init_database():
    """Инициализация базы данных"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    migrate = Migrate(app, db)
    
    with app.app_context():
        try:
            # Создаем все таблицы
            print("Создание таблиц...")
            db.create_all()
            print("✅ Таблицы созданы успешно!")
            
            # Проверяем, есть ли пользователи
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                print("Создание администратора...")
                admin_user = User(
                    username='admin',
                    password=User.hash_password('admin123'),
                    role='Админ'
                )
                db.session.add(admin_user)
                print("✅ Администратор создан: admin / admin123")
            else:
                print("✅ Администратор уже существует")
            
            # Проверяем, есть ли менеджер
            manager_user = User.query.filter_by(username='manager').first()
            if not manager_user:
                print("Создание менеджера...")
                manager_user = User(
                    username='manager',
                    password=User.hash_password('5678'),
                    role='Менеджер'
                )
                db.session.add(manager_user)
                print("✅ Менеджер создан: manager / 5678")
            else:
                print("✅ Менеджер уже существует")
            
            # Создаем других пользователей
            users_to_create = [
                ('worker', '0000', 'Производство'),
                ('cutter', '7777', 'Фрезеровка'),
                (' polisher', '8888', 'Шлифовка'),
                ('monitor', '9999', 'Монитор')
            ]
            
            for username, password, role in users_to_create:
                existing_user = User.query.filter_by(username=username).first()
                if not existing_user:
                    user = User(
                        username=username,
                        password=User.hash_password(password),
                        role=role
                    )
                    db.session.add(user)
                    print(f"✅ Пользователь создан: {username} / {password}")
            
            db.session.commit()
            
            # Проверяем подключение
            result = db.session.execute(db.text("SELECT 1"))
            print("✅ Подключение к базе данных работает!")
            
        except Exception as e:
            print(f"❌ Ошибка при инициализации базы данных: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("🚀 Инициализация базы данных на Render...")
    success = init_database()
    if success:
        print("🎉 База данных успешно инициализирована!")
    else:
        print("💥 Ошибка при инициализации базы данных!")
        sys.exit(1)
