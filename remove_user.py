#!/usr/bin/env python3
"""
Скрипт для удаления пользователя Творог VPN
"""

import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, get_user, update_user
from vpn_manager import remove_peer

def main():
    if len(sys.argv) < 2:
        print("Использование: python remove_user.py <user_id>")
        print("Пример: python remove_user.py 123456789")
        sys.exit(1)

    user_id = int(sys.argv[1])

    # Инициализация базы данных
    init_db()

    # Получение пользователя
    user = get_user(user_id)

    if not user:
        print(f"❌ Пользователь {user_id} не найден")
        sys.exit(1)

    # Удаление из WireGuard
    if user["wg_public_key"]:
        try:
            remove_peer(user["wg_public_key"])
            print(f"✅ Пир удалён из WireGuard")
        except Exception as e:
            print(f"⚠️ Ошибка при удалении из WireGuard: {e}")

    # Деактивация в базе данных
    update_user(user_id, is_active=0)

    print(f"✅ Пользователь деактивирован:")
    print(f"   User ID: {user_id}")
    print(f"   Подписка деактивирована")

if __name__ == "__main__":
    main()