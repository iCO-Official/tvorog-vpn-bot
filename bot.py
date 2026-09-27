import html
import io
import logging
import os
import sqlite3
import sys
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile,
    BotCommand, LinkPreviewOptions
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, Conflict, InvalidToken
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    Defaults,
    MessageHandler,
    PicklePersistence,
    filters,
    ContextTypes
)

from config import (
    BOT_TOKEN, TARIFFS, SERVERS, ADMIN_ID, BOT_NAME, DEMO_MODE,
    WELCOME_TEXT, HELP_TEXT, INFO_TEXT,
    CONFIG_INSTRUCTION_TEXT, DATABASE_PATH, TRIAL_DAYS, MAX_DEVICES,
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
from payments import create_payment_link, check_payment_status
from ozon_helper import generate_ozon_link, OZON_PRODUCT_NAME, OZON_PRODUCT_PRICE
from pvz_finder import (
    get_city_name, get_pvz_list, get_pvz_by_id, format_order_message, POPULAR_CITIES
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

SUPPORT_URL = "https://t.me/tvorog_support"

DEVICES = {
    "iphone": ("🍎 iPhone / iPad", INSTALL_IPHONE_TEXT),
    "android": ("🤖 Android", INSTALL_ANDROID_TEXT),
    "windows": ("💻 Windows", INSTALL_WINDOWS_TEXT),
    "mac": ("🖥 macOS", INSTALL_MAC_TEXT),
    "linux": ("🐧 Linux", INSTALL_LINUX_TEXT),
}

# Тарифы с подарком-творогом
CHEESE_TARIFFS = ["month", "quarter", "year"]


# ───────────────────────── Вспомогательное ─────────────────────────

def btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text, callback_data=data)


def url_btn(text: str, url: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text, url=url)


MENU_ROW = [btn("‹ Главное меню", "back_to_menu")]


def plural_days(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} день"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return f"{n} дня"
    return f"{n} дней"


def format_date(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%d.%m.%Y")


def days_left(iso: str) -> int:
    return max((datetime.fromisoformat(iso) - datetime.now()).days, 0)


def trial_available(user) -> bool:
    """Пробный период доступен только тем, у кого ещё никогда не было подписки"""
    return not user or not user["expires_at"]


def register(update: Update):
    """Создать пользователя, если его ещё нет, и вернуть его"""
    tg_user = update.effective_user
    create_user(tg_user.id, tg_user.username or tg_user.first_name)
    return get_user(tg_user.id)


async def show(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, keyboard=None):
    """Показать экран. Нажата кнопка — меняем текущее сообщение, команда — отправляем новое."""
    markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    query = update.callback_query
    if query:
        try:
            await query.edit_message_text(text, reply_markup=markup)
            return
        except BadRequest as e:
            if "not modified" in str(e).lower():
                return
            # Сообщение с файлом или фото редактировать нельзя — отправим новое
        await context.bot.send_message(query.message.chat_id, text, reply_markup=markup)
    else:
        await update.effective_message.reply_text(text, reply_markup=markup)


async def notify_admin(context: ContextTypes.DEFAULT_TYPE, text: str):
    """Отправить сообщение админу, не ломая сценарий пользователя при ошибке"""
    if not ADMIN_ID:
        logger.warning("ADMIN_ID не задан, уведомление админу не отправлено: %s", text)
        return
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=text)
    except Exception as e:
        logger.error("Не удалось отправить сообщение админу %s: %s", ADMIN_ID, e)


# ───────────────────────── Экраны ─────────────────────────

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = register(update)
    keyboard = []
    if trial_available(user):
        keyboard.append([btn(f"🎁 Попробовать {plural_days(TRIAL_DAYS)} бесплатно", "claim_gift")])
    keyboard += [
        [btn("🔑 Подключить устройство", "connect")],
        [btn("💳 Тарифы", "buy"), btn("👤 Кабинет", "personal_account")],
        [btn("ℹ️ О сервисе", "info"), url_btn("💬 Поддержка", SUPPORT_URL)],
    ]
    text = WELCOME_TEXT.strip()
    if not trial_available(user):
        # Строка-призыв про пробный период не нужна, если кнопки уже нет
        text = "\n".join(line for line in text.splitlines() if not line.startswith("✨")).strip()
    await show(update, context, text, keyboard)


def tariff_discount(key: str) -> int:
    """Скидка тарифа относительно помесячной оплаты, %"""
    month = TARIFFS["month"]
    tariff = TARIFFS[key]
    full_price = month["price"] / month["days"] * tariff["days"]
    return round((1 - tariff["price"] / full_price) * 100)


async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "<b>💳 Тарифы</b>\n\n"
        "В каждый тариф входит:\n"
        f"• до {MAX_DEVICES} устройств на одну подписку\n"
        "• безлимитный трафик и высокая скорость\n"
        "• поддержка 24/7\n"
        "• 🎁 творог в подарок\n\n"
        "Выберите срок подписки:"
    )
    keyboard = []
    for key, tariff in TARIFFS.items():
        if tariff["price"] == 0:
            continue
        label = f"{tariff['name']} · {tariff['price']} ₽"
        discount = tariff_discount(key)
        if discount >= 5:
            label += f"  (−{discount}%)"
        keyboard.append([btn(label, f"buy_{key}")])
    keyboard.append(MENU_ROW)
    await show(update, context, text, keyboard)


