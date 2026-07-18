#!/bin/bash

# Скрипт удаления VPN-бота

echo "========================================"
echo "   VPN Telegram Bot - Удаление"
echo "========================================"
echo ""

read -p "⚠️ Вы уверены, что хотите удалить бота? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Отменено"
    exit 0
fi

echo ""
echo "1. Остановка сервисов..."
if systemctl is-active --quiet vpn-bot; then
    sudo systemctl stop vpn-bot
    sudo systemctl disable vpn-bot
fi

if systemctl is-active --quiet wg-quick@wg0; then
    sudo systemctl stop wg-quick@wg0
    sudo systemctl disable wg-quick@wg0
fi

echo "2. Удаление файлов..."
sudo rm -f /etc/systemd/system/vpn-bot.service
sudo rm -rf /etc/wireguard
sudo rm -rf /home/vpnbot/vpn-bot

echo "3. Удаление пользователя..."
if id -u vpnbot &>/dev/null; then
    sudo deluser --remove-home vpnbot
fi

echo "4. Очистка..."
sudo systemctl daemon-reload

echo ""
echo "✅ Удаление завершено"
echo ""
echo "⚠️ Не забудьте удалить:"
echo "   - Бота из @BotFather"
echo "   - VPS сервер (если больше не нужен)"