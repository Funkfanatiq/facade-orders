from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from sqlalchemy import or_, text
from datetime import datetime, timedelta, timezone, date
from calendar import monthrange
import os
import time
import io
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


# Импортируем модели после инициализации Flask
from models import db, User, Order, Employee, WorkHours, SalaryPeriod, Counterparty, PriceListItem, Invoice, InvoiceItem, Payment, PRICE_CATEGORIES
db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def _ensure_counterparty_column():
    """Добавляет колонку counterparty_id в таблицу order, если её ещё нет (миграция без Alembic)."""
    try:
        with db.engine.connect() as conn:
            backend = db.engine.url.get_backend_name()
            if backend == "postgresql":
                r = conn.execute(text("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'order' AND column_name = 'counterparty_id'
                """))
                if r.fetchone() is None:
                    conn.execute(text('ALTER TABLE "order" ADD COLUMN counterparty_id INTEGER REFERENCES counterparty(id)'))
                    conn.commit()
                    print("✅ Колонка order.counterparty_id добавлена")
                else:
                    conn.commit()
            else:
                # SQLite
                r = conn.execute(text('PRAGMA table_info("order")'))
                cols = [row[1] for row in r.fetchall()]
                if "counterparty_id" not in cols:
                    conn.execute(text('ALTER TABLE "order" ADD COLUMN counterparty_id INTEGER REFERENCES counterparty(id)'))
                    conn.commit()
                    print("✅ Колонка order.counterparty_id добавлена")
    except Exception as e:
        print(f"⚠️ Проверка/добавление counterparty_id: {e}")


def _ensure_pricelist_category_column():
    """Добавляет колонку category в таблицу price_list_item, если её ещё нет."""
    try:
        with db.engine.connect() as conn:
            backend = db.engine.url.get_backend_name()
            if backend == "postgresql":
                r = conn.execute(text("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'price_list_item' AND column_name = 'category'
                """))
                if r.fetchone() is None:
                    conn.execute(text("ALTER TABLE price_list_item ADD COLUMN category VARCHAR(32)"))
                    conn.commit()
                    print("✅ Колонка price_list_item.category добавлена")
                else:
                    conn.commit()
            else:
                r = conn.execute(text('PRAGMA table_info(price_list_item)'))
                cols = [row[1] for row in r.fetchall()]
                if "category" not in cols:
                    conn.execute(text("ALTER TABLE price_list_item ADD COLUMN category VARCHAR(32)"))
                    conn.commit()
                    print("✅ Колонка price_list_item.category добавлена")
    except Exception as e:
        print(f"⚠️ Проверка/добавление category в прайс-лист: {e}")


def _ensure_pricelist_sort_order_column():
    """Добавляет колонку sort_order в таблицу price_list_item, если её ещё нет."""
    try:
        with db.engine.connect() as conn:
            backend = db.engine.url.get_backend_name()
            if backend == "postgresql":
                r = conn.execute(text("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'price_list_item' AND column_name = 'sort_order'
                """))
                if r.fetchone() is None:
                    conn.execute(text("ALTER TABLE price_list_item ADD COLUMN sort_order INTEGER DEFAULT 0"))
                    conn.commit()
                    print("✅ Колонка price_list_item.sort_order добавлена")
                else:
                    conn.commit()
            else:
                r = conn.execute(text('PRAGMA table_info(price_list_item)'))
                cols = [row[1] for row in r.fetchall()]
                if "sort_order" not in cols:
                    conn.execute(text("ALTER TABLE price_list_item ADD COLUMN sort_order INTEGER DEFAULT 0"))
                    conn.commit()
                    print("✅ Колонка price_list_item.sort_order добавлена")
    except Exception as e:
        print(f"⚠️ Проверка/добавление sort_order в прайс-лист: {e}")


def _ensure_invoice_order_ids_column():
    """Добавляет колонку order_ids в таблицу invoice, если её ещё нет."""
    try:
        with db.engine.connect() as conn:
            backend = db.engine.url.get_backend_name()
            if backend == "postgresql":
                r = conn.execute(text("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'invoice' AND column_name = 'order_ids'
                """))
                if r.fetchone() is None:
                    conn.execute(text("ALTER TABLE invoice ADD COLUMN order_ids VARCHAR(256)"))
                    conn.commit()
                    print("✅ Колонка invoice.order_ids добавлена")
                else:
                    conn.commit()
            else:
                r = conn.execute(text('PRAGMA table_info(invoice)'))
                cols = [row[1] for row in r.fetchall()]
                if "order_ids" not in cols:
                    conn.execute(text("ALTER TABLE invoice ADD COLUMN order_ids VARCHAR(256)"))
                    conn.commit()
                    print("✅ Колонка invoice.order_ids добавлена")
    except Exception as e:
        print(f"⚠️ Проверка/добавление order_ids в invoice: {e}")


# Инициализация базы данных при запуске (с retry для Render PostgreSQL)
def init_database():
    """Инициализация базы данных. Retry при SSL/сетевых ошибках (Render)."""
    max_attempts = 5
    delay_seconds = 3
    use_pg = bool(os.environ.get('DATABASE_URL'))

    for attempt in range(1, max_attempts + 1):
        try:
            with app.app_context():
                print(f"🚀 Инициализация базы данных... (попытка {attempt}/{max_attempts})")
                
                # Создаем все таблицы
                db.create_all()
                print("✅ Таблицы созданы")
                # Добавляем колонку counterparty_id в order, если её ещё нет (миграция без Alembic)
                _ensure_counterparty_column()
                # Добавляем колонку category в price_list_item, если её ещё нет
                _ensure_pricelist_category_column()
                # Добавляем колонку sort_order в price_list_item, если её ещё нет
                _ensure_pricelist_sort_order_column()
                _ensure_invoice_order_ids_column()

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
                return
                
        except Exception as e:
            err_msg = str(e).lower()
            is_retryable = use_pg and (
                'ssl' in err_msg or 'connection' in err_msg or 'e3q8' in err_msg or 'operational' in err_msg
            )
            print(f"❌ Ошибка инициализации: {e}")
            if attempt < max_attempts and is_retryable:
                print(f"⏳ Повтор через {delay_seconds} сек...")
                time.sleep(delay_seconds)
            else:
                import traceback
                traceback.print_exc()
                return

# Запускаем инициализацию
try:
    init_database()
except Exception as e:
    print(f"⚠️ Предупреждение: Не удалось выполнить инициализацию БД при запуске: {e}")
    print("⚠️ Приложение продолжит работу, но функциональность может быть ограничена")

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
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        print(f"Ошибка при загрузке пользователя: {e}")
        return None

