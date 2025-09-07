# ⚡ БЫСТРОЕ ИСПРАВЛЕНИЕ ОШИБКИ RENDER

## 🚨 Проблема: SQLAlchemy Error
```
(Background on this error at: https://sqlalche.me/e/20/e3q8)
```

## 🔧 Быстрое решение:

### 1. Обновите код на GitHub
```bash
git add .
git commit -m "Fix SQLAlchemy error for Render deployment"
git push origin main
```

### 2. На Render выполните:
1. **Manual Deploy** → "Deploy latest commit"
2. **Откройте Shell** в настройках веб-сервиса
3. **Выполните команду:**
```bash
python render_init_db.py
```

### 3. Если не помогло:
```bash
python create_migration.py
```

## ✅ Готово!

После выполнения этих шагов:
- Ошибка SQLAlchemy исправлена
- База данных инициализирована
- Тестовые аккаунты созданы

## 🔑 Тестовые аккаунты:
- **Админ:** `admin` / `admin123`
- **Менеджер:** `manager` / `manager123`
- **Фрезеровка:** `frez` / `frez123`
- **Шлифовка:** `shlif` / `shlif123`
- **Производство:** `prod` / `prod123`
- **Монитор:** `monitor` / `monitor123`

---

**🎉 Приложение должно работать без ошибок!**
