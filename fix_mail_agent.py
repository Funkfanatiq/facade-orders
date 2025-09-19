#!/usr/bin/env python3
"""
Комплексный скрипт для исправления почтового агента
"""

import os
import sys

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Email

def fix_mail_agent():
    """Исправляет все проблемы с почтовым агентом"""
    with app.app_context():
        try:
            print("🔧 Исправление почтового агента...")
            print("=" * 50)
            
            # 1. Очищаем все письма
            print("1️⃣ Очистка всех писем...")
            Email.query.delete()
            db.session.commit()
            print("✅ Все письма удалены")
            
            # 2. Обновляем структуру таблицы
            print("\n2️⃣ Обновление структуры таблицы...")
            try:
                # Удаляем старый уникальный индекс если он существует
                db.engine.execute("DROP INDEX IF EXISTS email_message_id_key")
                print("✅ Удален старый уникальный индекс")
            except Exception as e:
                print(f"ℹ️ Старый индекс не найден: {e}")
            
            try:
                # Создаем новый обычный индекс
                db.engine.execute("CREATE INDEX IF NOT EXISTS idx_email_message_id ON email (message_id)")
                print("✅ Создан новый индекс")
            except Exception as e:
                print(f"ℹ️ Индекс уже существует: {e}")
            
            print("\n✅ Почтовый агент исправлен!")
            print("📧 Теперь можно заново получать письма")
            print("🔄 Автоматическое обновление будет работать корректно")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            db.session.rollback()

if __name__ == "__main__":
    fix_mail_agent()
