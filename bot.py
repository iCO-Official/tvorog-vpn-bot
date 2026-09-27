import html
import io
import logging
import os
import sqlite3
import sys
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.error import Conflict, InvalidToken
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PicklePersistence,
    filters,
    ContextTypes
)

from config import (
    BOT_TOKEN, TARIFFS, SERVERS, ADMIN_ID, BOT_NAME, DEMO_MODE,
    WELCOME_TEXT, HELP_TEXT, TARIFF_TEXT, INFO_TEXT,
    CONFIG_INSTRUCTION_TEXT, DATABASE_PATH, TRIAL_DAYS,
    INSTALL_IPHONE_TEXT, INSTALL_ANDROID_TEXT, INSTALL_WINDOWS_TEXT, INSTALL_MAC_TEXT,
    INSTALL_LINUX_TEXT
)
from database import (
    init_db, get_user, create_user,
    activate_subscription, is_subscription_active,
    add_payment, get_user_stats, update_user,
    is_cheese_eligible, get_pending_cheese_orders, update_cheese_order,
    get_used_wg_ips, get_wg_peers
)
from vpn_manager import (
    generate_wg_keys, create_client_config, save_client_config,
    get_next_ip, add_peer, remove_peer, WireGuardError
)
from payments import (
    create_payment_link, check_payment_status,
    get_tariff_info, format_subscription_status,
    format_payment_message
)
from ozon_helper import (
    generate_ozon_link, format_cheese_order_message,
    format_cheese_delivery_message, OZON_PRODUCT_NAME, OZON_PRODUCT_PRICE
)
from pvz_finder import (
    get_city_keyboard, get_pvz_keyboard, get_city_name,
    get_pvz_by_id, format_order_message, POPULAR_CITIES
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Как часто проверять истёкшие подписки и отключать их от VPN (секунды)
EXPIRED_PEERS_CHECK_INTERVAL = 3600


async def notify_admin(context: ContextTypes.DEFAULT_TYPE, text: str):
    """Отправить сообщение админу, не ломая сценарий пользователя при ошибке"""
    if not ADMIN_ID:
        logger.warning("ADMIN_ID не задан, уведомление админу не отправлено: %s", text)
        return
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode='HTML')
    except Exception as e:
        logger.error("Не удалось отправить сообщение админу %s: %s", ADMIN_ID, e)


def trial_available(user) -> bool:
    """Пробный период доступен только тем, у кого ещё никогда не было подписки"""
    return not user or not user["expires_at"]


def ensure_vpn_peer(user_id: int):
    """Выдать пользователю ключи и IP, добавить его на сервер WireGuard. Возвращает (user, ip)."""
    user = get_user(user_id)
    if not user["wg_private_key"]:
        private_key, public_key = generate_wg_keys()
        update_user(user_id, wg_private_key=private_key, wg_public_key=public_key)
    if not user["wg_ip"]:
        update_user(user_id, wg_ip=get_next_ip(get_used_wg_ips()))
    user = get_user(user_id)
    add_peer(user["wg_public_key"], user["wg_ip"])
    return user


