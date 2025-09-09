#!/usr/bin/env python3
"""
Улучшенная инициализация базы данных для Render.com с диагностикой
"""

import os
import sys
from datetime import datetime

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_and_init_render_db():
    print("🚀 ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ НА RENDER")
    print("=" * 60)
    
    # Диагностика окружения
    print("🔍 Диагностика окружения:")
    print(f"  Python версия: {sys.version}")
    print(f"  Рабочая директория: {os.getcwd()}")
    print(f"  DATABASE_URL установлена: {'Да' if os.environ.get('DATABASE_URL') else 'Нет'}")
    
    if os.environ.get('DATABASE_URL'):
        db_url = os.environ.get('DATABASE_URL')
        print(f"  DATABASE_URL: {db_url[:30]}...{db_url[-10:]}")
        
        # Проверяем формат URL
        if db_url.startswith('postgres://'):
            print("  ⚠️  Обнаружен старый формат postgres://")
            print("  🔧 Исправляем на postgresql://")
            os.environ['DATABASE_URL'] = db_url.replace('postgres://', 'postgresql://', 1)
        elif db_url.startswith('postgresql://'):
            print("  ✅ Формат postgresql:// корректен")
        else:
            print(f"  ❌ Неизвестный формат URL")
    
    try:
        # Импортируем модули приложения
        print("\n📦 Загрузка модулей приложения...")
        from app import app, db
        from models import User, Employee, WorkHours
        from werkzeug.security import generate_password_hash
        from sqlalchemy import text
        
        print("  ✅ Модули загружены успешно")
        
        # Тестируем подключение
        print("\n🔌 Тест подключения к базе данных...")
        with app.app_context():
            # Проверяем подключение
            result = db.session.execute(text("SELECT 1")).scalar()
            print(f"  ✅ Подключение успешно: {result}")
            
            # Проверяем существование таблиц
            print("\n📋 Проверка таблиц...")
            tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = db.session.execute(tables_query).fetchall()
            existing_tables = [table[0] for table in tables]
            print(f"  Существующие таблицы: {existing_tables}")
            
            # Создаем таблицы если их нет
            if not existing_tables:
                print("  📝 Создаем таблицы...")
                db.create_all()
                print("  ✅ Таблицы созданы")
            else:
                print("  ✅ Таблицы уже существуют")
            
            # Проверяем и обновляем схему
            print("\n🔧 Проверка схемы...")
            try:
                # Проверяем размер поля password
                password_length_query = text("""
                    SELECT character_maximum_length 
                    FROM information_schema.columns 
                    WHERE table_name = 'user' AND column_name = 'password'
                """)
                password_length = db.session.execute(password_length_query).scalar()
                
                if password_length and password_length < 255:
                    print(f"  ⚠️  Размер поля password: {password_length}, обновляем до 255...")
                    db.session.execute(text("ALTER TABLE \"user\" ALTER COLUMN password TYPE VARCHAR(255);"))
                    db.session.commit()
                    print("  ✅ Поле password обновлено")
                else:
                    print("  ✅ Поле password имеет достаточный размер")
            except Exception as e:
                print(f"  ⚠️  Ошибка проверки схемы: {e}")
            
            # Создаем пользователей
            print("\n👥 Создание пользователей...")
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
                print(f"  ✅ Создано {len(users_data)} пользователей")
            else:
                print(f"  ℹ️  Пользователи уже существуют: {User.query.count()}")
            
            # Создаем тестового сотрудника
            print("\n👷 Создание сотрудников...")
            if Employee.query.count() == 0:
                employee = Employee(
                    name='Тестовый сотрудник',
                    position='Оператор',
                    hourly_rate=500.0,
                    is_active=True
                )
                db.session.add(employee)
                db.session.commit()
                print("  ✅ Тестовый сотрудник создан")
            else:
                print(f"  ℹ️  Сотрудники уже существуют: {Employee.query.count()}")
            
            print("\n🎉 ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
            print(f"👥 Пользователей: {User.query.count()}")
            print(f"👷 Сотрудников: {Employee.query.count()}")
            
            print("\n📋 Тестовые аккаунты:")
            print("- Администратор: admin / admin123")
            print("- Менеджер: manager / 5678")
            print("- Производство: worker / 0000")
            print("- Фрезеровка: cutter / 7777")
            print("- Шлифовка: polisher / 8888")
            print("- Монитор: monitor / 9999")
            
            return True
            
    except Exception as e:
        print(f"\n❌ ОШИБКА ИНИЦИАЛИЗАЦИИ: {str(e)}")
        print(f"Тип ошибки: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_and_init_render_db()
    if not success:
        sys.exit(1)
