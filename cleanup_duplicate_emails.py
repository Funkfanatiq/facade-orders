#!/usr/bin/env python3
"""
Скрипт для очистки дублированных писем в базе данных
"""

import os
import sys
from datetime import datetime

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Email

def cleanup_duplicate_emails():
    """Удаляет дублированные письма из базы данных"""
    with app.app_context():
        try:
            print("🔍 Поиск дублированных писем...")
            
            # Находим дублированные письма по message_id
            duplicates = db.session.query(Email.message_id).group_by(Email.message_id).having(db.func.count(Email.id) > 1).all()
            
            if not duplicates:
                print("✅ Дублированных писем не найдено")
                return
            
            print(f"📧 Найдено {len(duplicates)} дублированных message_id")
            
            total_deleted = 0
            
            for (message_id,) in duplicates:
                # Получаем все письма с этим message_id
                emails = Email.query.filter_by(message_id=message_id).order_by(Email.created_at.asc()).all()
                
                # Оставляем только первое письмо, остальные удаляем
                for email in emails[1:]:
                    print(f"🗑️ Удаляем дублированное письмо: {email.subject[:50]}...")
                    db.session.delete(email)
                    total_deleted += 1
            
            # Коммитим изменения
            db.session.commit()
            print(f"✅ Удалено {total_deleted} дублированных писем")
            
        except Exception as e:
            print(f"❌ Ошибка при очистке: {e}")
            db.session.rollback()

def show_email_stats():
    """Показывает статистику писем"""
    with app.app_context():
        try:
            total_emails = Email.query.count()
            inbox_emails = Email.query.filter_by(is_sent=False).count()
            sent_emails = Email.query.filter_by(is_sent=True).count()
            unread_emails = Email.query.filter_by(is_sent=False, is_read=False).count()
            
            print("📊 Статистика писем:")
            print(f"   Всего писем: {total_emails}")
            print(f"   Входящих: {inbox_emails}")
            print(f"   Отправленных: {sent_emails}")
            print(f"   Непрочитанных: {unread_emails}")
            
        except Exception as e:
            print(f"❌ Ошибка при получении статистики: {e}")

if __name__ == "__main__":
    print("🧹 Очистка дублированных писем")
    print("=" * 50)
    
    show_email_stats()
    print()
    
    cleanup_duplicate_emails()
    print()
    
    show_email_stats()
    print()
    print("✅ Очистка завершена!")
