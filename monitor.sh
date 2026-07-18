#!/bin/bash

# Скрипт мониторинга Творог VPN

echo "🧀 Мониторинг Творог VPN"
echo "Нажмите Ctrl+C для остановки"
echo ""

while true; do
    clear

    echo "📊 $(date)"
    echo ""

    # Статус сервисов
    echo "🤖 Сервисы:"
    if systemctl is-active --quiet tvorog-vpn-bot; then
        echo "   Бот: ✅ Работает"
    else
        echo "   Бот: ❌ Остановлен"
    fi

    if systemctl is-active --quiet wg-quick@wg0; then
        echo "   WireGuard: ✅ Работает"
    else
        echo "   WireGuard: ❌ Остановлен"
    fi
    echo ""

    # Подключения
    echo "👥 Подключения:"
    wg show wg0 peers | wc -l | xargs -I {} echo "   Активных: {}"
    echo ""

    # Ресурсы
    echo "💻 Ресурсы:"
    echo "   CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
    echo "   RAM: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
    echo "   Диск: $(df -h / | tail -1 | awk '{print $5}')"
    echo ""

    # Последние события
    echo "📋 Последние события:"
    journalctl -u tvorog-vpn-bot --no-pager -n 3 --since "5 minutes ago" 2>/dev/null || echo "   Нет событий"

    sleep 5
done