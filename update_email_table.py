#!/usr/bin/env python3
"""
Скрипт для обновления таблицы email в базе данных
"""

import os
import sys

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def update_email_table():
    """Обновляет таблицу email в базе данных"""
    with app.app_context():
        try:
            print("🔧 Обновление таблицы email...")
            
            # Удаляем старый уникальный индекс если он существует
            try:
                db.engine.execute("DROP INDEX IF EXISTS email_message_id_key")
                print("✅ Удален старый уникальный индекс")
            except Exception as e:
                print(f"ℹ️ Старый индекс не найден: {e}")
            
            # Создаем новый обычный индекс
            try:
                db.engine.execute("CREATE INDEX IF NOT EXISTS idx_email_message_id ON email (message_id)")
                print("✅ Создан новый индекс")
            except Exception as e:
                print(f"ℹ️ Индекс уже существует: {e}")
            
            print("✅ Таблица email обновлена")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    update_email_table()
