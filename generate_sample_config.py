#!/usr/bin/env python3
"""
Генератор примера конфигурации
"""

import os

sample_config = '''# Конфигурация VPN Telegram Bot

# Telegram Bot Token (получить у @BotFather)
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# WireGuard настройки
WG_INTERFACE = "wg0"
WG_PORT = 51820
WG_DNS = "1.1.1.1, 8.8.8.8"
WG_SERVER_IP = "YOUR_SERVER_IP"  # IP адрес VPS сервера

# Тарифы (в Telegram Stars)
TARIFFS = {
    "week": {
        "name": "1 неделя",
        "price": 99,
        "days": 7
    },
    "month": {
        "name": "1 месяц",
        "price": 299,
        "days": 30
    },
    "quarter": {
        "name": "3 месяца",
        "price": 699,
        "days": 90
    }
}

# База данных
DATABASE_PATH = "vpn_users.db"

# Лимиты
MAX_DEVICES = 3  # Максимум устройств на аккаунт
TRIAL_DAYS = 3  # Пробный период (дни)
'''

def main():
    if os.path.exists("config.py"):
        print("⚠️ Файл config.py уже существует")
        print("Хотите перезаписать? (y/n): ", end="")
        if input().lower() != 'y':
            print("Отменено")
            return
    
    with open("config.py", "w") as f:
        f.write(sample_config)
    
    print("✅ Файл config.py создан")
    print()
    print("📝 Следующие шаги:")
    print("1. Отредактируйте config.py")
    print("2. Замените YOUR_BOT_TOKEN на токен от BotFather")
    print("3. Замените YOUR_SERVER_IP на IP вашего сервера")
    print()
    print("💡 Как получить токен:")
    print("   1. Откройте Telegram")
    print("   2. Найдите @BotFather")
    print("   3. Отправьте /newbot")
    print("   4. Скопируйте токен")

if __name__ == "__main__":
    main()