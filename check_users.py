#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки всех пользователей в базе данных
"""

from app import app, db
from models import User
from werkzeug.security import check_password_hash

def check_all_users():
    """Проверяем всех пользователей в базе данных"""
    with app.app_context():
        users = User.query.all()
        
        print("👥 ВСЕ ПОЛЬЗОВАТЕЛИ В БАЗЕ ДАННЫХ:")
        print("=" * 50)
        
        for user in users:
            print(f"ID: {user.id}")
            print(f"Логин: {user.username}")
            print(f"Роль: {user.role}")
            print(f"Пароль (хеш): {user.password[:20]}...")
            print("-" * 30)
        
        print(f"\nВсего пользователей: {len(users)}")
        
        # Проверяем возможные пароли
        print("\n🔍 ПРОВЕРКА ВОЗМОЖНЫХ ПАРОЛЕЙ:")
        print("=" * 50)
        
        possible_passwords = [
            "admin123", "1234",
            "manager123", "5678", 
            "prod123", "0000",
            "frez123", "7777",
            "shlif123", "8888",
            "monitor123", "9999"
        ]
        
        for user in users:
            print(f"\nПользователь: {user.username} ({user.role})")
            for password in possible_passwords:
                if check_password_hash(user.password, password):
                    print(f"  ✅ Пароль найден: {password}")
                    break
            else:
                print(f"  ❌ Пароль не найден среди известных")

if __name__ == "__main__":
    check_all_users()

