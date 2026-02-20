# Web Push — уведомления о заказах по сроку

## Что делает

- **«Заказ №X пора брать в работу»** — когда до срока 4–7 дней
- **«Заказ №X срочный»** — когда до срока ≤3 дней

Уведомления получают все пользователи **кроме Менеджера** (Админ, Производство, Фрезеровка, Шлифовка, Монитор).

## Настройка

### 1. Генерация VAPID-ключей

```bash
pip install py-vapid
python -c "
from vapid import Vapid
import base64
v = Vapid()
v.generate_keys()
print('VAPID_PRIVATE_KEY=')
print(v.private_key.decode())
print()
pub = base64.urlsafe_b64encode(v.public_key).decode().rstrip('=')
print('VAPID_PUBLIC_KEY=')
print(pub)
"
```

Сохраните вывод в переменные окружения (`.env` локально или Environment Variables в Render).

### 2. Переменные окружения

- `VAPID_PRIVATE_KEY` — приватный ключ (PEM)
- `VAPID_PUBLIC_KEY` — публичный ключ (base64url)
- `CRON_PUSH_KEY` — секретный ключ для вызова `/internal/push-check` (при желании)

### 3. Cron для проверки заказов (Render)

Добавьте **Cron Job** в Render:

- **Command:** `curl -s "https://ВАШ-СЕРВИС.onrender.com/internal/push-check?key=ВАШ_CRON_PUSH_KEY"`
- **Schedule:** `0 * * * *` (каждый час)

Если `CRON_PUSH_KEY` не задан, проверка будет доступна без авторизации (не рекомендуется в production).

### 4. Подписка пользователей

Пользователи (кроме Менеджера) видят кнопку **«Включить уведомления»** в шапке страницы. Нужно нажать её — браузер запросит разрешение, после подтверждения подписка сохранится.

Важно: без клика по кнопке запрос разрешения не показывается (ограничение браузеров).
