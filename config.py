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
    "week": {
        "name": "1 неделя",
        "price": 99,
        "days": 7,
        "description": "99 ₽"
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
YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID", "YOUR_SHOP_ID")
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY", "YOUR_SECRET_KEY")
PAYMENT_METHODS = ["bank_card", "sbp", "yoo_money"]

# Серверы
SERVERS = {
    "main": {
        "name": "Основной",
        "ip": WG_SERVER_IP,
        "port": 51820,
        "country": "🇷🇺 Россия"
    }
}

# База данных
DATABASE_PATH = os.environ.get("DATABASE_PATH", "tvorog_vpn.db")

# Лимиты
MAX_DEVICES = 3
TRIAL_DAYS = 3

# Тексты сообщений
WELCOME_TEXT = """
<b>Добро пожаловать в Творог VPN!</b>

Мы подготовили для вас подарок:

<b>3 дня бесплатного VPN</b>

Полный доступ ко всем серверам
Без ограничения скорности
Без привязки карты

Нажмите кнопку ниже, чтобы забрать подарок!
"""

HELP_TEXT = """
<b>Помощь</b>

Если у вас возникли вопросы или проблемы, напишите в поддержку:

<a href="https://t.me/tvorog_support">@tvorog_support</a>
"""

TARIFF_TEXT = """
<b>Выбери тариф</b>

<b>Пробный</b> — бесплатно (3 дня)
<b>1 неделя</b> — 99 ₽
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

CONFIG_INSTRUCTION_TEXT = """
<b>Инструкция по установке</b>

1. Скачайте Happ для вашего устройства
2. Нажмите «Получить VPN-ключ»
3. Добавьте подписку в Happ
4. Подключитесь к серверу

Готово!
"""

HELP_TEXT = """
<b>Как пользоваться Творог VPN:</b>

1. Купи подписку через бота
2. Получи конфигурационный файл
3. Установи приложение <b>Happ</b> (iPhone/Android) или <b>MantaRay</b> (Windows)
4. Импортируй конфиг через QR-код или файл
5. Нажми "Подключить"

<b>Где скачать:</b>
• iPhone: Happ из App Store
• Android: Happ из Google Play
• Windows: MantaRay

<b>Команды:</b>
/start — Главное меню
/buy — Купить подписку
/status — Проверить статус
/gift — Получить творог
/servers — Выбрать сервер
/help — Эта справка

<b>При покупке от 1 месяца — получи настоящий творог домой!</b>
Используй /gift чтобы указать адрес доставки.

<b>Безопасность:</b>
• Все данные зашифрованы
• Мы не храним логи активности
• Автоматическое обновление ключей

<b>Поддержка:</b>
@tvorog_support
"""

TARIFF_TEXT = """
<b>Выбери тариф Творог VPN:</b>

<b>Пробный</b> — бесплатно (3 дня)
<b>1 неделя</b> — 99 ₽
<b>1 месяц</b> — 299 ₽ + творог!
<b>3 месяца</b> — 699 ₽ + творог!
<b>1 год</b> — 1999 ₽ + творог!

<i>При покупке от 1 месяца — получи настоящий творог домой!</i>
"""

SUCCESS_PAYMENT_TEXT = """
✅ <b>Оплата прошла успешно!</b>

Твоя подписка <b>Творог VPN</b> активирована!

Теперь ты можешь:
1. Скачать конфигурационный файл
2. Импортировать его в Happ/MantaRay
3. Наслаждаться безопасным интернетом 🔒

Нажми кнопку ниже, чтобы получить конфиг:
"""

CONFIG_INSTRUCTION_TEXT = """
📱 <b>Инструкция по установке:</b>

<b>Для iPhone/Android (Happ):</b>
1. Скачай Happ из App Store / Google Play
2. Открой приложение
3. Нажми "+" и выбери "Импорт конфига"
4. Выбери скачанный файл
5. Нажми на подключение

<b>Для Windows (MantaRay):</b>
1. Скачай MantaRay с официального сайта
2. Установи приложение
3. Нажми "Импорт" и выбери файл
4. Активируй подключение

<b>Настройка маршрутизации:</b>
В Happ/MantaRay можно выбрать:
• Весь трафик через VPN
• Только определённые приложения
• Исключить определённые сайты

Готово! Твой трафик защищён 🔒
"""
