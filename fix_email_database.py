#!/usr/bin/env python3
"""
Простой скрипт для исправления проблем с базой данных писем
"""

import os
import sys

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Email

def fix_database():
    """Исправляет проблемы с базой данных"""
    with app.app_context():
        try:
            print("🔧 Исправление базы данных писем...")
            
            # Удаляем все письма (начинаем с чистого листа)
            Email.query.delete()
            db.session.commit()
            
            print("✅ База данных писем очищена")
            print("📧 Теперь можно заново получать письма")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            db.session.rollback()

if __name__ == "__main__":
    fix_database()
