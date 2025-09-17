# 🚀 Инструкция по деплою

## ✅ Проект готов к деплою!

### 📋 Основные файлы:
- `app.py` - основное приложение
- `models.py` - модели базы данных
- `config.py` - конфигурация
- `requirements.txt` - зависимости (psycopg2-binary)
- `runtime.txt` - Python 3.11.9
- `Procfile` - команда запуска

### 🔧 Настройки Render.com:

1. **Build Command**: `pip install -r requirements.txt`
2. **Start Command**: `gunicorn app:app`
3. **Python Version**: 3.11.10 (ВАЖНО!)
4. **Buildpack**: `https://github.com/heroku/heroku-buildpack-python`

### 🚨 Если Python 3.13:
Измените Build Command на: `pip install -r requirements_python313.txt`

### 📊 Переменные окружения:
- `SECRET_KEY` - секретный ключ
- `DATABASE_URL` - URL PostgreSQL базы данных

### 🎯 Готово!
Проект очищен от лишних файлов и готов к деплою.

### 🔧 Исправления:
- ✅ Исправлена версия psycopg2-binary (2.9.9)
- ✅ Настроен Python 3.11.9
- ✅ Удалены все лишние файлы
- ✅ Оставлены только необходимые файлы для деплоя
