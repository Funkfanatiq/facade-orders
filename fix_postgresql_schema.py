#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для исправления схемы PostgreSQL базы данных
Увеличивает размер поля password для поддержки scrypt хешей
"""

import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_postgresql_schema():
    """Исправляет схему PostgreSQL базы данных"""
    try:
        from app import app, db
        
        with app.app_context():
            print("🔧 Исправляем схему PostgreSQL базы данных...")
            
            # Проверяем, есть ли таблица user
            result = db.session.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user'
                );
            """)
            table_exists = result.fetchone()[0]
            
            if not table_exists:
                print("📋 Таблица user не существует, создаем все таблицы...")
                db.create_all()
                print("✅ Таблицы созданы!")
            else:
                print("📋 Таблица user существует, обновляем схему...")
                
                # Проверяем текущий размер поля password
                result = db.session.execute("""
                    SELECT character_maximum_length 
                    FROM information_schema.columns 
                    WHERE table_name = 'user' AND column_name = 'password';
                """)
                current_length = result.fetchone()
                
                if current_length and current_length[0] < 255:
                    print(f"🔧 Текущий размер поля password: {current_length[0]} символов")
                    print("🔧 Увеличиваем размер поля password до 255 символов...")
                    
                    # Увеличиваем размер поля password
                    db.session.execute("""
                        ALTER TABLE "user" 
                        ALTER COLUMN password TYPE VARCHAR(255);
                    """)
                    db.session.commit()
                    print("✅ Размер поля password увеличен до 255 символов!")
                else:
                    print("✅ Поле password уже имеет правильный размер")
            
            # Теперь создаем пользователей
            print("👥 Создаем пользователей...")
            
            from models import User
            from werkzeug.security import generate_password_hash
            
            # Проверяем, есть ли уже пользователи
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
            from models import Employee
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
            
            print("🎉 Схема PostgreSQL исправлена успешно!")
            print("\n📋 Тестовые аккаунты:")
            print("- Администратор: admin / admin123")
            print("- Менеджер: manager / 5678")
            print("- Производство: worker / 0000")
            print("- Фрезеровка: cutter / 7777")
            print("- Шлифовка: polisher / 8888")
            print("- Монитор: monitor / 9999")
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка исправления схемы: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 ИСПРАВЛЕНИЕ СХЕМЫ POSTGRESQL")
    print("=" * 50)
    print("💡 Увеличиваем размер поля password для scrypt хешей")
    print("=" * 50)
    
    success = fix_postgresql_schema()
    
    if success:
        print("\n✅ СХЕМА ИСПРАВЛЕНА УСПЕШНО!")
        print("Теперь можно запустить приложение:")
        print("python app.py")
    else:
        print("\n❌ ОШИБКА ИСПРАВЛЕНИЯ СХЕМЫ!")
        sys.exit(1)