@app.before_request
def clear_session_if_not_logged_in():
    try:
        if not current_user.is_authenticated:
            session.clear()
    except AttributeError:
        # Если current_user еще не инициализирован
        session.clear()

@app.errorhandler(500)
def internal_error(error):
    """Обработчик внутренних ошибок сервера"""
    try:
        db.session.rollback()
    except Exception:
        pass
    import traceback
    import sys
    print("=" * 60, file=sys.stderr)
    print("ВНУТРЕННЯЯ ОШИБКА СЕРВЕРА (500):", file=sys.stderr)
    print(f"Ошибка: {error}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    try:
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            flash("Произошла внутренняя ошибка. Попробуйте позже.", "error")
            return redirect(url_for("dashboard"))
    except:
        pass
    flash("Произошла внутренняя ошибка. Попробуйте позже.", "error")
    return redirect(url_for("login"))

@app.errorhandler(404)
def not_found_error(error):
    """Обработчик ошибки 404"""
    flash("Страница не найдена", "error")
    try:
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            return redirect(url_for("dashboard"))
    except:
        pass
    return redirect(url_for("login"))

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



@app.route("/login", methods=["GET", "POST"])
def login():
    try:
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            
            if not username or not password:
                flash("Введите логин и пароль", "error")
                return render_template("login.html")
            
            try:
                user = User.query.filter_by(username=username).first()
            except Exception as e:
                print(f"Ошибка при запросе пользователя: {e}")
                flash("Ошибка подключения к базе данных. Попробуйте позже.", "error")
                return render_template("login.html")

            if user and check_password_hash(user.password, password):
                login_user(user)
                if user.role == "Монитор":
                    return redirect(url_for("monitor"))
                elif user.role == "Фрезеровка":
                    return redirect(url_for("milling_station"))
                elif user.role == "Шлифовка":
                    return redirect(url_for("polishing_station"))
                return redirect(url_for("dashboard"))

            flash("Неверный логин или пароль", "error")

        return render_template("login.html")
    except Exception as e:
        print(f"Критическая ошибка в login: {e}")
        import traceback
        traceback.print_exc()
        flash("Произошла ошибка. Попробуйте позже.", "error")
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
            for path in (o.filepaths or "").split(";"):
                path = (path or "").strip()
                if not path:
                    continue
                try:
                    os.remove(os.path.join(app.config["UPLOAD_FOLDER"], path))
                except (FileNotFoundError, OSError) as e:
                    print(f"⚠️ Не удалось удалить файл {path}: {e}")
        db.session.delete(o)

    if expired:
        db.session.commit()
        flash(f"🧹 Удалено заказов: {len(expired)}")

    if request.method == "POST" and current_user.role == "Менеджер":
        order_id = (request.form.get("order_id") or "").strip()
        client = (request.form.get("client") or "").strip()
        counterparty_id = request.form.get("counterparty_id", type=int)
        if not order_id:
            flash("Укажите номер заказа", "error")
            return redirect(url_for("dashboard"))
        if counterparty_id:
            cp = Counterparty.query.get(counterparty_id)
            if cp:
                client = cp.name
        if not client:
            flash("Укажите клиента или выберите контрагента", "error")
            return redirect(url_for("dashboard"))
        
        # Валидация входных данных
        try:
            days = int(request.form.get("days", 0))
            if days <= 0:
                raise ValueError("Количество дней должно быть положительным")
        except (ValueError, TypeError):
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
                path = os.path.join(app.config["UPLOAD_FOLDER"], safe_filename)
                try:
                    f.save(path)
                    # Храним относительный путь как имя файла для обслуживания через /uploads/<filename>
                    filenames.append(safe_filename)
                    filepaths.append(safe_filename)
                except Exception as e:
                    print(f"Ошибка при сохранении файла {safe_filename}: {e}")
                    flash(f"Не удалось сохранить файл {f.filename}", "error")
                    continue

        order = Order(
            order_id=order_id,
            client=client,
            counterparty_id=counterparty_id if counterparty_id else None,
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
    
    # Для менеджера — список заказчиков из заказов и контрагенты из справочника
    customers = []
    counterparties = []
    counterparties_json = []
    price_list = []
    cp_id_for_client = {}
    all_cp = Counterparty.query.all()
    for c in all_cp:
        cp_id_for_client[c.name] = c.id
        if c.full_name:
            cp_id_for_client[c.full_name] = c.id
    debtors = []
    if current_user.role == "Менеджер":
        customers = [row[0] for row in db.session.query(Order.client).distinct().order_by(Order.client).all()]
        counterparties = Counterparty.query.order_by(Counterparty.name).all()
        counterparties_json = [{"name": c.name, "id": c.id} for c in counterparties]
        price_list = PriceListItem.query.order_by(
            PriceListItem.category, PriceListItem.sort_order, PriceListItem.name
        ).all()
        for cp in counterparties:
            invoices = Invoice.query.filter(Invoice.counterparty_id == cp.id).all()
            total_invoiced = sum(inv.total for inv in invoices)
            total_paid = sum(p.amount for p in Payment.query.filter(Payment.counterparty_id == cp.id).all())
            balance = total_invoiced - total_paid
            if balance > 0:
                unpaid_nums = []
                for inv in invoices:
                    paid_amt = sum(p.amount for p in inv.payments)
                    if inv.total - paid_amt > 0:
                        unpaid_nums.append(inv.invoice_number)
                debtors.append({"counterparty": cp, "unpaid_invoices": unpaid_nums, "balance": balance})

    return render_template("dashboard.html", orders=orders, datetime=datetime, storage_info=storage_info, customers=customers, counterparties=counterparties, counterparties_json=counterparties_json, price_list=price_list, price_categories=PRICE_CATEGORIES, cp_id_for_client=cp_id_for_client, debtors=debtors)


@app.route("/counterparty/add", methods=["POST"])
@login_required
def counterparty_add():
    """Добавление контрагента (только менеджер)."""
    if current_user.role != "Менеджер":
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    name = (request.form.get("counterparty_name") or "").strip()
    if not name:
        flash("Укажите имя контрагента", "error")
        return redirect(url_for("dashboard"))
    c = Counterparty(
        name=name,
        phone=request.form.get("counterparty_phone") or None,
        email=request.form.get("counterparty_email") or None,
        counterparty_type=request.form.get("counterparty_type") or None,
        inn=request.form.get("counterparty_inn") or None,
        full_name=request.form.get("counterparty_full_name") or None,
        legal_address=request.form.get("counterparty_legal_address") or None,
        fias_code=request.form.get("counterparty_fias_code") or None,
        kpp=request.form.get("counterparty_kpp") or None,
        ogrn=request.form.get("counterparty_ogrn") or None,
        okpo=request.form.get("counterparty_okpo") or None,
        bik=request.form.get("counterparty_bik") or None,
        bank=request.form.get("counterparty_bank") or None,
        address=request.form.get("counterparty_address") or None,
        corr_account=request.form.get("counterparty_corr_account") or None,
        payment_account=request.form.get("counterparty_payment_account") or None,
    )
    db.session.add(c)
    db.session.commit()
    flash("Контрагент добавлен", "success")
    return redirect(url_for("dashboard"))


@app.route("/counterparty/<int:counterparty_id>/edit", methods=["POST"])
@login_required
def counterparty_edit(counterparty_id):
    """Редактирование контрагента (менеджер и админ)."""
    if current_user.role not in ["Менеджер", "Админ"]:
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    c = Counterparty.query.get_or_404(counterparty_id)
    name = (request.form.get("counterparty_name") or "").strip()
    if not name:
        flash("Укажите имя контрагента", "error")
        return redirect(url_for("counterparty_card", counterparty_id=counterparty_id))
    c.name = name
    c.phone = request.form.get("counterparty_phone") or None
    c.email = request.form.get("counterparty_email") or None
    c.counterparty_type = request.form.get("counterparty_type") or None
    c.inn = request.form.get("counterparty_inn") or None
    c.full_name = request.form.get("counterparty_full_name") or None
    c.legal_address = request.form.get("counterparty_legal_address") or None
    c.fias_code = request.form.get("counterparty_fias_code") or None
    c.kpp = request.form.get("counterparty_kpp") or None
    c.ogrn = request.form.get("counterparty_ogrn") or None
    c.okpo = request.form.get("counterparty_okpo") or None
    c.bik = request.form.get("counterparty_bik") or None
    c.bank = request.form.get("counterparty_bank") or None
    c.address = request.form.get("counterparty_address") or None
    c.corr_account = request.form.get("counterparty_corr_account") or None
    c.payment_account = request.form.get("counterparty_payment_account") or None
    db.session.commit()
    flash("Контрагент изменён", "success")
    return redirect(url_for("counterparty_card", counterparty_id=counterparty_id))


@app.route("/payment/<int:payment_id>/delete", methods=["POST"])
@login_required
def payment_delete(payment_id):
    """Удаление оплаты (менеджер и админ)."""
    if current_user.role not in ["Менеджер", "Админ"]:
        return jsonify({"ok": False, "error": "Доступ запрещен"}), 403
    p = Payment.query.get_or_404(payment_id)
    cp_id = p.counterparty_id
    db.session.delete(p)
    db.session.commit()
    return jsonify({"ok": True, "redirect": url_for("counterparty_card", counterparty_id=cp_id)})


@app.route("/invoice/<int:invoice_id>/delete", methods=["POST"])
@login_required
def invoice_delete(invoice_id):
    """Удаление счёта (менеджер и админ). Оплаты, привязанные к счёту, станут общими."""
    if current_user.role not in ["Менеджер", "Админ"]:
        return jsonify({"ok": False, "error": "Доступ запрещен"}), 403
    inv = Invoice.query.get_or_404(invoice_id)
    cp_id = inv.counterparty_id
    for p in inv.payments:
        p.invoice_id = None
    db.session.delete(inv)
    db.session.commit()
    return jsonify({"ok": True, "redirect": url_for("counterparty_card", counterparty_id=cp_id)})


@app.route("/pricelist/add", methods=["POST"])
@login_required
def pricelist_add():
    """Добавление позиции прайс-листа (только менеджер)."""
    if current_user.role != "Менеджер":
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    name = (request.form.get("pricelist_name") or "").strip()
    if not name:
        flash("Укажите наименование позиции", "error")
        return redirect(url_for("dashboard"))
    try:
        price = float(request.form.get("pricelist_price") or "0")
    except (TypeError, ValueError):
        flash("Укажите корректную цену", "error")
        return redirect(url_for("dashboard"))
    category = request.form.get("pricelist_category") or None
    # sort_order = max+1 в данной категории
    from sqlalchemy import func
    q = db.session.query(func.coalesce(func.max(PriceListItem.sort_order), -1))
    if category:
        q = q.filter(PriceListItem.category == category)
    else:
        q = q.filter(PriceListItem.category.is_(None))
    max_order = q.scalar() or -1
    item = PriceListItem(
        name=name,
        price=price,
        unit=request.form.get("pricelist_unit") or None,
        category=category,
        sort_order=max_order + 1,
        note=request.form.get("pricelist_note") or None,
    )
    db.session.add(item)
    db.session.commit()
    flash("Позиция прайс-листа добавлена", "success")
    return redirect(url_for("dashboard", tab="pricelist"))


@app.route("/pricelist/<int:item_id>/edit", methods=["POST"])
@login_required
def pricelist_edit(item_id):
    """Редактирование позиции прайс-листа (только менеджер)."""
    if current_user.role != "Менеджер":
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    item = PriceListItem.query.get_or_404(item_id)
    name = (request.form.get("pricelist_name") or "").strip()
    if not name:
        flash("Укажите наименование позиции", "error")
        return redirect(url_for("dashboard"))
    try:
        price = float(request.form.get("pricelist_price") or "0")
    except (TypeError, ValueError):
        flash("Укажите корректную цену", "error")
        return redirect(url_for("dashboard"))
    item.name = name
    item.price = price
    item.unit = request.form.get("pricelist_unit") or None
    item.category = request.form.get("pricelist_category") or None
    db.session.commit()
    flash("Позиция прайс-листа изменена", "success")
    return redirect(url_for("dashboard", tab="pricelist"))


@app.route("/pricelist/reorder", methods=["POST"])
@login_required
def pricelist_reorder():
    """Изменение порядка позиций прайс-листа (только менеджер)."""
    if current_user.role != "Менеджер":
        return jsonify({"ok": False, "error": "Доступ запрещен"}), 403
    data = request.get_json()
    if not data or "item_ids" not in data:
        return jsonify({"ok": False, "error": "Нужен массив item_ids"}), 400
    item_ids = data.get("item_ids", [])
    for idx, iid in enumerate(item_ids):
        item = PriceListItem.query.get(iid)
        if item:
            item.sort_order = idx
    db.session.commit()
    return jsonify({"ok": True})


def _get_pdf_font():
    """Регистрирует шрифт с поддержкой кириллицы и возвращает его имя."""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        _base = os.path.dirname(os.path.abspath(__file__))
        font_paths = [
            os.path.join(_base, "fonts", "DejaVuSans.ttf"),  # bundled font
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/fonts-liberation/LiberationSans-Regular.ttf",
        ]
        for path in font_paths:
            if path and os.path.isfile(path):
                pdfmetrics.registerFont(TTFont("PricelistFont", path))
                return "PricelistFont"
    except Exception:
        pass
    return "Helvetica"  # fallback — не поддерживает кириллицу, может вызывать 500


@app.route("/pricelist/export/pdf")
@login_required
def pricelist_export_pdf():
    """Выгрузка прайс-листа в PDF (менеджер и админ)."""
    if current_user.role not in ["Менеджер", "Админ"]:
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from xml.sax.saxutils import escape

    def esc(s):
        return escape(str(s or "—"))

    items = PriceListItem.query.order_by(
        PriceListItem.category, PriceListItem.sort_order, PriceListItem.name
    ).all()
    font_name = _get_pdf_font()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm, leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontName=font_name)
    cat_style = ParagraphStyle("Cat", parent=styles["Heading2"], fontName=font_name, fontSize=12)
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontName=font_name, fontSize=9)
    flow = []
    flow.append(Paragraph("Прайс-лист", title_style))
    flow.append(Spacer(1, 8*mm))
    flow.append(Paragraph(f"Дата: {date.today().strftime('%d.%m.%Y')}", cat_style))
    flow.append(Spacer(1, 6*mm))

    # Ширины: № 12mm, Наименование 110mm (с переносом), Цена 28mm, Ед.изм 22mm = 172mm (умещается в A4)
    col_widths = [12*mm, 110*mm, 28*mm, 22*mm]
    tbl_style = [
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0e0e0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]

    grid_cats = [
        ("плоский", "Плоские"), ("фрезерованный", "Фрезерованные"), ("шпон", "Шпон"),
        ("услуги по покраске", "Услуги по покраске"), ("Доп услуги", "Доп услуги")
    ]
    for cat, label in grid_cats:
        cat_items = [p for p in items if p.category == cat]
        if cat_items:
            flow.append(Paragraph(label, cat_style))
            data = [["№", "Наименование", "Цена, ₽", "Ед. изм."]]
            for i, p in enumerate(cat_items, 1):
                price_str = f"{p.price:.2f}".replace(".", ",") if p.price is not None else "—"
                name_para = Paragraph(esc(p.name), cell_style)
                data.append([str(i), name_para, price_str, p.unit or "—"])
            t = Table(data, colWidths=col_widths)
            t.setStyle(TableStyle(tbl_style))
            flow.append(t)
            flow.append(Spacer(1, 6*mm))

    doc.build(flow)
    buf.seek(0)
    filename = f"pricelist_{date.today().strftime('%Y-%m-%d')}.pdf"
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=filename)


