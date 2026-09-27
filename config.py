"""
Конфигурация Творог VPN Bot
Читает настройки из переменных окружения (файл .env рядом с bot.py)
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

# Название бота
BOT_NAME = "Творог VPN"
BOT_USERNAME = "tvorog_vpn_bot"

# Telegram Bot Token (получить у @BotFather). Никогда не храните токен в коде!
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

# ID администратора (узнать свой ID: @userinfobot)
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or 0)

# WireGuard настройки
WG_INTERFACE = os.environ.get("WG_INTERFACE", "wg0")
WG_PORT = int(os.environ.get("WG_PORT", "51820"))
WG_DNS = os.environ.get("WG_DNS", "1.1.1.1, 8.8.8.8")
WG_SERVER_IP = os.environ.get("WG_SERVER_IP", "YOUR_SERVER_IP")
# Публичный ключ сервера WireGuard. Если пусто — берётся из `wg show` или /etc/wireguard/server_public.key
WG_SERVER_PUBLIC_KEY = os.environ.get("WG_SERVER_PUBLIC_KEY", "").strip()

# Демо-режим: бот работает без VPN-сервера и без ЮKassa (для показа).
# VPN-ключи генерируются, но не подключаются; оплата засчитывается без денег.
DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"

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
YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID", "").strip()
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY", "").strip()
PAYMENT_METHODS = ["bank_card", "sbp", "sberpay"]

# Серверы
SERVERS = {
    "main": {
        "name": "Основной",
        "ip": WG_SERVER_IP,
        "port": WG_PORT,
        "country": "Россия"
    }
}

# База данных
DATABASE_PATH = os.environ.get("DATABASE_PATH", "tvorog_vpn.db")

# Лимиты
MAX_DEVICES = int(os.environ.get("MAX_DEVICES", "3"))
TRIAL_DAYS = int(os.environ.get("TRIAL_DAYS", "3"))

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

✨ Нажмите «Попробовать 3 дня бесплатно» — и подключитесь за минуту!
"""

INFO_TEXT = """
<b>ℹ️ О сервисе</b>

Творог VPN использует современный протокол с открытым исходным кодом, который обеспечивает высокую скорость и стабильное соединение. Все наши серверы подключены к каналу до 10 Гбит/с, чтобы выдерживать нагрузку и не терять скорость в часы пик.

Мы не храним историю посещений и не собираем данные о том, какие сайты вы открываете. Мы не продадим никакие данные о вас — в отличие от многих бесплатных сервисов.

Доступ к VPN выдаётся через Telegram, поэтому сервис не зависит от App Store и других площадок, и его сложнее ограничить через удаление приложения.

<b>Команды</b>
/start — главное меню
/buy — тарифы и оплата
/status — личный кабинет
/gift — творог в подарок
/help — поддержка
"""

HELP_TEXT = """
<b>💬 Поддержка</b>

Что-то не работает или есть вопрос? Напишите нам — отвечаем 24/7 и поможем подключиться за пару минут.

Поддержка: @tvorog_support
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
<b>📲 Установка на iPhone / iPad</b>

1. <b>Установка приложения</b>
Скачайте Happ из App Store:
• <a href="https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973">App Store (Россия)</a>
• <a href="https://apps.apple.com/us/app/happ-proxy-utility/id6504287215">App Store (другие страны)</a>

Запустите приложение, в окне разрешения VPN-конфигурации нажмите Allow и введите свой пароль.

2. <b>Добавление ключа</b>
Нажмите «Получить ключ» ниже — бот пришлёт файл и QR-код. Откройте файл в приложении или отсканируйте QR-код.

3. <b>Подключение</b>
Нажмите большую кнопку включения в центре. Выберите сервер в списке серверов.
"""

INSTALL_ANDROID_TEXT = """
<b>📲 Установка на Android</b>

1. <b>Установка приложения</b>
Скачайте Happ:
• <a href="https://play.google.com/store/apps/details?id=com.happproxy">Google Play</a>
• <a href="https://github.com/Happ-proxy/happ-android/releases/latest/download/Happ.apk">Скачать APK</a> (если Google Play не работает)

2. <b>Добавление ключа</b>
Нажмите «Получить ключ» ниже — бот пришлёт файл и QR-код. Откройте файл в приложении или отсканируйте QR-код.

3. <b>Подключение</b>
Откройте приложение и подключитесь к серверу.
"""

INSTALL_WINDOWS_TEXT = """
<b>📲 Установка на Windows</b>

1. <b>Установка приложения</b>
Скачайте и установите Happ:
• <a href="https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe">Скачать Happ для Windows</a>

2. <b>Добавление ключа</b>
Нажмите «Получить ключ» ниже — бот пришлёт файл и QR-код. Откройте файл в приложении или отсканируйте QR-код.

3. <b>Подключение</b>
Нажмите большую кнопку включения и выберите сервер.
"""

INSTALL_MAC_TEXT = """
<b>📲 Установка на Mac / MacBook</b>

1. <b>Установка приложения</b>
Скачайте Happ из App Store:
• <a href="https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973">App Store (Россия)</a>
• <a href="https://apps.apple.com/us/app/happ-proxy-utility/id6504287215">App Store (другие страны)</a>

Запустите приложение, разрешите VPN-конфигурацию.

2. <b>Добавление ключа</b>
Нажмите «Получить ключ» ниже — бот пришлёт файл и QR-код. Откройте файл в приложении или отсканируйте QR-код.

3. <b>Подключение</b>
Нажмите кнопку включения и выберите сервер.
"""

INSTALL_LINUX_TEXT = """
<b>📲 Установка на Linux</b>

1. <b>Установка приложения</b>
Скачайте Happ:
• <a href="https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.AppImage">Скачать Happ для Linux</a>

2. <b>Добавление ключа</b>
Нажмите «Получить ключ» ниже — бот пришлёт файл и QR-код. Откройте файл в приложении или отсканируйте QR-код.

3. <b>Подключение</b>
Нажмите кнопку включения и выберите сервер.
"""

CONFIG_INSTRUCTION_TEXT = """
<b>📖 Как подключиться</b>

1. Установите приложение — ссылки есть в разделе «Подключить устройство»
2. Нажмите «Получить ключ» — бот пришлёт файл и QR-код
3. Откройте файл в приложении или отсканируйте QR-код
4. Включите VPN — готово!

Не получается? Напишите в поддержку @tvorog_support — поможем.
"""
