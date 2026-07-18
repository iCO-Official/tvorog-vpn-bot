# 🧀 Пошаговая установка Творог VPN

## Шаг 1: Получите VPS сервер

### Рекомендации по хостингу

1. **Timeweb** (timeweb.com)
   - Тариф: Базовый (99₽/мес)
   - ОС: Ubuntu 22.04
   - RAM: 512MB
   - SSD: 10GB

2. **Selectel** (selectel.com)
   - Тариф: VDS Start (от 300₽/мес)
   - ОС: Ubuntu 22.04
   - RAM: 512MB
   - SSD: 10GB

3. **Hetzner** (hetzner.com)
   - Тариф: CPX11 (от €3.5/мес)
   - ОС: Ubuntu 22.04
   - RAM: 2GB
   - SSD: 40GB

### Настройка сервера

1. Создайте аккаунт
2. Выберите Ubuntu 22.04
3. Настройте SSH-ключ
4. Запустите сервер
5. Запишите IP-адрес

## Шаг 2: Получите Telegram Bot Token

1. Откройте Telegram
2. Найдите **@BotFather**
3. Отправьте `/newbot`
4. Введите имя бота: `Творог VPN Bot`
5. Введите username: `Tvorog_vpn_bot`
6. Скопируйте полученный токен

## Шаг 3: Подключитесь к серверу

```bash
ssh root@your-server-ip
```

## Шаг 4: Установите бота

```bash
# Обновите систему
apt update && apt upgrade -y

# Установите необходимые пакеты
apt install -y python3 python3-pip python3-venv wireguard ufw git

# Создайте пользователя
adduser --disabled-password --gecos "" vpnbot
usermod -aG sudo vpnbot
su - vpnbot

# Скачайте бота
git clone https://github.com/your-repo/tvorog-vpn-bot.git
cd tvorog-vpn-bot

# Установите зависимости
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Шаг 5: Настройте WireGuard

```bash
# Генерация серверных ключей
wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key

# Просмотр серверного публичного ключа
cat /etc/wireguard/server_public.key

# Создание конфигурации
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = $(cat /etc/wireguard/server_private.key)
Address = 10.0.0.1/24
ListenPort = 51820
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
EOF

# Настройка файрвола
ufw allow 22/tcp
ufw allow 51820/udp
echo "y" | ufw enable

# Включение IP forwarding
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p

# Запуск WireGuard
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0
```

## Шаг 6: Настройте бота

```bash
# Скопируйте конфигурацию
cp config.py.example config.py

# Отредактируйте конфигурацию
nano config.py
```

Замените:
- `YOUR_BOT_TOKEN` — ваш токен от BotFather
- `YOUR_SERVER_IP` — IP вашего сервера
- `ADMIN_ID` — ваш Telegram ID

## Шаг 7: Запустите бота

```bash
# Тестовый запуск
python3 bot.py

# Для продакшена создайте systemd сервис
sudo nano /etc/systemd/system/tvorog-vpn-bot.service
```

Содержимое сервиса:

```ini
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
```

```bash
# Запустите сервис
sudo systemctl daemon-reload
sudo systemctl enable tvorog-vpn-bot
sudo systemctl start tvorog-vpn-bot

# Проверьте статус
sudo systemctl status tvorog-vpn-bot
```

## Шаг 8: Проверьте работу

1. Откройте Telegram
2. Найдите вашего бота: @Tvorog_vpn_bot
3. Отправьте `/start`
4. Нажмите "Купить VPN"
5. Выберите тариф
6. Оплатите (для теста используйте тестовый режим)

## Шаг 9: Настройте оплату

Для принимать платежи через Telegram Stars:

1. Откройте @BotFather
2. Выберите вашего бота
3. Отправьте `/mybots`
4. Выберите "Payments"
5. Выберите "Telegram Stars"

## Шаг 10: Протестируйте

1. Купите подписку
2. Получите конфиг
3. Установите Happ на телефон
4. Импортируйте конфиг
5. Подключитесь к VPN
6. Проверьте IP-адрес

## Готово!

Бот работает и принимает оплату.

## Следующие шаги

- Настройте реферальную программу
- Добавьте несколько серверов
- Создайте канал для продвижения
- Оптимизируйте конверсию