@app.route("/counterparty/<int:counterparty_id>/invoice/create", methods=["POST"])
@login_required
def invoice_create(counterparty_id):
    """Создание счёта на оплату для контрагента."""
    if current_user.role not in ["Менеджер", "Админ"]:
        return jsonify({"ok": False, "error": "Доступ запрещен"}), 403
    cp = Counterparty.query.get_or_404(counterparty_id)
    data = request.get_json()
    if not data or "items" not in data:
        return jsonify({"ok": False, "error": "Добавьте хотя бы одну позицию"}), 400
    items_data = data.get("items", [])
    if not items_data:
        return jsonify({"ok": False, "error": "Добавьте хотя бы одну позицию"}), 400
    order_ids = (data.get("order_ids") or "").strip()
    invoice_number = (data.get("invoice_number") or "").strip()
    if not invoice_number:
        return jsonify({"ok": False, "error": "Укажите номер счёта"}), 400
    inv = Invoice(counterparty_id=counterparty_id, invoice_number=invoice_number, invoice_date=date.today(), order_ids=order_ids or None)
    db.session.add(inv)
    db.session.flush()
    for it in items_data:
        name = (it.get("name") or "").strip()
        if not name:
            continue
        try:
            qty = float(it.get("quantity") or 1)
        except (TypeError, ValueError):
            qty = 1.0
        try:
            price = float(it.get("price") or 0)
        except (TypeError, ValueError):
            price = 0.0
        unit = (it.get("unit") or "").strip() or "шт"
        db.session.add(InvoiceItem(invoice_id=inv.id, name=name, unit=unit, quantity=qty, price=price, price_list_item_id=it.get("price_list_item_id")))
    db.session.commit()
    return jsonify({"ok": True, "invoice_id": inv.id, "invoice_number": inv.invoice_number})


