#!/bin/bash

# Скрипт проверки состояния сервера Творог VPN

echo "🔍 Проверка состояния сервера..."
echo ""

# Проверка WireGuard
echo "📡 WireGuard:"
if systemctl is-active --quiet wg-quick@wg0; then
    echo "   ✅ Запущен"
    wg show wg0 | head -5
else
    echo "   ❌ Не запущен"
fi
echo ""

# Проверка бота
echo "🤖 Telegram-бот:"
if systemctl is-active --quiet tvorog-vpn-bot; then
    echo "   ✅ Запущен"
else
    echo "   ❌ Не запущен"
fi
echo ""

# Проверка портов
echo "🔌 Порты:"
if ss -tuln | grep -q ":51820"; then
    echo "   ✅ Порт 51820 (WireGuard) открыт"
else
    echo "   ❌ Порт 51820 закрыт"
fi
echo ""

# Проверка диска
echo "💾 Диск:"
df -h / | tail -1 | awk '{print "   Использовано: " $5 " (" $3 " из " $2 ")"}'
echo ""

# Проверка памяти
echo "🧠 Память:"
free -h | grep Mem | awk '{print "   Использовано: " $3 " из " $2}'
echo ""

# Проверка подключений
echo "👥 Активные подключения:"
wg show wg0 peers | wc -l | xargs -I {} echo "   {} пользователей подключено"
echo ""

# Последние логи бота
echo "📋 Последние логи бота:"
journalctl -u tvorog-vpn-bot --no-pager -n 5 2>/dev/null || echo "   Логи недоступны"
echo ""

echo "✅ Проверка завершена"