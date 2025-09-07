#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для инициализации базы данных на Render.com
Исправленная версия для устранения ошибок SQLAlchemy
"""

import os
import sys
from werkzeug.security import generate_password_hash

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def init_database():
    """Инициализация базы данных с начальными данными"""
    try:
        # Импортируем после настройки пути
        from app import app, db
        from models import User, Order, Employee, WorkHours, SalaryPeriod
        
        with app.app_context():
            print("🔧 Создаем таблицы базы данных...")
            # Создаем все таблицы
            db.create_all()
            print("✅ Таблицы созданы успешно!")
            
            # Проверяем, есть ли уже пользователи
            if User.query.count() == 0:
                print("👥 Создаем начальных пользователей...")
                
                # Создаем пользователей
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
            else:
                print("ℹ️ Пользователи уже существуют, пропускаем создание.")
            
            print("🎉 База данных инициализирована успешно!")
            print("\n📋 Тестовые аккаунты:")
            print("- Администратор: admin / admin123")
            print("- Менеджер: manager / 5678")
            print("- Производство: worker / 0000")
            print("- Фрезеровка: cutter / 7777")
            print("- Шлифовка: polisher / 8888")
            print("- Монитор: monitor / 9999")
            
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {str(e)}")
        print(f"Тип ошибки: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ НА RENDER")
    print("=" * 50)
    
    success = init_database()
    
    if success:
        print("\n✅ ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
    else:
        print("\n❌ ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА С ОШИБКАМИ!")
        sys.exit(1)
