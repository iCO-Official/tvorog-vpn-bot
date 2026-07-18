# 🧀 Творог VPN Bot

[![CI](https://github.com/your-repo/tvorog-vpn-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/your-repo/tvorog-vpn-bot/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Telegram-бот для продажи VPN-доступа через WireGuard. Работает с приложениями **Happ** (iPhone/Android) и **MantaRay** (Windows).

## Возможности

- Автоматическая продажа VPN-ключей
- Оплата через Telegram Stars
- Выбор серверов
- QR-коды для быстрого подключения
- Админ-панель со статистикой
- Пробный бесплатный период

## Быстрый старт

```bash
# Клонируйте репозиторий
git clone https://github.com/your-repo/tvorog-vpn-bot.git
cd tvorog-vpn-bot

# Установите зависимости
pip install -r requirements.txt

# Настройте конфигурацию
cp config.py.example config.py
nano config.py

# Запустите бота
python bot.py
```

## Документация

- [Быстрый старт](QUICKSTART.md)
- [Установка](SETUP.md)
- [FAQ](FAQ.md)
- [Решение проблем](TROUBLESHOOTING.md)

## Лицензия

MIT License