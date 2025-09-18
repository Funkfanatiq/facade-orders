from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify, send_from_directory 
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv

# Константы приложения
URGENT_DAYS_THRESHOLD = 3  # Дней до срока для срочных заказов
SHEET_AREA = 2.75 * 2.05  # Площадь листа в м² (5.6375)
MAX_FILE_SIZE = 16 * 1024 * 1024  # Максимальный размер файла (16MB)
EXPIRED_DAYS = 180  # Дней для удаления старых заказов

# Разрешенные типы файлов для загрузки
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'txt', 'doc', 'docx', 'xls', 'xlsx', 'dwg', 'dxf'}

# Загружаем переменные окружения из .env файла
load_dotenv()

app = Flask(__name__)
app.config.from_object('config.Config')

# Импортируем модели после инициализации Flask
from models import db, User, Order, Employee, WorkHours, SalaryPeriod
db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Инициализация базы данных при запуске
def init_database():
    """Инициализация базы данных"""
    with app.app_context():
        try:
            print("🚀 Инициализация базы данных...")
            
            # Создаем все таблицы
            db.create_all()
            print("✅ Таблицы созданы")
            
            # Проверяем количество пользователей
            user_count = User.query.count()
            print(f"👥 Пользователей в базе: {user_count}")
            
            if user_count == 0:
                print("👤 Создание пользователей...")
                
                # Создаем менеджера
                manager = User(
                    username='manager',
                    password=User.hash_password('5678'),
                    role='Менеджер'
                )
                db.session.add(manager)
                
                # Создаем админа
                admin = User(
                    username='admin',
                    password=User.hash_password('admin123'),
                    role='Админ'
                )
                db.session.add(admin)
                
                # Создаем других пользователей
                users_data = [
                    ('worker', '0000', 'Производство'),
                    ('cutter', '7777', 'Фрезеровка'),
                    ('polisher', '8888', 'Шлифовка'),
                    ('monitor', '9999', 'Монитор')
                ]
                
                for username, password, role in users_data:
                    user = User(
                        username=username,
                        password=User.hash_password(password),
                        role=role
                    )
                    db.session.add(user)
                
                db.session.commit()
                print("✅ Пользователи созданы")
            else:
                print("✅ Пользователи уже существуют")
            
            print("🎉 Инициализация завершена!")
            
        except Exception as e:
            print(f"❌ Ошибка инициализации: {e}")
            import traceback
            traceback.print_exc()

# Запускаем инициализацию
init_database()

def allowed_file(filename):
    """Проверяет, разрешен ли тип файла для загрузки"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def secure_filename_custom(filename):
    """Безопасное имя файла с проверкой"""
    import re
    # Удаляем опасные символы
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    # Ограничиваем длину
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:95] + ext
    return filename

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Остальной код приложения...
# (здесь должен быть весь остальной код из app.py)
