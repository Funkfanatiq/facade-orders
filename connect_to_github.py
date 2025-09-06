#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для подключения локального репозитория к GitHub
"""

import subprocess
import sys
import webbrowser

def run_git_command(command):
    """Выполняет Git команду"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def main():
    """Основная функция"""
    print("🔗 ПОДКЛЮЧЕНИЕ К GITHUB")
    print("=" * 30)
    
    # Получаем GitHub username
    username = input("Введите ваш GitHub username: ").strip()
    if not username:
        print("❌ Username не может быть пустым")
        return
    
    # Получаем название репозитория
    repo_name = input("Введите название репозитория (по умолчанию: facade-orders): ").strip()
    if not repo_name:
        repo_name = "facade-orders"
    
    print(f"\n📋 Подключаемся к репозиторию: {username}/{repo_name}")
    
    # Проверяем, что мы в Git репозитории
    success, output = run_git_command("git status")
    if not success:
        print("❌ Это не Git репозиторий. Сначала инициализируйте Git.")
        return
    
    # Добавляем remote origin
    remote_url = f"https://github.com/{username}/{repo_name}.git"
    print(f"🔗 Добавляем remote origin: {remote_url}")
    
    success, output = run_git_command(f"git remote add origin {remote_url}")
    if not success:
        if "already exists" in output:
            print("⚠️ Remote origin уже существует. Обновляем...")
            run_git_command(f"git remote set-url origin {remote_url}")
        else:
            print(f"❌ Ошибка добавления remote: {output}")
            return
    
    # Переименовываем ветку в main
    print("🌿 Переименовываем ветку в main...")
    success, output = run_git_command("git branch -M main")
    if not success:
        print(f"❌ Ошибка переименования ветки: {output}")
        return
    
    # Загружаем код на GitHub
    print("📤 Загружаем код на GitHub...")
    success, output = run_git_command("git push -u origin main")
    if not success:
        print(f"❌ Ошибка загрузки: {output}")
        print("\n💡 Возможные решения:")
        print("1. Убедитесь, что репозиторий создан на GitHub")
        print("2. Проверьте, что репозиторий публичный")
        print("3. Убедитесь, что у вас есть права на запись")
        return
    
    print("✅ Код успешно загружен на GitHub!")
    print(f"🌐 Репозиторий доступен по адресу: https://github.com/{username}/{repo_name}")
    
    # Открываем репозиторий в браузере
    response = input("\nОткрыть репозиторий в браузере? (y/n): ")
    if response.lower() in ['y', 'yes', 'да', 'д']:
        webbrowser.open(f"https://github.com/{username}/{repo_name}")
        print("✅ Репозиторий открыт в браузере")
    
    print("\n🎉 ПОДКЛЮЧЕНИЕ К GITHUB ЗАВЕРШЕНО!")
    print("=" * 30)
    print("📋 Следующие шаги:")
    print("1. Создайте базу данных PostgreSQL на Render")
    print("2. Создайте веб-сервис на Render")
    print("3. Настройте переменные окружения")
    print("4. Инициализируйте базу данных")
    print("\n📖 Подробные инструкции в файле: FINAL_DEPLOYMENT_STEPS.md")

if __name__ == "__main__":
    main()

