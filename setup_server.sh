#!/bin/bash

# Скрипт автоматической настройки сервера для Творог VPN
# Запускать от root на Ubuntu 22.04

set -e

echo "🧀 Настройка сервера для Творог VPN..."

# Обновление системы
echo "📦 Обновление системы..."
apt update && apt upgrade -y

# Установка необходимых пакетов
echo "📦 Установка пакетов..."
apt install -y python3 python3-pip python3-venv wireguard ufw curl git

# Создание пользователя
echo "👤 Создание пользователя vpnbot..."
if ! id -u vpnbot &>/dev/null; then
    adduser --disabled-password --gecos "" vpnbot
    usermod -aG sudo vpnbot
fi

# Генерация серверных ключей WireGuard
echo "🔑 Генерация ключей WireGuard..."
mkdir -p /etc/wireguard
wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
chmod 600 /etc/wireguard/server_private.key

SERVER_PUBLIC_KEY=$(cat /etc/wireguard/server_public.key)

# Получение IP сервера
SERVER_IP=$(curl -s ifconfig.me)
echo "📡 IP сервера: $SERVER_IP"

# Создание конфигурации WireGuard
echo "📝 Создание конфигурации WireGuard..."
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = $(cat /etc/wireguard/server_private.key)
Address = 10.0.0.1/24
ListenPort = 51820
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
EOF

# Настройка файрвола
echo "🔥 Настройка файрвола..."
ufw allow 22/tcp
ufw allow 51820/udp
echo "y" | ufw enable

# Включение IP forwarding
echo "🌐 Включение IP forwarding..."
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p

# Запуск WireGuard
echo "▶️ Запуск WireGuard..."
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

# Копирование файлов бота
echo "📁 Копирование файлов бота..."
cp -r /home/vpnbot/tvorog-vpn-bot/* /home/vpnbot/tvorog-vpn-bot/ /home/vpnbot/
chown -R vpnbot:vpnbot /home/vpnbot/tvorog-vpn-bot

# Установка Python зависимостей
echo "🐍 Установка Python зависимостей..."
cd /home/vpnbot/tvorog-vpn-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Настройка systemd сервиса
echo "⚙️ Настройка systemd сервиса..."
cat > /etc/systemd/system/tvorog-vpn-bot.service << EOF
[Unit]
Description=Творог VPN Bot
After=network.target

[Service]
User=vpnbot
WorkingDirectory=/home/vpnbot/tvorog-vpn-bot
Environment="PATH=/home/vpnbot/tvorog-vpn-bot/venv/bin"
ExecStart=/home/vpnbot/tvorog-vpn-bot/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Запуск сервиса
systemctl daemon-reload
systemctl enable tvorog-vpn-bot
systemctl start tvorog-vpn-bot

echo ""
echo "✅ Установка Творог VPN завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Отредактируйте config.py с вашим BOT_TOKEN"
echo "2. Перезапустите бота: systemctl restart tvorog-vpn-bot"
echo "3. Проверьте логи: journalctl -u tvorog-vpn-bot -f"
echo ""
echo "🔑 Ваш серверный публичный ключ:"
echo "$SERVER_PUBLIC_KEY"
echo ""
echo "📡 IP сервера: $SERVER_IP"
echo ""
echo "💡 Сохраните эти данные - они понадобятся для настройки"