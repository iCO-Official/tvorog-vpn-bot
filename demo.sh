#!/bin/bash
# Быстрый запуск бота для показа (без VPN-сервера и без ЮKassa).
# Если в .env задан SUPPORT_BOT_TOKEN — вместе с ним запускается бот поддержки.
# Использование: bash demo.sh
set -e
cd "$(dirname "$0")"

if [ ! -d venv ]; then
    echo "📦 Устанавливаю зависимости (1–2 минуты)..."
    python3 -m venv venv
fi
./venv/bin/pip install -q -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    read -r -p "🤖 Вставьте токен бота от @BotFather и нажмите Enter: " T
    read -r -p "👤 Ваш Telegram ID (от @userinfobot, можно пропустить Enter): " A
    sed -i "s|^BOT_TOKEN=.*|BOT_TOKEN=$T|" .env
    sed -i "s|^ADMIN_ID=.*|ADMIN_ID=$A|" .env
    sed -i "s|^WG_SERVER_IP=.*|WG_SERVER_IP=demo.tvorog-vpn|" .env
    echo "DEMO_MODE=true" >> .env
fi

if grep -q "^SUPPORT_BOT_TOKEN=..*" .env; then
    echo "💬 Запускаю бота поддержки..."
    ./venv/bin/python support_bot.py &
    SUPPORT_PID=$!
    trap 'kill $SUPPORT_PID 2>/dev/null' EXIT
fi

echo ""
echo "✅ Бот запускается. Напишите ему /start в Telegram."
echo "   Не закрывайте эту вкладку — пока она открыта, бот работает."
echo ""
./venv/bin/python bot.py
