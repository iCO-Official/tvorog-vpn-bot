#!/bin/bash

# Обновление бота на сервере с вашего компьютера
# Использование: ./deploy.sh root@server-ip

set -e

SERVER=$1
REMOTE_DIR="/opt/tvorog-vpn-bot"

if [ -z "$SERVER" ]; then
    echo "❌ Укажите сервер: ./deploy.sh root@server-ip"
    exit 1
fi

echo "🧀 Деплой Творог VPN на $SERVER..."
ssh "$SERVER" "cd $REMOTE_DIR && bash update_bot.sh"

echo ""
echo "✅ Деплой завершён!"
echo "📋 Логи: ssh $SERVER 'journalctl -u tvorog-vpn-bot -f'"
