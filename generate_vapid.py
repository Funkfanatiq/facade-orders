#!/usr/bin/env python3
"""Генерация VAPID-ключей для Web Push. Запуск: python generate_vapid.py"""
import subprocess
import os
import sys

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    # vapid может быть в venv/bin
    vapid_cmd = os.path.join(os.path.dirname(sys.executable), "vapid")
    if not os.path.isfile(vapid_cmd):
        vapid_cmd = "vapid"
    try:
        result = subprocess.run(
            [vapid_cmd, "--gen"],
            capture_output=True, text=True, cwd=base
        )
        if result.returncode != 0:
            # Пробуем через python -m
            result = subprocess.run(
                [sys.executable, "-m", "vapid", "--gen"],
                capture_output=True, text=True, cwd=base
            )
        if result.returncode != 0:
            print("Ошибка. Установите: pip install -r requirements.txt")
            return

        # Читаем сгенерированные файлы
        with open(os.path.join(base, "private_key.pem")) as f:
            priv = f.read().strip()
        with open(os.path.join(base, "public_key.pem")) as f:
            pub_pem = f.read()

        # Получаем Application Server Key (base64url для браузера)
        r2 = subprocess.run(
            [vapid_cmd, "--applicationServerKey"],
            capture_output=True, text=True, cwd=base
        )
        if r2.returncode != 0:
            r2 = subprocess.run(
                [sys.executable, "-m", "vapid", "--applicationServerKey"],
                capture_output=True, text=True, cwd=base
            )
        pub_b64 = r2.stdout.strip().split("=")[-1].strip() if r2.returncode == 0 else ""

        print("# Добавьте в .env и в Environment Variables на Render:")
        print()
        priv_one_line = priv.replace("\n", "\\n")
        print('VAPID_PRIVATE_KEY="' + priv_one_line + '"')
        print("VAPID_PUBLIC_KEY=" + pub_b64)
        print()
        print("# Файлы private_key.pem и public_key.pem можно удалить.")
    except FileNotFoundError:
        print("Установите зависимости: pip install -r requirements.txt")
        print("Затем: python generate_vapid.py")

if __name__ == "__main__":
    main()
