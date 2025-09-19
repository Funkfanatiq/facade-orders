from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify, send_from_directory 
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import datetime, timedelta, timezone
import os
import imaplib
import email
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

# Константы приложения
URGENT_DAYS_THRESHOLD = 3  # Дней до срока для срочных заказов
SHEET_AREA = 2.75 * 2.05  # Площадь листа в м² (5.6375)
MAX_FILE_SIZE = 16 * 1024 * 1024  # Максимальный размер файла (16MB)
EXPIRED_DAYS = 180  # Дней для удаления старых заказов

# Константы для управления хранилищем
STORAGE_LIMIT_MB = 980  # Лимит хранилища в МБ
ORDER_SIZE_MB = 10  # Средний размер заказа в МБ
CLEANUP_BATCH_SIZE = 10  # Количество заказов для удаления за раз

# Разрешенные типы файлов для загрузки
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'txt', 'doc', 'docx', 'xls', 'xlsx', 'dwg', 'dxf'}

# Загружаем переменные окружения из .env файла
load_dotenv()

app = Flask(__name__)
app.config.from_object('config.Config')

# Инициализация почты
mail = Mail(app)

# Импортируем модели после инициализации Flask
from models import db, User, Order, Employee, WorkHours, SalaryPeriod, Email, EmailAttachment
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

def get_storage_usage_mb():
    """Получает текущее использование хранилища в МБ"""
    try:
        upload_folder = app.config["UPLOAD_FOLDER"]
        total_size = 0
        
        for dirpath, dirnames, filenames in os.walk(upload_folder):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        
        return total_size / (1024 * 1024)  # Конвертируем в МБ
    except Exception as e:
        print(f"Ошибка при подсчете размера хранилища: {e}")
        return 0

def cleanup_old_orders():
    """Очищает старые заказы со статусом 'отправлено' при достижении лимита хранилища"""
    try:
        current_usage = get_storage_usage_mb()
        print(f"📊 Текущее использование хранилища: {current_usage:.2f} МБ")
        
        if current_usage >= STORAGE_LIMIT_MB:
            print(f"⚠️ Достигнут лимит хранилища ({STORAGE_LIMIT_MB} МБ). Начинаем очистку...")
            
            # Находим заказы со статусом "отправлено" (shipment = True)
            old_orders = Order.query.filter_by(shipment=True).order_by(Order.due_date.asc()).limit(CLEANUP_BATCH_SIZE).all()
            
            if old_orders:
                deleted_count = 0
                for order in old_orders:
                    # Удаляем файлы заказа
                    if order.filepaths:
                        file_paths = order.filepaths.split(';')
                        for file_path in file_paths:
                            if file_path.strip():
                                full_path = os.path.join(app.config["UPLOAD_FOLDER"], file_path.strip())
                                if os.path.exists(full_path):
                                    try:
                                        os.remove(full_path)
                                        print(f"🗑️ Удален файл: {file_path}")
                                    except Exception as e:
                                        print(f"Ошибка при удалении файла {file_path}: {e}")
                    
                    # Удаляем запись заказа из базы данных
                    db.session.delete(order)
                    deleted_count += 1
                
                db.session.commit()
                
                new_usage = get_storage_usage_mb()
                freed_space = current_usage - new_usage
                
                print(f"✅ Очистка завершена!")
                print(f"🗑️ Удалено заказов: {deleted_count}")
                print(f"💾 Освобождено места: {freed_space:.2f} МБ")
                print(f"📊 Новое использование: {new_usage:.2f} МБ")
                
                return deleted_count
            else:
                print("ℹ️ Нет заказов со статусом 'отправлено' для удаления")
                return 0
        else:
            print(f"✅ Хранилище в норме: {current_usage:.2f} МБ / {STORAGE_LIMIT_MB} МБ")
            return 0
            
    except Exception as e:
        print(f"❌ Ошибка при очистке хранилища: {e}")
        import traceback
        traceback.print_exc()
        return 0

@app.template_filter("zip")
def zip_filter(a, b):
    return zip(a, b)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_request
def clear_session_if_not_logged_in():
    if not current_user.is_authenticated:
        session.clear()

def is_urgent_order(order):
    """
    Определяет является ли заказ срочным.
    Срочные заказы: осталось URGENT_DAYS_THRESHOLD дней или меньше до срока сдачи.
    """
    days_left = (order.due_date - datetime.now(timezone.utc).date()).days
    return days_left <= URGENT_DAYS_THRESHOLD

def generate_daily_pool():
    """
    Формирует оптимизированный пул заказов для фрезеровки:
    1. Приоритет срочным заказам (игнорируют оптимизацию)
    2. Оптимизация остатков листов МДФ
    3. Группировка по типу фасада
    4. Лист МДФ: 2750×2050 = 5.6375 м²
    """
    # Константы для МДФ листа 2750×2050 мм
    SHEET_AREA = 2.75 * 2.05  # 5.6375 м²
    MAX_SHEET_COUNT = 4
    LARGE_ORDER_THRESHOLD = SHEET_AREA * MAX_SHEET_COUNT  # 22.55 м²
    OPTIMAL_UTILIZATION = 0.85  # 85% использования листа считается хорошим
    ACCEPTABLE_WASTE = 0.3  # Допустимые остатки в м²

    # Получаем все незафрезерованные заказы
    candidates = Order.query.filter(
        Order.milling == False,
        Order.shipment == False,
        Order.area != None,
        Order.area > 0
    ).order_by(Order.due_date.asc()).all()

    if not candidates:
        return []

    # Проверяем срочные заказы
    urgent_orders = [o for o in candidates if is_urgent_order(o)]
    
    # Если есть срочные заказы - берём первый срочный, игнорируя оптимизацию
    if urgent_orders:
        urgent_order = urgent_orders[0]
        # Если срочный заказ очень большой - отдельный пул
        if urgent_order.area >= LARGE_ORDER_THRESHOLD:
            return [urgent_order]
        
        # Для срочного заказа просто добавляем заказы того же типа до 4 листов
        same_type_urgent = [o for o in urgent_orders if o.facade_type == urgent_order.facade_type]
        pool = []
        total_area = 0
        
        for order in same_type_urgent:
            if total_area + order.area <= LARGE_ORDER_THRESHOLD:
                pool.append(order)
                total_area += order.area
            else:
                break
        
        return pool

    # Обычная оптимизация для несрочных заказов
    first_order = candidates[0]
    target_facade_type = first_order.facade_type

    # Если первый заказ очень большой (>4 листов) - делаем отдельный пул
    if first_order.area >= LARGE_ORDER_THRESHOLD:
        return [first_order]

    # Получаем заказы того же типа
    same_type_orders = [o for o in candidates if o.facade_type == target_facade_type]
    
    # Алгоритм оптимизации: ищем лучшую комбинацию заказов
    best_combination = find_optimal_combination(same_type_orders, SHEET_AREA, MAX_SHEET_COUNT)
    
    return best_combination if best_combination else [first_order]

