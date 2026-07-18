#!/bin/bash

# Скрипт резервного копирования Творог VPN

BACKUP_DIR="/home/vpnbot/backups"
DATE=$(date +%Y%m%d_%H%M%S)

echo "📦 Создание резервной копии Творог VPN..."

# Создание директории для бэкапов
mkdir -p "$BACKUP_DIR"

# Бэкап базы данных
echo "📁 Бэкап базы данных..."
cp tvorog_vpn.db "$BACKUP_DIR/tvorog_vpn_$DATE.db"

# Бэкап конфигурации
echo "⚙️ Бэкап конфигурации..."
cp config.py "$BACKUP_DIR/config_$DATE.py"

# Бэкап WireGuard конфига
echo "🔑 Бэкап WireGuard..."
cp /etc/wireguard/wg0.conf "$BACKUP_DIR/wg0_$DATE.conf"

# Очистка старых бэкапов (оставляем последние 7)
echo "🧹 Очистка старых бэкапов..."
find "$BACKUP_DIR" -name "*.db" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.py" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.conf" -mtime +7 -delete

echo ""
echo "✅ Резервная копия создана: $BACKUP_DIR"
echo ""
ls -lh "$BACKUP_DIR" | grep "$DATE"