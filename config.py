# config.py

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__)) 


def _make_database_uri():
    """Формирует URI для PostgreSQL (Render) с поддержкой SSL."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')

    # Исправляем старый формат postgres:// на postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    # Добавляем sslmode=require для Render PostgreSQL (исправляет SSL connection closed)
    sep = '&' if '?' in database_url else '?'
    if 'sslmode=' not in database_url.lower():
        database_url = database_url.rstrip('/') + f'{sep}sslmode=require'

    return database_url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-change-in-production'

    SQLALCHEMY_DATABASE_URI = _make_database_uri()

    # Реквизиты организации (продавца) для счёта на оплату
    COMPANY_NAME = os.environ.get('COMPANY_NAME') or 'Индивидуальный предприниматель Урядников Ярослав Юрьевич'
    COMPANY_INN = os.environ.get('COMPANY_INN') or '781136464040'
    COMPANY_KPP = os.environ.get('COMPANY_KPP') or ''
    COMPANY_ADDRESS = os.environ.get('COMPANY_ADDRESS') or '190000, Россия, г Санкт-Петербург, тел.'
    COMPANY_BANK = os.environ.get('COMPANY_BANK') or 'ФИЛИАЛ "САНКТ-ПЕТЕРБУРГСКИЙ" АО "АЛЬФА-БАНК", г Санкт-Петербург'
    COMPANY_BIK = os.environ.get('COMPANY_BIK') or '044030786'
    COMPANY_ACCOUNT = os.environ.get('COMPANY_ACCOUNT') or '40802810932390000451'
    COMPANY_CORR_ACCOUNT = os.environ.get('COMPANY_CORR_ACCOUNT') or '30101810600000000786'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

    # Настройки пула подключений для PostgreSQL на Render:
    # pool_pre_ping — проверка соединения перед использованием (переподключение при обрыве SSL)
    # pool_recycle — переподключение каждые 5 минут (избегаем "SSL connection closed")
    if os.environ.get('DATABASE_URL'):
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'connect_args': {
                'connect_timeout': 10,
                'sslmode': 'require',  # Дополнительно указываем SSL через connect_args
            },
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {}
    