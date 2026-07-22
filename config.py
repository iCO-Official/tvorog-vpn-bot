"""
Конфигурация Творог VPN Bot
Читает настройки из переменных окружения
"""
import os

# Название бота
BOT_NAME = "Творог VPN"
BOT_USERNAME = "tvorog_vpn_bot"

# Telegram Bot Token
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8782090577:AAEFp08ZPvh9QDDeESi6EsmljEs2Bh2Qqq8")

# ID администратора
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))

# WireGuard настройки
WG_INTERFACE = "wg0"
WG_PORT = 51820
WG_DNS = "1.1.1.1, 8.8.8.8"
WG_SERVER_IP = os.environ.get("WG_SERVER_IP", "YOUR_SERVER_IP")

# Тарифы (в рублях)
TARIFFS = {
    "trial": {
        "name": "Пробный",
        "price": 0,
        "days": 3,
        "description": "Бесплатно на 3 дня"
    },
    "month": {
        "name": "1 месяц",
        "price": 299,
        "days": 30,
        "description": "299 ₽"
    },
    "quarter": {
        "name": "3 месяца",
        "price": 699,
        "days": 90,
        "description": "699 ₽"
    },
    "year": {
        "name": "1 год",
        "price": 1999,
        "days": 365,
        "description": "1999 ₽"
    }
}

# ЮKassa настройки
YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID", "1412568")
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY", "live_vpeOwoU9atdXO_CyOv0ZzW6weVD2_iJ7nbdbTp1e2LQ")
PAYMENT_METHODS = ["bank_card", "sbp", "sberpay"]

# Серверы
SERVERS = {
    "main": {
        "name": "Основной",
        "ip": WG_SERVER_IP,
        "port": 51820,
        "country": "Россия"
    }
}

# База данных
DATABASE_PATH = os.environ.get("DATABASE_PATH", "tvorog_vpn.db")

# Лимиты
MAX_DEVICES = 3
TRIAL_DAYS = 3

# Тексты сообщений
WELCOME_TEXT = """
<b>Что умеет этот бот?</b>

🔒 Творог VPN — быстрый и стабильный VPN на каждый день
🎁 3 дня бесплатно — без привязки банковской карты
🚀 Высокая скорость для Telegram, видео, игр и стримов
📞 Звонки и видеосвязь без лишних задержек
🛡 Надёжное и стабильное соединение
📱 До 3-х устройств на одну подписку
⚡ Простое подключение за пару секунд
👨‍💻 Поддержка 24/7

✨ Нажмите «Подключиться», чтобы получить 3 дня бесплатно!
"""

INFO_TEXT = """
<b>О сервисе</b>

Творог VPN использует современный протокол с открытым исходным кодом, который обеспечивает высокую скорость и стабильное соединение. Все наши серверы подключены к каналу до 10 Гбит/с, чтобы выдерживать нагрузку и не терять скорость в часы пик.

Мы не храним историю посещений и не собираем данные о том, какие сайты вы открываете. Мы не продадим никакие данные о вас — в отличие от многих бесплатных сервисов.

Доступ к VPN выдаётся через Telegram, поэтому сервис не зависит от App Store и других площадок, и его сложнее ограничить через удаление приложения.

<b>Команды:</b>
/start — Главное меню
/buy — Купить подписку
/status — Проверить статус
/gift — Получить творог
/help — Помощь
"""

HELP_TEXT = """
<b>Помощь</b>

Если у вас возникли вопросы или проблемы, напишите в поддержку:

<a href="https://t.me/tvorog_support">@tvorog_support</a>
"""

TARIFF_TEXT = """
<b>Выбери тариф</b>

<b>1 месяц</b> — 299 ₽ + творог!
<b>3 месяца</b> — 699 ₽ + творог!
<b>1 год</b> — 1999 ₽ + творог!

<i>При покупке от 1 месяца — получи настоящий творог домой!</i>
"""

SUCCESS_PAYMENT_TEXT = """
<b>Оплата прошла успешно!</b>

Твоя подписка активирована!

Теперь выбери устройство, чтобы получить VPN-ключ:
"""

DEVICE_SELECT_TEXT = """
Выбери устройство, чтобы получить VPN-ключ:
"""

INSTALL_IPHONE_TEXT = """
<b>Установка на iPhone / iPad</b>

1. <b>Установка приложения</b>
Скачайте Happ из App Store:
• <a href="https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973">App Store (Россия)</a>
• <a href="https://apps.apple.com/us/app/happ-proxy-utility/id6504287215">App Store (другие страны)</a>

Запустите приложение, в окне разрешения VPN-конфигурации нажмите Allow и введите свой пароль.

2. <b>Добавление подписки</b>
Нажмите кнопку «Получить VPN-ключ» ниже — затем «Добавить в Happ», и подписка добавится автоматически.

3. <b>Подключение</b>
Нажмите большую кнопку включения в центре. Выберите сервер в списке серверов.
"""

INSTALL_ANDROID_TEXT = """
<b>Установка на Android</b>

1. <b>Установка приложения</b>
Скачайте Happ:
• <a href="https://play.google.com/store/apps/details?id=com.happproxy">Google Play</a>
• <a href="https://github.com/Happ-proxy/happ-android/releases/latest/download/Happ.apk">Скачать APK</a> (если Google Play не работает)

2. <b>Добавление подписки</b>
Нажмите «Получить VPN-ключ» ниже — затем «Добавить в Happ», и подписка добавится автоматически.

3. <b>Подключение</b>
Откройте приложение и подключитесь к серверу.
"""

INSTALL_WINDOWS_TEXT = """
<b>Установка на Windows</b>

1. <b>Установка приложения</b>
Скачайте и установите Happ:
• <a href="https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe">Скачать Happ для Windows</a>

2. <b>Добавление подписки</b>
Нажмите «Получить VPN-ключ» ниже — затем «Добавить в Happ», и подписка добавится автоматически.

3. <b>Подключение</b>
Нажмите большую кнопку включения и выберите сервер.
"""

INSTALL_MAC_TEXT = """
<b>Установка на Mac / MacBook</b>

1. <b>Установка приложения</b>
Скачайте Happ из App Store:
• <a href="https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973">App Store (Россия)</a>
• <a href="https://apps.apple.com/us/app/happ-proxy-utility/id6504287215">App Store (другие страны)</a>

Запустите приложение, разрешите VPN-конфигурацию.

2. <b>Добавление подписки</b>
Нажмите «Получить VPN-ключ» ниже — затем «Добавить в Happ».

3. <b>Подключение</b>
Нажмите кнопку включения и выберите сервер.
"""

INSTALL_LINUX_TEXT = """
<b>Установка на Linux</b>

1. <b>Установка приложения</b>
Скачайте Happ:
• <a href="https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.AppImage">Скачать Happ для Linux</a>

2. <b>Добавление подписки</b>
Нажмите «Получить VPN-ключ» ниже — затем «Добавить в Happ».

3. <b>Подключение</b>
Нажмите кнопку включения и выберите сервер.
"""

CONFIG_INSTRUCTION_TEXT = """
<b>Инструкция по установке</b>

1. Скачайте Happ для вашего устройства
2. Нажмите «Получить VPN-ключ»
3. Добавьте подписку в Happ
4. Подключитесь к серверу

Готово!
"""
