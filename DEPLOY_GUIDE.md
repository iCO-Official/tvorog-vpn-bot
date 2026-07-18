# 🧀 Инструкция по запуску Творог VPN на VPS

## Шаг 0: Настрой ЮKassa (для оплаты)

### 1. Зарегистрируйся в ЮKassa
- Зайди на **yookassa.ru**
- Создай аккаунт
- Выбери "С помощью телеграм-бота"
- Заполни данные:
  - Что продаёшь: "VPN-подписки для безопасного интернета"
  - Ссылка на бота: `@tvorog_vpn_bot`
  - Сделай скриншоты бота

### 2. Получи API ключи
- После одобрения зайди в **Настройки** → **API ключи**
- Скопируй:
  - **Shop ID** (ID магазина)
  - **Secret Key** (секретный ключ)

### 3. Вставь ключи в конфиг
Открой `config.py` и замени:
```python
YOOKASSA_SHOP_ID = "ТВОЙ_SHOP_ID"
YOOKASSA_SECRET_KEY = "ТВОЙ_SECRET_KEY"
```

---

## Шаг 1: Купи VPS сервер

### Рекомендую Timeweb (99₽/мес)

1. Зайди на **timeweb.com**
2. Создай аккаунт
3. Выбери тариф:
   - ОС: **Ubuntu 22.04**
   - RAM: **512 MB**
   - SSD: **10 GB**
   - Цена: **99₽/мес**
4. Оплати
5. Запиши:
   - **IP-адрес** (например: 185.123.45.67)
   - **Пароль root** (пришлёт на почту)

---

## Шаг 2: Подключись к серверу

### Через PowerShell (Windows):

```powershell
ssh root@ТВОЙ_IP_АДРЕС
```

Введи пароль root.

### Через Putty (если не работает PowerShell):

1. Скачай Putty: putty.org
2. Введи IP-адрес сервера
3. Нажми Open
4. Login: `root`
5. Password: твой пароль

---

## Шаг 3: Установи софт на сервере

Вводи команды по очереди:

```bash
# Обнови систему
apt update && apt upgrade -y

# Установи Python и WireGuard
apt install -y python3 python3-pip python3-venv wireguard ufw git

# Создай папку для бота
mkdir -p /root/tvorog-bot
cd /root/tvorog-bot
```

---

## Шаг 4: Загрузи файлы бота

### Способ 1: Через SCP (с своего ПК)

Открой PowerShell на своём ПК и введи:

```powershell
scp C:\Users\iCO\vpn-bot\*.py root@ТВОЙ_IP:/root/tvorog-bot/
```

### Способ 2: Через nano (на сервере)

```bash
cd /root/tvorog-bot

# Создай bot.py
nano bot.py
```

Нажми `Ctrl+V` чтобы вставить код. Потом `Ctrl+X` → `Y` → `Enter`.

Так же создай файлы: `config.py`, `database.py`, `vpn_manager.py`, `payments.py`, `ozon_helper.py`

---

## Шаг 5: Настрой конфигурацию

```bash
nano config.py
```

Замени:
- `BOT_TOKEN` — на свой токен от BotFather
- `ADMIN_ID` — на свой Telegram ID (узнай у @userinfobot)
- `WG_SERVER_IP` — на IP твоего сервера

---

## Шаг 6: Настрой WireGuard

```bash
# Генерация ключей
wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key

# Создай конфиг
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = $(cat /etc/wireguard/server_private.key)
Address = 10.0.0.1/24
ListenPort = 51820
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
EOF

# Открой порты
ufw allow 22/tcp
ufw allow 51820/udp
echo "y" | ufw enable

# Включи forwarding
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p

# Запусти WireGuard
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0
```

---

## Шаг 7: Установи зависимости и запусти

```bash
cd /root/tvorog-bot

# Установи библиотеки
pip3 install python-telegram-bot aiohttp

# Запусти бота
python3 bot.py
```

Если всё ок, увидишь: `🧀 Творог VPN запущен!`

---

## Шаг 8: Сделай бота работающим 24/7

```bash
# Создай сервис
cat > /etc/systemd/system/tvorog-bot.service << EOF
[Unit]
Description=Tvorog VPN Bot
After=network.target

[Service]
User=root
WorkingDirectory=/root/tvorog-bot
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Запусти
systemctl daemon-reload
systemctl enable tvorog-bot
systemctl start tvorog-bot

# Проверь статус
systemctl status tvorog-bot
```

---

## Шаг 9: Проверь работу

1. Открой Telegram
2. Найди бота: `@tvorog_vpn_bot`
3. Нажми `/start`
4. Бот должен ответить!

---

## Полезные команды на сервере

```bash
# Статус бота
systemctl status tvorog-bot

# Перезапуск бота
systemctl restart tvorog-bot

# Логи бота
journalctl -u tvorog-bot -f

# Статус WireGuard
wg show

# Остановка бота
systemctl stop tvorog-bot
```

---

## Если что-то не работает

### Бот не запускается:
```bash
journalctl -u tvorog-bot -n 50
```

### WireGuard не работает:
```bash
wg show
systemctl status wg-quick@wg0
```

### Порт закрыт:
```bash
ufw allow 51820/udp
ufw reload
```

---

## Готово! 🧀

Теперь твой бот работает 24/7 и принимает заказы!