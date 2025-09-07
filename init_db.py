#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для инициализации базы данных на Render.com
"""

from app import app, db
from models import User, Order, Employee, WorkHours, SalaryPeriod

def init_database():
    """Инициализация базы данных с начальными данными"""
    with app.app_context():
        # Создаем все таблицы
        db.create_all()
        
        # Проверяем, есть ли уже пользователи
        if User.query.count() == 0:
            print("Создаем начальных пользователей...")
            
            # Создаем администратора
            admin = User(
                username='admin',
                password=User.hash_password('admin123'),
                role='Админ'
            )
            db.session.add(admin)
            
            # Создаем менеджера
            manager = User(
                username='manager',
                password=User.hash_password('5678'),
                role='Менеджер'
            )
            db.session.add(manager)
            
            # Создаем пользователей для производства
            production_users = [
                ('worker', '0000', 'Производство'),
                ('cutter', '7777', 'Фрезеровка'),
                ('polisher', '8888', 'Шлифовка'),
                ('monitor', '9999', 'Монитор')
            ]
            
            for username, password, role in production_users:
                user = User(
                    username=username,
                    password=User.hash_password(password),
                    role=role
                )
                db.session.add(user)
            
            db.session.commit()
            print("✅ Пользователи созданы успешно!")
            
            # Создаем тестового сотрудника
            if Employee.query.count() == 0:
                print("Создаем тестового сотрудника...")
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
            print("Пользователи уже существуют, пропускаем создание.")
        
        print("✅ База данных инициализирована успешно!")

if __name__ == "__main__":
    init_database()

