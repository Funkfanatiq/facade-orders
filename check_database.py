#!/usr/bin/env python3
"""
Скрипт для проверки базы данных и пользователей
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from models import db, User

def check_database():
    """Проверка базы данных и пользователей"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    
    with app.app_context():
        try:
            # Проверяем подключение
            result = db.session.execute(db.text("SELECT 1"))
            print("✅ Подключение к базе данных работает!")
            
            # Проверяем пользователей
            users = User.query.all()
            print(f"📊 Найдено пользователей: {len(users)}")
            
            for user in users:
                print(f"  - {user.username} ({user.role})")
            
            # Проверяем конкретно менеджера
            manager = User.query.filter_by(username='manager').first()
            if manager:
                print(f"✅ Менеджер найден: {manager.username} ({manager.role})")
            else:
                print("❌ Менеджер не найден!")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при проверке базы данных: {e}")
            return False

if __name__ == "__main__":
    print("🔍 Проверка базы данных...")
    success = check_database()
    if not success:
        sys.exit(1)
