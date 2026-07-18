#!/usr/bin/env python3
"""
Скрипт для ручного добавления пользователя Творог VPN
"""

import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, create_user, activate_subscription, get_user

def main():
    if len(sys.argv) < 2:
        print("Использование: python add_user.py <user_id> [days]")
        print("Пример: python add_user.py 123456789 30")
        sys.exit(1)

    user_id = int(sys.argv[1])
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    # Инициализация базы данных
    init_db()

    # Создание пользователя
    user = create_user(user_id, f"manual_user_{user_id}")

    # Активация подписки
    activate_subscription(user_id, days)

    # Получение обновлённых данных
    user = get_user(user_id)

    print(f"✅ Пользователь добавлен:")
    print(f"   User ID: {user_id}")
    print(f"   Подписка: {days} дней")
    print(f"   Истекает: {user['expires_at']}")

if __name__ == "__main__":
    main()