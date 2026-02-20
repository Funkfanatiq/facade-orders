/* Web Push для уведомлений о заказах. Вызов enablePushNotifications() по клику пользователя. */
(function() {
  if (window.PUSH_ENABLED !== true) return;

  function urlBase64ToUint8Array(base64String) {
    var padding = '='.repeat((4 - base64String.length % 4) % 4);
    var base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    var rawData = window.atob(base64);
    var outputArray = new Uint8Array(rawData.length);
    for (var i = 0; i < rawData.length; ++i) outputArray[i] = rawData.charCodeAt(i);
    return outputArray;
  }

  window.enablePushNotifications = function() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      alert('Ваш браузер не поддерживает push-уведомления');
      return;
    }
    if (!('Notification' in window)) {
      alert('Уведомления недоступны');
      return;
    }
    var btn = document.getElementById('btn-enable-push');
    if (btn) { btn.disabled = true; btn.textContent = 'Проверка...'; }
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).then(function(reg) {
      return reg.pushManager.getSubscription().then(function(sub) {
        if (sub) {
          if (btn) { btn.textContent = 'Уведомления включены'; }
          alert('Уведомления уже включены');
          return;
        }
        return Notification.requestPermission().then(function(perm) {
          if (perm !== 'granted') {
            if (btn) { btn.disabled = false; btn.textContent = 'Включить уведомления'; }
            if (perm === 'denied') alert('Разрешите уведомления в настройках браузера для этого сайта.');
            return;
          }
          if (btn) { btn.textContent = 'Загрузка...'; }
          return fetch('/api/push/vapid-public', { credentials: 'same-origin' }).then(function(r) {
            if (!r.ok) {
              if (btn) { btn.disabled = false; btn.textContent = 'Включить уведомления'; }
              alert('Уведомления не настроены на сервере (VAPID ключи)');
              return;
            }
            return r.json().then(function(d) {
              if (!d.publicKey) {
                if (btn) { btn.disabled = false; btn.textContent = 'Включить уведомления'; }
                return;
              }
              return reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(d.publicKey)
              }).then(function(subscription) {
                var j = subscription.toJSON();
                return fetch('/api/push/subscribe', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  credentials: 'same-origin',
                  body: JSON.stringify({ endpoint: j.endpoint, keys: j.keys })
                });
              }).then(function(res) {
                if (res && res.ok) {
                  if (btn) { btn.textContent = 'Включено'; }
                  alert('Уведомления включены. Вы будете получать оповещения о срочных заказах.');
                } else if (btn) {
                  btn.disabled = false;
                  btn.textContent = 'Включить уведомления';
                }
              });
            });
          });
        });
      });
    }).catch(function(err) {
      if (btn) { btn.disabled = false; btn.textContent = 'Включить уведомления'; }
      console.error('Push error:', err);
      alert('Ошибка: ' + (err.message || 'не удалось включить'));
    });
  };

  document.addEventListener('DOMContentLoaded', function() {
    if (!('Notification' in window)) return;
    var bar = document.querySelector('.top-bar > div') || document.querySelector('.top-bar .user-info');
    if (!bar) return;
    var btn = document.createElement('button');
    btn.id = 'btn-enable-push';
    btn.type = 'button';
    btn.textContent = 'Включить уведомления';
    btn.style.cssText = 'margin-left:12px;padding:6px 12px;font-size:13px;background:#4CAF50;color:#fff;border:none;border-radius:6px;cursor:pointer;';
    btn.onclick = enablePushNotifications;
    bar.insertBefore(btn, bar.firstChild);
  });
})();
