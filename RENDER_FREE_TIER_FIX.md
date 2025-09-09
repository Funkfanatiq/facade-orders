# 🚀 Исправление проблем с бесплатным планом Render.com

## 🔍 Проблемы бесплатного плана:

1. **Перезагрузки**: Приложение "засыпает" после 15 минут неактивности
2. **Потеря данных**: SQLite база данных теряется при перезагрузке
3. **Ограничения**: 512MB RAM, 0.1 CPU, 750 часов/месяц

## 🛠️ Решения:

### Вариант 1: Настройка PostgreSQL (Рекомендуется)

#### Шаг 1: Создать PostgreSQL базу данных на Render
1. Зайдите в [Render Dashboard](https://dashboard.render.com)
2. Нажмите "New +" → "PostgreSQL"
3. Настройки:
   - **Name**: `facade-orders-db`
   - **Database**: `facade_orders`
   - **User**: `facade_user`
   - **Region**: `Frankfurt (EU Central)`
   - **Plan**: `Free` (0.5GB storage)
4. Нажмите "Create Database"

#### Шаг 2: Подключить базу к приложению
1. В настройках вашего веб-сервиса найдите "Environment"
2. Добавьте переменную окружения:
   - **Key**: `DATABASE_URL`
   - **Value**: Скопируйте из настроек PostgreSQL (Internal Database URL)

#### Шаг 3: Обновить приложение
```bash
# В Render Dashboard нажмите "Manual Deploy" → "Deploy latest commit"
```

### Вариант 2: Использование внешнего хранилища

#### Настройка Google Drive API (для файлов)
1. Создайте проект в [Google Cloud Console](https://console.cloud.google.com)
2. Включите Google Drive API
3. Создайте Service Account
4. Скачайте JSON ключ
5. Добавьте переменные окружения в Render:
   - `GOOGLE_DRIVE_CREDENTIALS` (содержимое JSON файла)
   - `GOOGLE_DRIVE_FOLDER_ID` (ID папки в Google Drive)

### Вариант 3: Оптимизация для бесплатного плана

#### Настройка Keep-Alive
Добавьте в `Procfile`:
```
web: python app.py
```

Создайте `keep_alive.py`:
```python
import requests
import time
import os

def keep_alive():
    url = os.environ.get('RENDER_URL', 'https://your-app.onrender.com')
    while True:
        try:
            requests.get(url, timeout=10)
            print("Keep-alive ping sent")
        except:
            print("Keep-alive failed")
        time.sleep(300)  # 5 минут

if __name__ == "__main__":
    keep_alive()
```

## 🔧 Дополнительные оптимизации:

### 1. Уменьшить размер приложения
```bash
# Удалить ненужные файлы
rm -rf __pycache__/
rm -rf migrations/versions/*.pyc
rm -rf uploads/*.log
```

### 2. Оптимизировать requirements.txt
```
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
Flask-Migrate==4.0.5
Werkzeug==2.3.7
psycopg2-binary==2.9.7
```

### 3. Настроить переменные окружения
В Render Dashboard → Environment:
```
SECRET_KEY=your-super-secret-key-here
DATABASE_URL=postgresql://user:pass@host:port/dbname
FLASK_ENV=production
```

## 🚨 Альтернативные платформы:

### 1. Railway.app
- Бесплатный план: $5 кредитов/месяц
- Постоянная база данных
- Автоматические деплои

### 2. Fly.io
- Бесплатный план: 3 приложения
- Постоянные тома
- Глобальная сеть

### 3. Heroku (платный)
- $7/месяц за базовый план
- Надежная инфраструктура
- Множество аддонов

## 📋 Пошаговая инструкция для Render + PostgreSQL:

1. **Создайте PostgreSQL базу** (как описано выше)
2. **Скопируйте Internal Database URL** из настроек базы
3. **Добавьте переменную окружения** `DATABASE_URL` в настройки веб-сервиса
4. **Перезапустите приложение** через Manual Deploy
5. **Проверьте работу** - данные должны сохраняться

## ✅ Проверка работы:

После настройки PostgreSQL:
- Создайте тестового пользователя
- Добавьте тестовый заказ
- Перезагрузите страницу
- Данные должны сохраниться

## 🆘 Если проблемы остаются:

1. Проверьте логи в Render Dashboard
2. Убедитесь, что `DATABASE_URL` правильно настроен
3. Проверьте, что PostgreSQL база активна
4. Рассмотрите переход на платный план ($7/месяц)

---

**Рекомендация**: Используйте PostgreSQL + бесплатный план Render для начала. Если нужна стабильность - переходите на платный план.

