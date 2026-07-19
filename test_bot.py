#!/usr/bin/env python3
"""
Тестовый скрипт для проверки компонентов Творог VPN
"""

import sys
import os

def test_database():
    """Тест базы данных"""
    print("📁 Тест базы данных...")
    try:
        from database import init_db, create_user, get_user, activate_subscription
        init_db()
        user = create_user(123456, "test_user")
        assert user is not None
        activate_subscription(123456, 30)
        user = get_user(123456)
        assert user["expires_at"] is not None
        print("✅ База данных работает")
        return True
    except Exception as e:
        print(f"❌ Ошибка базы данных: {e}")
        return False

def test_config():
    """Тест конфигурации"""
    print("⚙️ Тест конфигурации...")
    try:
        from config import BOT_TOKEN, TARIFFS, SERVERS, BOT_NAME
        assert BOT_TOKEN != "YOUR_BOT_TOKEN_HERE", "Замените BOT_TOKEN в config.py"
        assert len(TARIFFS) > 0
        assert len(SERVERS) > 0
        assert BOT_NAME == "Творог VPN"
        print("✅ Конфигурация корректна")
        return True
    except AssertionError as e:
        print(f"❌ {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return False

def test_vpn_manager():
    """Тест менеджера VPN"""
    print("🔑 Тест менеджера VPN...")
    try:
        from vpn_manager import generate_wg_keys, create_client_config
        private_key, public_key = generate_wg_keys()
        assert private_key is not None
        assert public_key is not None
        print("✅ Генерация ключей работает")
        return True
    except Exception as e:
        print(f"❌ Ошибка VPN-менеджера: {e}")
        return False

def test_telegram_import():
    """Тест импорта Telegram библиотеки"""
    print("🤖 Тест Telegram API...")
    try:
        from telegram import Update
        from telegram.ext import Application
        print("✅ Telegram библиотека установлена")
        return True
    except ImportError as e:
        print(f"❌ Telegram библиотека не установлена: {e}")
        print("   Выполните: pip install python-telegram-bot")
        return False

def main():
    """Запуск всех тестов"""
    print("=" * 50)
    print("🔒 Тестирование Творог VPN Bot")
    print("=" * 50)
    print()

    tests = [
        test_database,
        test_config,
        test_vpn_manager,
        test_telegram_import
    ]

    results = []
    for test in tests:
        results.append(test())
        print()

    print("=" * 50)
    print("📊 Результаты:")
    print(f"   Пройдено: {sum(results)}/{len(results)}")

    if all(results):
        print()
        print("✅ Все тесты пройдены! Бот готов к запуску.")
        print()
        print("🚀 Для запуска выполните:")
        print("   python bot.py")
        return 0
    else:
        print()
        print("❌ Есть ошибки. Исправьте их перед запуском.")
        return 1

if __name__ == "__main__":
    sys.exit(main())