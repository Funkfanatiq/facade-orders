# 🚀 ЗАГРУЗКА ПРОЕКТА НА GITHUB

## 📋 Пошаговая инструкция

### 1. Установите Git
1. Перейдите на https://git-scm.com/download/win
2. Скачайте и установите Git для Windows
3. Перезапустите PowerShell после установки

### 2. Проверьте установку Git
```bash
git --version
```

### 3. Настройте Git (если еще не настроен)
```bash
git config --global user.name "Ваше Имя"
git config --global user.email "ваш@email.com"
```

### 4. Инициализируйте Git репозиторий
```bash
git init
```

### 5. Создайте .gitignore файл
```bash
# Конфиденциальные файлы
yandex_token.txt
sync_info.json
token.pickle
credentials.json

# База данных (только для локальной разработки)
database.db
*.db
*.sqlite
*.sqlite3
/instance/
/migrations/versions/

# Загруженные файлы
uploads/

# Локальные резервные копии
/backups/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
```

### 6. Добавьте файлы в Git
```bash
git add .
```

### 7. Создайте первый коммит
```bash
git commit -m "Initial commit: Facade Orders app for Render deployment"
```

### 8. Создайте репозиторий на GitHub
1. Перейдите на https://github.com/new
2. Название репозитория: `facade-orders`
3. Сделайте репозиторий **ПУБЛИЧНЫМ** (важно для бесплатного Render)
4. **НЕ** добавляйте README, .gitignore или лицензию
5. Нажмите "Create repository"

### 9. Подключите локальный репозиторий к GitHub
```bash
git remote add origin https://github.com/YOUR_USERNAME/facade-orders.git
git branch -M main
git push -u origin main
```

**Замените `YOUR_USERNAME` на ваш GitHub username!**

## 🎯 Альтернативный способ (автоматизация)

После установки Git запустите:
```bash
python connect_to_github.py
```

Скрипт автоматически:
- Проверит Git репозиторий
- Добавит remote origin
- Загрузит код на GitHub
- Откроет репозиторий в браузере

## ✅ Проверка

После загрузки ваш репозиторий будет доступен по адресу:
`https://github.com/YOUR_USERNAME/facade-orders`

## 🚀 Следующие шаги

После загрузки на GitHub:
1. Разверните проект на Render.com
2. Создайте базу данных PostgreSQL
3. Настройте переменные окружения
4. Инициализируйте базу данных

Подробные инструкции в файле: `FINAL_DEPLOYMENT_STEPS.md`

## 🆘 Устранение неполадок

### Git не найден
- Убедитесь, что Git установлен
- Перезапустите PowerShell
- Проверьте PATH переменную

### Ошибка аутентификации
- Используйте Personal Access Token вместо пароля
- Настройте SSH ключи для GitHub

### Репозиторий уже существует
- Удалите существующий репозиторий на GitHub
- Или используйте другое название

---

**🎉 После выполнения этих шагов ваш проект будет на GitHub!**


