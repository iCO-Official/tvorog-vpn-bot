"""
Бот поддержки Творог VPN.

Клиент: частые вопросы кнопками → «Написать оператору» → обращение с номером.
Оператор: обращения приходят в SUPPORT_CHAT_ID (по умолчанию — ADMIN_ID).
Чтобы ответить клиенту — ответьте (Reply) на его сообщение. Кнопка «Закрыть» закрывает
обращение, клиент ставит оценку.
"""
import html
import logging
import os
import sys
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions, BotCommand
from telegram.constants import ParseMode
from telegram.error import BadRequest, Conflict, InvalidToken
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes, Defaults,
    MessageHandler, PicklePersistence, filters,
)

from config import SUPPORT_BOT_TOKEN, SUPPORT_CHAT_ID, BOT_USERNAME, BOT_NAME

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("support_bot")

MAIN_BOT_URL = f"https://t.me/{BOT_USERNAME}"

FAQ = {
    "not_working": (
        "🔌 Не подключается VPN",
        "<b>🔌 Не подключается VPN</b>\n\n"
        "Попробуйте по порядку:\n"
        "1. Проверьте, что подписка активна: основной бот → 👤 Кабинет\n"
        "2. Выключите и снова включите VPN в приложении\n"
        "3. Переключитесь между Wi-Fi и мобильным интернетом\n"
        "4. Удалите ключ из приложения и получите новый: 🔑 Подключить устройство\n\n"
        "Не помогло — напишите оператору, разберёмся."
    ),
    "payment": (
        "💳 Вопрос по оплате",
        "<b>💳 Оплата</b>\n\n"
        "• Подписка включается сразу после оплаты — в счёте нажмите «Я оплатил»\n"
        "• Принимаем банковские карты и СБП\n"
        "• Подписка не продлевается автоматически — ничего отменять не нужно\n\n"
        "Деньги списались, а подписка не активна? Напишите оператору и приложите чек."
    ),
    "install": (
        "📲 Как установить",
        "<b>📲 Установка</b>\n\n"
        "Откройте основной бот → 🔑 Подключить устройство → выберите устройство.\n"
        "Бот пришлёт короткую инструкцию, файл-ключ и QR-код.\n\n"
        "Одна подписка — до 3 устройств."
    ),
    "refund": (
        "↩️ Возврат денег",
        "<b>↩️ Возврат денег</b>\n\n"
        "Напишите оператору: укажите дату оплаты и причину — мы рассмотрим обращение "
        "и ответим здесь же."
    ),
}

RATING_TEXT = {1: "😞", 2: "😕", 3: "😐", 4: "🙂", 5: "🤩"}


def btn(text, data):
    return InlineKeyboardButton(text, callback_data=data)


def main_keyboard():
    rows = [[btn(title, f"faq_{key}")] for key, (title, _) in FAQ.items()]
    rows.append([btn("✍️ Написать оператору", "operator")])
    rows.append([InlineKeyboardButton(f"🔒 Открыть {BOT_NAME}", url=MAIN_BOT_URL)])
    return InlineKeyboardMarkup(rows)


