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
    
    return render_template("dashboard.html", orders=orders, datetime=datetime)

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
    return render_template("admin_dashboard.html", orders=orders, datetime=datetime, current_user=current_user)

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
    
    employees = Employee.query.filter_by(is_active=True).all()
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Вычисляем данные по рабочим часам
    work_hours_data = calculate_work_hours_data(employees, current_year, current_month)
    
    return render_template("admin_salary.html", 
                         employees=employees,
                         work_hours_data=work_hours_data,
                         current_year=current_year)

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
            name = request.form.get("name")
            position = request.form.get("position")
            try:
                hourly_rate = float(request.form.get("hourly_rate", 0))
                if hourly_rate < 0:
                    raise ValueError("Часовая ставка не может быть отрицательной")
            except (ValueError, TypeError):
                flash("Неверная часовая ставка", "error")
                return redirect(url_for("admin_employees"))
            
            employee = Employee.query.get(employee_id)
            if employee:
                employee.name = name
                employee.position = position
                employee.hourly_rate = hourly_rate
                db.session.commit()
                flash(f"Сотрудник {name} обновлен", "success")
        
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
                         work_hours_data=work_hours_data)

@app.route("/admin/salary-report")
@login_required
def admin_salary_report():
    """Страница отчетов по зарплатам"""
    if current_user.role != "Админ":
        flash("Доступ запрещен", "error")
        return redirect(url_for("dashboard"))
    
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
                         work_hours_data=work_hours_data)

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
