#!/bin/bash
# Быстрый запуск бота для показа (без VPN-сервера и без ЮKassa).
# Использование: bash demo.sh
set -e
cd "$(dirname "$0")"

if [ ! -d venv ]; then
    echo "📦 Устанавливаю зависимости (1–2 минуты)..."
    python3 -m venv venv
    ./venv/bin/pip install -q -r requirements.txt
fi

if [ ! -f .env ]; then
    cp .env.example .env
    read -r -p "🤖 Вставьте токен бота от @BotFather и нажмите Enter: " T
    read -r -p "👤 Ваш Telegram ID (от @userinfobot, можно пропустить Enter): " A
    sed -i "s|^BOT_TOKEN=.*|BOT_TOKEN=$T|" .env
    sed -i "s|^ADMIN_ID=.*|ADMIN_ID=$A|" .env
    sed -i "s|^WG_SERVER_IP=.*|WG_SERVER_IP=demo.tvorog-vpn|" .env
    echo "DEMO_MODE=true" >> .env
fi

echo ""
echo "✅ Бот запускается. Напишите ему /start в Telegram."
echo "   Не закрывайте эту вкладку — пока она открыта, бот работает. Остановить: Ctrl+C"
echo ""
./venv/bin/python bot.py