def _amount_to_words_rub(amount):
    """Сумма прописью: 75661.50 -> Семьдесят пять тысяч шестьсот шестьдесят один рубль 50 копеек."""
    try:
        from num2words import num2words
        s = num2words(amount, lang='ru', to='currency', currency='RUB')
        return s[0].upper() + s[1:] if s else f"{amount:.2f}".replace(".", ",")
    except Exception:
        try:
            rub = int(amount)
            kop = round((amount - rub) * 100)
            w = num2words(rub, lang='ru')
            w = w[0].upper() + w[1:] if w else str(rub)
            return f"{w} руб. {kop:02d} коп."
        except Exception:
            return f"{amount:.2f}".replace(".", ",")


@app.route("/invoice/<int:invoice_id>/pdf")
@login_required
def invoice_pdf(invoice_id):
    """Скачивание счёта в PDF (форма как в образце)."""
    if current_user.role not in ["Менеджер", "Админ"]:
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    inv = Invoice.query.get_or_404(invoice_id)
    cp = inv.counterparty
    cfg = app.config
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from xml.sax.saxutils import escape
    font_name = _get_pdf_font()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=12*mm, bottomMargin=12*mm, leftMargin=12*mm, rightMargin=12*mm)
    styles = getSampleStyleSheet()
    p_style = ParagraphStyle("P", parent=styles["Normal"], fontName=font_name, fontSize=9)
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontName=font_name, fontSize=9)
    small_style = ParagraphStyle("Small", parent=styles["Normal"], fontName=font_name, fontSize=8)

    def esc(s):
        return escape(str(s or ""))

    def fmt_num(x):
        try:
            return f"{float(x or 0):.2f}".replace(".", ",")
        except (TypeError, ValueError):
            return "0,00"

    seller_name = esc(cfg.get('COMPANY_NAME'))
    seller_addr = esc(cfg.get('COMPANY_ADDRESS'))
    seller_inn = esc(cfg.get('COMPANY_INN'))
    seller_kpp = esc(cfg.get('COMPANY_KPP'))
    seller_bank = esc(cfg.get('COMPANY_BANK'))
    seller_bik = esc(cfg.get('COMPANY_BIK'))
    seller_account = esc(cfg.get('COMPANY_ACCOUNT'))
    seller_corr = esc(cfg.get('COMPANY_CORR_ACCOUNT'))
    buyer_name = esc(cp.full_name or cp.name)

    flow = []

    flow.append(Paragraph(seller_name, p_style))
    flow.append(Paragraph(seller_addr, p_style))
    flow.append(Spacer(1, 4*mm))

    req_rows = [
        ["Образец заполнения платежного поручения"],
        [f"ИНН {seller_inn}"],
        [f"КПП {seller_kpp or ''}"],
        ["Получатель"],
        [seller_name],
        [f"Сч. № {seller_account}"],
        ["Банк получателя"],
        [seller_bank],
        [f"БИК {seller_bik}"],
        [f"Сч. № {seller_corr}"],
    ]
    req_table = Table(req_rows, colWidths=[170*mm])
    req_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    flow.append(req_table)
    flow.append(Spacer(1, 6*mm))

    from reportlab.lib.enums import TA_CENTER
    invoice_title_style = ParagraphStyle("InvoiceTitle", parent=styles["Normal"], fontName=font_name, fontSize=12, alignment=TA_CENTER, fontWeight='bold')
    flow.append(Paragraph(f"СЧЕТ № {esc(inv.invoice_number)} от {inv.invoice_date.strftime('%d.%m.%Y')}", invoice_title_style))
    flow.append(Spacer(1, 4*mm))

    payer_data = [
        [f"Плательщик {buyer_name}"],
        [f"Грузополучатель {buyer_name}"],
    ]
    payer_table = Table(payer_data, colWidths=[170*mm])
    payer_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    flow.append(payer_table)
    flow.append(Spacer(1, 4*mm))

    headers = ["№", "Наименование товара", "Цена", "Кол-во", "Ед. изм.", "Сумма"]
    col_widths = [12*mm, 80*mm, 22*mm, 18*mm, 18*mm, 30*mm]
    data = [headers]
    total_sum = 0.0
    for i, it in enumerate(inv.items, 1):
        s = round(it.quantity * it.price, 2)
        total_sum += s
        data.append([
            str(i),
            Paragraph(esc(it.name), cell_style),
            fmt_num(it.price),
            fmt_num(it.quantity),
            it.unit or "шт",
            fmt_num(s),
        ])
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    flow.append(t)
    flow.append(Spacer(1, 4*mm))

    total_str = fmt_num(total_sum)
    flow.append(Paragraph(f"Итого: {total_str}", p_style))
    flow.append(Paragraph("В том числе НДС: 0,00", p_style))
    amount_words = _amount_to_words_rub(total_sum)
    flow.append(Paragraph(f"Итого к оплате: {amount_words}", p_style))
    flow.append(Spacer(1, 8*mm))

    sig_data = [
        ["Главный бухгалтер ()", "Руководитель организации или иное уполномоченное лицо ()"],
        ["", seller_name],
    ]
    sig_table = Table(sig_data, colWidths=[85*mm, 85*mm])
    sig_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    flow.append(sig_table)
    doc.build(flow)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=f"invoice_{inv.invoice_number}.pdf")


