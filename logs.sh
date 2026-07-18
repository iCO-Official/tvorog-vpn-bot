#!/bin/bash

# Скрипт просмотра логов Творог VPN

echo "📋 Логи Творог VPN"
echo "Нажмите Ctrl+C для остановки"
echo ""

journalctl -u tvorog-vpn-bot -f