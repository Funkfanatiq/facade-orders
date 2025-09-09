#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для настройки приложения на Render.com
Автоматически создает базу данных и начальных пользователей
"""

import os
import sys
from werkzeug.security import generate_password_hash

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_render_app():
    """Настройка приложения для Render.com"""
    try:
        # Импортируем после настройки пути
        from app import app, db
        from models import User, Order, Employee, WorkHours, SalaryPeriod
        
        with app.app_context():
            print("🚀 Настройка приложения для Render.com")
            print("=" * 50)
            
            # Проверяем тип базы данных
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if 'postgresql' in db_url:
                print("✅ Используется PostgreSQL база данных")
            elif 'sqlite' in db_url:
                print("⚠️  Используется SQLite (данные могут теряться при перезагрузке)")
            else:
                print("❓ Неизвестный тип базы данных")
            
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
                print("ℹ️  Пользователи уже существуют, пропускаем создание.")
            
            # Создаем тестовый заказ
            if Order.query.count() == 0:
                print("📦 Создаем тестовый заказ...")
                from datetime import datetime, timedelta
                
                test_order = Order(
                    order_id='TEST-001',
                    client='Тестовый клиент',
                    days=7,
                    due_date=datetime.utcnow().date() + timedelta(days=7),
                    milling=False,
                    packaging=False,
                    shipment=False,
                    paid=False,
                    filenames='',
                    filepaths='',
                    facade_type='фрезерованный',
                    area=2.5
                )
                db.session.add(test_order)
                db.session.commit()
                print("✅ Тестовый заказ создан!")
            
            print("\n🎉 Настройка завершена успешно!")
            print("\n📋 Тестовые аккаунты:")
            print("- Администратор: admin / admin123")
            print("- Менеджер: manager / 5678")
            print("- Производство: worker / 0000")
            print("- Фрезеровка: cutter / 7777")
            print("- Шлифовка: polisher / 8888")
            print("- Монитор: monitor / 9999")
            
            print("\n🔗 Доступ к приложению:")
            render_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://your-app.onrender.com')
            print(f"- URL: {render_url}")
            
            print("\n💡 Рекомендации:")
            if 'sqlite' in db_url:
                print("- ⚠️  Рекомендуется настроить PostgreSQL для сохранения данных")
                print("- 📖 См. RENDER_FREE_TIER_FIX.md для инструкций")
            else:
                print("- ✅ PostgreSQL настроен, данные будут сохраняться")
            
    except Exception as e:
        print(f"❌ Ошибка настройки: {str(e)}")
        print(f"Тип ошибки: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 НАСТРОЙКА ПРИЛОЖЕНИЯ ДЛЯ RENDER.COM")
    print("=" * 50)
    
    success = setup_render_app()
    
    if success:
        print("\n✅ НАСТРОЙКА ЗАВЕРШЕНА УСПЕШНО!")
        print("Приложение готово к работе на Render.com")
    else:
        print("\n❌ НАСТРОЙКА ЗАВЕРШЕНА С ОШИБКАМИ!")
        sys.exit(1)

