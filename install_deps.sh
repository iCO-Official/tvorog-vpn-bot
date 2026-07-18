#!/bin/bash

# Скрипт установки зависимостей

echo "========================================"
echo "   VPN Telegram Bot - Установка зависимостей"
echo "========================================"
echo ""

# Проверка Python
echo "1. Проверка Python..."
if ! command -v python3 &> /dev/null; then
    echo "   Python3 не найден. Установка..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
fi

python3 --version
echo ""

# Проверка pip
echo "2. Проверка pip..."
if ! command -v pip3 &> /dev/null; then
    echo "   pip3 не найден. Установка..."
    sudo apt install -y python3-pip
fi
echo ""

# Установка Python зависимостей
echo "3. Установка Python зависимостей..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Ошибка установки зависимостей"
    exit 1
fi
echo ""

# Установка QRCodes (опционально)
echo "4. Установка QRCodes (опционально)..."
pip3 install qrcode[pil]
echo ""

# Установка WireGuard
echo "5. Проверка WireGuard..."
if ! command -v wg &> /dev/null; then
    echo "   WireGuard не найден. Установка..."
    sudo apt install -y wireguard
fi
echo ""

# Проверка ufw
echo "6. Проверка файрвола..."
if ! command -v ufw &> /dev/null; then
    echo "   ufw не найден. Установка..."
    sudo apt install -y ufw
fi
echo ""

echo "========================================"
echo "✅ Установка завершена!"
echo ""
echo "Следующие шаги:"
echo "1. Настройте config.py"
echo "2. Запустите: ./start_bot.sh"
echo "========================================"