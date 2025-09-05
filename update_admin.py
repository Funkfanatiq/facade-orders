#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def update_admin_password():
    with app.app_context():
        # Находим администратора
        admin = User.query.filter_by(username="admin").first()
        if admin:
            # Обновляем пароль
            admin.password = generate_password_hash("admin123")
            db.session.commit()
            print("✅ Пароль администратора обновлен!")
            print("Логин: admin")
            print("Пароль: admin123")
        else:
            print("❌ Администратор не найден!")

if __name__ == "__main__":
    update_admin_password()