def find_optimal_combination(orders, sheet_area, max_sheets):
    """
    Ищет оптимальную комбинацию заказов для минимизации остатков.
    Использует жадный алгоритм с проверкой различных стратегий.
    """
    max_total_area = sheet_area * max_sheets
    best_combination = []
    best_efficiency = 0
    
    # Стратегия 1: Начинаем с самого большого заказа
    combination1 = pack_orders_greedy(orders, max_total_area, sort_by='area_desc')
    efficiency1 = calculate_efficiency(combination1, sheet_area)
    
    if efficiency1 > best_efficiency:
        best_combination = combination1
        best_efficiency = efficiency1
    
    # Стратегия 2: Начинаем с самых срочных
    combination2 = pack_orders_greedy(orders, max_total_area, sort_by='due_date')
    efficiency2 = calculate_efficiency(combination2, sheet_area)
    
    if efficiency2 > best_efficiency:
        best_combination = combination2
        best_efficiency = efficiency2
    
    # Стратегия 3: Комбинированная - ищем заказы, которые хорошо дополняют друг друга
    combination3 = pack_orders_complementary(orders, max_total_area, sheet_area)
    efficiency3 = calculate_efficiency(combination3, sheet_area)
    
    if efficiency3 > best_efficiency:
        best_combination = combination3
        best_efficiency = efficiency3
    
    return best_combination

def pack_orders_greedy(orders, max_area, sort_by='area_desc'):
    """Жадная упаковка заказов"""
    if sort_by == 'area_desc':
        sorted_orders = sorted(orders, key=lambda x: x.area, reverse=True)
    elif sort_by == 'due_date':
        sorted_orders = sorted(orders, key=lambda x: x.due_date)
    else:
        sorted_orders = orders[:]
    
    combination = []
    total_area = 0
    
    for order in sorted_orders:
        if total_area + order.area <= max_area:
            combination.append(order)
            total_area += order.area
    
    return combination

def pack_orders_complementary(orders, max_area, sheet_area):
    """
    Ищет заказы, которые хорошо комбинируются для минимизации остатков
    """
    if not orders:
        return []
    
    # Начинаем с первого заказа (самый приоритетный)
    combination = [orders[0]]
    total_area = orders[0].area
    remaining_orders = orders[1:]
    
    # Пытаемся найти заказы, которые хорошо дополняют текущую комбинацию
    while remaining_orders and total_area < max_area:
        best_fit = None
        best_waste = float('inf')
        
        for order in remaining_orders:
            if total_area + order.area <= max_area:
                # Рассчитываем остатки после добавления этого заказа
                new_total = total_area + order.area
                sheets_needed = (new_total / sheet_area)
                full_sheets = int(sheets_needed)
                
                if sheets_needed == full_sheets:
                    waste = 0  # Идеальное попадание
                else:
                    waste = sheet_area - (new_total - full_sheets * sheet_area)
                
                # Предпочитаем заказы с минимальными остатками
                if waste < best_waste:
                    best_waste = waste
                    best_fit = order
        
        if best_fit:
            combination.append(best_fit)
            total_area += best_fit.area
            remaining_orders.remove(best_fit)
        else:
            break
    
    return combination

def calculate_efficiency(combination, sheet_area):
    """
    Рассчитывает эффективность использования материала
    """
    if not combination:
        return 0
    
    total_area = sum(order.area for order in combination)
    sheets_needed = total_area / sheet_area
    full_sheets = int(sheets_needed)
    
    if sheets_needed == full_sheets:
        # Идеальное использование
        return 1.0
    else:
        # Рассчитываем процент использования последнего листа
        partial_sheet_usage = (total_area - full_sheets * sheet_area) / sheet_area
        # Общая эффективность
        if full_sheets > 0:
            return (full_sheets + partial_sheet_usage) / (full_sheets + 1)
        else:
            return partial_sheet_usage

def send_email_notification(to_email, subject, template, **kwargs):
    """Отправка email уведомления"""
    try:
        msg = Message(
            subject=subject,
            recipients=[to_email],
            html=render_template(template, **kwargs)
        )
        mail.send(msg)
        print(f"✅ Email отправлен на {to_email}")
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки email: {e}")
        return False

def send_order_notification(order, notification_type):
    """Отправка уведомления о заказе"""
    if not order.client or '@' not in order.client:
        return False
    
    if notification_type == "ready":
        subject = f"Заказ {order.order_id} готов к отправке"
        template = "email/order_ready.html"
    elif notification_type == "shipped":
        subject = f"Заказ {order.order_id} отправлен"
        template = "email/order_shipped.html"
    else:
        return False
    
    return send_email_notification(
        to_email=order.client,
        subject=subject,
        template=template,
        order=order,
        datetime=datetime
    )

