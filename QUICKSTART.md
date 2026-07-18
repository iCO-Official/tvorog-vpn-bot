# 🧀 Быстрый старт Творог VPN

## 5 минут до запуска

### 1. Получите VPS сервер

Рекомендации:
- **Timeweb** — от 99₽/мес
- **Selectel** — от 300₽/мес
- **Hetzner** — от €3.5/мес

### 2. Получите Telegram Bot Token

1. Откройте Telegram
2. Найдите **@BotFather**
3. Отправьте `/newbot`
4. Введите имя: `Творог VPN Bot`
5. Введите username: `Tvorog_vpn_bot`
6. Скопируйте токен

### 3. Подключитесь к серверу

```bash
ssh root@your-server-ip
```

### 4. Установите бота

```bash
# Скачайте бота
cd /home
git clone https://github.com/your-repo/tvorog-vpn-bot.git
cd tvorog-vpn-bot

# Запустите установку
chmod +x setup_server.sh
sudo ./setup_server.sh
```

### 5. Настройте конфигурацию

```bash
nano config.py
```

Замените:
- `YOUR_BOT_TOKEN` — ваш токен
- `YOUR_SERVER_IP` — IP сервера
- `ADMIN_ID` — ваш Telegram ID

### 6. Запуск

```bash
sudo systemctl start tvorog-vpn-bot
```

## Готово!

Бот запущен и работает.

## Следующие шаги

1. Найдите бота в Telegram: @Tvorog_vpn_bot
2. Отправьте `/start`
3. Протестируйте покупку
4. Установите Happ на телефон
5. Подключитесь к VPN

## Проблемы?

- Проверьте логи: `journalctl -u tvorog-vpn-bot -f`
- Проверьте статус: `sudo systemctl status tvorog-vpn-bot`
- Перезапустите: `sudo systemctl restart tvorog-vpn-bot`