#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой скрипт для инициализации PostgreSQL базы данных
"""

import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def init_postgresql():
    """Простая инициализация PostgreSQL базы данных"""
    try:
        from app import app, db
        from models import User, Employee
        from werkzeug.security import generate_password_hash
        from sqlalchemy import text
        
        with app.app_context():
            print("🔧 Инициализируем PostgreSQL базу данных...")
            
            # Создаем все таблицы
            print("📋 Создаем таблицы...")
            db.create_all()
            print("✅ Таблицы созданы!")
            
            # Увеличиваем размер поля password если нужно
            try:
                print("🔧 Проверяем размер поля password...")
                db.session.execute(text("ALTER TABLE \"user\" ALTER COLUMN password TYPE VARCHAR(255);"))
                db.session.commit()
                print("✅ Размер поля password обновлен!")
            except Exception as e:
                print(f"ℹ️ Поле password уже имеет правильный размер: {str(e)[:100]}...")
            
            # Создаем пользователей
            print("👥 Создаем пользователей...")
            
            if User.query.count() == 0:
                users_data = [
                    ('admin', 'admin123', 'Админ'),
                    ('manager', '5678', 'Менеджер'),
                    ('worker', '0000', 'Производство'),
                    ('cutter', '7777', 'Фрезеровка'),
                    ('polisher', '8888', 'Шлифовка'),
                    ('monitor', '9999', 'Монитор')
                ]
                
                for username, password, role in users_data:
                    user = User(
                        username=username,
                        password=generate_password_hash(password),
                        role=role
                    )
                    db.session.add(user)
                
                db.session.commit()
                print("✅ Пользователи созданы успешно!")
            else:
                print("ℹ️ Пользователи уже существуют, пропускаем создание.")
            
            # Создаем тестового сотрудника
            if Employee.query.count() == 0:
                print("👷 Создаем тестового сотрудника...")
                employee = Employee(
                    name='Тестовый сотрудник',
                    position='Оператор',
                    hourly_rate=500.0,
                    is_active=True
                )
                db.session.add(employee)
                db.session.commit()
                print("✅ Тестовый сотрудник создан!")
            
            # Проверяем результат
            user_count = User.query.count()
            employee_count = Employee.query.count()
            
            print("🎉 PostgreSQL база данных инициализирована успешно!")
            print(f"👥 Пользователей: {user_count}")
            print(f"👷 Сотрудников: {employee_count}")
            print("\n📋 Тестовые аккаунты:")
            print("- Администратор: admin / admin123")
            print("- Менеджер: manager / 5678")
            print("- Производство: worker / 0000")
            print("- Фрезеровка: cutter / 7777")
            print("- Шлифовка: polisher / 8888")
            print("- Монитор: monitor / 9999")
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка инициализации: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 ИНИЦИАЛИЗАЦИЯ POSTGRESQL")
    print("=" * 50)
    print("💡 Данные будут сохраняться навсегда!")
    print("=" * 50)
    
    success = init_postgresql()
    
    if success:
        print("\n✅ ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("Теперь можно запустить приложение:")
        print("python app.py")
    else:
        print("\n❌ ОШИБКА ИНИЦИАЛИЗАЦИИ!")
        sys.exit(1)
