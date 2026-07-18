#!/bin/bash

# Скрипт очистки Творог VPN

echo "🧹 Очистка Творог VPN..."

# Очистка старых конфигов
echo "1. Очистка старых конфигов..."
if [ -d "configs" ]; then
    find configs -name "*.conf" -mtime +30 -delete
    echo "   Удалены конфиги старше 30 дней"
fi

# Очистка старых логов
echo "2. Очистка старых логов..."
find . -name "*.log" -mtime +7 -delete
echo "   Удалены логи старше 7 дней"

# Очистка старых отчётов
echo "3. Очистка старых отчётов..."
find . -name "report_*.txt" -mtime +7 -delete
echo "   Удалены отчёты старше 7 дней"

# Очистка кэша Python
echo "4. Очистка кэша Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
echo "   Кэш Python очищен"

# Очистка временных файлов
echo "5. Очистка временных файлов..."
find . -type f -name "*.tmp" -delete 2>/dev/null
find . -type f -name "*.bak" -delete 2>/dev/null
echo "   Временные файлы удалены"

echo ""
echo "✅ Очистка завершена"