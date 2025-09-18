#!/usr/bin/env python3
"""
Принудительная инициализация базы данных
"""

import os
import sys
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from models import db, User

def force_init():
    """Принудительная инициализация"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    
    with app.app_context():
        try:
            print("🔥 Принудительная инициализация...")
            
            # Удаляем все таблицы (если есть)
            db.drop_all()
            print("🗑️ Старые таблицы удалены")
            
            # Создаем все таблицы заново
            db.create_all()
            print("✅ Таблицы созданы")
            
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
            print("🎉 Инициализация завершена!")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    return True

if __name__ == "__main__":
    force_init()