async def show_devices(update: Update, context: ContextTypes.DEFAULT_TYPE, title: str = None):
    text = (title or "<b>🔑 Подключение</b>") + (
        "\n\nВыберите устройство — пришлём короткую инструкцию и персональный ключ."
    )
    names = {key: name for key, (name, _) in DEVICES.items()}
    keyboard = [
        [btn(names["iphone"], "install_iphone"), btn(names["android"], "install_android")],
        [btn(names["windows"], "install_windows"), btn(names["mac"], "install_mac")],
        [btn(names["linux"], "install_linux")],
        MENU_ROW,
    ]
    await show(update, context, text, keyboard)


async def show_install(update: Update, context: ContextTypes.DEFAULT_TYPE, device: str):
    _, text = DEVICES[device]
    keyboard = [
        [btn("🔑 Получить ключ", f"get_config_{device}")],
        [btn("‹ Назад", "connect")],
    ]
    await show(update, context, text.strip(), keyboard)


async def show_no_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    keyboard = []
    if trial_available(user):
        keyboard.append([btn(f"🎁 Попробовать {plural_days(TRIAL_DAYS)} бесплатно", "claim_gift")])
    keyboard += [[btn("💳 Выбрать тариф", "buy")], MENU_ROW]
    await show(update, context,
        "<b>Подписка не активна</b>\n\n"
        "Чтобы получить ключ, оформите подписку"
        + (" или попробуйте бесплатно." if trial_available(user) else "."),
        keyboard
    )


async def show_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = register(update)
    user_id = user["user_id"]
    active = is_subscription_active(user_id)

    lines = ["<b>👤 Личный кабинет</b>", "", f"ID: <code>{user_id}</code>"]
    if active:
        lines += [
            "Подписка: ✅ активна",
            f"Действует до: <b>{format_date(user['expires_at'])}</b> "
            f"(осталось {plural_days(days_left(user['expires_at']))})",
        ]
    elif user["expires_at"]:
        lines.append(f"Подписка: ❌ закончилась {format_date(user['expires_at'])}")
    else:
        lines.append("Подписка: ❌ не оформлена")
    lines.append(f"Устройства: до {MAX_DEVICES}")

    keyboard = []
    if active:
        keyboard.append([btn("🔑 Подключить устройство", "connect")])
    keyboard.append([btn("💳 Продлить подписку" if user["expires_at"] else "💳 Оформить подписку", "buy")])
    if is_cheese_eligible(user_id):
        keyboard.append([btn("🎁 Получить творог", "gift")])
    keyboard.append(MENU_ROW)
    await show(update, context, "\n".join(lines), keyboard)


