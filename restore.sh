#!/bin/bash

# Скрипт восстановления Творог VPN из резервной копии

BACKUP_DIR="/home/vpnbot/backups"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Директория бэкапов не найдена: $BACKUP_DIR"
    exit 1
fi

echo "📦 Доступные резервные копии:"
echo ""

# Показываем доступные бэкапы
ls -lh "$BACKUP_DIR" | grep ".db" | awk '{print NR". "$NF}'

echo ""
read -p "Введите номер бэкапа для восстановления: " BACKUP_NUM

# Получаем имя файла
BACKUP_FILE=$(ls "$BACKUP_DIR"/*.db | sed -n "${BACKUP_NUM}p")

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Неверный номер бэкапа"
    exit 1
fi

echo ""
echo "🔄 Восстановление из: $BACKUP_FILE"

# Восстановление базы данных
cp "$BACKUP_FILE" tvorog_vpn.db

echo "✅ База данных восстановлена"
echo ""
echo "⚠️ Не забудьте перезапустить бота:"
echo "   sudo systemctl restart tvorog-vpn-bot"