def _unit_to_okei(unit):
    """Код ОКЕИ по наименованию единицы измерения."""
    u = (unit or "").strip().lower()
    if u in ("м²", "м2", "м.кв.", "кв.м", "кв/м"): return "055"
    if u in ("шт", "штук"): return "796"
    if u in ("п.м", "п.м.", "пм", "пог.м"): return "018"
    return "796"


@app.route("/invoice/<int:invoice_id>/torg12")
@login_required
def invoice_torg12(invoice_id):
    """Скачивание товарной накладной ТОРГ-12. Точная копия формы по образцу."""
    if current_user.role not in ["Менеджер", "Админ"]:
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    inv = Invoice.query.get_or_404(invoice_id)
    cp = inv.counterparty
    if not cp:
        flash("Контрагент по счёту не найден", "error")
        return redirect(url_for("dashboard"))
    cfg = app.config
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from xml.sax.saxutils import escape
    font_name = _get_pdf_font()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), topMargin=8*mm, bottomMargin=8*mm, leftMargin=10*mm, rightMargin=10*mm)
    styles = getSampleStyleSheet()
    fs6 = ParagraphStyle("FS6", parent=styles["Normal"], fontName=font_name, fontSize=6)
    fs7 = ParagraphStyle("FS7", parent=styles["Normal"], fontName=font_name, fontSize=7)
    fs8 = ParagraphStyle("FS8", parent=styles["Normal"], fontName=font_name, fontSize=8)

    def esc(s):
        return escape(str(s or ""))

    def fmt_num(x):
        try:
            return f"{float(x or 0):.2f}".replace(".", ",")
        except (TypeError, ValueError):
            return "0,00"

    seller_name = esc(cfg.get('COMPANY_NAME'))
    seller_addr = esc(cfg.get('COMPANY_ADDRESS'))
    seller_inn = esc(cfg.get('COMPANY_INN'))
    seller_bank = esc(cfg.get('COMPANY_BANK'))
    seller_bik = esc(cfg.get('COMPANY_BIK'))
    seller_account = esc(cfg.get('COMPANY_ACCOUNT'))
    seller_corr = esc(cfg.get('COMPANY_CORR_ACCOUNT'))
    seller_okpo = esc(cfg.get('COMPANY_OKPO') or "")

    buyer_name = esc(cp.full_name or cp.name)
    buyer_addr = esc(cp.address or cp.legal_address or "")
    buyer_inn = esc(cp.inn or "")
    buyer_bank = esc(cp.bank or "")
    buyer_bik = esc(cp.bik or "")
    buyer_account = esc(cp.payment_account or "")
    buyer_corr = esc(cp.corr_account or "")
    buyer_okpo = esc(cp.okpo or "")

    doc_date = date.today()
    org_str = f"{seller_name}, {seller_addr}, ИНН {seller_inn}, р/с {seller_account} в банке {seller_bank} БИК {seller_bik}, корр/с {seller_corr}"
    consignee_str = f"{buyer_name}, {buyer_addr or ''}, ИНН {buyer_inn}".strip()
    if cp.payment_account and cp.bank:
        consignee_str += f", р/с {buyer_account} в банке {buyer_bank} БИК {buyer_bik}, корр/с {buyer_corr}"
    basis = f"Счет на оплату № {esc(inv.invoice_number)} от {inv.invoice_date.strftime('%d.%m.%Y')}"

    flow = []
    tbl_style = lambda t: t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))

    header_title = ParagraphStyle("H", parent=styles["Normal"], fontName=font_name, fontSize=9, alignment=TA_CENTER)
    flow.append(Paragraph("Унифицированная форма № ТОРГ-12", header_title))
    flow.append(Paragraph("Утверждена постановлением Госкомстата России от 25.12.98 № 132", fs7))
    flow.append(Spacer(1, 1*mm))

    left_block = Table([
        ["Грузоотправитель", f"по ОКПО {seller_okpo}" if seller_okpo else ""],
        [org_str, ""],
        ["организация-грузоотправитель, адрес, номер телефона, факса, банковские реквизиты", ""],
        ["структурное подразделение", ""],
        ["Грузополучатель", f"по ОКПО {buyer_okpo}" if buyer_okpo else ""],
        [consignee_str, ""],
        ["организации, адрес, номер телефона, банковские реквизиты", ""],
        ["Поставщик", f"по ОКПО {seller_okpo}" if seller_okpo else ""],
        [org_str, ""],
        ["наименование организации, адрес, номер телефона, банковские реквизиты", ""],
        ["Плательщик", f"по ОКПО {buyer_okpo}" if buyer_okpo else ""],
        [consignee_str, ""],
        ["организации, адрес, номер телефона, банковские реквизиты", ""],
        ["Основание", ""],
        [basis, ""],
        ["наименование документа (договор, контракт, заказ-наряд)", ""],
    ], colWidths=[165*mm, 35*mm])
    left_block.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
    ]))

    right_block = Table([
        ["Форма по ОКУД", "0330212"],
        ["Код", ""],
        ["Вид деятельности по ОКДП", ""],
        ["по ОКПО", seller_okpo or "—"],
        ["Транспортная накладная", ""],
        ["номер", "дата"],
        ["", ""],
        ["Вид операции", ""],
        ["Страница 1", ""],
    ], colWidths=[35*mm, 45*mm])
    right_block.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8f8f8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
    ]))

    top_section = Table([[left_block, right_block]], colWidths=[200*mm, 70*mm])
    top_section.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    flow.append(top_section)
    flow.append(Spacer(1, 2*mm))

    title_block = Table([
        [Paragraph("ТОВАРНАЯ НАКЛАДНАЯ", ParagraphStyle("Title", parent=styles["Normal"], fontName=font_name, fontSize=10, alignment=TA_CENTER, fontWeight='bold')), "Номер документа", "Дата составления"],
        ["", esc(inv.invoice_number), doc_date.strftime('%d.%m.%Y')],
    ], colWidths=[100*mm, 35*mm, 35*mm])
    title_block.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (0, -1), "MIDDLE"),
        ("SPAN", (0, 0), (0, -1)),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (1, 0), (2, -1), colors.HexColor("#f8f8f8")),
        ("ALIGN", (1, 0), (2, -1), "CENTER"),
    ]))
    flow.append(title_block)
    flow.append(Spacer(1, 1*mm))

    # Точная копия формы ТОРГ-12 — 15 колонок по образцу Госкомстата
    header_row = [
        "№ п/п", "наименование, характеристика, сорт, артикул товара", "код", "наименование",
        "Код по ОКЕИ", "Вид упак.", "в одном месте", "штук", "Масса брутто", "Кол-во (масса нетто)",
        "Цена, руб. коп.", "Сумма без учета НДС", "ставка, %", "сумма", "Сумма с учетом НДС"
    ]
    col_w = [5*mm, 40*mm, 6*mm, 8*mm, 7*mm, 8*mm, 8*mm, 6*mm, 10*mm, 12*mm, 14*mm, 18*mm, 6*mm, 12*mm, 18*mm]  # ~176мм
    data = [header_row]
    total_sum = 0.0
    total_qty = 0.0
    for i, it in enumerate(inv.items, 1):
        qty = float(it.quantity or 0)
        prc = float(it.price or 0)
        s = round(qty * prc, 2)
        total_sum += s
        total_qty += qty
        unit = it.unit or "шт"
        okei = _unit_to_okei(unit)
        code_str = str(it.price_list_item_id) if it.price_list_item_id else ""
        mass_brutto = fmt_num(qty)
        data.append([str(i), Paragraph(esc(it.name), fs7), code_str, unit, okei, "", "", "", mass_brutto, fmt_num(qty), fmt_num(prc), fmt_num(s), "0%", "0,00", fmt_num(s)])
    total_row = ["Всего по накладной"] + [""]*7 + ["0", fmt_num(total_qty), "х", fmt_num(total_sum), "х", "0,00", fmt_num(total_sum)]
    data.append(total_row)
    goods_tbl = Table(data, colWidths=col_w, repeatRows=1)
    goods_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f0f0f0")),
        ("SPAN", (0, -1), (7, -1)),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (8, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    flow.append(goods_tbl)
    flow.append(Spacer(1, 1*mm))

    n_items = len(inv.items)
    records_word = "записей" if n_items >= 5 or (10 <= n_items % 100 <= 20) else "записи" if 2 <= n_items % 10 <= 4 else "запись"
    flow.append(Paragraph(f"Товарная накладная имеет приложение на ___ листах и содержит {n_items} порядковых номера {records_word}", fs7))
    flow.append(Paragraph("Масса груза (нетто) ___ прописью   Масса груза (брутто) ___ прописью   Всего мест ___ прописью", fs7))
    flow.append(Paragraph("Приложение (паспорта, сертификаты, и т.д.) на ___ листах   По доверенности № ___ выданной ___", fs7))
    amount_words = _amount_to_words_rub(total_sum)
    flow.append(Paragraph(f"Всего отпущено на сумму {amount_words}", fs8))
    flow.append(Spacer(1, 2*mm))

    sig_left = Table([
        ["Отпуск груза разрешил", "Руководитель организац.", ""],
        ["должность", "подпись", "расшифровка подписи"],
        ["Главный (старший) бухгалтер", "", ""],
        ["должность", "подпись", "расшифровка подписи"],
    ], colWidths=[50*mm, 35*mm, 35*mm])
    sig_right = Table([
        ["Груз принял", "", ""],
        ["должность", "подпись", "расшифровка подписи"],
        ["Груз получил грузополучатель", "", ""],
        ["должность", "подпись", "расшифровка подписи"],
    ], colWidths=[50*mm, 35*mm, 35*mm])
    for st in [sig_left, sig_right]:
        st.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
    sig_combined = Table([[sig_left, sig_right]], colWidths=[120*mm, 120*mm])
    sig_combined.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    flow.append(sig_combined)
    flow.append(Paragraph(f"Отпуск груза произвел ___ {doc_date.strftime('%d.%m.%Y')} г.   м.п.", fs7))
    doc.build(flow)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=f"torg12_{inv.invoice_number}.pdf")


