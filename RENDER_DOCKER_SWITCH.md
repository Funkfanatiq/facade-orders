# Как переключить facade-orders на Docker (для ТОРГ-12 из Excel-шаблона)

Render **не позволяет** менять Language/Runtime в Settings существующего сервиса. Нужно создать новый сервис с Docker.

## Способ: новый сервис с Docker

### 1. Откройте Render Dashboard
[ dashboard.render.com ](https://dashboard.render.com) → ваши сервисы.

### 2. Узнайте переменные окружения
Зайдите в текущий **facade-orders** → **Environment** → скопируйте все переменные (DATABASE_URL, SECRET_KEY и т.д.).

### 3. Создайте новый Web Service
- **New** → **Web Service**
- Подключите тот же репозиторий: **Funkfanatiq/facade-orders**
- **Branch**: main (или ваша ветка)

### 4. В форме создания
- **Name**: facade-orders-docker (или другое имя)
- **Region**: тот же, что и у БД (например Frankfurt)
- **Language**: выберите **Docker** в выпадающем списке
- **Instance Type**: Free (или тот же, что был)

### 5. Environment
- Добавьте те же переменные, что и у старого сервиса (DATABASE_URL, SECRET_KEY и др.)

### 6. Создание
- Нажмите **Create Web Service**
- Дождитесь деплоя (первые 5–10 минут из‑за LibreOffice)

### 7. Смена URL (если нужно)
- Новый URL будет типа `facade-orders-docker.onrender.com`
- Либо скопируйте Custom Domain с старого сервиса на новый
- Либо удалите старый **facade-orders** и создайте новый с именем **facade-orders**

---

## Альтернатива: Blueprint

Если в репозитории есть `render.yaml`:

1. **New** → **Blueprint**
2. Подключите репозиторий
3. Render создаст сервис по blueprint
4. Добавьте DATABASE_URL и SECRET_KEY в **Environment** созданного сервиса