def fetch_incoming_emails():
    """Получение входящих писем через IMAP"""
    try:
        # Подключение к IMAP серверу Mail.ru
        mail_server = imaplib.IMAP4_SSL('imap.mail.ru', 993)
        mail_server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        mail_server.select('INBOX')
        
        # Поиск непрочитанных писем
        status, messages = mail_server.search(None, 'UNSEEN')
        
        if status != 'OK':
            return []
        
        email_ids = messages[0].split()
        new_emails = []
        
        for email_id in email_ids[-10:]:  # Берем последние 10 писем
            status, msg_data = mail_server.fetch(email_id, '(RFC822)')
            
            if status != 'OK':
                continue
                
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Извлекаем данные письма
            subject = email_message.get('Subject', '')
            sender = email_message.get('From', '')
            recipient = app.config['MAIL_USERNAME']
            date_str = email_message.get('Date', '')
            
            # Получаем тело письма
            body = ""
            html_body = ""
            
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    elif content_type == "text/html" and "attachment" not in content_disposition:
                        html_body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # Проверяем, есть ли уже такое письмо в базе
            existing_email = Email.query.filter_by(
                sender=sender,
                subject=subject,
                recipient=recipient
            ).first()
            
            if not existing_email:
                # Создаем новое письмо в базе данных
                new_email = Email(
                    message_id=email_message.get('Message-ID', ''),
                    subject=subject,
                    sender=sender,
                    recipient=recipient,
                    body=body,
                    html_body=html_body,
                    is_read=False,
                    is_sent=False,
                    created_at=datetime.now()
                )
                
                db.session.add(new_email)
                new_emails.append(new_email)
        
        db.session.commit()
        mail_server.close()
        mail_server.logout()
        
        return new_emails
        
    except Exception as e:
        print(f"❌ Ошибка получения писем: {e}")
        return []

def send_email_with_storage(to_email, subject, body, html_body=None, reply_to_id=None):
    """Отправка письма с сохранением в базе данных"""
    try:
        # Создаем письмо
        msg = Message(
            subject=subject,
            recipients=[to_email],
            body=body,
            html=html_body,
            sender=app.config['MAIL_DEFAULT_SENDER']
        )
        
        # Отправляем письмо
        mail.send(msg)
        
        # Сохраняем в базе данных
        sent_email = Email(
            subject=subject,
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipient=to_email,
            body=body,
            html_body=html_body,
            is_read=True,
            is_sent=True,
            reply_to_id=reply_to_id,
            sent_at=datetime.now()
        )
        
        db.session.add(sent_email)
        db.session.commit()
        
        print(f"✅ Письмо отправлено на {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отправки письма: {e}")
        return False

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            if user.role == "Монитор":
                return redirect(url_for("monitor"))
            elif user.role == "Фрезеровка":
                return redirect(url_for("milling_station"))
            elif user.role == "Шлифовка":
                return redirect(url_for("polishing_station"))
            return redirect(url_for("dashboard"))

        flash("Неверный логин или пароль")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
@login_required
def dashboard():
    if current_user.role == "Монитор":
        return redirect(url_for("monitor"))
    if current_user.role == "Фрезеровка":
        return redirect(url_for("milling_station"))
    if current_user.role == "Шлифовка":
        return redirect(url_for("polishing_station"))
    
    # Администраторы видят специальный интерфейс
    if current_user.role == "Админ":
        return render_admin_dashboard()

    cutoff = datetime.now(timezone.utc).date() - timedelta(days=EXPIRED_DAYS)
    expired = Order.query.filter(Order.shipment == True, Order.due_date < cutoff).all()

    for o in expired:
        if o.filepaths:
            for path in o.filepaths.split(";"):
                try:
                    os.remove(os.path.join("static", path))
                except (FileNotFoundError, OSError) as e:
                    print(f"⚠️ Не удалось удалить файл {path}: {e}")
        db.session.delete(o)

    if expired:
        db.session.commit()
        flash(f"🧹 Удалено заказов: {len(expired)}")

    if request.method == "POST" and current_user.role == "Менеджер":
        order_id = request.form["order_id"]
        client = request.form["client"]
        
        # Валидация входных данных
        try:
            days = int(request.form["days"])
            if days <= 0:
                raise ValueError("Количество дней должно быть положительным")
        except (ValueError, KeyError):
            flash("Неверное количество дней", "error")
            return redirect(url_for("dashboard"))
        
        facade_type = request.form.get("facade_type") or None
        area = request.form.get("area")
        
        try:
            area = float(area) if area else None
            if area is not None and area <= 0:
                raise ValueError("Площадь должна быть положительной")
        except ValueError:
            flash("Неверная площадь", "error")
            return redirect(url_for("dashboard"))
        
        due_date = datetime.now(timezone.utc).date() + timedelta(days=days)

        uploaded_files = request.files.getlist("files")
        filenames = []
        filepaths = []

        for f in uploaded_files:
            if f and f.filename:
                # Проверяем тип файла
                if not allowed_file(f.filename):
                    flash(f"Файл {f.filename} имеет недопустимый тип", "error")
                    continue
                
                # Проверяем размер файла
                f.seek(0, 2)  # Переходим в конец файла
                file_size = f.tell()
                f.seek(0)  # Возвращаемся в начало
                
                if file_size > MAX_FILE_SIZE:
                    flash(f"Файл {f.filename} слишком большой (максимум {MAX_FILE_SIZE // (1024*1024)}MB)", "error")
                    continue
                
                # Создаем безопасное имя файла
                safe_filename = secure_filename_custom(f.filename)
                filenames.append(safe_filename)
                path = os.path.join(app.config["UPLOAD_FOLDER"], safe_filename)
                f.save(path)
                filepaths.append(os.path.relpath(path, start="static"))

        order = Order(
            order_id=order_id,
            client=client,
            days=days,
            due_date=due_date,
            milling=False,
            packaging=False,
            shipment=False,
            paid=False,
            filenames=";".join(filenames),
            filepaths=";".join(filepaths),
            facade_type=facade_type,
            area=area
        )

        db.session.add(order)
        db.session.commit()
        
        # Проверяем и очищаем хранилище при необходимости
        cleanup_old_orders()
        
        flash("✅ Заказ добавлен!")
        return redirect(url_for("dashboard"))

    # Для роли "Производство" показываем заказы после фрезеровки и шлифовки
    if current_user.role == "Производство":
        # Получаем заказы, которые прошли фрезеровку и шлифовку
        orders = Order.query.filter(
            Order.milling == True,
            Order.polishing_1 == True,
            Order.shipment == False
        ).order_by(
            # Сначала незавершенные заказы (без упаковки), затем завершенные
            Order.packaging.asc(),
            Order.due_date.asc()
        ).all()
    else:
        # Для остальных ролей показываем все заказы
        orders = Order.query.order_by(Order.due_date).all()
    
    # Получаем информацию о хранилище
    storage_usage = get_storage_usage_mb()
    storage_info = {
        'current_mb': round(storage_usage, 2),
        'limit_mb': STORAGE_LIMIT_MB,
        'percentage': round((storage_usage / STORAGE_LIMIT_MB) * 100, 1)
    }
    
    return render_template("dashboard.html", orders=orders, datetime=datetime, storage_info=storage_info)

