# models.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

# Возможные типы фасадов (смешанный — с подтипами: плоский, фрезерованный, шпон)
facade_choices = ["фрезерованный", "плоский", "шпон", "смешанный"]

class User(db.Model, UserMixin):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Увеличили размер для scrypt хешей
    role     = db.Column(db.String(32), nullable=False)
    
    @staticmethod
    def hash_password(password):
        """Хеширование пароля"""
        from werkzeug.security import generate_password_hash
        return generate_password_hash(password)

class Order(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.String(64), nullable=False)
    invoice_number = db.Column(db.String(32), nullable=True)  # № счёта — привязка к выставленному счёту
    client     = db.Column(db.String(128), nullable=False)
    counterparty_id = db.Column(db.Integer, db.ForeignKey('counterparty.id'), nullable=True)  # связь с контрагентом
    days       = db.Column(db.Integer, nullable=False)
    due_date   = db.Column(db.Date, nullable=False)

    milling    = db.Column(db.Boolean, default=False)
    polishing_1 = db.Column(db.Boolean, default=False)
    packaging  = db.Column(db.Boolean, default=False)
    shipment   = db.Column(db.Boolean, default=False)
    paid       = db.Column(db.Boolean, default=False)

    filenames  = db.Column(db.Text)  # Пример: "чертёж.pdf;заметка.txt"
    filepaths  = db.Column(db.Text)  # Пример: "uploads/чертёж.pdf;uploads/заметка.txt"

    facade_type = db.Column(db.String(32), nullable=True)  # фрезерованный / плоский / шпон / смешанный
    area        = db.Column(db.Float, nullable=True)       # площадь в м² (для смешанного — сумма)
    mixed_facade_data = db.Column(db.Text, nullable=True)  # JSON: [{"type":"плоский","area":1.5,"thickness":18},...]

    counterparty = db.relationship('Counterparty', backref=db.backref('orders', lazy=True))

class Employee(db.Model):
    """Модель сотрудника"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    position = db.Column(db.String(64), nullable=False)  # Должность
    hourly_rate = db.Column(db.Float, nullable=False, default=0.0)  # Часовая ставка
    is_active = db.Column(db.Boolean, default=True)  # Активен ли сотрудник
    created_at = db.Column(db.DateTime, default=db.func.now())

class WorkHours(db.Model):
    """Модель рабочих часов"""
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Float, nullable=False, default=0.0)  # Количество часов
    notes = db.Column(db.Text)  # Заметки о работе
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    # Связь с сотрудником
    employee = db.relationship('Employee', backref=db.backref('work_hours', lazy=True))

class SalaryPeriod(db.Model):
    """Модель для отслеживания выплат по периодам"""
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    period_type = db.Column(db.String(10), nullable=False)  # 'first' (1-15) или 'second' (16-31)
    total_hours = db.Column(db.Float, nullable=False, default=0.0)
    total_salary = db.Column(db.Float, nullable=False, default=0.0)
    is_paid = db.Column(db.Boolean, default=False)  # Выплачено ли
    paid_at = db.Column(db.DateTime, nullable=True)  # Дата выплаты
    notes = db.Column(db.Text)  # Заметки о выплате
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    # Связь с сотрудником
    employee = db.relationship('Employee', backref=db.backref('salary_periods', lazy=True))
    
    # Уникальный индекс для предотвращения дублирования периодов
    __table_args__ = (db.UniqueConstraint('employee_id', 'year', 'month', 'period_type', name='unique_salary_period'),)


class Counterparty(db.Model):
    """Контрагент (заказчик/поставщик)."""
    id = db.Column(db.Integer, primary_key=True)
    # Блок 1: контактные данные
    name = db.Column(db.String(256), nullable=False)  # Имя
    phone = db.Column(db.String(64), nullable=True)  # Телефон
    email = db.Column(db.String(256), nullable=True)  # Электронный адрес
    # Блок 2: реквизиты
    counterparty_type = db.Column(db.String(16), nullable=True)  # юр лицо / физ лицо
    inn = db.Column(db.String(20), nullable=True)  # ИНН
    full_name = db.Column(db.String(512), nullable=True)  # Полное наименование
    legal_address = db.Column(db.String(512), nullable=True)  # Юридический адрес
    fias_code = db.Column(db.String(64), nullable=True)  # Код ФИАС
    kpp = db.Column(db.String(20), nullable=True)  # КПП
    ogrn = db.Column(db.String(20), nullable=True)  # ОГРН
    okpo = db.Column(db.String(20), nullable=True)  # ОКПО
    bik = db.Column(db.String(20), nullable=True)  # БИК
    bank = db.Column(db.String(256), nullable=True)  # Банк
    address = db.Column(db.String(512), nullable=True)  # Адрес
    corr_account = db.Column(db.String(34), nullable=True)  # Корр. счёт
    payment_account = db.Column(db.String(34), nullable=True)  # Расчётный счёт
    created_at = db.Column(db.DateTime, default=db.func.now())

    # orders — обратная связь через Order.counterparty_id


# Категории прайс-листа (как типы фасадов)
PRICE_CATEGORIES = ["плоский", "фрезерованный", "шпон", "услуги по покраске", "Доп услуги"]


class PriceListItem(db.Model):
    """Позиция прайс-листа."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)   # Наименование
    price = db.Column(db.Float, nullable=False)       # Цена
    unit = db.Column(db.String(32), nullable=True)     # Ед. изм. (шт, м², п.м. и т.д.)
    category = db.Column(db.String(32), nullable=True)  # плоский / фрезерованный / шпон
    sort_order = db.Column(db.Integer, default=0)      # Порядок отображения внутри категории
    note = db.Column(db.String(512), nullable=True)    # Примечание
    created_at = db.Column(db.DateTime, default=db.func.now())


class Invoice(db.Model):
    """Счёт на оплату."""
    id = db.Column(db.Integer, primary_key=True)
    counterparty_id = db.Column(db.Integer, db.ForeignKey('counterparty.id'), nullable=False)
    invoice_number = db.Column(db.String(32), nullable=False)  # Номер счёта
    invoice_date = db.Column(db.Date, nullable=False)
    order_ids = db.Column(db.String(256), nullable=True)  # Номера заказов через запятую (для отображения "по каким заказам")
    created_at = db.Column(db.DateTime, default=db.func.now())
    counterparty = db.relationship('Counterparty', backref=db.backref('invoices', lazy=True))

    @property
    def total(self):
        return sum(it.quantity * it.price for it in self.items)


class Payment(db.Model):
    """Оплата от контрагента."""
    id = db.Column(db.Integer, primary_key=True)
    counterparty_id = db.Column(db.Integer, db.ForeignKey('counterparty.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=True)  # Привязка к счёту (если указан)
    note = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    counterparty = db.relationship('Counterparty', backref=db.backref('payments', lazy=True))
    invoice = db.relationship('Invoice', backref=db.backref('payments', lazy=True))


class InvoiceItem(db.Model):
    """Позиция счёта (из прайса или вручную)."""
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    name = db.Column(db.String(512), nullable=False)   # Наименование
    unit = db.Column(db.String(32), nullable=True)     # Ед. изм.
    quantity = db.Column(db.Float, nullable=False, default=1.0)
    price = db.Column(db.Float, nullable=False)       # Цена за ед.
    price_list_item_id = db.Column(db.Integer, db.ForeignKey('price_list_item.id'), nullable=True)  # Ссылка на прайс или NULL для ручных
    invoice = db.relationship('Invoice', backref=db.backref('items', lazy=True, cascade='all, delete-orphan'))

