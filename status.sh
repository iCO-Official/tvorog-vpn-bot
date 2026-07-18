#!/bin/bash

# Скрипт проверки статуса Творог VPN

echo "🧀 ============================================"
echo "   Творог VPN - Статус"
echo "=========================================="
echo ""

# Проверка сервисов
echo "🤖 Сервисы:"
echo ""

# Проверка бота
if systemctl is-active --quiet tvorog-vpn-bot; then
    echo "   Бот: ✅ Работает"
else
    echo "   Бот: ❌ Остановлен"
fi

# Проверка WireGuard
if systemctl is-active --quiet wg-quick@wg0; then
    echo "   WireGuard: ✅ Работает"
else
    echo "   WireGuard: ❌ Остановлен"
fi

echo ""

# Проверка портов
echo "🔌 Порты:"
if ss -tuln | grep -q ":51820"; then
    echo "   Порт 51820 (WireGuard): ✅ Открыт"
else
    echo "   Порт 51820 (WireGuard): ❌ Закрыт"
fi

echo ""

# Проверка подключений
echo "👥 Подключения:"
if command -v wg &> /dev/null; then
    PEERS=$(wg show wg0 peers | wc -l)
    echo "   Активных подключений: $PEERS"
else
    echo "   WireGuard не установлен"
fi

echo ""

# Проверка ресурсов
echo "💻 Ресурсы:"
echo "   CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
echo "   RAM: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "   Диск: $(df -h / | tail -1 | awk '{print $5}')"

echo ""

# Последние события
echo "📋 Последние события (5 минут):"
journalctl -u tvorog-vpn-bot --no-pager -n 5 --since "5 minutes ago" 2>/dev/null || echo "   Нет событий"

echo ""
echo "==========================================="