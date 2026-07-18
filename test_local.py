#!/usr/bin/env python3
"""
Тестовый скрипт для проверки бота локально
"""

import os
import sys

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Тест импортов"""
    print("📦 Тест импортов...")
    try:
        import telegram
        from telegram.ext import Application
        print("✅ Telegram библиотека установлена")
    except ImportError as e:
        print(f"❌ Telegram библиотека не установлена: {e}")
        print("   Выполните: pip install python-telegram-bot")
        return False
    
    try:
        import qrcode
        print("✅ QRCodes библиотека установлена")
    except ImportError:
        print("⚠️ QRCodes библиотека не установлена (необязательно)")
        print("   Выполните: pip install qrcode[pil]")
    
    return True

def test_database():
    """Тест базы данных"""
    print("\n📁 Тест базы данных...")
    try:
        from database import init_db, create_user, get_user
        init_db()
        user = create_user(999999, "test_user")
        if user:
            print("✅ База данных работает")
            return True
        else:
            print("❌ Ошибка создания пользователя")
            return False
    except Exception as e:
        print(f"❌ Ошибка базы данных: {e}")
        return False

def test_config():
    """Тест конфигурации"""
    print("\n⚙️ Тест конфигурации...")
    try:
        from config import BOT_TOKEN, TARIFFS, WG_SERVER_IP
        
        if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("⚠️ BOT_TOKEN не настроен")
            print("   Отредактируйте config.py")
            return False
        
        if WG_SERVER_IP == "YOUR_SERVER_IP":
            print("⚠️ WG_SERVER_IP не настроен")
            print("   Отредактируйте config.py")
            return False
        
        print("✅ Конфигурация корректна")
        return True
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return False

def main():
    print("=" * 50)
    print("🧪 Локальное тестирование VPN-бота")
    print("=" * 50)
    
    results = []
    results.append(test_imports())
    results.append(test_database())
    results.append(test_config())
    
    print("\n" + "=" * 50)
    
    if all(results):
        print("✅ Все тесты пройдены!")
        print()
        print("🚀 Для запуска бота выполните:")
        print("   python bot.py")
        return 0
    else:
        print("❌ Есть ошибки")
        print()
        print("📝 Исправьте ошибки и попробуйте снова")
        return 1

if __name__ == "__main__":
    sys.exit(main())