@app.route("/counterparty/<int:counterparty_id>/payment/create", methods=["POST"])
@login_required
def payment_create(counterparty_id):
    """Внесение оплаты от контрагента."""
    if current_user.role not in ["Менеджер", "Админ"]:
        return jsonify({"ok": False, "error": "Доступ запрещен"}), 403
    Counterparty.query.get_or_404(counterparty_id)
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "error": "Укажите сумму"}), 400
    try:
        amount = float(data.get("amount") or 0)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Некорректная сумма"}), 400
    if amount <= 0:
        return jsonify({"ok": False, "error": "Сумма должна быть больше 0"}), 400
    payment_date_str = data.get("payment_date") or date.today().isoformat()
    try:
        payment_date = datetime.strptime(payment_date_str[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        payment_date = date.today()
    invoice_id = data.get("invoice_id")
    if invoice_id is not None:
        try:
            invoice_id = int(invoice_id)
        except (TypeError, ValueError):
            invoice_id = None
    p = Payment(counterparty_id=counterparty_id, amount=amount, payment_date=payment_date, invoice_id=invoice_id, note=(data.get("note") or "").strip() or None)
    db.session.add(p)
    db.session.commit()
    return jsonify({"ok": True, "payment_id": p.id})


@app.route("/counterparty/<int:counterparty_id>")
@login_required
def counterparty_card(counterparty_id):
    """Карточка контрагента: данные и текущие заказы с этапами производства."""
    if current_user.role not in ["Админ", "Менеджер"]:
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    cp = Counterparty.query.get_or_404(counterparty_id)
    orders = Order.query.filter(
        or_(Order.counterparty_id == counterparty_id, Order.client == cp.name)
    ).order_by(Order.due_date.asc()).all()
    _price_raw = PriceListItem.query.filter(PriceListItem.category.in_(PRICE_CATEGORIES)).order_by(PriceListItem.sort_order, PriceListItem.name).all()
    cat_order = {c: i for i, c in enumerate(PRICE_CATEGORIES)}
    price_list = sorted(_price_raw, key=lambda p: (cat_order.get(p.category, 0), p.sort_order or 0, p.name or ""))
    invoices = Invoice.query.filter(Invoice.counterparty_id == counterparty_id).order_by(Invoice.invoice_date.desc()).all()
    payments = Payment.query.filter(Payment.counterparty_id == counterparty_id).order_by(Payment.payment_date.desc()).all()
    total_invoiced = sum(inv.total for inv in invoices)
    total_paid = sum(p.amount for p in payments)
    balance = total_invoiced - total_paid
    for inv in invoices:
        inv.paid_amount = sum(p.amount for p in inv.payments)
        inv.balance = inv.total - inv.paid_amount
    return render_template("counterparty_card.html", counterparty=cp, orders=orders, price_list=price_list, price_categories=PRICE_CATEGORIES, invoices=invoices, payments=payments, total_invoiced=total_invoiced, total_paid=total_paid, balance=balance, datetime=datetime)


def render_admin_dashboard():
    """Рендеринг панели администратора"""
    if request.method == "POST":
        order_id = (request.form.get("order_id") or "").strip()
        client = (request.form.get("client") or "").strip()
        if not order_id or not client:
            flash("Заполните номер заказа и клиента", "error")
            return redirect(url_for("dashboard"))
        
        # Валидация входных данных
        try:
            days = int(request.form.get("days", 0))
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
                    os.remove(os.path.join(app.config["UPLOAD_FOLDER"], path))
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

    # Заказы для шлифовки: отфрезерованы, но не шпон (шпон не требует шлифовки)
    polishing_orders = Order.query.filter(
        Order.milling == True,
        Order.facade_type != "шпон",
        Order.shipment == False
    ).order_by(Order.due_date.asc()).all()
    
    # Заказы для упаковки: прошли шлифовку и не отгружены
    packaging_orders = Order.query.filter(
        Order.polishing_1 == True,
        Order.shipment == False
    ).order_by(Order.due_date.asc()).all()
    
    # Информация о срочности для заказов шлифовки
    polishing_urgency = {}
    for order in polishing_orders:
        days_left = (order.due_date - datetime.now(timezone.utc).date()).days
        polishing_urgency[order.id] = {
            'is_urgent': is_urgent_order(order),
            'days_left': days_left
        }
    
    # Информация о срочности для заказов упаковки
    packaging_urgency = {}
    for order in packaging_orders:
        days_left = (order.due_date - datetime.now(timezone.utc).date()).days
        packaging_urgency[order.id] = {
            'is_urgent': is_urgent_order(order),
            'days_left': days_left
        }
    
    return render_template("polishing.html", 
                          polishing_orders=polishing_orders,
                          packaging_orders=packaging_orders,
                          polishing_urgency=polishing_urgency,
                          packaging_urgency=packaging_urgency)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Маршрут для обслуживания загруженных файлов"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/health")
def health():
    """Проверка доступности приложения (для внешних пингов)"""
    return "ok", 200

@app.route("/warmup")
def warmup():
    """Лёгкий прогрев: обращаемся к БД и возвращаем краткий статус"""
    try:
        users = User.query.count()
        orders = Order.query.count()
        return jsonify({"status": "ok", "users": users, "orders": orders}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/admin/salary")
@login_required
def admin_salary():
    """Расчёт зарплат по периодам: 1–15 и 16–конец месяца. Выплаты: 10 числа — за 16–конец, 25 числа — за 1–15."""
    if current_user.role != "Админ":
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    
    try:
        now = datetime.now(timezone.utc)
        year = request.args.get("year", type=int) or now.year
        month = request.args.get("month", type=int) or now.month
        if month < 1 or month > 12:
            month = now.month
        if year < 2000 or year > 2100:
            year = now.year
        
        last_day = monthrange(year, month)[1]
        period1_start = date(year, month, 1)
        period1_end = date(year, month, 15)
        period2_start = date(year, month, 16)
        period2_end = date(year, month, last_day)
        
        employees = Employee.query.filter_by(is_active=True).all()
        rows = []
        for emp in employees:
            hours_first = db.session.query(db.func.coalesce(db.func.sum(WorkHours.hours), 0)).filter(
                WorkHours.employee_id == emp.id,
                WorkHours.date >= period1_start,
                WorkHours.date <= period1_end,
            ).scalar() or 0
            hours_second = db.session.query(db.func.coalesce(db.func.sum(WorkHours.hours), 0)).filter(
                WorkHours.employee_id == emp.id,
                WorkHours.date >= period2_start,
                WorkHours.date <= period2_end,
            ).scalar() or 0
            salary_first = round(float(hours_first) * emp.hourly_rate, 2)
            salary_second = round(float(hours_second) * emp.hourly_rate, 2)
            sp_first = SalaryPeriod.query.filter_by(
                employee_id=emp.id, year=year, month=month, period_type="first"
            ).first()
            sp_second = SalaryPeriod.query.filter_by(
                employee_id=emp.id, year=year, month=month, period_type="second"
            ).first()
            rows.append({
                "employee": emp,
                "hours_first": hours_first,
                "hours_second": hours_second,
                "salary_first": salary_first,
                "salary_second": salary_second,
                "is_paid_first": sp_first.is_paid if sp_first else False,
                "is_paid_second": sp_second.is_paid if sp_second else False,
                "paid_at_first": sp_first.paid_at if sp_first else None,
                "paid_at_second": sp_second.paid_at if sp_second else None,
            })
        
        month_names = ("", "январь", "февраль", "март", "апрель", "май", "июнь",
                       "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь")
        return render_template(
            "admin_salary.html",
            employees=employees,
            rows=rows,
            year=year,
            month=month,
            month_name=month_names[month],
            period1_start=period1_start,
            period1_end=period1_end,
            period2_start=period2_start,
            period2_end=period2_end,
        )
    except Exception as e:
        print(f"Ошибка в admin_salary: {e}")
        import traceback
        traceback.print_exc()
        flash("Ошибка при загрузке страницы зарплат", "error")
        return redirect(url_for("dashboard"))


@app.route("/admin/salary/mark_paid", methods=["POST"])
@login_required
def admin_salary_mark_paid():
    """Отметить период как выплаченный."""
    if current_user.role != "Админ":
        flash("Доступ запрещен", "error")
        return redirect(url_for("admin_salary"))
    try:
        employee_id = request.form.get("employee_id", type=int)
        year = request.form.get("year", type=int)
        month = request.form.get("month", type=int)
        period_type = request.form.get("period_type")  # "first" или "second"
        if not all([employee_id, year, month, period_type]) or period_type not in ("first", "second"):
            flash("Неверные данные", "error")
            return redirect(url_for("admin_salary", year=year, month=month))
        sp = SalaryPeriod.query.filter_by(
            employee_id=employee_id, year=year, month=month, period_type=period_type
        ).first()
        if sp:
            sp.is_paid = True
            sp.paid_at = datetime.now(timezone.utc)
        else:
            emp = Employee.query.get(employee_id)
            if not emp:
                flash("Сотрудник не найден", "error")
                return redirect(url_for("admin_salary", year=year, month=month))
            if period_type == "first":
                hours = db.session.query(db.func.coalesce(db.func.sum(WorkHours.hours), 0)).filter(
                    WorkHours.employee_id == employee_id,
                    WorkHours.date >= date(year, month, 1),
                    WorkHours.date <= date(year, month, 15),
                ).scalar() or 0
            else:
                last_day = monthrange(year, month)[1]
                hours = db.session.query(db.func.coalesce(db.func.sum(WorkHours.hours), 0)).filter(
                    WorkHours.employee_id == employee_id,
                    WorkHours.date >= date(year, month, 16),
                    WorkHours.date <= date(year, month, last_day),
                ).scalar() or 0
            salary = round(float(hours) * emp.hourly_rate, 2)
            sp = SalaryPeriod(
                employee_id=employee_id, year=year, month=month, period_type=period_type,
                total_hours=float(hours), total_salary=salary, is_paid=True,
                paid_at=datetime.now(timezone.utc),
            )
            db.session.add(sp)
        db.session.commit()
        flash("Отмечено как выплачено", "success")
        return redirect(url_for("admin_salary", year=year, month=month))
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка: {str(e)}", "error")
        return redirect(url_for("admin_salary", year=request.form.get("year"), month=request.form.get("month")))


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


@app.route("/admin/work-hours", methods=["GET", "POST"])
@login_required
def admin_work_hours():
    """Ввод рабочих часов по каждому дню двух периодов: 1–15 и 16–конец месяца."""
    if current_user.role != "Админ":
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    try:
        now = datetime.now(timezone.utc)
        year = request.args.get("year", type=int) or request.form.get("year", type=int) or now.year
        month = request.args.get("month", type=int) or request.form.get("month", type=int) or now.month
        if month < 1 or month > 12:
            month = now.month
        if year < 2000 or year > 2100:
            year = now.year
        last_day = monthrange(year, month)[1]
        period1_start = date(year, month, 1)
        period1_end = date(year, month, 15)
        period2_start = date(year, month, 16)
        period2_end = date(year, month, last_day)
        period1_dates = [date(year, month, d) for d in range(1, 16)]
        period2_dates = [date(year, month, d) for d in range(16, last_day + 1)]
        day_names = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
        employees = Employee.query.filter_by(is_active=True).all()
        selected_employee_id = request.args.get("employee_id", type=int) or request.form.get("employee_id", type=int)
        existing_by_date = {}
        if selected_employee_id:
            for wh in WorkHours.query.filter(
                WorkHours.employee_id == selected_employee_id,
                WorkHours.date >= period1_start,
                WorkHours.date <= period2_end,
            ).all():
                existing_by_date[wh.date] = wh
        if request.method == "POST" and selected_employee_id:
            all_dates = period1_dates + period2_dates
            for d in all_dates:
                key = f"hours_{d.strftime('%Y-%m-%d')}"
                value = request.form.get(key)
                notes = request.form.get(f"notes_{d.strftime('%Y-%m-%d')}", "").strip()
                try:
                    hours_val = float(value.strip().replace(",", ".")) if value and value.strip() else None
                except (ValueError, TypeError):
                    hours_val = None
                if hours_val is not None and hours_val < 0:
                    continue
                existing = WorkHours.query.filter_by(
                    employee_id=selected_employee_id, date=d
                ).first()
                if hours_val is None and not notes:
                    if existing:
                        db.session.delete(existing)
                    continue
                hours_to_save = (hours_val if hours_val is not None else 0.0)
                if existing:
                    existing.hours = hours_to_save
                    existing.notes = notes or None
                else:
                    db.session.add(WorkHours(
                        employee_id=selected_employee_id,
                        date=d,
                        hours=hours_to_save,
                        notes=notes or None,
                    ))
            db.session.commit()
            flash("Часы за периоды сохранены", "success")
            return redirect(url_for("admin_work_hours", year=year, month=month, employee_id=selected_employee_id))
        return render_template(
            "admin_work_hours.html",
            employees=employees,
            year=year,
            month=month,
            selected_employee_id=selected_employee_id,
            period1_dates=period1_dates,
            period2_dates=period2_dates,
            existing_by_date=existing_by_date,
            day_names=day_names,
            last_day=last_day,
        )
    except Exception as e:
        print(f"Ошибка в admin_work_hours: {e}")
        import traceback
        traceback.print_exc()
        flash("Ошибка при загрузке страницы рабочих часов", "error")
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