def render_admin_dashboard():
    """Рендеринг панели администратора"""
    if request.method == "POST":
        order_id = request.form["order_id"]
        client = request.form["client"]
        
        # Валидация входных данных
        try:
            days = int(request.form["days"])
            if days <= 0:
                raise ValueError("Количество дней должно быть положительным")
        except (ValueError, KeyError):
            flash("Неверное количество дней", "error")
            return redirect(url_for("edit_order", order_id=order_id))
        
        facade_type = request.form.get("facade_type") or None
        area = request.form.get("area")
        
        try:
            area = float(area) if area else None
            if area is not None and area <= 0:
                raise ValueError("Площадь должна быть положительной")
        except ValueError:
            flash("Неверная площадь", "error")
            return redirect(url_for("edit_order", order_id=order_id))
        
        due_date = datetime.now(timezone.utc).date() + timedelta(days=days)

        order = Order(
            order_id=order_id,
            client=client,
            days=days,
            due_date=due_date,
            milling=False,
            packaging=False,
            shipment=False,
            paid=False,
            filenames="",
            filepaths="",
            facade_type=facade_type,
            area=area
        )

        db.session.add(order)
        db.session.commit()
        flash("✅ Заказ добавлен!")
        return redirect(url_for("dashboard"))

    orders = Order.query.order_by(Order.due_date).all()
    
    # Получаем информацию о хранилище
    storage_usage = get_storage_usage_mb()
    storage_info = {
        'current_mb': round(storage_usage, 2),
        'limit_mb': STORAGE_LIMIT_MB,
        'percentage': round((storage_usage / STORAGE_LIMIT_MB) * 100, 1)
    }
    
    return render_template("admin_dashboard.html", orders=orders, datetime=datetime, current_user=current_user, storage_info=storage_info)

@app.route("/delete_order/<int:order_id>", methods=["DELETE"])
@login_required
def delete_order(order_id):
    """Удаление заказа (для администраторов и менеджеров)"""
    if current_user.role not in ["Админ", "Менеджер"]:
        return jsonify({"success": False, "message": "⛔ Нет доступа"}), 403
    
    try:
        order = Order.query.get_or_404(order_id)
        
        # Удаляем файлы, если они есть
        if order.filepaths:
            for path in order.filepaths.split(";"):
                try:
                    os.remove(os.path.join("static", path))
                except (FileNotFoundError, OSError) as e:
                    print(f"⚠️ Не удалось удалить файл {path}: {e}")
        
        db.session.delete(order)
        db.session.commit()
        
        return jsonify({"success": True, "message": "✅ Заказ удален"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"❌ Ошибка: {str(e)}"}), 500

@app.route("/update_status/<int:order_id>", methods=["POST"])
@login_required
def update_status(order_id):
    if current_user.role not in ["Админ", "Менеджер", "Производство", "Фрезеровка", "Шлифовка"]:
        return "⛔ Нет доступа", 403

    order = Order.query.get_or_404(order_id)
    form = request.form

    order.milling = form.get("milling") == "1"
    order.polishing_1 = form.get("polishing_1") == "1"
    order.packaging = form.get("packaging") == "1"
    order.shipment = form.get("shipment") == "1"
    order.paid = form.get("paid") == "1"

    db.session.commit()
    return "✅ Сохранено", 200

@app.route("/update_stage", methods=["POST"])
@login_required
def update_stage():
    """Обновление отдельного этапа (для страницы шлифовки)"""
    if current_user.role not in ["Менеджер", "Производство", "Фрезеровка", "Шлифовка"]:
        return "⛔ Нет доступа", 403

    data = request.get_json()
    order_id = data.get("order_id")
    field_name = data.get("field_name")
    value = data.get("value")

    if not all([order_id, field_name is not None, value is not None]):
        return "❌ Неверные данные", 400

    order = Order.query.get_or_404(order_id)
    
    # Проверяем, что поле существует и можно его изменять
    allowed_fields = ["polishing_1", "milling", "packaging", "shipment", "paid"]
    if field_name not in allowed_fields:
        return "❌ Недопустимое поле", 400

    setattr(order, field_name, value)
    db.session.commit()
    
    return "✅ Сохранено", 200

@app.route("/monitor")
@login_required
def monitor():
    if current_user.role != "Монитор":
        return redirect(url_for("dashboard"))

    orders = Order.query.filter(Order.milling == True, Order.shipment == False).order_by(Order.due_date).all()
    return render_template("monitor.html", orders=orders, datetime=datetime)

