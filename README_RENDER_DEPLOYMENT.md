# 🚀 РАЗВЕРТЫВАНИЕ НА RENDER.COM

## 📦 Готовые файлы для развертывания

У вас есть все необходимое для развертывания на Render.com:

### 📋 Документация
- **`RENDER_QUICK_START.md`** - Быстрый старт (3 шага)
- **`RENDER_DEPLOY.md`** - Полное руководство
- **`README_RENDER_DEPLOYMENT.md`** - Этот файл

### 🛠️ Скрипты автоматизации
- **`deploy_to_render.py`** - Автоматизация подготовки к развертыванию

### 📦 Готовые файлы
- **`requirements.txt`** - Зависимости Python
- **`Procfile`** - Команда запуска для Render
- **`init_db.py`** - Инициализация базы данных
- **`config.py`** - Конфигурация приложения
- **`app.py`** - Основное приложение
- **`models.py`** - Модели базы данных
- **`templates/`** - HTML шаблоны
- **`static/`** - Статические файлы

## 🚀 Быстрый старт (3 шага)

### 1. Подготовьте GitHub репозиторий
```bash
# Запустите автоматизацию
python deploy_to_render.py

# Или вручную:
git init
git add .
git commit -m "Initial commit: Facade Orders app"
# Создайте репозиторий на GitHub и подключите его
```

### 2. Создайте базу данных PostgreSQL
1. Войдите в [render.com](https://render.com)
2. Нажмите "New +" → "PostgreSQL"
3. Настройте:
   - **Name:** `facade-orders-db`
   - **Plan:** `Free`
   - **Region:** `Oregon (US West)`
4. Сохраните **External Database URL**

### 3. Создайте веб-сервис
1. Нажмите "New +" → "Web Service"
2. Подключите GitHub репозиторий
3. Настройте:
   - **Name:** `facade-orders-app`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
4. Добавьте переменные окружения:
   ```
   SECRET_KEY=your-super-secret-key-here-change-this-2024
   DATABASE_URL=postgresql://username:password@host:port/database
   RENDER=true
   ```

## ✅ Что вы получите

- 🖥️ **Бесплатный хостинг** на Render.com
- 🗄️ **PostgreSQL** база данных
- 🔄 **Автоматические деплои** из GitHub
- 🔒 **HTTPS** сертификат
- 📊 **Мониторинг** и логи
- 💰 **БЕСПЛАТНО** навсегда!

## 🔐 Тестовые аккаунты

После инициализации базы данных будут созданы:
- **Администратор:** `admin` / `admin123`
- **Менеджер:** `manager` / `manager123`
- **Фрезеровка:** `frez` / `frez123`
- **Шлифовка:** `shlif` / `shlif123`
- **Производство:** `prod` / `prod123`
- **Монитор:** `monitor` / `monitor123`

## 🔧 Управление приложением

### Обновление кода
```bash
# Внесите изменения в код
git add .
git commit -m "Update app"
git push origin main
# Render автоматически пересоберет приложение
```

### Просмотр логов
1. В панели Render перейдите в ваш веб-сервис
2. Откройте раздел "Logs"
3. Просматривайте логи в реальном времени

### Инициализация базы данных
После первого деплоя выполните в Render Shell:
```bash
python init_db.py
```

## 🆘 Устранение неполадок

### Приложение не запускается
1. Проверьте логи в панели Render
2. Убедитесь, что все переменные окружения настроены
3. Проверьте, что база данных PostgreSQL создана

### Ошибки базы данных
1. Проверьте переменную `DATABASE_URL`
2. Убедитесь, что база данных PostgreSQL активна
3. Выполните инициализацию: `python init_db.py`

### Проблемы с зависимостями
1. Проверьте `requirements.txt`
2. Убедитесь, что все зависимости указаны
3. Проверьте логи сборки

## 💰 Стоимость

### Бесплатный план
- **Веб-сервис:** 750 часов в месяц
- **PostgreSQL:** 1 ГБ хранилища
- **Автоматические деплои** из GitHub
- **HTTPS** сертификат

### Платные планы
- **Starter:** $7/месяц - без ограничений по времени
- **Standard:** $25/месяц - больше ресурсов

## 🔒 Безопасность

### После развертывания
1. **Измените пароли** по умолчанию
2. **Используйте сильный SECRET_KEY**
3. **HTTPS** включен по умолчанию
4. **Регулярно обновляйте** зависимости

## 📞 Поддержка

### Полезные ссылки
- **Render Documentation:** https://render.com/docs
- **Render Support:** https://render.com/support
- **GitHub:** https://github.com

### Контакты
- **Render Support:** через панель управления
- **GitHub Support:** https://support.github.com

---
**🎉 Готово к развертыванию на Render.com!**


