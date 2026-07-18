# 🧀 Решение проблем Творог VPN

## Частые проблемы

### 1. Бот не запускается

**Симптом:** `sudo systemctl status tvorog-vpn-bot` показывает ошибку

**Решение:**
```bash
# Проверьте логи
journalctl -u tvorog-vpn-bot -n 50

# Проверьте конфигурацию
python3 -c "import config; print('OK')"

# Проверьте зависимости
pip3 install -r requirements.txt

# Перезапустите
sudo systemctl restart tvorog-vpn-bot
```

### 2. WireGuard не запускается

**Симптом:** `wg show` не работает

**Решение:**
```bash
# Проверьте конфигурацию
cat /etc/wireguard/wg0.conf

# Проверьте ключи
ls -la /etc/wireguard/

# Перезапустите
sudo systemctl restart wg-quick@wg0

# Проверьте статус
sudo systemctl status wg-quick@wg0
```

### 3. Порт 51820 закрыт

**Симптом:** Пользователи не могут подключиться

**Решение:**
```bash
# Откройте порт
sudo ufw allow 51820/udp

# Проверьте файрвол
sudo ufw status

# Проверьте порт
ss -tuln | grep 51820
```

### 4. Ошибка базы данных

**Симптом:** `database is locked` или подобная ошибка

**Решение:**
```bash
# Остановите бота
sudo systemctl stop tvorog-vpn-bot

# Удалите блокировку
rm -f tvorog_vpn.db-wal tvorog_vpn.db-shm

# Запустите бота
sudo systemctl start tvorog-vpn-bot
```

### 5. Telegram API ошибка

**Симптом:** `Unauthorized` или `Forbidden`

**Решение:**
```bash
# Проверьте токен
grep BOT_TOKEN config.py

# Проверьте, что бот не заблокирован
# Откройте Telegram и найдите бота

# Перезапустите бота
sudo systemctl restart tvorog-vpn-bot
```

### 6. Нет свободных IP-адресов

**Симптом:** `Нет свободных IP-адресов`

**Решение:**
```bash
# Проверьте используемые IP
wg show wg0 allowed-ips

# Очистите неактивных пользователей
python3 remove_user.py USER_ID

# Расширьте пул IP
# Отредактируйте config.py: USER_IP_POOL = "10.0.0.0/23"
```

### 7. Медленное соединение

**Симптом:** Низкая скорость VPN

**Решение:**
```bash
# Проверьте нагрузку на сервер
top
free -h

# Проверьте трафик
vnstat

# Оптимизируйте WireGuard
# Добавьте в /etc/sysctl.conf:
# net.core.rmem_max=26214400
# net.core.wmem_max=26214400
# sysctl -p
```

### 8. Бот отвечает медленно

**Симптом:** Долгая обработка команд

**Решение:**
```bash
# Проверьте нагрузку
top

# Проверьте память
free -h

# Оптимизируйте код
# Используйте асинхронные операции

# Увеличьте ресурсы сервера
```

## Диагностика

### Проверка всех сервисов

```bash
echo "=== Сервисы ==="
systemctl status tvorog-vpn-bot
systemctl status wg-quick@wg0

echo "=== Порты ==="
ss -tuln | grep 51820

echo "=== Ресурсы ==="
top -bn1 | head -5
free -h
df -h /

echo "=== Логи ==="
journalctl -u tvorog-vpn-bot -n 10 --no-pager
```

### Проверка подключений

```bash
echo "=== WireGuard подключения ==="
wg show wg0

echo "=== Активные соединения ==="
ss -tunap | grep 51820
```

## Получение помощи

1. Проверьте логи
2. Проверьте статус сервисов
3. Проверьте конфигурацию
4. Перезапустите сервисы
5. Создайте issue в GitHub