@app.route("/milling", methods=["GET", "POST"])
@login_required
def milling_station():
    if current_user.role != "Фрезеровка":
        return redirect(url_for("dashboard"))

    pool = generate_daily_pool()
    
    # Добавляем информацию об оптимизации и срочности
    pool_info = {
        'is_urgent': any(is_urgent_order(order) for order in pool) if pool else False,
        'efficiency': 0,
        'waste': 0
    }
    
    # Добавляем информацию о срочности для каждого заказа
    order_urgency = {}
    for order in pool:
        days_left = (order.due_date - datetime.now(timezone.utc).date()).days
        order_urgency[order.id] = {
            'is_urgent': is_urgent_order(order),
            'days_left': days_left
        }
    
    if pool:
        total_area = sum(order.area for order in pool)
        sheet_area = SHEET_AREA
        sheets_needed = total_area / sheet_area
        full_sheets = int(sheets_needed)
        partial_sheet = sheets_needed - full_sheets
        
        if partial_sheet > 0:
            pool_info['waste'] = sheet_area - (total_area - full_sheets * sheet_area)
            pool_info['efficiency'] = (total_area / ((full_sheets + 1) * sheet_area)) * 100
        else:
            pool_info['waste'] = 0
            pool_info['efficiency'] = 100
    
    return render_template("milling.html", orders=pool, pool_info=pool_info, order_urgency=order_urgency)

@app.route("/mark_pool_complete", methods=["POST"])
@login_required
def mark_pool_complete():
    if current_user.role != "Фрезеровка":
        return "⛔ Нет доступа", 403

    pool = generate_daily_pool()
    for order in pool:
        order.milling = True

    db.session.commit()
    
    # Возвращаем JSON ответ для AJAX запросов
    if request.headers.get('Content-Type') == 'application/json':
        return {"success": True, "message": "✅ Пул заказов завершён"}
    
    flash("✅ Пул заказов завершён. Загружается следующий...")
    return redirect(url_for("milling_station"))

@app.route("/milling-pool")
@login_required
def milling_pool():
    """Страница пула заказов для фрезеровщика"""
    if current_user.role != "Фрезеровка":
        return redirect(url_for("dashboard"))

    pool = generate_daily_pool()
    
    # Добавляем информацию об оптимизации и срочности
    pool_info = {
        'is_urgent': any(is_urgent_order(order) for order in pool) if pool else False,
        'efficiency': 0,
        'waste': 0
    }
    
    # Добавляем информацию о срочности для каждого заказа
    order_urgency = {}
    for order in pool:
        days_left = (order.due_date - datetime.now(timezone.utc).date()).days
        order_urgency[order.id] = {
            'is_urgent': is_urgent_order(order),
            'days_left': days_left
        }
    
    if pool:
        total_area = sum(order.area for order in pool)
        sheet_area = SHEET_AREA
        sheets_needed = total_area / sheet_area
        full_sheets = int(sheets_needed)
        partial_sheet = sheets_needed - full_sheets
        
        if partial_sheet > 0:
            pool_info['waste'] = sheet_area - (total_area - full_sheets * sheet_area)
            pool_info['efficiency'] = (total_area / ((full_sheets + 1) * sheet_area)) * 100
        else:
            pool_info['waste'] = 0
            pool_info['efficiency'] = 100
    
    return render_template("milling_pool.html", orders=pool, pool_info=pool_info, order_urgency=order_urgency)

@app.route("/milling-orders")
@login_required
def milling_orders():
    """Страница управления всеми заказами для фрезеровщика"""
    if current_user.role != "Фрезеровка":
        return redirect(url_for("dashboard"))

    # Получаем все заказы для отображения
    orders = Order.query.filter(Order.shipment == False).order_by(Order.due_date.asc()).all()
    
    # Получаем текущий пул
    current_pool = generate_daily_pool()
    pool_order_ids = [order.id for order in current_pool]
    
    # Добавляем информацию о срочности для каждого заказа
    order_urgency = {}
    for order in orders:
        days_left = (order.due_date - datetime.now(timezone.utc).date()).days
        order_urgency[order.id] = {
            'is_urgent': is_urgent_order(order),
            'days_left': days_left
        }
    
    return render_template("milling_orders.html", 
                         orders=orders, 
                         current_pool=current_pool,
                         pool_order_ids=pool_order_ids,
                         order_urgency=order_urgency)

@app.route("/update_milling_manual", methods=["POST"])
@login_required
def update_milling_manual():
    """Обновление статуса фрезеровки с пересчетом пула"""
    if current_user.role != "Фрезеровка":
        return jsonify({"success": False, "message": "⛔ Нет доступа"}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "❌ Неверный формат данных"}), 400
            
        order_id = data.get('order_id')
        status = data.get('status')
        
        if order_id is None or status is None:
            return jsonify({"success": False, "message": "❌ Отсутствуют обязательные параметры"}), 400
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({"success": False, "message": "❌ Заказ не найден"}), 404
        
        order.milling = status
        db.session.commit()
        
        # Пересчитываем пул после изменения
        new_pool = generate_daily_pool()
        pool_info = {
            'is_urgent': any(is_urgent_order(order) for order in new_pool) if new_pool else False,
            'efficiency': 0,
            'waste': 0
        }
        
        if new_pool:
            total_area = sum(order.area for order in new_pool)
            sheet_area = SHEET_AREA
            sheets_needed = total_area / sheet_area
            full_sheets = int(sheets_needed)
            partial_sheet = sheets_needed - full_sheets
            
            if partial_sheet > 0:
                pool_info['waste'] = sheet_area - (total_area - full_sheets * sheet_area)
                pool_info['efficiency'] = (total_area / ((full_sheets + 1) * sheet_area)) * 100
            else:
                pool_info['waste'] = 0
                pool_info['efficiency'] = 100
        
        return jsonify({
            'success': True,
            'message': f"✅ Статус заказа {order.order_id} обновлен",
            'new_pool': [
                {
                    'id': o.id,
                    'order_id': o.order_id,
                    'client': o.client,
                    'area': o.area,
                    'facade_type': o.facade_type,
                    'due_date': o.due_date.strftime('%Y-%m-%d'),
                    'is_urgent': is_urgent_order(o)
                } for o in new_pool
            ],
            'pool_info': pool_info
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"❌ Ошибка сервера: {str(e)}"}), 500
@app.route("/update_polishing", methods=["POST"])
@login_required
def update_polishing():
    """Обновление статуса шлифовки"""
    if current_user.role not in ["Производство", "Фрезеровка", "Шлифовка"]:
        return jsonify({"success": False, "message": "⛔ Нет доступа"}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "❌ Неверный формат данных"}), 400
            
        order_id = data.get('order_id')
        status = data.get('status')
        
        if order_id is None or status is None:
            return jsonify({"success": False, "message": "❌ Отсутствуют обязательные параметры"}), 400
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({"success": False, "message": "❌ Заказ не найден"}), 404
        
        order.polishing_1 = status
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f"✅ Статус шлифовки заказа {order.order_id} обновлен"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"❌ Ошибка сервера: {str(e)}"}), 500