async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [btn("📖 Как подключиться", "instruction")],
        [url_btn("💬 Поддержка", SUPPORT_URL)],
        MENU_ROW,
    ]
    await show(update, context, INFO_TEXT.strip(), keyboard)


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[url_btn("💬 Написать в поддержку", SUPPORT_URL)], MENU_ROW]
    await show(update, context, HELP_TEXT.strip(), keyboard)


async def show_instruction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[btn("🔑 Подключить устройство", "connect")], MENU_ROW]
    await show(update, context, CONFIG_INSTRUCTION_TEXT.strip(), keyboard)


async def show_servers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["<b>🌍 Серверы</b>", ""]
    for server in SERVERS.values():
        lines.append(f"• {server['name']} — {server['country']}")
    lines += ["", "Сервер подбирается автоматически при подключении."]
    await show(update, context, "\n".join(lines), [[btn("🔑 Подключить устройство", "connect")], MENU_ROW])


# ───────────────────────── Пробный период и оплата ─────────────────────────

async def claim_trial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = register(update)
    user_id = user["user_id"]

    if is_subscription_active(user_id):
        await show_devices(update, context,
            f"<b>✅ Подписка уже активна</b>\n\nДействует до <b>{format_date(user['expires_at'])}</b>."
        )
        return

    if not trial_available(user):
        await show(update, context,
            "<b>Пробный период уже использован</b>\n\n"
            "Оформите подписку, чтобы продолжить пользоваться VPN.",
            [[btn("💳 Выбрать тариф", "buy")], MENU_ROW]
        )
        return

    activate_subscription(user_id, TRIAL_DAYS)
    add_payment(user_id, 0, "trial", "trial")
    user = get_user(user_id)
    await show_devices(update, context,
        f"<b>🎁 Пробный период активирован</b>\n\n"
        f"{plural_days(TRIAL_DAYS).capitalize()} бесплатного доступа — до <b>{format_date(user['expires_at'])}</b>."
    )


async def create_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE, tariff_key: str):
    user_id = update.effective_user.id
    register(update)
    tariff = TARIFFS[tariff_key]

    payment = await create_payment_link(tariff_key, user_id)
    if not payment:
        await show(update, context,
            "<b>⚠️ Не удалось создать счёт</b>\n\n"
            "Попробуйте через пару минут или напишите в поддержку.",
            [[url_btn("💬 Поддержка", SUPPORT_URL)], [btn("‹ Назад к тарифам", "buy")]]
        )
        return

    context.user_data["pending_payment"] = {"payment_id": payment["payment_id"], "tariff": tariff_key}
    demo_payment = payment["payment_id"].startswith("demo-")

    text = (
        "<b>🧾 Оформление подписки</b>\n\n"
        f"Тариф: <b>{tariff['name']}</b>\n"
        f"Срок: {plural_days(tariff['days'])}\n"
        f"К оплате: <b>{tariff['price']} ₽</b>\n\n"
        "Оплата банковской картой или через СБП."
    )
    if tariff_key in CHEESE_TARIFFS:
        text += "\n🎁 После оплаты — творог в подарок."

    if demo_payment:
        text += "\n\n<i>Демо-режим: деньги не списываются.</i>"
        keyboard = [[btn(f"💳 Оплатить {tariff['price']} ₽", f"check_payment_{tariff_key}")]]
    else:
        text += "\n\nПосле оплаты вернитесь сюда и нажмите «Я оплатил»."
        keyboard = [
            [url_btn(f"💳 Оплатить {tariff['price']} ₽", payment["confirmation_url"])],
            [btn("✅ Я оплатил", f"check_payment_{tariff_key}")],
        ]
    keyboard.append([btn("‹ Назад к тарифам", "buy")])
    await show(update, context, text, keyboard)


