#!/bin/bash

# Скрипт обновления Творог VPN

echo "🔄 Обновление Творог VPN..."

# Проверка git
if ! command -v git &> /dev/null; then
    echo "ОШИБКА: Git не установлен!"
    echo "Установите: sudo apt install git"
    exit 1
fi

# Проверка репозитория
if [ ! -d ".git" ]; then
    echo "ОШИБКА: Это не git-репозиторий!"
    echo "Клонируйте репозиторий заново"
    exit 1
fi

# Сохранение изменений
echo "1. Сохранение локальных изменений..."
git stash

# Обновление
echo "2. Загрузка обновлений..."
git pull

# Установка зависимостей
echo "3. Установка зависимостей..."
pip3 install -r requirements.txt

# Перезапуск
echo "4. Перезапуск бота..."
if systemctl is-active --quiet tvorog-vpn-bot; then
    sudo systemctl restart tvorog-vpn-bot
    echo "✅ Сервис перезапущен"
else
    echo "⚠️ Сервис не запущен. Запустите: ./start_bot.sh"
fi

echo ""
echo "✅ Обновление завершено"