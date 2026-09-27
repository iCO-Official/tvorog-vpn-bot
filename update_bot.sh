#!/bin/bash

# Скрипт обновления Творог VPN (запускать из папки с ботом)

set -e
cd "$(dirname "$0")"

echo "🔄 Обновление Творог VPN..."

if [ ! -d ".git" ]; then
    echo "ОШИБКА: Это не git-репозиторий! Клонируйте репозиторий заново"
    exit 1
fi

echo "1. Загрузка обновлений..."
git pull --ff-only

echo "2. Установка зависимостей..."
if [ -x venv/bin/pip ]; then
    venv/bin/pip install -r requirements.txt -q
else
    python3 -m venv venv && venv/bin/pip install -r requirements.txt -q
fi

echo "3. Перезапуск бота..."
sudo systemctl restart tvorog-vpn-bot
if systemctl is-enabled --quiet tvorog-support-bot 2>/dev/null; then
    sudo systemctl restart tvorog-support-bot
fi
sleep 3
systemctl --no-pager status tvorog-vpn-bot | head -5

echo ""
echo "✅ Обновление завершено"
