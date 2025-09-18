# 🔧 ИСПРАВЛЕНИЕ БАЗЫ ДАННЫХ

## ❌ Проблема
```
relation "user" does not exist
```

## ✅ Решение

### Вариант 1: Автоматическое исправление
1. **Закоммитьте изменения:**
   ```bash
   git add .
   git commit -m "Fix database initialization"
   git push origin master
   ```

2. **На Render нажмите "Manual Deploy"**

### Вариант 2: Ручное исправление
1. **Зайдите в Render Dashboard**
2. **Перейдите в ваш веб-сервис**
3. **Нажмите "Shell" (Console)**
4. **Выполните команду:**
   ```bash
   python force_init_db.py
   ```

### Вариант 3: Изменить Build Command
В настройках Render измените:
- **Build Command**: `pip install -r requirements.txt && python init_database.py`

## 🎯 После исправления

Попробуйте войти:
- **Менеджер**: `manager` / `5678`
- **Админ**: `admin` / `admin123`

## 📋 Созданные файлы:
- `init_database.py` - надежная инициализация
- `force_init_db.py` - принудительная инициализация
- `Procfile` - обновлен для автоматической инициализации
