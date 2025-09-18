# 🗄️ НАСТРОЙКА БАЗЫ ДАННЫХ НА RENDER

## ❌ Проблема
```
could not translate host name "dpg-d2vj30ur433s73c09er0-a" to address: Name or service not known
```

## ✅ Решение

### 1. Создайте базу данных PostgreSQL на Render

1. **Зайдите в Render Dashboard**
2. **Нажмите "New +" → "PostgreSQL"**
3. **Настройте базу данных:**
   - **Name**: `facade-orders-db`
   - **Database**: `facade_orders`
   - **User**: `facade_user`
   - **Region**: `Oregon (US West)`
   - **Plan**: `Free` (или платный)

### 2. Получите DATABASE_URL

После создания базы данных:
1. **Перейдите в настройки базы данных**
2. **Скопируйте "External Database URL"**
3. **Пример URL:**
   ```
   postgresql://facade_user:password@dpg-xxxxx-a.oregon-postgres.render.com/facade_orders
   ```

### 3. Настройте переменные окружения

В настройках вашего веб-сервиса на Render:
1. **Environment Variables**
2. **Добавьте:**
   - `DATABASE_URL` = ваш PostgreSQL URL
   - `SECRET_KEY` = любой секретный ключ

### 4. Обновите Build Command

В настройках веб-сервиса:
- **Build Command**: `pip install -r requirements.txt && python render_init_db.py`

### 5. Проверьте настройки

Убедитесь, что:
- ✅ **Python Version**: 3.11.9
- ✅ **Build Command**: `pip install -r requirements.txt && python render_init_db.py`
- ✅ **Start Command**: `gunicorn app:app`
- ✅ **DATABASE_URL** настроен правильно

### 6. Деплой

1. **Нажмите "Manual Deploy" → "Deploy latest commit"**
2. **Дождитесь завершения сборки**
3. **Проверьте логи на наличие ошибок**

## 🔍 Проверка

После успешного деплоя:
1. **Откройте ваше приложение**
2. **Попробуйте войти:**
   - **Логин**: `admin`
   - **Пароль**: `admin123`

## 🚨 Если не работает

1. **Проверьте логи** в Render Dashboard
2. **Убедитесь, что DATABASE_URL правильный**
3. **Проверьте, что база данных создана и доступна**
4. **Убедитесь, что Build Command выполнился без ошибок**

## 📝 Пример правильного DATABASE_URL

```
postgresql://facade_user:your_password@dpg-xxxxx-a.oregon-postgres.render.com/facade_orders
```

**Важно**: URL должен начинаться с `postgresql://`, а не `postgres://`