async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    pending = context.user_data.get("pending_payment")

    if not pending or not pending.get("payment_id"):
        await query.answer("Счёт устарел. Оформите подписку заново.", show_alert=True)
        await show_tariffs(update, context)
        return

    # Тариф берём из созданного платежа, а не из кнопки — её можно подделать
    tariff_key = pending["tariff"]
    payment_status = await check_payment_status(pending["payment_id"])
    owner = payment_status.get("metadata", {}).get("user_id")

    if not payment_status["paid"]:
        await query.answer("Оплата ещё не поступила. Попробуйте через минуту.", show_alert=True)
        return

    if owner not in (None, str(user_id)):
        logger.warning("Платёж %s принадлежит другому пользователю", pending["payment_id"])
        context.user_data.pop("pending_payment", None)
        await query.answer("Платёж не найден. Оформите подписку заново.", show_alert=True)
        return

    await query.answer("Оплата получена!")
    tariff = TARIFFS[tariff_key]
    activate_subscription(user_id, tariff["days"])
    add_payment(user_id, tariff["price"], tariff_key, pending["payment_id"])
    context.user_data.pop("pending_payment", None)

    user = get_user(user_id)
    keyboard = [[btn("🔑 Подключить устройство", "connect")]]
    text = (
        "<b>✅ Оплата прошла успешно</b>\n\n"
        f"Подписка «{tariff['name']}» активна до <b>{format_date(user['expires_at'])}</b>.\n\n"
        "Подключите устройство — это займёт минуту."
    )
    if is_cheese_eligible(user_id):
        text += "\n\n🎁 А ещё вам положен творог в подарок!"
        keyboard.append([btn("🎁 Получить творог", "gift")])
    keyboard.append(MENU_ROW)
    await show(update, context, text, keyboard)


# ───────────────────────── VPN-ключ ─────────────────────────

def ensure_vpn_peer(user_id: int):
    """Выдать пользователю ключи и IP, добавить его на сервер WireGuard"""
    user = get_user(user_id)
    if not user["wg_private_key"]:
        private_key, public_key = generate_wg_keys()
        update_user(user_id, wg_private_key=private_key, wg_public_key=public_key)
    if not user["wg_ip"]:
        update_user(user_id, wg_ip=get_next_ip(get_used_wg_ips()))
    user = get_user(user_id)
    add_peer(user["wg_public_key"], user["wg_ip"])
    return user


