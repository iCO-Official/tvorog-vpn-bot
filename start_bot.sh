#!/bin/bash

# Скрипт запуска Творог VPN

echo "🧀 Запуск Творог VPN..."

if systemctl is-active --quiet tvorog-vpn-bot; then
    echo "⚠️ Бот уже запущен"
else
    sudo systemctl start tvorog-vpn-bot
    echo "✅ Бот запущен"
fi