async def send_vpn_key(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int):
    """Отправить пользователю конфиг WireGuard (файл + QR-код)"""
    user = get_user(user_id)
    if not user or not is_subscription_active(user_id):
        await context.bot.send_message(chat_id,
            "Нет активной подписки.\n"
            "Нажмите «Забрать подарок» чтобы получить 3 дня бесплатно или купите подписку через /buy.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Забрать подарок", callback_data="claim_gift")]])
        )
        return

    try:
        user = ensure_vpn_peer(user_id)
        config = create_client_config(user["wg_private_key"], user["wg_ip"])
    except WireGuardError as e:
        logger.error("Ошибка выдачи VPN-ключа для %s: %s", user_id, e)
        await context.bot.send_message(chat_id,
            "⚠️ Не удалось создать VPN-ключ. Мы уже знаем о проблеме, попробуйте чуть позже "
            "или напишите в поддержку @tvorog_support."
        )
        await notify_admin(context, f"⚠️ Ошибка выдачи VPN-ключа пользователю {user_id}:\n<code>{html.escape(str(e))}</code>")
        return

    path = save_client_config(user_id, config)
    with open(path, "rb") as f:
        await context.bot.send_document(chat_id,
            document=InputFile(f, filename="TvorogVPN.conf"),
            caption="🔑 <b>VPN-ключ готов!</b>\n\nИмпортируйте файл в приложение (WireGuard или Happ).",
            parse_mode='HTML'
        )

    try:
        import qrcode
        buf = io.BytesIO()
        qrcode.make(config).save(buf, format="PNG")
        buf.seek(0)
        await context.bot.send_photo(chat_id, photo=buf,
            caption="📷 Или отсканируйте QR-код в приложении WireGuard на телефоне."
        )
    except Exception as e:
        logger.warning("Не удалось отправить QR-код: %s", e)

    keyboard = [[InlineKeyboardButton("📖 Инструкция", callback_data="instruction")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
    await context.bot.send_message(chat_id,
        "✅ Готово! Если что-то не получается — нажмите «Инструкция».",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Главное меню клавиатура
def get_main_menu_keyboard():
    """Клавиатура главного меню"""
    return [
        [InlineKeyboardButton("🔑 Подключиться", callback_data="connect")],
        [InlineKeyboardButton("🏠 Личный кабинет", callback_data="personal_account"),
         InlineKeyboardButton("ℹ️ Информация", callback_data="info")]
    ]

# Клавиатура выбора устройства
def get_device_keyboard():
    """Клавиатура выбора устройства"""
    return [
        [InlineKeyboardButton("🤖 Android", callback_data="install_android"),
         InlineKeyboardButton("🍎 iPhone/iPad", callback_data="install_iphone")],
        [InlineKeyboardButton("💻 Windows", callback_data="install_windows"),
         InlineKeyboardButton("🖥 MacOS", callback_data="install_mac")],
        [InlineKeyboardButton("🐧 Linux", callback_data="install_linux")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
    ]

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    create_user(user.id, user.username or user.first_name)

    keyboard = [
        [InlineKeyboardButton("🎁 Забрать подарок", callback_data="claim_gift")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    keyboard = [
        [InlineKeyboardButton("💬 Написать в поддержку", url="https://t.me/tvorog_support")],
        [InlineKeyboardButton("🏠 В меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(HELP_TEXT, parse_mode='HTML', reply_markup=reply_markup)

# Команда /buy
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /buy"""
    keyboard = []
    for key, tariff in TARIFFS.items():
        if tariff["price"] == 0:
            text = f"🆓 {tariff['name']} — бесплатно"
        else:
            text = f"💳 {tariff['name']} — {tariff['price']} ₽"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"buy_{key}")])

    keyboard.append([InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(TARIFF_TEXT, parse_mode='HTML', reply_markup=reply_markup)

# Команда /status
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /status"""
    user = get_user(update.effective_user.id)
    if user:
        await update.message.reply_text(format_subscription_status(user), parse_mode='HTML')
    else:
        await update.message.reply_text("❌ Ты ещё не зарегистрирован. Используй /start")

# Команда /servers
async def servers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /servers"""
    keyboard = []
    for server_id, server in SERVERS.items():
        keyboard.append([InlineKeyboardButton(
            f"{server['country']} {server['name']}",
            callback_data=f"server_{server_id}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🌍 <b>Выбери сервер:</b>", parse_mode='HTML', reply_markup=reply_markup)

# Команда /gift — получить творог
async def gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /gift"""
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        await update.message.reply_text("❌ Сначала зарегистрируйся через /start")
        return

    if not is_cheese_eligible(user_id):
        if user["cheese_order_status"] != "none":
            await update.message.reply_text("🔒 Ты уже получил творог в подарок!\nОдна упаковка на аккаунт 🎁")
        else:
            await update.message.reply_text(
                "🔒 <b>Творог в подарок!</b>\n\n"
                "Этот подарок только для тех, кто купил подписку от 1 месяца.\n\n"
                "Купи подписку через /buy и получи настоящий творог домой! 🎁",
                parse_mode='HTML'
            )
        return

    context.user_data["waiting_for_address"] = True
    await update.message.reply_text(
        "🔒 <b>Поздравляю! Ты получаешь творог в подарок!</b>\n\n"
        "Напиши свой адрес для доставки:\n\n"
        "📝 <b>Формат:</b>\nГород, улица, дом, квартира\n\n"
        "Пример: Москва, ул. Пушкина, д. 10, кв. 5",
        parse_mode='HTML'
    )

# Обработка текстовых сообщений (для адреса или города)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    # Если пользователь вводит город вручную
    if context.user_data.get("waiting_for_city"):
        city_name = html.escape(update.message.text)
        context.user_data["waiting_for_city"] = False

        # Показываем сообщение что город принят
        await update.message.reply_text(
            f"🏙️ Город: <b>{city_name}</b>\n\n"
            f"📝 Напиши адрес пункта выдачи Ozon:\n\n"
            f"Пример:\n"
            f"Ozon Волгоград, ул. Ленина, д. 48",
            parse_mode='HTML'
        )
        context.user_data["waiting_for_address"] = True
        return

    # Если пользователь вводит адрес пункта выдачи
    if context.user_data.get("waiting_for_address"):
        user_id = update.effective_user.id
        address = update.message.text
        update_user(user_id, delivery_address=address, cheese_order_status="pending")
        address = html.escape(address)
        context.user_data["waiting_for_address"] = False

        user = get_user(user_id)
        username = html.escape(user["username"] or "Без username")

        # Формируем сообщение для админа
        admin_text = (
            f"🔒 <b>Новый заказ на творог!</b>\n\n"
            f"👤 @{username} (ID: {user_id})\n"
            f"📍 Адрес: {address}\n\n"
            f"📦 Творог Коровка из Кореновки 180г (~76₽)\n\n"
            f"🔗 <a href=\"https://www.ozon.ru/product/154359454\">Открыть на Ozon</a>\n\n"
            f"После заказа: /set_cheese {user_id} ordered"
        )

        await notify_admin(context, admin_text)

        # Ответ пользователю
        await update.message.reply_text(
            "✅ <b>Адрес принят!</b>\n\n"
            "Мы заказываем творог на Ozon.\n"
            "Ожидай доставку в ближайшие дни! 🔒",
            parse_mode='HTML'
        )

# Обработка нажатий на кнопки — НОВЫЕ СООБЩЕНИЯ
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback_query — каждая кнопка = новое сообщение"""
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id

    # === КУПИТЬ VPN ===
    if data == "buy":
        keyboard = []
        for key, tariff in TARIFFS.items():
            if tariff["price"] == 0:
                text = f"🆓 {tariff['name']} — бесплатно"
            else:
                emoji = {"week": "⏰", "month": "📅", "quarter": "📆", "year": "🎯"}.get(key, "💳")
                text = f"{emoji} {tariff['name']} — {tariff['price']} ₽"
            keyboard.append([InlineKeyboardButton(text, callback_data=f"buy_{key}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id, TARIFF_TEXT, parse_mode='HTML', reply_markup=reply_markup)

    # === ВЫБОР ТАРИФА ===
    elif data.startswith("buy_"):
        tariff_key = data.replace("buy_", "")
        if tariff_key == "trial":
            user_id = query.from_user.id
            create_user(user_id, query.from_user.username or query.from_user.first_name)
            if not trial_available(get_user(user_id)):
                await context.bot.send_message(chat_id,
                    "Пробный период уже был использован. Выберите тариф через /buy 🙂"
                )
                return
            activate_subscription(user_id, TRIAL_DAYS)
            add_payment(user_id, 0, "trial", "trial")
            reply_markup = InlineKeyboardMarkup(get_device_keyboard())
            await context.bot.send_message(chat_id,
                f"✅ <b>Пробный период активирован!</b>\n\n{TRIAL_DAYS} дня бесплатно. Выберите устройство:",
                parse_mode='HTML', reply_markup=reply_markup
            )
        elif tariff_key in TARIFFS:
            user_id = query.from_user.id
            tariff = TARIFFS[tariff_key]

            # Создаём платёжную ссылку
            payment = await create_payment_link(tariff_key, user_id)

            if payment:
                # Сохраняем ID платежа в context
                context.user_data["pending_payment"] = {
                    "payment_id": payment["payment_id"],
                    "tariff": tariff_key
                }

                # Сообщение как у Шука VPN
                payment_text = (
                    f"⚡ <b>Счёт на оплату подписки создан.</b>\n\n"
                    f"💰 Стоимость: <b>{tariff['price']} ₽</b>\n"
                    f"📦 Подписка: <b>{tariff['name']}</b>\n"
                    f"⏰ Срок: {tariff['days']} дней\n\n"
                    f"💳 <b>Способы оплаты:</b>\n"
                    f"• Счёт (СБП)\n"
                    f"• Карта ****\n"
                    f"• Система быстрых платежей\n\n"
                    f"📱 СБП или 💳 Карта · <b>{tariff['price']} ₽</b>"
                )
                if DEMO_MODE:
                    payment_text += "\n\n<i>🧪 Демо-режим: деньги не списываются, просто нажмите «Проверить оплату».</i>"

                # Кнопки оплаты
                keyboard = [
                    [InlineKeyboardButton(
                        f"📱 СБП или 💳 Карта · {tariff['price']} ₽",
                        url=payment["confirmation_url"]
                    )],
                    [InlineKeyboardButton(
                        "🔄 Другой способ оплаты",
                        url=payment["confirmation_url"]
                    )]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await context.bot.send_message(chat_id, payment_text, parse_mode='HTML', reply_markup=reply_markup)

                # Кнопка проверки оплаты
                check_keyboard = [[
                    InlineKeyboardButton(
                        "✅ Проверить оплату",
                        callback_data=f"check_payment_{tariff_key}"
                    )
                ]]
                check_markup = InlineKeyboardMarkup(check_keyboard)
                await context.bot.send_message(chat_id,
                    "После оплаты нажми кнопку ниже:",
                    reply_markup=check_markup
                )
            else:
                await context.bot.send_message(chat_id,
                    "❌ Ошибка создания платежа. Попробуй позже.",
                    parse_mode='HTML'
                )

    # === ПРОВЕРКА ОПЛАТЫ ===
    elif data.startswith("check_payment_"):
        user_id = query.from_user.id
        pending = context.user_data.get("pending_payment")

        if pending and pending.get("payment_id"):
            # Тариф берём из созданного платежа, а не из кнопки — её можно подделать
            tariff_key = pending["tariff"]
            payment_status = await check_payment_status(pending["payment_id"])
            metadata = payment_status.get("metadata", {})

            if payment_status["paid"] and metadata.get("user_id") not in (None, str(user_id)):
                logger.warning("Платёж %s принадлежит другому пользователю", pending["payment_id"])
                context.user_data.pop("pending_payment", None)
                await context.bot.send_message(chat_id, "❌ Платёж не найден. Начни заново через /buy")
            elif payment_status["paid"]:
                # Оплата прошла!
                activate_subscription(user_id, TARIFFS[tariff_key]["days"])
                add_payment(user_id, TARIFFS[tariff_key]["price"], tariff_key, pending["payment_id"])

                reply_markup = InlineKeyboardMarkup(get_device_keyboard())

                await context.bot.send_message(chat_id,
                    "✅ <b>Оплата прошла успешно!</b>\n\n"
                    "Твоя подписка активирована!\n\n"
                    "Выбери устройство, чтобы получить VPN-ключ:",
                    parse_mode='HTML', reply_markup=reply_markup
                )

                # Творог при подписке от 1 месяца
                if tariff_key in ["month", "quarter", "year"]:
                    await context.bot.send_message(chat_id,
                        "🔒 <b>Поздравляю! Ты получаешь творог!</b>\n\n"
                        "Нажми кнопку ниже и выбери город:",
                        parse_mode='HTML',
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎁 Получить творог", callback_data="gift")]])
                    )

                context.user_data.pop("pending_payment", None)
            else:
                await context.bot.send_message(chat_id,
                    "⏳ Оплата ещё не поступила.\n"
                    "Попробуй проверить через минуту.",
                    parse_mode='HTML'
                )
        else:
            await context.bot.send_message(chat_id,
                "❌ Нет активного платежа. Начни заново через /buy",
                parse_mode='HTML'
            )

    # === МОЙ СТАТУС ===
    elif data == "status":
        user = get_user(query.from_user.id)
        if user:
            await context.bot.send_message(chat_id, format_subscription_status(user), parse_mode='HTML')
        else:
            await context.bot.send_message(chat_id, "❌ Ты ещё не зарегистрирован")

    # === СЕРВЕРЫ ===
    elif data == "servers":
        keyboard = []
        for server_id, server in SERVERS.items():
            keyboard.append([InlineKeyboardButton(
                f"{server['country']} {server['name']}",
                callback_data=f"server_{server_id}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id, "🌍 <b>Выбери сервер:</b>", parse_mode='HTML', reply_markup=reply_markup)

    # === ВЫБОР СЕРВЕРА ===
    elif data.startswith("server_"):
        server_id = data.replace("server_", "")
        if server_id in SERVERS:
            server = SERVERS[server_id]
            await context.bot.send_message(chat_id,
                f"🌍 <b>{server['name']}</b>\n\n"
                f"Страна: {server['country']}\n"
                f"IP: {server['ip']}\n"
                f"Порт: {server['port']}\n\n"
                f"Теперь купи подписку через /buy",
                parse_mode='HTML'
            )

    # === ПОМОЩЬ ===
    elif data == "help":
        keyboard = [
            [InlineKeyboardButton("💬 Написать в поддержку", url="https://t.me/tvorog_support")],
            [InlineKeyboardButton("🏠 Назад в меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id, HELP_TEXT, parse_mode='HTML', reply_markup=reply_markup)

    # === ПОДКЛЮЧИТЬСЯ (выбор устройства) ===
    elif data == "connect":
        reply_markup = InlineKeyboardMarkup(get_device_keyboard())
        await context.bot.send_message(chat_id,
            "Выберите устройство, которое хотите подключить:",
            reply_markup=reply_markup
        )

    # === ИНФОРМАЦИЯ О СЕРВИСЕ ===
    elif data == "info":
        keyboard = [
            [InlineKeyboardButton("📖 Инструкция", url="https://t.me/tvorog_vpn_bot")],
            [InlineKeyboardButton("🔑 Тех. поддержка", url="https://t.me/tvorog_support")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id, INFO_TEXT, parse_mode='HTML', reply_markup=reply_markup)

    # === ЛИЧНЫЙ КАБИНЕТ ===
    elif data == "personal_account":
        user_id = query.from_user.id
        user = get_user(user_id)

        if user:
            from datetime import datetime
            expires = user["expires_at"][:10] if user["expires_at"] else "Неизвестно"
            is_active = "Активна" if user["expires_at"] and datetime.fromisoformat(user["expires_at"]) > datetime.now() else "Не активна"

            account_text = f"""
<b>Личный кабинет</b>

<b>ID:</b> {user_id}
<b>Email:</b> {query.from_user.username or "Не указан"}

<b>Информация о подписке:</b>
• Текущий план: {is_active}
• Дата окончания: {expires}

<b>Команды:</b>
"""
            keyboard = [
                [InlineKeyboardButton("🔑 Подключиться", callback_data="connect")],
                [InlineKeyboardButton("📖 Инструкция", callback_data="help")],
                [InlineKeyboardButton("🎁 Получить творог", callback_data="gift")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id, account_text, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id, "Вы ещё не зарегистрированы. Нажмите /start")

    # === ЗАБРАТЬ ПОДАРОК (3 дня бесплатно) ===
    elif data == "claim_gift":
        user_id = query.from_user.id
        create_user(user_id, query.from_user.username or query.from_user.first_name)
        user = get_user(user_id)

        if is_subscription_active(user_id):
            # Уже есть активная подписка
            keyboard = [[InlineKeyboardButton("📱 Выбрать устройство", callback_data="select_device")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id,
                "🎉 У вас уже есть активная подписка!\n\n"
                "📱 Выберите устройство для установки:",
                reply_markup=reply_markup
            )
            return

        # Пробный период — только один раз
        if not trial_available(user):
            keyboard = [[InlineKeyboardButton("💳 Купить подписку", callback_data="buy")]]
            await context.bot.send_message(chat_id,
                "Пробный период уже был использован, а подписка закончилась.\n\n"
                "Продлите подписку, чтобы продолжить пользоваться VPN:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        # Активируем пробный период
        activate_subscription(user_id, TRIAL_DAYS)
        add_payment(user_id, 0, "trial", "trial")

        keyboard = [[InlineKeyboardButton("📱 Выбрать устройство", callback_data="select_device")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(chat_id,
            f"🎉 Пробный период на {TRIAL_DAYS} дня активирован!\n\n"
            "📱 Теперь выберите ваше устройство, чтобы получить VPN-ключ:",
            reply_markup=reply_markup
        )

    # === ВЫБОР УСТРОЙСТВА ===
    elif data == "select_device" or data == "devices":
        reply_markup = InlineKeyboardMarkup(get_device_keyboard())
        await context.bot.send_message(chat_id,
            "📱 Выберите устройство, чтобы получить VPN-ключ:",
            reply_markup=reply_markup
        )

    # === УСТАНОВКА IPHONE ===
    elif data == "install_iphone":
        keyboard = [
            [InlineKeyboardButton("🔑 Получить VPN-ключ", callback_data="get_config_iphone")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id, INSTALL_IPHONE_TEXT, parse_mode='HTML', reply_markup=reply_markup)

    # === УСТАНОВКА ANDROID ===
    elif data == "install_android":
        keyboard = [
            [InlineKeyboardButton("🔑 Получить VPN-ключ", callback_data="get_config_android")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id, INSTALL_ANDROID_TEXT, parse_mode='HTML', reply_markup=reply_markup)

    # === УСТАНОВКА WINDOWS ===
    elif data == "install_windows":
        keyboard = [
            [InlineKeyboardButton("🔑 Получить VPN-ключ", callback_data="get_config_windows")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id, INSTALL_WINDOWS_TEXT, parse_mode='HTML', reply_markup=reply_markup)

    # === УСТАНОВКА MAC ===
    elif data == "install_mac":
        keyboard = [
            [InlineKeyboardButton("🔑 Получить VPN-ключ", callback_data="get_config_mac")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id, INSTALL_MAC_TEXT, parse_mode='HTML', reply_markup=reply_markup)

    # === УСТАНОВКА LINUX ===
    elif data == "install_linux":
        keyboard = [
            [InlineKeyboardButton("🔑 Получить VPN-ключ", callback_data="get_config_linux")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id, INSTALL_LINUX_TEXT, parse_mode='HTML', reply_markup=reply_markup)

    # === ПОЛУЧИТЬ VPN-КЛЮЧ (для всех устройств) ===
    # get_config_iphone / get_config_android / ... и старые кнопки get_config_<id>.
    # Ключ всегда выдаётся только тому, кто нажал кнопку.
    elif data.startswith("get_config_"):
        await send_vpn_key(context, chat_id, query.from_user.id)

    # === ПОЛУЧИТЬ ТВОРОГ ===
    elif data == "gift":
        user_id = query.from_user.id
        if is_cheese_eligible(user_id):
            # Показываем выбор города
            reply_markup = get_city_keyboard()
            await context.bot.send_message(chat_id,
                "🔒 <b>Поздравляю! Творог в подарок!</b>\n\n"
                "Выбери свой город для доставки:",
                parse_mode='HTML', reply_markup=reply_markup
            )
        else:
            user = get_user(user_id)
            if user and user["cheese_order_status"] != "none":
                text = "🔒 Ты уже получил творог!\nОдна упаковка на аккаунт 🎁"
            else:
                text = "🔒 <b>Творог в подарок!</b>\n\nТолько при покупке от 1 месяца.\nКупи через /buy! 🎁"
            await context.bot.send_message(chat_id, text, parse_mode='HTML')

    # === ВЫБОР ГОРОДА ===
    elif data.startswith("city_"):
        city_id = data.replace("city_", "")
        if city_id == "other":
            context.user_data["waiting_for_city"] = True
            await context.bot.send_message(chat_id,
                "📝 Напиши название своего города:",
                parse_mode='HTML'
            )
        else:
            # Сохраняем город
            context.user_data["selected_city"] = city_id
            city_name = get_city_name(city_id)

            # Показываем пункты выдачи
            reply_markup = get_pvz_keyboard(city_id)
            await context.bot.send_message(chat_id,
                f"🏙️ <b>{city_name}</b>\n\n"
                f"Выбери пункт выдачи Ozon:",
                parse_mode='HTML', reply_markup=reply_markup
            )

    # === ВЫБОР ПУНКТА ВЫДАЧИ ===
    elif data.startswith("pvz_"):
        # city_id может содержать "_" (nizhny_novgorod), поэтому режем справа
        city_id, pvz_id = data[len("pvz_"):].rsplit("_", 1)

        user_id = query.from_user.id
        if not is_cheese_eligible(user_id):
            await context.bot.send_message(chat_id, "🔒 Творог доступен только при покупке подписки от 1 месяца.")
            return

        user = get_user(user_id)
        username = html.escape(user["username"] or "Без username")

        city_name = get_city_name(city_id)
        pvz = get_pvz_by_id(city_id, pvz_id)
        if not pvz:
            await context.bot.send_message(chat_id, "❌ Пункт выдачи не найден, выберите ещё раз.")
            return

        # Отправляем админу
        await notify_admin(context, format_order_message(username, user_id, city_id, pvz_id))

        # Сохраняем данные

        update_user(user_id,
            delivery_address=f"{city_name}, {pvz['address']}",
            cheese_order_status="pending"
        )

        # Ответ пользователю
        await context.bot.send_message(chat_id,
            f"✅ <b>Выбор принят!</b>\n\n"
            f"🏙️ Город: {city_name}\n"
            f"📍 Пункт: {pvz['name']}\n"
            f"📍 Адрес: {pvz['address']}\n\n"
            f"Мы заказываем творог на Ozon.\n"
            f"Ожидай доставку в ближайшие дни! 🔒\n\n"
            f"💡 <i>Творог можно добавить в кашу или есть просто так 😋</i>",
            parse_mode='HTML'
        )

    # === НАЗАД К ГОРОДАМ ===
    elif data == "back_to_cities":
        reply_markup = get_city_keyboard()
        await context.bot.send_message(chat_id,
            "🏙️ Выбери свой город:",
            parse_mode='HTML', reply_markup=reply_markup
        )

    # === ГЛАВНОЕ МЕНЮ ===
    elif data == "back_to_menu":
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard())
        await context.bot.send_message(chat_id,
            WELCOME_TEXT,
            parse_mode='HTML', reply_markup=reply_markup
        )

    # === ИНСТРУКЦИЯ ===
    elif data == "instruction":
        await context.bot.send_message(chat_id, CONFIG_INSTRUCTION_TEXT, parse_mode='HTML')

# Команда /admin
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ-панель с расширенной статистикой"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет доступа")
        return

    stats = get_user_stats()

    # Форматируем статистику по тарифам
    tariffs_text = ""
    for tariff, data in stats.get("tariffs_stats", {}).items():
        tariffs_text += f"  • {tariff}: {data['count']} продаж ({data['revenue']} ₽)\n"

    admin_text = f"""
📊 <b>Админ-панель {BOT_NAME}</b>

━━━━━━━━━━━━━━━━━━━━━━

👥 <b>Пользователи:</b>
  • Всего: {stats['total_users']}
  • Активных: {stats['active_users']}
  • Новых сегодня: {stats['new_today']}
  • Новых за неделю: {stats['new_week']}

━━━━━━━━━━━━━━━━━━━━━━

💰 <b>Доход:</b>
  • Сегодня: {stats['today_revenue']} ₽
  • За неделю: {stats['week_revenue']} ₽
  • За месяц: {stats['month_revenue']} ₽
  • Всего: {stats['total_revenue']} ₽

━━━━━━━━━━━━━━━━━━━━━━

📦 <b>Продажи по тарифам:</b>
{tariffs_text if tariffs_text else "  Нет продаж"}

━━━━━━━━━━━━━━━━━━━━━━

🧪 <b>Пробные периоды:</b>
  • Взяли: {stats['trial_users']}
  • Купили потом: {stats['paid_users']}

━━━━━━━━━━━━━━━━━━━━━━

🔒 <b>Творог:</b>
  • Заказов: {stats['cheese_orders']}
  • Ожидают: {stats['cheese_pending']}
  • Доставлено: {stats['cheese_delivered']}

━━━━━━━━━━━━━━━━━━━━━━

📝 <b>Команды:</b>
/add_user ID DAYS — Добавить подписку
/cheese_orders — Заказы творога
/order_cheese ID — Заказать на Ozon
/set_cheese ID STATUS — Статус творога
/users — Список пользователей
"""
    await update.message.reply_text(admin_text, parse_mode='HTML')

# Команда /add_user
async def add_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление подписки"""
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        user_id = int(context.args[0])
        days = int(context.args[1])
        activate_subscription(user_id, days)
        await update.message.reply_text(f"✅ Подписка на {days} дней добавлена ({user_id})")
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /add_user USER_ID DAYS")

# Команда /users — список пользователей
async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список активных пользователей"""
    if update.effective_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT user_id, username, expires_at FROM users WHERE is_active = 1 AND expires_at > ? ORDER BY expires_at DESC LIMIT 20",
        (datetime.now().isoformat(),)
    )
    users = cursor.fetchall()
    conn.close()

    if not users:
        await update.message.reply_text("📋 Нет активных пользователей")
        return

    text = "📋 <b>Активные пользователи (последние 20):</b>\n\n"
    for user_id, username, expires_at in users:
        expires = datetime.fromisoformat(expires_at)
        days_left = (expires - datetime.now()).days
        text += f"👤 @{username or 'нет'} (ID: {user_id})\n"
        text += f"   ⏰ До: {expires.strftime('%d.%m.%Y')} ({days_left} дн.)\n\n"

    await update.message.reply_text(text, parse_mode='HTML')

# Команда /cheese_orders
async def cheese_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pending заказы на творог"""
    if update.effective_user.id != ADMIN_ID:
        return
    orders = get_pending_cheese_orders()
    if not orders:
        await update.message.reply_text("🔒 Нет pending заказов")
        return
    text = "🔒 <b>Pending заказы:</b>\n\n"
    for o in orders:
        text += f"👤 @{o['username']} (ID: {o['user_id']})\n📍 {o['address']}\n✅ /set_cheese {o['user_id']} ordered\n\n"
    await update.message.reply_text(text, parse_mode='HTML')

# Команда /set_cheese
async def set_cheese(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменить статус творога"""
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        user_id = int(context.args[0])
        status = context.args[1]
        if status not in ["pending", "ordered", "delivered", "none"]:
            await update.message.reply_text("Статус: pending, ordered, delivered, none")
            return
        update_cheese_order(user_id, status)
        await update.message.reply_text(f"✅ Статус творога для {user_id} → {status}")
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /set_cheese USER_ID STATUS")

# Команда /order_cheese USER_ID — быстрый переход на Ozon
async def order_cheese(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Открыть Ozon для заказа творога"""
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        user_id = int(context.args[0])
        user = get_user(user_id)
        if not user or not user["delivery_address"]:
            await update.message.reply_text("❌ У пользователя нет адреса")
            return

        address = user["delivery_address"]
        username = user["username"] or "Без username"
        ozon_link = generate_ozon_link(address)

        await update.message.reply_text(
            f"🔒 <b>Заказ творога</b>\n\n"
            f"👤 @{username} (ID: {user_id})\n"
            f"📍 Адрес: {address}\n\n"
            f"📦 {OZON_PRODUCT_NAME}\n"
            f"💰 Цена: {OZON_PRODUCT_PRICE}₽\n\n"
            f"🔗 <a href=\"{ozon_link}\">Открыть на Ozon</a>\n\n"
            f"После заказа: /set_cheese {user_id} ordered",
            parse_mode='HTML'
        )
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /order_cheese USER_ID")

async def sync_wg_peers(context: ContextTypes.DEFAULT_TYPE):
    """Отключить истёкшие подписки от VPN"""
    for peer in get_wg_peers(active=False):
        try:
            remove_peer(peer["public_key"])
        except WireGuardError as e:
            logger.warning("Не удалось отключить пир %s: %s", peer["user_id"], e)


async def post_init(application: Application):
    """После старта: вернуть активных пользователей в WireGuard (после перезагрузки сервера пиры теряются)"""
    restored = 0
    for peer in get_wg_peers(active=True):
        try:
            add_peer(peer["public_key"], peer["ip"])
            restored += 1
        except WireGuardError as e:
            logger.error("Не удалось восстановить пир %s: %s", peer["user_id"], e)
            break
    logger.info("Восстановлено VPN-подключений: %s", restored)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Логировать все ошибки, чтобы бот не падал молча"""
    if isinstance(context.error, Conflict):
        logger.error(
            "Конфликт: этот же токен используется другой копией бота. "
            "Остановите старую копию или перевыпустите токен в @BotFather."
        )
        return
    logger.error("Ошибка при обработке обновления %s", update, exc_info=context.error)


def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        sys.exit("❌ BOT_TOKEN не задан. Впишите токен от @BotFather в файл .env (BOT_TOKEN=...)")
    if not ADMIN_ID:
        logger.warning("ADMIN_ID не задан — админ-команды и уведомления о заказах работать не будут")

    init_db()
    persistence = PicklePersistence(filepath=os.environ.get("PERSISTENCE_PATH", "bot_state.pickle"))
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .persistence(persistence)
        .post_init(post_init)
        .build()
    )

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("buy", buy))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("servers", servers))
    application.add_handler(CommandHandler("gift", gift))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CommandHandler("add_user", add_user_command))
    application.add_handler(CommandHandler("cheese_orders", cheese_orders))
    application.add_handler(CommandHandler("set_cheese", set_cheese))
    application.add_handler(CommandHandler("order_cheese", order_cheese))
    application.add_handler(CommandHandler("users", users_list))

    # Кнопки
    application.add_handler(CallbackQueryHandler(button_callback))

    # Текст (для адреса)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.add_error_handler(error_handler)

    if application.job_queue:
        application.job_queue.run_repeating(sync_wg_peers, interval=EXPIRED_PEERS_CHECK_INTERVAL, first=60)
    else:
        logger.warning("JobQueue недоступен: установите python-telegram-bot[job-queue]")

    if DEMO_MODE:
        logger.warning("ДЕМО-РЕЖИМ: VPN-ключи не настоящие, оплата засчитывается без денег")
    logger.info("🔒 %s запускается...", BOT_NAME)
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except InvalidToken:
        sys.exit("❌ Telegram отклонил токен. Проверьте BOT_TOKEN в .env или перевыпустите его в @BotFather")

def run_api_server():
    """Запуск API сервера для админ-панели"""
    from api import run_server
    import threading
    port = int(os.environ.get("API_PORT", "8080"))
    thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    thread.start()

if __name__ == '__main__':
    # Запускаем API сервер если включено
    if os.environ.get("ENABLE_API", "false").lower() == "true":
        run_api_server()
    main()
