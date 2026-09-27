#!/bin/bash

# Автоматическая настройка сервера для Творог VPN (Ubuntu 22.04 / 24.04, Debian 12)
# Запуск (от root, из папки с ботом):
#   git clone https://github.com/iCO-Official/tvorog-vpn-bot.git /opt/tvorog-vpn-bot
#   cd /opt/tvorog-vpn-bot && bash setup_server.sh
# Скрипт можно запускать повторно — ключи сервера и .env не перезаписываются.

set -e

BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="tvorog-vpn-bot"

if [ "$(id -u)" -ne 0 ]; then
    echo "❌ Запустите от root: sudo bash setup_server.sh"
    exit 1
fi

echo "🧀 Настройка сервера для Творог VPN (папка: $BOT_DIR)..."

echo "📦 Установка пакетов..."
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-pip python3-venv wireguard wireguard-tools ufw curl git iptables qrencode

# Ключи сервера WireGuard — создаём только если их ещё нет
mkdir -p /etc/wireguard
chmod 700 /etc/wireguard
if [ ! -f /etc/wireguard/server_private.key ]; then
    echo "🔑 Генерация ключей WireGuard..."
    wg genkey > /etc/wireguard/server_private.key
    chmod 600 /etc/wireguard/server_private.key
    wg pubkey < /etc/wireguard/server_private.key > /etc/wireguard/server_public.key
else
    echo "🔑 Ключи WireGuard уже есть — оставляем"
fi

SERVER_IP=$(curl -4 -s --max-time 10 ifconfig.me || hostname -I | awk '{print $1}')
NET_IFACE=$(ip -4 route show default | awk '{print $5; exit}')
echo "📡 IP сервера: $SERVER_IP, сетевой интерфейс: $NET_IFACE"

if [ ! -f /etc/wireguard/wg0.conf ]; then
    echo "📝 Создание конфигурации WireGuard..."
    cat > /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = $(cat /etc/wireguard/server_private.key)
Address = 10.0.0.1/24
ListenPort = 51820
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o $NET_IFACE -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o $NET_IFACE -j MASQUERADE
EOF
    chmod 600 /etc/wireguard/wg0.conf
fi

echo "🌐 Включение IP forwarding..."
echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-tvorog-vpn.conf
sysctl --system > /dev/null

echo "🔥 Настройка файрвола..."
ufw allow OpenSSH
ufw allow 22/tcp
ufw allow 51820/udp
sed -i 's/^DEFAULT_FORWARD_POLICY=.*/DEFAULT_FORWARD_POLICY="ACCEPT"/' /etc/default/ufw
ufw --force enable
ufw reload

echo "▶️ Запуск WireGuard..."
systemctl enable wg-quick@wg0
systemctl restart wg-quick@wg0

echo "🐍 Установка Python-зависимостей..."
cd "$BOT_DIR"
python3 -m venv venv
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r requirements.txt -q

# Файл настроек .env
if [ ! -f "$BOT_DIR/.env" ]; then
    cp "$BOT_DIR/.env.example" "$BOT_DIR/.env"
    sed -i "s|^WG_SERVER_IP=.*|WG_SERVER_IP=$SERVER_IP|" "$BOT_DIR/.env"
    echo ""
    read -r -p "🤖 Вставьте токен бота от @BotFather: " BOT_TOKEN_INPUT < /dev/tty || true
    read -r -p "👤 Ваш Telegram ID (узнать у @userinfobot): " ADMIN_ID_INPUT < /dev/tty || true
    read -r -p "💳 ЮKassa shopId (Enter — пропустить): " SHOP_ID_INPUT < /dev/tty || true
    read -r -p "💳 ЮKassa секретный ключ (Enter — пропустить): " SHOP_KEY_INPUT < /dev/tty || true
    sed -i "s|^BOT_TOKEN=.*|BOT_TOKEN=$BOT_TOKEN_INPUT|" "$BOT_DIR/.env"
    sed -i "s|^ADMIN_ID=.*|ADMIN_ID=$ADMIN_ID_INPUT|" "$BOT_DIR/.env"
    sed -i "s|^YOOKASSA_SHOP_ID=.*|YOOKASSA_SHOP_ID=$SHOP_ID_INPUT|" "$BOT_DIR/.env"
    sed -i "s|^YOOKASSA_SECRET_KEY=.*|YOOKASSA_SECRET_KEY=$SHOP_KEY_INPUT|" "$BOT_DIR/.env"
fi
chmod 600 "$BOT_DIR/.env"

echo "⚙️ Настройка автозапуска (systemd)..."
sed "s|/opt/tvorog-vpn-bot|$BOT_DIR|g" "$BOT_DIR/deploy/tvorog-vpn-bot.service" > /etc/systemd/system/$SERVICE_NAME.service
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

sleep 3
echo ""
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ Готово! Бот запущен и будет сам стартовать после перезагрузки сервера."
else
    echo "⚠️ Бот не запустился. Посмотрите ошибку: journalctl -u $SERVICE_NAME -n 50"
fi
echo ""
echo "📋 Полезные команды:"
echo "   Логи:        journalctl -u $SERVICE_NAME -f"
echo "   Статус:      systemctl status $SERVICE_NAME"
echo "   Перезапуск:  systemctl restart $SERVICE_NAME"
echo "   Настройки:   nano $BOT_DIR/.env"
