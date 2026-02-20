/* Регистрация подписки на Web Push для уведомлений о заказах. PUSH_ENABLED должен быть true (для ролей кроме Менеджера). */
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
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
  navigator.serviceWorker.register('/sw.js', { scope: '/' }).then(function(reg) {
    return reg.pushManager.getSubscription().then(function(sub) {
      if (sub) return;
      return fetch('/api/push/vapid-public', { credentials: 'same-origin' }).then(function(r) {
        if (!r.ok) return;
        return r.json().then(function(d) {
          if (!d.publicKey) return;
          return reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(d.publicKey)
          }).then(function(subscription) {
            var j = subscription.toJSON();
            var payload = { endpoint: j.endpoint, keys: j.keys };
            return fetch('/api/push/subscribe', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'same-origin',
              body: JSON.stringify(payload)
            });
          });
        });
      });
    });
  }).catch(function() {});
})();
