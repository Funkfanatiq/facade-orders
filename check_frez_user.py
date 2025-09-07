#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки пароля пользователя frez_user
"""

from app import app, db
from models import User
from werkzeug.security import check_password_hash

def check_frez_user():
    """Проверяем пароль для frez_user"""
    with app.app_context():
        frez_user = User.query.filter_by(username="frez_user").first()
        
        if not frez_user:
            print("❌ Пользователь frez_user не найден!")
            return
        
        print(f"👤 Пользователь: {frez_user.username}")
        print(f"Роль: {frez_user.role}")
        print(f"Пароль (хеш): {frez_user.password[:20]}...")
        
        # Проверяем дополнительные пароли
        additional_passwords = [
            "frez123", "frez_user123", "frez_user", "frez",
            "1234", "password", "123456", "qwerty",
            "frez1234", "user123", "frez_user1234"
        ]
        
        print("\n🔍 ПРОВЕРКА ДОПОЛНИТЕЛЬНЫХ ПАРОЛЕЙ:")
        print("=" * 40)
        
        for password in additional_passwords:
            if check_password_hash(frez_user.password, password):
                print(f"✅ Пароль найден: {password}")
                return password
        
        print("❌ Пароль не найден среди проверенных")
        return None

if __name__ == "__main__":
    check_frez_user()
