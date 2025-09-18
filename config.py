ну# config.py

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__)) 

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-change-in-production'
    
    # Поддержка PostgreSQL для Render.com
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Исправляем старый формат postgres:// на postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        # Fallback на SQLite для локальной разработки
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