def store(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Состояние обращений (сохраняется между перезапусками)"""
    data = context.bot_data
    data.setdefault("next_ticket", 1)
    data.setdefault("tickets", {})       # номер → {user_id, name, status, topic, created}
    data.setdefault("open_by_user", {})  # user_id → номер открытого обращения
    data.setdefault("msg_to_ticket", {}) # id сообщения у оператора → номер обращения
    return data


def user_label(user) -> str:
    name = html.escape(user.full_name or "Без имени")
    return f"{name} (@{html.escape(user.username)})" if user.username else name


async def show(update: Update, text: str, markup=None):
    query = update.callback_query
    if query:
        try:
            await query.edit_message_text(text, reply_markup=markup)
            return
        except BadRequest as e:
            if "not modified" in str(e).lower():
                return
    await update.effective_chat.send_message(text, reply_markup=markup)


# ───────────────────────── Клиент ─────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    first_name = html.escape(update.effective_user.first_name or "")
    await update.message.reply_text(
        f"<b>Здравствуйте{', ' + first_name if first_name else ''}! 👋</b>\n\n"
        f"Это поддержка {BOT_NAME}. Мы на связи 24/7.\n\n"
        "Выберите вопрос — большинство проблем решается за минуту. "
        "Или сразу напишите оператору.",
        reply_markup=main_keyboard()
    )


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("close_"):
        await close_ticket(update, context, int(data[len("close_"):]))
        return
    if data.startswith("rate_"):
        await rate_ticket(update, context, data)
        return

    await query.answer()

    if data == "menu":
        await show(update,
            "<b>Поддержка " + BOT_NAME + "</b>\n\nВыберите вопрос или напишите оператору.",
            main_keyboard()
        )
    elif data.startswith("faq_") and data[4:] in FAQ:
        title, text = FAQ[data[4:]]
        context.user_data["topic"] = title
        await show(update, text, InlineKeyboardMarkup([
            [btn("✅ Помогло", "helped"), btn("✍️ Оператору", "operator")],
            [btn("‹ Все вопросы", "menu")],
        ]))
    elif data == "helped":
        await show(update,
            "<b>Отлично, рады помочь! 🙌</b>\n\nЕсли появятся вопросы — мы здесь.",
            InlineKeyboardMarkup([[btn("‹ Все вопросы", "menu")]])
        )
    elif data == "operator":
        await show(update,
            "<b>✍️ Напишите ваш вопрос</b>\n\n"
            "Опишите проблему одним сообщением — можно приложить скриншот.\n"
            "Оператор ответит здесь же, обычно в течение 15 минут.",
            InlineKeyboardMarkup([[btn("‹ Все вопросы", "menu")]])
        )


async def on_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сообщение клиента → в обращение"""
    msg = update.effective_message
    user = update.effective_user
    data = store(context)

    if not SUPPORT_CHAT_ID:
        await msg.reply_text("Оператор временно недоступен. Попробуйте позже.")
        logger.error("SUPPORT_CHAT_ID / ADMIN_ID не задан — обращения некуда отправлять")
        return

    ticket_id = data["open_by_user"].get(user.id)
    is_new = ticket_id is None
    if is_new:
        ticket_id = data["next_ticket"]
        data["next_ticket"] += 1
        topic = context.user_data.pop("topic", "Общий вопрос")
        data["tickets"][ticket_id] = {
            "user_id": user.id, "name": user_label(user), "status": "open",
            "topic": topic, "created": datetime.now().isoformat(timespec="minutes"),
        }
        data["open_by_user"][user.id] = ticket_id
        header = await context.bot.send_message(SUPPORT_CHAT_ID,
            f"🆕 <b>Обращение №{ticket_id}</b>\n"
            f"👤 {user_label(user)} · ID <code>{user.id}</code>\n"
            f"📌 {html.escape(topic)}\n\n"
            "<i>Чтобы ответить — ответьте (Reply) на сообщение клиента ниже.</i>",
            reply_markup=InlineKeyboardMarkup([[btn(f"✅ Закрыть №{ticket_id}", f"close_{ticket_id}")]])
        )
        data["msg_to_ticket"][header.message_id] = ticket_id

    copied = await msg.copy(SUPPORT_CHAT_ID)
    data["msg_to_ticket"][copied.message_id] = ticket_id

    if is_new:
        await msg.reply_text(
            f"✅ <b>Обращение №{ticket_id} принято</b>\n\n"
            "Оператор ответит здесь же, обычно в течение 15 минут. "
            "Можете дописать подробности или прислать скриншот."
        )
    else:
        try:
            await msg.set_reaction("👌")
        except Exception:
            pass


# ───────────────────────── Оператор ─────────────────────────

async def on_operator_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Ответ оператора (Reply на сообщение обращения) → клиенту. True, если это был ответ."""
    msg = update.effective_message
    if update.effective_chat.id != SUPPORT_CHAT_ID or not msg.reply_to_message:
        return False
    data = store(context)
    ticket_id = data["msg_to_ticket"].get(msg.reply_to_message.message_id)
    if ticket_id is None:
        return False

    ticket = data["tickets"][ticket_id]
    try:
        if msg.text:
            await context.bot.send_message(ticket["user_id"],
                f"💬 <b>Поддержка</b>\n\n{html.escape(msg.text)}"
            )
        else:
            caption = "💬 <b>Поддержка</b>" + (f"\n\n{html.escape(msg.caption)}" if msg.caption else "")
            await msg.copy(ticket["user_id"], caption=caption)
    except Exception as e:
        await msg.reply_text(f"⚠️ Не удалось доставить ответ: {html.escape(str(e))}")
        return True

    if ticket["status"] == "closed":
        ticket["status"] = "open"
        data["open_by_user"][ticket["user_id"]] = ticket_id
    try:
        await msg.set_reaction("👍")
    except Exception:
        await msg.reply_text(f"✅ Отправлено в обращение №{ticket_id}")
    return True


async def close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE, ticket_id: int):
    query = update.callback_query
    data = store(context)
    ticket = data["tickets"].get(ticket_id)
    if query.message.chat.id != SUPPORT_CHAT_ID or not ticket:
        await query.answer()
        return
    if ticket["status"] == "closed":
        await query.answer("Обращение уже закрыто")
        return

    ticket["status"] = "closed"
    data["open_by_user"].pop(ticket["user_id"], None)
    await query.answer(f"Обращение №{ticket_id} закрыто")
    await query.edit_message_text(
        f"✅ <b>Обращение №{ticket_id} закрыто</b>\n"
        f"👤 {ticket['name']} · ID <code>{ticket['user_id']}</code>\n"
        f"📌 {html.escape(ticket['topic'])}"
    )
    await context.bot.send_message(ticket["user_id"],
        f"<b>Обращение №{ticket_id} закрыто</b>\n\n"
        "Оцените, пожалуйста, работу поддержки:",
        reply_markup=InlineKeyboardMarkup([
            [btn("⭐" * n, f"rate_{ticket_id}_{n}") for n in (1, 2, 3)],
            [btn("⭐" * n, f"rate_{ticket_id}_{n}") for n in (4, 5)],
        ])
    )


async def rate_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE, data_str: str):
    query = update.callback_query
    _, ticket_id, score = data_str.split("_")
    ticket_id, score = int(ticket_id), int(score)
    ticket = store(context)["tickets"].get(ticket_id)
    if not ticket or ticket.get("rating") or ticket["user_id"] != query.from_user.id:
        await query.answer()
        return
    ticket["rating"] = score
    await query.answer("Спасибо за оценку!")
    await query.edit_message_text(
        f"Спасибо за оценку {'⭐' * score} {RATING_TEXT[score]}\n\n"
        "Если понадобится помощь — просто напишите сюда.",
        reply_markup=InlineKeyboardMarkup([[btn("‹ Все вопросы", "menu")]])
    )
    await context.bot.send_message(SUPPORT_CHAT_ID, f"⭐ Оценка обращения №{ticket_id}: {'⭐' * score}")


async def tickets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/tickets — открытые обращения (для оператора)"""
    if update.effective_chat.id != SUPPORT_CHAT_ID:
        return
    data = store(context)
    open_tickets = [(tid, t) for tid, t in data["tickets"].items() if t["status"] == "open"]
    if not open_tickets:
        await update.message.reply_text("🎉 Открытых обращений нет")
        return
    lines = ["<b>📋 Открытые обращения</b>", ""]
    for tid, t in open_tickets:
        lines.append(f"№{tid} · {t['name']} · {html.escape(t['topic'])} · {t['created'].replace('T', ' ')}")
    await update.message.reply_text("\n".join(lines))


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await on_operator_reply(update, context):
        return
    if update.effective_chat.type != "private":
        return  # в группе операторов обычные сообщения не пересылаем
    await on_user_message(update, context)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, Conflict):
        logger.error("Конфликт: этот токен поддержки используется другой копией бота.")
        return
    logger.error("Ошибка при обработке обновления %s", update, exc_info=context.error)