@app.route("/polishing")
@login_required
def polishing_station():
    if current_user.role not in ["Производство", "Фрезеровка", "Шлифовка"]:
        return redirect(url_for("dashboard"))

    # Получаем все заказы, которые отфрезерованы, но не шпон (шпон не требует шлифовки)
    orders = Order.query.filter(
        Order.milling == True,
        Order.facade_type != "шпон",
        Order.shipment == False
    ).order_by(Order.due_date.asc()).all()
    
    # Добавляем информацию о срочности для каждого заказа
    order_urgency = {}
    for order in orders:
        days_left = (order.due_date - datetime.now(timezone.utc).date()).days
        order_urgency[order.id] = {
            'is_urgent': is_urgent_order(order),
            'days_left': days_left
        }
    
    return render_template("polishing.html", orders=orders, order_urgency=order_urgency)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Маршрут для обслуживания загруженных файлов"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/admin/salary")
@login_required
def admin_salary():
    """Страница управления зарплатами"""
    if current_user.role != "Админ":
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    
    try:
        employees = Employee.query.filter_by(is_active=True).all()
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Вычисляем данные по рабочим часам
        work_hours_data = calculate_work_hours_data(employees, current_year, current_month)
        
        return render_template("admin_salary.html", 
                             employees=employees,
                             work_hours_data=work_hours_data or {},
                             current_year=current_year)
    except Exception as e:
        print(f"Ошибка в admin_salary: {e}")
        import traceback
        traceback.print_exc()
        flash("Ошибка при загрузке страницы зарплат", "error")
        return redirect(url_for("dashboard"))

@app.route("/admin/employees", methods=["GET", "POST"])
@login_required
def admin_employees():
    """Страница управления сотрудниками"""
    if current_user.role != "Админ":
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "add_employee":
            name = request.form.get("name")
            position = request.form.get("position")
            try:
                hourly_rate = float(request.form.get("hourly_rate", 0))
                if hourly_rate < 0:
                    raise ValueError("Часовая ставка не может быть отрицательной")
            except (ValueError, TypeError):
                flash("Неверная часовая ставка", "error")
                return redirect(url_for("admin_employees"))
            
            if name and position:
                employee = Employee(
                    name=name,
                    position=position,
                    hourly_rate=hourly_rate
                )
                db.session.add(employee)
                db.session.commit()
                flash(f"Сотрудник {name} добавлен", "success")
            else:
                flash("Заполните все обязательные поля", "error")
        
        elif action == "update_employee":
            employee_id = request.form.get("employee_id")
            try:
                hourly_rate = float(request.form.get("hourly_rate", 0))
                if hourly_rate < 0:
                    raise ValueError("Часовая ставка не может быть отрицательной")
            except (ValueError, TypeError):
                flash("Неверная часовая ставка", "error")
                return redirect(url_for("admin_employees"))
            
            employee = Employee.query.get(employee_id)
            if employee:
                employee.hourly_rate = hourly_rate
                db.session.commit()
                flash(f"Часовая ставка сотрудника {employee.name} обновлена", "success")
        
        elif action == "deactivate":
            employee_id = request.form.get("employee_id")
            employee = Employee.query.get(employee_id)
            if employee:
                employee.is_active = False
                db.session.commit()
                flash(f"Сотрудник {employee.name} деактивирован", "success")
        
        return redirect(url_for("admin_employees"))
    
    employees = Employee.query.all()
    return render_template("admin_employees.html", employees=employees)

def calculate_work_hours_data(employees, year=None, month=None):
    """Вычисляет данные по рабочим часам и зарплатам для сотрудников"""
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month
    
    work_hours_data = {}
    
    for employee in employees:
        # Получаем все рабочие часы сотрудника за указанный месяц
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        work_hours = WorkHours.query.filter(
            WorkHours.employee_id == employee.id,
            WorkHours.date >= start_date,
            WorkHours.date <= end_date
        ).all()
        
        # Разделяем на два периода
        first_period_hours = 0.0
        second_period_hours = 0.0
        
        for wh in work_hours:
            if wh.date.day <= 15:
                first_period_hours += wh.hours
            else:
                second_period_hours += wh.hours
        
        # Рассчитываем зарплаты
        first_period_salary = first_period_hours * employee.hourly_rate
        second_period_salary = second_period_hours * employee.hourly_rate
        month_salary = first_period_salary + second_period_salary
        
        work_hours_data[employee.id] = {
            'first_period_hours': first_period_hours,
            'second_period_hours': second_period_hours,
            'first_period_salary': first_period_salary,
            'second_period_salary': second_period_salary,
            'month_salary': month_salary
        }
    
    return work_hours_data

