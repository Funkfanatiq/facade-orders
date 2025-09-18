#!/usr/bin/env python3
"""
Скрипт для проверки подключения к базе данных
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config

def test_connection():
    """Тестирование подключения к базе данных"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # Проверяем подключение
            result = db.session.execute(db.text("SELECT 1"))
            print("✅ Подключение к базе данных работает!")
            print(f"📊 DATABASE_URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к базе данных: {e}")
            print(f"📊 DATABASE_URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
            return False

if __name__ == "__main__":
    print("🔍 Тестирование подключения к базе данных...")
    success = test_connection()
    if not success:
        sys.exit(1)