async def post_init(application: Application):
    try:
        await application.bot.set_my_commands([BotCommand("start", "Частые вопросы и связь с оператором")])
    except Exception as e:
        logger.warning("Не удалось установить меню команд: %s", e)


def main():
    if not SUPPORT_BOT_TOKEN:
        sys.exit("❌ SUPPORT_BOT_TOKEN не задан. Создайте второго бота в @BotFather и впишите токен в .env")
    if not SUPPORT_CHAT_ID:
        logger.warning("ADMIN_ID / SUPPORT_CHAT_ID не задан — обращения некуда отправлять")

    application = (
        Application.builder()
        .token(SUPPORT_BOT_TOKEN)
        .defaults(Defaults(parse_mode=ParseMode.HTML, link_preview_options=LinkPreviewOptions(is_disabled=True)))
        .persistence(PicklePersistence(filepath=os.environ.get("SUPPORT_PERSISTENCE_PATH", "support_state.pickle")))
        .post_init(post_init)
        .build()
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("tickets", tickets_command))
    application.add_handler(CallbackQueryHandler(on_button))
    application.add_handler(MessageHandler(~filters.COMMAND & ~filters.StatusUpdate.ALL, on_message))
    application.add_error_handler(error_handler)

    logger.info("💬 Бот поддержки запускается...")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except InvalidToken:
        sys.exit("❌ Telegram отклонил SUPPORT_BOT_TOKEN. Проверьте токен в .env")


if __name__ == "__main__":
    main()
