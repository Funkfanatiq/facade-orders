# 🎯 ФИНАЛЬНОЕ РЕШЕНИЕ ДЛЯ RENDER

## ❌ ТЕКУЩАЯ ПРОБЛЕМА
```
could not translate host name "dpg-d2vj30ur433s73c09er0-a" to address: Name or service not known
```

## ✅ РЕШЕНИЕ

### 1. Создайте базу данных PostgreSQL на Render

1. **Зайдите в Render Dashboard**
2. **Нажмите "New +" → "PostgreSQL"**
3. **Настройте базу данных:**
   - **Name**: `facade-orders-db`
   - **Database**: `facade_orders`
   - **User**: `facade_user`
   - **Region**: `Oregon (US West)`
   - **Plan**: `Free`

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

### 4. Настройки Render.com:

1. **Build Command**: `pip install -r requirements.txt`
2. **Start Command**: `gunicorn app:app`
3. **Python Version**: 3.11.9 (в настройках Render)

### 🔧 Файлы проекта:
- `requirements.txt` - psycopg2-binary для Python 3.11
- `runtime.txt` - Python 3.11.9
- `.python-version` - Python 3.11.9
- `config.py` - правильная конфигурация PostgreSQL
- `render_init_db.py` - инициализация базы данных
- `Procfile` - запуск с инициализацией БД

### 🎯 Готово к деплою!

1. Закоммитьте изменения: `git add . && git commit -m "Database setup fix"`
2. Отправьте на GitHub: `git push origin master`
3. На Render нажмите "Manual Deploy" → "Deploy latest commit"

### 🎉 Ожидаемый результат:
- ✅ Python 3.11.9 будет использоваться
- ✅ psycopg2-binary установится без ошибок
- ✅ База данных PostgreSQL подключится
- ✅ Таблицы создадутся автоматически
- ✅ Пользователи создадутся:
  - **Администратор**: admin / admin123
  - **Менеджер**: manager / 5678
  - **Производство**: worker / 0000
  - **Фрезеровка**: cutter / 7777
  - **Шлифовка**: polisher / 8888
  - **Монитор**: monitor / 9999
