# 📋 Changelog Творог VPN

## [1.0.0] - 2024-01-01

### Добавлено
- Основной функционал бота
- Интеграция с WireGuard
- Оплата через Telegram Stars
- QR-коды для подключения
- Админ-панель
- Система тарифов
- Выбор серверов
- Пробный бесплатный период
- Интеграция с Happ/MantaRay

### Исправлено
- Начальный релиз

### Удалено
- Ничего

---

## Версионирование

Бот использует [Semantic Versioning](https://semver.org/):

- **MAJOR** — несовместимые изменения API
- **MINOR** — добавление функциональности (обратно совместимо)
- **PATCH** — исправление ошибок (обратно совместимо)

---

## Обновление

### Автоматическое обновление

```bash
./update_bot.sh
```

### Ручное обновление

```bash
# Остановите бота
sudo systemctl stop tvorog-vpn-bot

# Обновите код
git pull

# Установите зависимости
pip3 install -r requirements.txt

# Запустите бота
sudo systemctl start tvorog-vpn-bot
```

### Откат версии

```bash
# Остановите бота
sudo systemctl stop tvorog-vpn-bot

# Откатите изменения
git checkout HEAD~1

# Запустите бота
sudo systemctl start tvorog-vpn-bot
```