async def send_vpn_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить пользователю ключ WireGuard (файл + QR-код). Ключ — всегда того, кто нажал."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    register(update)

    if not is_subscription_active(user_id):
        await show_no_subscription(update, context)
        return

    try:
        user = ensure_vpn_peer(user_id)
        config = create_client_config(user["wg_private_key"], user["wg_ip"])
    except WireGuardError as e:
        logger.error("Ошибка выдачи VPN-ключа для %s: %s", user_id, e)
        await show(update, context,
            "<b>⚠️ Не удалось создать ключ</b>\n\n"
            "Мы уже знаем о проблеме. Попробуйте чуть позже или напишите в поддержку.",
            [[url_btn("💬 Поддержка", SUPPORT_URL)], MENU_ROW]
        )
        await notify_admin(context, f"⚠️ Ошибка выдачи VPN-ключа пользователю {user_id}:\n<code>{html.escape(str(e))}</code>")
        return

    path = save_client_config(user_id, config)
    with open(path, "rb") as f:
        await context.bot.send_document(chat_id,
            document=InputFile(f, filename="TvorogVPN.conf"),
            caption=(
                "<b>🔑 Ваш ключ Творог VPN</b>\n\n"
                "Откройте файл и импортируйте его в приложение.\n"
                "<i>Не пересылайте ключ другим людям.</i>"
            )
        )

    keyboard = InlineKeyboardMarkup([[btn("📖 Как подключиться", "instruction")], MENU_ROW])
    try:
        import qrcode
        buf = io.BytesIO()
        qrcode.make(config).save(buf, format="PNG")
        buf.seek(0)
        await context.bot.send_photo(chat_id, photo=buf,
            caption="📷 Или отсканируйте этот QR-код в приложении на телефоне.",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.warning("Не удалось отправить QR-код: %s", e)
        await context.bot.send_message(chat_id, "✅ Ключ отправлен выше.", reply_markup=keyboard)


# ───────────────────────── Творог в подарок ─────────────────────────

def city_keyboard():
    cities = list(POPULAR_CITIES.items())[:12]
    keyboard = [
        [btn(name, f"city_{city_id}") for city_id, name in cities[i:i + 2]]
        for i in range(0, len(cities), 2)
    ]
    keyboard += [[btn("📍 Другой город", "city_other")], MENU_ROW]
    return keyboard


async def show_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = register(update)
    if is_cheese_eligible(user["user_id"]):
        await show(update, context,
            "<b>🎁 Творог в подарок</b>\n\n"
            "Выберите город — доставим в пункт выдачи Ozon:",
            city_keyboard()
        )
    elif user["cheese_order_status"] != "none":
        await show(update, context,
            "<b>🎁 Творог в подарок</b>\n\n"
            "Вы уже получили подарок — одна упаковка на аккаунт. Спасибо, что вы с нами!",
            [MENU_ROW]
        )
    else:
        await show(update, context,
            "<b>🎁 Творог в подарок</b>\n\n"
            "Оформите подписку от 1 месяца — и мы отправим вам настоящий творог "
            "в ближайший пункт выдачи Ozon.",
            [[btn("💳 Выбрать тариф", "buy")], MENU_ROW]
        )


async def show_city(update: Update, context: ContextTypes.DEFAULT_TYPE, city_id: str):
    if city_id == "other":
        context.user_data["waiting_for_city"] = True
        await show(update, context,
            "<b>📍 Другой город</b>\n\nНапишите название вашего города одним сообщением.",
            [[btn("‹ К списку городов", "back_to_cities")]]
        )
        return
    keyboard = [
        [btn(f"{pvz['name']} · {pvz['address']}", f"pvz_{city_id}_{pvz['id']}")]
        for pvz in get_pvz_list(city_id)
    ]
    keyboard.append([btn("‹ К списку городов", "back_to_cities")])
    await show(update, context,
        f"<b>🏙 {get_city_name(city_id)}</b>\n\nВыберите пункт выдачи Ozon:",
        keyboard
    )


async def confirm_cheese_order(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    # city_id может содержать "_" (nizhny_novgorod), поэтому режем справа
    city_id, pvz_id = data[len("pvz_"):].rsplit("_", 1)
    user_id = update.effective_user.id
    if not is_cheese_eligible(user_id):
        await show_gift(update, context)
        return

    pvz = get_pvz_by_id(city_id, pvz_id)
    if not pvz:
        await show_city(update, context, city_id)
        return

    user = get_user(user_id)
    city_name = get_city_name(city_id)
    username = html.escape(user["username"] or "Без username")
    await notify_admin(context, format_order_message(username, user_id, city_id, pvz_id))
    update_user(user_id, delivery_address=f"{city_name}, {pvz['address']}", cheese_order_status="pending")

    await show(update, context,
        "<b>✅ Заказ принят</b>\n\n"
        f"📍 {city_name}, {pvz['name']}\n"
        f"{pvz['address']}\n\n"
        "Мы оформим доставку в ближайшее время. Приятного аппетита! 😋",
        [MENU_ROW]
    )


# ───────────────────────── Команды ─────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("waiting_for_city", None)
    context.user_data.pop("waiting_for_address", None)
    await show_main_menu(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_help(update, context)


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_tariffs(update, context)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_account(update, context)


async def servers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_servers(update, context)


async def gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_gift(update, context)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Текстовые сообщения: город / адрес для творога, иначе — подсказка с меню"""
    user_id = update.effective_user.id

    if context.user_data.get("waiting_for_city") or context.user_data.get("waiting_for_address"):
        if not is_cheese_eligible(user_id):
            context.user_data.pop("waiting_for_city", None)
            context.user_data.pop("waiting_for_address", None)
            await show_gift(update, context)
            return

    if context.user_data.get("waiting_for_city"):
        context.user_data["waiting_for_city"] = False
        context.user_data["waiting_for_address"] = True
        context.user_data["cheese_city"] = update.message.text
        await update.message.reply_text(
            f"🏙 Город: <b>{html.escape(update.message.text)}</b>\n\n"
            "Теперь напишите адрес пункта выдачи Ozon.\n"
            "<i>Например: ул. Ленина, д. 48</i>"
        )
        return

    if context.user_data.get("waiting_for_address"):
        context.user_data["waiting_for_address"] = False
        city = context.user_data.pop("cheese_city", "")
        address = f"{city}, {update.message.text}" if city else update.message.text
        update_user(user_id, delivery_address=address, cheese_order_status="pending")

        user = get_user(user_id)
        username = html.escape(user["username"] or "Без username")
        await notify_admin(context,
            f"📦 <b>Новый заказ на творог!</b>\n\n"
            f"👤 @{username} (ID: {user_id})\n"
            f"📍 Адрес: {html.escape(address)}\n\n"
            f"📦 {OZON_PRODUCT_NAME} (~{OZON_PRODUCT_PRICE}₽)\n\n"
            f"🔗 <a href=\"{generate_ozon_link()}\">Открыть на Ozon</a>\n\n"
            f"После заказа: /set_cheese {user_id} ordered"
        )
        await update.message.reply_text(
            "<b>✅ Заказ принят</b>\n\n"
            f"📍 {html.escape(address)}\n\n"
            "Мы оформим доставку в ближайшее время. Приятного аппетита! 😋",
            reply_markup=InlineKeyboardMarkup([MENU_ROW])
        )
        return

    await update.message.reply_text(
        "Я понимаю только кнопки 🙂 Откройте меню:",
        reply_markup=InlineKeyboardMarkup([[btn("🏠 Главное меню", "back_to_menu")]])
    )


# ───────────────────────── Кнопки ─────────────────────────

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    data = query.data

    # Проверка оплаты сама отвечает на нажатие (всплывающим сообщением)
    if data.startswith("check_payment_"):
        await check_payment(update, context)
        return

    await query.answer()

    if data in ("back_to_menu", "menu"):
        await show_main_menu(update, context)
    elif data == "buy":
        await show_tariffs(update, context)
    elif data.startswith("buy_"):
        tariff_key = data[len("buy_"):]
        if tariff_key == "trial":
            await claim_trial(update, context)
        elif tariff_key in TARIFFS:
            await create_invoice(update, context, tariff_key)
    elif data == "claim_gift":
        await claim_trial(update, context)
    elif data in ("connect", "select_device", "devices"):
        await show_devices(update, context)
    elif data.startswith("install_") and data[len("install_"):] in DEVICES:
        await show_install(update, context, data[len("install_"):])
    elif data.startswith("get_config_"):
        # get_config_iphone / ... и старые кнопки get_config_<id>
        await send_vpn_key(update, context)
    elif data in ("personal_account", "status"):
        await show_account(update, context)
    elif data == "info":
        await show_info(update, context)
    elif data == "help":
        await show_help(update, context)
    elif data == "instruction":
        await show_instruction(update, context)
    elif data == "servers" or data.startswith("server_"):
        await show_servers(update, context)
    elif data == "gift" or data == "back_to_cities":
        await show_gift(update, context)
    elif data.startswith("city_"):
        await show_city(update, context, data[len("city_"):])
    elif data.startswith("pvz_"):
        await confirm_cheese_order(update, context, data)


# ───────────────────────── Админ-команды ─────────────────────────

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ-панель с расширенной статистикой"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет доступа")
        return

    stats = get_user_stats()

    tariffs_text = ""
    for tariff, data in stats.get("tariffs_stats", {}).items():
        tariffs_text += f"  • {tariff}: {data['count']} продаж ({data['revenue']} ₽)\n"

    admin_text = f"""
📊 <b>Админ-панель {BOT_NAME}</b>

👥 <b>Пользователи</b>
  • Всего: {stats['total_users']}
  • Активных: {stats['active_users']}
  • Новых сегодня: {stats['new_today']}
  • Новых за неделю: {stats['new_week']}

💰 <b>Доход</b>
  • Сегодня: {stats['today_revenue']} ₽
  • За неделю: {stats['week_revenue']} ₽
  • За месяц: {stats['month_revenue']} ₽
  • Всего: {stats['total_revenue']} ₽

📦 <b>Продажи по тарифам</b>
{tariffs_text if tariffs_text else "  Нет продаж"}
🧪 <b>Пробные периоды</b>
  • Взяли: {stats['trial_users']}
  • Купили потом: {stats['paid_users']}

🎁 <b>Творог</b>
  • Заказов: {stats['cheese_orders']}
  • Ожидают: {stats['cheese_pending']}
  • Доставлено: {stats['cheese_delivered']}

📝 <b>Команды</b>
/add_user ID DAYS — добавить подписку
/cheese_orders — заказы творога
/order_cheese ID — заказать на Ozon
/set_cheese ID STATUS — статус творога
/users — список пользователей
"""
    await update.message.reply_text(admin_text)


async def add_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление подписки"""
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        user_id = int(context.args[0])
        days = int(context.args[1])
        activate_subscription(user_id, days)
        await update.message.reply_text(f"✅ Подписка на {plural_days(days)} добавлена ({user_id})")
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /add_user USER_ID DAYS")


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

    text = "📋 <b>Активные пользователи (последние 20)</b>\n\n"
    for user_id, username, expires_at in users:
        text += f"👤 @{html.escape(username or 'нет')} (ID: {user_id})\n"
        text += f"   ⏰ До {format_date(expires_at)} (осталось {plural_days(days_left(expires_at))})\n\n"
    await update.message.reply_text(text)


async def cheese_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ожидающие заказы на творог"""
    if update.effective_user.id != ADMIN_ID:
        return
    orders = get_pending_cheese_orders()
    if not orders:
        await update.message.reply_text("🎁 Нет ожидающих заказов")
        return
    text = "🎁 <b>Ожидающие заказы</b>\n\n"
    for o in orders:
        text += (
            f"👤 @{html.escape(o['username'] or 'нет')} (ID: {o['user_id']})\n"
            f"📍 {html.escape(o['address'] or '')}\n"
            f"✅ /set_cheese {o['user_id']} ordered\n\n"
        )
    await update.message.reply_text(text)


async def set_cheese(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменить статус творога"""
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        user_id = int(context.args[0])
        new_status = context.args[1]
        if new_status not in ["pending", "ordered", "delivered", "none"]:
            await update.message.reply_text("Статус: pending, ordered, delivered, none")
            return
        update_cheese_order(user_id, new_status)
        await update.message.reply_text(f"✅ Статус творога для {user_id} → {new_status}")
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /set_cheese USER_ID STATUS")


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
        username = html.escape(user["username"] or "Без username")
        await update.message.reply_text(
            f"🎁 <b>Заказ творога</b>\n\n"
            f"👤 @{username} (ID: {user_id})\n"
            f"📍 Адрес: {html.escape(address)}\n\n"
            f"📦 {OZON_PRODUCT_NAME}\n"
            f"💰 Цена: {OZON_PRODUCT_PRICE}₽\n\n"
            f"🔗 <a href=\"{generate_ozon_link(address)}\">Открыть на Ozon</a>\n\n"
            f"После заказа: /set_cheese {user_id} ordered"
        )
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /order_cheese USER_ID")


# ───────────────────────── Запуск ─────────────────────────

async def sync_wg_peers(context: ContextTypes.DEFAULT_TYPE):
    """Отключить истёкшие подписки от VPN"""
    for peer in get_wg_peers(active=False):
        try:
            remove_peer(peer["public_key"])
        except WireGuardError as e:
            logger.warning("Не удалось отключить пир %s: %s", peer["user_id"], e)


async def post_init(application: Application):
    """После старта: меню команд и восстановление VPN-подключений (после перезагрузки сервера пиры теряются)"""
    try:
        await application.bot.set_my_commands([
            BotCommand("start", "Главное меню"),
            BotCommand("buy", "Тарифы и оплата"),
            BotCommand("status", "Личный кабинет"),
            BotCommand("gift", "Творог в подарок"),
            BotCommand("help", "Поддержка"),
        ])
    except Exception as e:
        logger.warning("Не удалось установить меню команд: %s", e)

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
    defaults = Defaults(
        parse_mode=ParseMode.HTML,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .defaults(defaults)
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

    # Текст (город / адрес для творога)
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