@app.route("/admin/work-hours", methods=["GET", "POST"])
@login_required
def admin_work_hours():
    """Страница управления рабочими часами"""
    if current_user.role != "Админ":
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    
    try:
        if request.method == "POST":
            action = request.form.get("action")
            
            if action == "add_hours":
                employee_id = request.form.get("employee_id")
                date_str = request.form.get("date")
                try:
                    hours = float(request.form.get("hours", 0))
                    if hours < 0:
                        raise ValueError("Количество часов не может быть отрицательным")
                except (ValueError, TypeError):
                    flash("Неверное количество часов", "error")
                    return redirect(url_for("admin_work_hours"))
                notes = request.form.get("notes", "")
                
                if employee_id and date_str and hours > 0:
                    try:
                        date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        employee_id_int = int(employee_id)
                        if employee_id_int <= 0:
                            raise ValueError("Неверный ID сотрудника")
                        work_hours = WorkHours(
                            employee_id=employee_id_int,
                            date=date,
                            hours=hours,
                            notes=notes
                        )
                        db.session.add(work_hours)
                        db.session.commit()
                        flash("Рабочие часы добавлены", "success")
                    except ValueError:
                        flash("Неверный формат даты", "error")
                else:
                    flash("Заполните все обязательные поля", "error")
            
            elif action == "bulk_hours":
                # Массовое добавление часов из новой формы
                employee_id = request.form.get("employee_id")
                month = int(request.form.get("month", 1))
                year = int(request.form.get("year", 2024))
                period_type = request.form.get("period_type", "first")
                notes = request.form.get("notes", "")
                
                if employee_id and month and year:
                    try:
                        # Определяем дни для периода
                        if period_type == "first":
                            start_day, end_day = 1, 15
                        else:
                            start_day, end_day = 16, 31
                        
                        # Получаем количество дней в месяце
                        days_in_month = (datetime(year, month + 1, 1) - timedelta(days=1)).day
                        end_day = min(end_day, days_in_month)
                        
                        added_count = 0
                        for day in range(start_day, end_day + 1):
                            # Получаем часы для этого дня
                            hours_key = f"hours_{day}"
                            hours_value = request.form.get(hours_key)
                            
                            if hours_value and float(hours_value) > 0:
                                date = datetime(year, month, day).date()
                                
                                # Проверяем, не добавлены ли уже часы на эту дату
                                existing = WorkHours.query.filter_by(
                                    employee_id=int(employee_id),
                                    date=date
                                ).first()
                                
                                if not existing:
                                    work_hours = WorkHours(
                                        employee_id=int(employee_id),
                                        date=date,
                                        hours=float(hours_value),
                                        notes=notes or f"Ввод за {day}.{month}.{year}"
                                    )
                                    db.session.add(work_hours)
                                    added_count += 1
                                else:
                                    # Обновляем существующие часы
                                    existing.hours = float(hours_value)
                                    existing.notes = notes or f"Обновлено {day}.{month}.{year}"
                                    added_count += 1
                        
                        db.session.commit()
                        flash(f"Рабочие часы добавлены/обновлены: {added_count} записей", "success")
                    except Exception as e:
                        db.session.rollback()
                        flash(f"Ошибка при добавлении часов: {str(e)}", "error")
                else:
                    flash("Заполните все обязательные поля", "error")
            
            return redirect(url_for("admin_work_hours"))
        
        employees = Employee.query.filter_by(is_active=True).all()
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Вычисляем данные по рабочим часам
        work_hours_data = calculate_work_hours_data(employees, current_year, current_month)
        
        return render_template("admin_work_hours.html", 
                             employees=employees, 
                             current_year=current_year,
                             work_hours_data=work_hours_data or {})
    except Exception as e:
        print(f"Ошибка в admin_work_hours: {e}")
        import traceback
        traceback.print_exc()
        flash("Ошибка при загрузке страницы рабочих часов", "error")
        return redirect(url_for("dashboard"))

@app.route("/admin/salary-report")
@login_required
def admin_salary_report():
    """Страница отчетов по зарплатам"""
    if current_user.role != "Админ":
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    
    try:
        employees = Employee.query.filter_by(is_active=True).all()
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Вычисляем данные по рабочим часам
        work_hours_data = calculate_work_hours_data(employees, current_year, current_month)
        
        # Формируем данные для отчета
        report_data = []
        for employee in employees:
            if employee.id in work_hours_data:
                data = work_hours_data[employee.id]
                
                # Получаем детальные данные по дням
                start_date = datetime(current_year, current_month, 1).date()
                if current_month == 12:
                    end_date = datetime(current_year + 1, 1, 1).date() - timedelta(days=1)
                else:
                    end_date = datetime(current_year, current_month + 1, 1).date() - timedelta(days=1)
                
                daily_hours = WorkHours.query.filter(
                    WorkHours.employee_id == employee.id,
                    WorkHours.date >= start_date,
                    WorkHours.date <= end_date
                ).order_by(WorkHours.date).all()
                
                report_data.append({
                    'employee': employee,
                    'month_hours': data['first_period_hours'] + data['second_period_hours'],
                    'month_salary': data['month_salary'],
                    'daily_hours': daily_hours
                })
    
        return render_template("admin_salary_report.html", 
                             employees=employees,
                             report_data=report_data,
                             work_hours_data=work_hours_data or {})
    except Exception as e:
        print(f"Ошибка в admin_salary_report: {e}")
        import traceback
        traceback.print_exc()
        flash("Ошибка при загрузке отчета по зарплатам", "error")
        return redirect(url_for("dashboard"))

@app.route("/admin/cleanup_storage", methods=["POST"])
@login_required
def cleanup_storage():
    """Ручная очистка хранилища (только для администраторов)"""
    if current_user.role != "Админ":
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    
    deleted_count = cleanup_old_orders()
    
    if deleted_count > 0:
        flash(f"✅ Очистка завершена! Удалено заказов: {deleted_count}")
    else:
        flash("ℹ️ Нет заказов для удаления или хранилище в норме")
    
    return redirect(url_for("dashboard"))

@app.route("/mail")
@login_required
def mail_agent():
    """Полноценный почтовый агент для менеджера в стиле macOS"""
    if current_user.role != "Менеджер":
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    
    # Получаем тип просмотра (inbox, sent, compose)
    view_type = request.args.get('view', 'inbox')
    
    # Получаем входящие письма
    inbox_emails = Email.query.filter_by(is_sent=False).order_by(Email.created_at.desc()).limit(50).all()
    
    # Получаем исходящие письма
    sent_emails = Email.query.filter_by(is_sent=True).order_by(Email.sent_at.desc()).limit(50).all()
    
    # Статистика
    unread_count = Email.query.filter_by(is_sent=False, is_read=False).count()
    total_inbox = Email.query.filter_by(is_sent=False).count()
    total_sent = Email.query.filter_by(is_sent=True).count()
    
    return render_template("mail_agent.html", 
                         view_type=view_type,
                         inbox_emails=inbox_emails,
                         sent_emails=sent_emails,
                         unread_count=unread_count,
                         total_inbox=total_inbox,
                         total_sent=total_sent,
                         datetime=datetime)

