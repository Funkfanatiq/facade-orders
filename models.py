# models.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

# Возможные типы фасадов
facade_choices = ["фрезерованный", "плоский", "шпон"]

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
    client     = db.Column(db.String(128), nullable=False)
    days       = db.Column(db.Integer, nullable=False)
    due_date   = db.Column(db.Date, nullable=False)

    milling    = db.Column(db.Boolean, default=False)
    polishing_1 = db.Column(db.Boolean, default=False)
    packaging  = db.Column(db.Boolean, default=False)
    shipment   = db.Column(db.Boolean, default=False)
    paid       = db.Column(db.Boolean, default=False)

    filenames  = db.Column(db.Text)  # Пример: "чертёж.pdf;заметка.txt"
    filepaths  = db.Column(db.Text)  # Пример: "uploads/чертёж.pdf;uploads/заметка.txt"

    facade_type = db.Column(db.String(32), nullable=True)  # фрезерованный / плоский / шпон
    area        = db.Column(db.Float, nullable=True)       # площадь в м²

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

class Email(db.Model):
    """Модель для хранения писем"""
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.String(255), unique=True, nullable=True)  # ID письма от почтового сервера
    subject = db.Column(db.String(255), nullable=False)
    sender = db.Column(db.String(255), nullable=False)
    recipient = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=True)
    html_body = db.Column(db.Text, nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    is_sent = db.Column(db.Boolean, default=False)  # True для исходящих, False для входящих
    reply_to_id = db.Column(db.Integer, db.ForeignKey('email.id'), nullable=True)  # ID письма, на которое отвечаем
    created_at = db.Column(db.DateTime, default=db.func.now())
    sent_at = db.Column(db.DateTime, nullable=True)
    
    # Связь для ответов
    reply_to = db.relationship('Email', remote_side=[id], backref='replies')

class EmailAttachment(db.Model):
    """Модель для вложений в письма"""
    id = db.Column(db.Integer, primary_key=True)
    email_id = db.Column(db.Integer, db.ForeignKey('email.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    content_type = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    # Связь с письмом
    email = db.relationship('Email', backref=db.backref('attachments', lazy=True))
