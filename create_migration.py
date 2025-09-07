#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания миграций базы данных
"""

import os
import sys

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_migration():
    """Создание миграции базы данных"""
    try:
        from app import app, db, migrate
        from models import User, Order, Employee, WorkHours, SalaryPeriod
        
        with app.app_context():
            print("🔧 Создаем миграцию...")
            
            # Создаем миграцию
            from flask_migrate import init, migrate, upgrade
            
            # Инициализируем миграции (если еще не инициализированы)
            try:
                init()
                print("✅ Миграции инициализированы")
            except:
                print("ℹ️ Миграции уже инициализированы")
            
            # Создаем новую миграцию
            migrate(message="Initial migration for Render deployment")
            print("✅ Миграция создана")
            
            # Применяем миграцию
            upgrade()
            print("✅ Миграция применена")
            
    except Exception as e:
        print(f"❌ Ошибка создания миграции: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 СОЗДАНИЕ МИГРАЦИИ БАЗЫ ДАННЫХ")
    print("=" * 40)
    
    success = create_migration()
    
    if success:
        print("\n✅ МИГРАЦИЯ СОЗДАНА УСПЕШНО!")
    else:
        print("\n❌ ОШИБКА ПРИ СОЗДАНИИ МИГРАЦИИ!")
        sys.exit(1)