@app.route("/mail/fetch")
@login_required
def fetch_emails():
    """Получение новых писем"""
    if current_user.role != "Менеджер":
        return jsonify({"success": False, "message": "Доступ запрещен"}), 403
    
    try:
        new_emails = fetch_incoming_emails()
        return jsonify({
            "success": True, 
            "message": f"Получено {len(new_emails)} новых писем",
            "count": len(new_emails)
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка: {str(e)}"}), 500

@app.route("/mail/read/<int:email_id>")
@login_required
def read_email(email_id):
    """Просмотр письма"""
    if current_user.role != "Менеджер":
        flash("Доступ запрещен", "error")
        return redirect(url_for("mail_agent"))
    
    email_obj = Email.query.get_or_404(email_id)
    
    # Отмечаем как прочитанное
    if not email_obj.is_read:
        email_obj.is_read = True
        db.session.commit()
    
    return render_template("email_view.html", email=email_obj, datetime=datetime)

@app.route("/mail/reply/<int:email_id>", methods=["GET", "POST"])
@login_required
def reply_email(email_id):
    """Ответ на письмо"""
    if current_user.role != "Менеджер":
        flash("Доступ запрещен", "error")
        return redirect(url_for("mail_agent"))
    
    original_email = Email.query.get_or_404(email_id)
    
    if request.method == "POST":
        subject = request.form.get("subject")
        body = request.form.get("body")
        
        if not all([subject, body]):
            flash("Заполните все поля", "error")
            return redirect(url_for("reply_email", email_id=email_id))
        
        # Отправляем ответ
        if send_email_with_storage(
            to_email=original_email.sender,
            subject=subject,
            body=body,
            reply_to_id=email_id
        ):
            flash("✅ Ответ отправлен", "success")
        else:
            flash("❌ Ошибка отправки ответа", "error")
        
        return redirect(url_for("mail_agent"))
    
    # Формируем тему ответа
    reply_subject = f"Re: {original_email.subject}" if not original_email.subject.startswith("Re:") else original_email.subject
    
    return render_template("email_reply.html", 
                         original_email=original_email,
                         reply_subject=reply_subject,
                         datetime=datetime)

@app.route("/mail/compose", methods=["GET", "POST"])
@login_required
def compose_email():
    """Создание нового письма"""
    if current_user.role != "Менеджер":
        flash("Доступ запрещен", "error")
        return redirect(url_for("mail_agent"))
    
    if request.method == "POST":
        to_email = request.form.get("to_email")
        subject = request.form.get("subject")
        body = request.form.get("body")
        
        if not all([to_email, subject, body]):
            flash("Заполните все поля", "error")
            return redirect(url_for("compose_email"))
        
        # Отправляем письмо
        if send_email_with_storage(
            to_email=to_email,
            subject=subject,
            body=body
        ):
            flash("✅ Письмо отправлено", "success")
            return redirect(url_for("mail_agent", view="sent"))
        else:
            flash("❌ Ошибка отправки письма", "error")
    
    return render_template("email_compose.html", datetime=datetime)

@app.route("/mail/send_notification/<int:order_id>", methods=["POST"])
@login_required
def send_order_notification_route(order_id):
    """Отправить уведомление клиенту о готовности заказа"""
    if current_user.role != "Менеджер":
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    
    order = Order.query.get_or_404(order_id)
    
    if send_order_notification(order, "ready"):
        flash(f"✅ Уведомление отправлено клиенту {order.client}", "success")
    else:
        flash("❌ Ошибка отправки уведомления", "error")
    
    return redirect(url_for("mail_agent"))

@app.route("/mail/ship_order/<int:order_id>", methods=["POST"])
@login_required
def ship_order(order_id):
    """Отметить заказ как отправленный и уведомить клиента"""
    if current_user.role != "Менеджер":
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    
    order = Order.query.get_or_404(order_id)
    order.shipment = True
    db.session.commit()
    
    # Отправляем уведомление клиенту
    send_order_notification(order, "shipped")
    
    flash(f"✅ Заказ {order.order_id} отмечен как отправленный", "success")
    return redirect(url_for("mail_agent"))

@app.route("/mail/send_custom", methods=["POST"])
@login_required
def send_custom_email():
    """Отправка произвольного email"""
    if current_user.role != "Менеджер":
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    
    to_email = request.form.get("to_email")
    subject = request.form.get("subject")
    message = request.form.get("message")
    
    if not all([to_email, subject, message]):
        flash("Заполните все поля", "error")
        return redirect(url_for("mail_agent"))
    
    try:
        msg = Message(
            subject=subject,
            recipients=[to_email],
            body=message,
            sender=app.config['MAIL_DEFAULT_SENDER']
        )
        mail.send(msg)
        flash(f"✅ Email отправлен на {to_email}", "success")
    except Exception as e:
        flash(f"❌ Ошибка отправки: {str(e)}", "error")
    
    return redirect(url_for("mail_agent"))

@app.cli.command("init-db")
def init_db():
    db.create_all()
    users = [
        {"username": "admin", "password": "admin123", "role": "Админ"},
        {"username": "manager", "password": "5678", "role": "Менеджер"},
        {"username": "worker", "password": "0000", "role": "Производство"},
        {"username": "cutter", "password": "7777", "role": "Фрезеровка"},
        {"username": "polisher", "password": "8888", "role": "Шлифовка"},
        {"username": "monitor", "password": "9999", "role": "Монитор"}
    ]

    for u in users:
        if not User.query.filter_by(username=u["username"]).first():
            db.session.add(User(
                username=u["username"],
                password=generate_password_hash(u["password"]),
                role=u["role"]
            ))
    db.session.commit()
    print("✅ База данных и пользователи инициализированы.")

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
