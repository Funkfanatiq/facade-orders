#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для поддержания активности приложения на Render.com
Предотвращает "засыпание" приложения на бесплатном плане
"""

import requests
import time
import os
import threading
from datetime import datetime

def ping_app():
    """Отправляет ping на приложение"""
    try:
        # Получаем URL приложения из переменных окружения
        app_url = os.environ.get('RENDER_EXTERNAL_URL')
        if not app_url:
            # Если нет переменной, используем стандартный URL Render
            app_name = os.environ.get('RENDER_SERVICE_NAME', 'facade-orders')
            app_url = f"https://{app_name}.onrender.com"
        
        # Отправляем GET запрос на главную страницу
        response = requests.get(f"{app_url}/login", timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Keep-alive ping успешен: {datetime.now().strftime('%H:%M:%S')}")
        else:
            print(f"⚠️  Keep-alive ping неуспешен: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка keep-alive ping: {str(e)}")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {str(e)}")

def keep_alive_loop():
    """Основной цикл keep-alive"""
    print("🔄 Запуск keep-alive сервиса...")
    print("📡 Приложение будет пинговаться каждые 5 минут")
    
    while True:
        try:
            ping_app()
            # Ждем 5 минут (300 секунд)
            time.sleep(300)
        except KeyboardInterrupt:
            print("🛑 Keep-alive сервис остановлен")
            break
        except Exception as e:
            print(f"❌ Ошибка в keep-alive цикле: {str(e)}")
            time.sleep(60)  # Ждем минуту перед повтором

def start_keep_alive():
    """Запускает keep-alive в отдельном потоке"""
    # Проверяем, нужно ли запускать keep-alive
    if os.environ.get('RENDER') == 'true':
        # Запускаем только на Render
        keep_alive_thread = threading.Thread(target=keep_alive_loop, daemon=True)
        keep_alive_thread.start()
        print("🚀 Keep-alive сервис запущен в фоновом режиме")
    else:
        print("ℹ️  Keep-alive не нужен (не на Render)")

if __name__ == "__main__":
    print("🔄 KEEP-ALIVE СЕРВИС ДЛЯ RENDER.COM")
    print("=" * 40)
    keep_alive_loop()

