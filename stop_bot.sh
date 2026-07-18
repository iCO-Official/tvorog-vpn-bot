#!/bin/bash

# Скрипт остановки Творог VPN

echo "🛑 Остановка Творог VPN..."

if systemctl is-active --quiet tvorog-vpn-bot; then
    sudo systemctl stop tvorog-vpn-bot
    echo "✅ Бот остановлен"
else
    echo "⚠️ Бот уже остановлен"
fi