# 🚀 РУЧНОЕ РАЗВЕРТЫВАНИЕ НА RENDER.COM

## 📦 Пакет готов к развертыванию!

### 1. Загрузите код в GitHub

**Вариант A: Через веб-интерфейс GitHub**
1. Перейдите на https://github.com
2. Нажмите "New repository"
3. Назовите репозиторий: `facade-orders`
4. НЕ добавляйте README, .gitignore или лицензию
5. Нажмите "Create repository"
6. Нажмите "uploading an existing file"
7. Загрузите файл `facade-orders-deploy.zip`
8. Распакуйте архив в репозиторий
9. Нажмите "Commit changes"

**Вариант B: Через Git (если установлен)**
```bash
# Распакуйте архив
unzip facade-orders-deploy.zip
cd facade-orders-deploy

# Инициализируйте Git
git init
git add .
git commit -m "Initial commit"

# Добавьте remote и загрузите
git remote add origin https://github.com/YOUR_USERNAME/facade-orders.git
git push -u origin main
```

### 2. Создайте PostgreSQL базу данных

1. Войдите в https://render.com
2. Нажмите "New +" → "PostgreSQL"
3. Настройки:
   - **Name:** `facade-orders-db`
   - **Database:** `facade_orders`
   - **User:** `facade_user`
   - **Region:** выберите ближайший
   - **Plan:** Free (для тестирования)
4. Нажмите "Create Database"
5. **Скопируйте DATABASE_URL** из настроек базы данных

### 3. Создайте Web Service

1. Нажмите "New +" → "Web Service"
2. Подключите ваш GitHub репозиторий
3. Настройки:
   - **Name:** `facade-orders-app`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`

### 4. Настройте переменные окружения

В настройках Web Service добавьте:

```
SECRET_KEY=your-super-secret-key-here-change-this-to-random-string
DATABASE_URL=postgresql://username:password@host:port/database
RENDER=true
```

**Важно:** 
- Замените `SECRET_KEY` на случайную строку (например: `Kj8#mN2$pL9@qR4&vX7!wE3%tY6*uI1^oP5`)
- Замените `DATABASE_URL` на реальный URL из настроек PostgreSQL базы данных

### 5. Инициализируйте базу данных

После первого деплоя выполните инициализацию:

**Вариант A: Через Render Shell**
1. В настройках Web Service найдите "Shell"
2. Выполните команду: `python init_db.py`

**Вариант B: Через Build Command**
Измените Build Command на:
```
pip install -r requirements.txt && python init_db.py
```

### 6. Проверьте развертывание

После успешного деплоя приложение будет доступно по адресу:
`https://your-app-name.onrender.com`

### 🔐 Тестовые аккаунты

После инициализации базы данных будут созданы:

- **Администратор:** `admin` / `admin123`
- **Менеджер:** `manager` / `manager123`
- **Фрезеровка:** `frez` / `frez123`
- **Шлифовка:** `shlif` / `shlif123`
- **Производство:** `prod` / `prod123`
- **Монитор:** `monitor` / `monitor123`

### 🆘 Устранение неполадок

**Проблема:** Ошибка при деплое
**Решение:** Проверьте логи в панели Render

**Проблема:** База данных не инициализирована
**Решение:** Выполните `python init_db.py` через Shell

**Проблема:** Ошибка 500
**Решение:** Проверьте переменные окружения

**Проблема:** Приложение не запускается
**Решение:** Убедитесь, что Start Command: `gunicorn app:app`

### 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи в панели Render
2. Убедитесь, что все переменные окружения настроены
3. Проверьте, что база данных инициализирована
4. Убедитесь, что все файлы загружены в GitHub

### 🎯 Быстрый старт

1. **Загрузите** `facade-orders-deploy.zip` в GitHub
2. **Создайте** PostgreSQL базу данных на Render
3. **Создайте** Web Service на Render
4. **Настройте** переменные окружения
5. **Инициализируйте** базу данных
6. **Готово!** Приложение работает

---
**Создано:** Автоматически для развертывания на Render.com



