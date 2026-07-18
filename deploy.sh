#!/bin/bash

# Скрипт деплоя Творог VPN на сервер
# Использование: ./deploy.sh user@server-ip

set -e

SERVER=$1
REMOTE_DIR="/home/vpnbot/tvorog-vpn-bot"

if [ -z "$SERVER" ]; then
    echo "❌ Укажите сервер: ./deploy.sh user@server-ip"
    exit 1
fi

echo "🧀 Деплой Творог VPN на $SERVER..."

# Копирование файлов
echo "📦 Копирование файлов..."
scp -r bot.py config.py database.py vpn_manager.py payments.py requirements.txt "$SERVER:$REMOTE_DIR/"

# Установка зависимостей на сервере
echo "📦 Установка зависимостей..."
ssh "$SERVER" "cd $REMOTE_DIR && pip3 install -r requirements.txt"

# Перезапуск сервиса
echo "🔄 Перезапуск бота..."
ssh "$SERVER" "sudo systemctl restart tvorog-vpn-bot"

echo ""
echo "✅ Деплой завершён!"
echo ""
echo "📋 Проверьте статус:"
echo "   ssh $SERVER 'sudo systemctl status tvorog-vpn-bot'"
echo ""
echo "📋 Просмотр логов:"
echo "   ssh $SERVER 'journalctl -u tvorog-vpn-bot -f'"