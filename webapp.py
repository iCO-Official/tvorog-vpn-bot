"""
Сервер мини-приложения (Telegram Mini App).

Отдаёт webapp/index.html и JSON API. Каждый запрос подписан Telegram (initData) —
проверяем подпись токеном бота, поэтому подделать пользователя нельзя.
"""
import hashlib
import hmac
import json
import logging
import math
import os
import time
from datetime import datetime
from urllib.parse import parse_qsl

from aiohttp import web
from telegram import InputFile, LabeledPrice

from config import (
    BOT_TOKEN, BOT_NAME, TARIFFS, MAX_DEVICES, DEMO_MODE,
    STARS_ENABLED, SUPPORT_URL, ADMIN_ID, REFERRAL_BONUS_DAYS,
)
from database import (
    create_user, get_user, is_subscription_active, is_cheese_eligible, update_user,
)
from payments import card_payments_enabled, create_payment_link, check_payment_status
from pvz_finder import POPULAR_CITIES, get_city_name, get_pvz_list, get_pvz_by_id, format_order_message
from subscription import (
    trial_available, trial_days_for, start_trial, record_payment, current_period_days,
    build_client_config, reset_client_key, qr_data_url, attach_referrer, referral_info,
)
from vpn_manager import WireGuardError

logger = logging.getLogger("webapp")

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webapp")
INIT_DATA_MAX_AGE = 24 * 3600
CHEESE_TARIFFS = ["month", "quarter", "year"]

HAPP_IOS = "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973"
DEVICES = [
    {"key": "iphone", "name": "iPhone", "icon": "apple", "apps": [
        {"label": "Happ — App Store", "url": HAPP_IOS},
        {"label": "WireGuard — App Store", "url": "https://apps.apple.com/app/wireguard/id1441195209"},
    ]},
    {"key": "android", "name": "Android", "icon": "android", "apps": [
        {"label": "Happ — Google Play", "url": "https://play.google.com/store/apps/details?id=com.happproxy"},
        {"label": "WireGuard — Google Play", "url": "https://play.google.com/store/apps/details?id=com.wireguard.android"},
    ]},
    {"key": "windows", "name": "Windows", "icon": "windows", "apps": [
        {"label": "Happ для Windows", "url": "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe"},
        {"label": "WireGuard для Windows", "url": "https://www.wireguard.com/install/"},
    ]},
    {"key": "mac", "name": "macOS", "icon": "laptop", "apps": [
        {"label": "Happ — App Store", "url": HAPP_IOS},
        {"label": "WireGuard — App Store", "url": "https://apps.apple.com/app/wireguard/id1451685025"},
    ]},
    {"key": "linux", "name": "Linux", "icon": "terminal", "apps": [
        {"label": "Happ для Linux", "url": "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.AppImage"},
        {"label": "WireGuard для Linux", "url": "https://www.wireguard.com/install/"},
    ]},
]


# ───────────────────────── Авторизация ─────────────────────────

def validate_init_data(init_data: str, bot_token: str = BOT_TOKEN):
    """Проверить подпись initData от Telegram. Возвращает данные пользователя
    (с полем start_param, если приложение открыто по ссылке) или None."""
    if not init_data:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError:
        return None
    received_hash = pairs.pop("hash", "")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        return None
    try:
        if time.time() - int(pairs.get("auth_date", "0")) > INIT_DATA_MAX_AGE:
            return None
        user = json.loads(pairs["user"])
        user["start_param"] = pairs.get("start_param", "")
        return user
    except (KeyError, ValueError):
        return None


@web.middleware
async def auth_middleware(request, handler):
    if request.path.startswith("/api/"):
        user = validate_init_data(request.headers.get("X-Init-Data", ""))
        if not user:
            return web.json_response({"error": "unauthorized"}, status=401)
        request["tg_user"] = user
        is_new = get_user(user["id"]) is None
        create_user(user["id"], user.get("username") or user.get("first_name"))
        if is_new and user.get("start_param"):
            attach_referrer(user["id"], user["start_param"])
    return await handler(request)


# ───────────────────────── Состояние ─────────────────────────

def format_date(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%d.%m.%Y")


def tariffs_payload():
    month = TARIFFS["month"]
    per_day = month["price"] / month["days"]
    result = []
    for key, t in TARIFFS.items():
        if not t["price"]:
            continue
        months = max(round(t["days"] / 30), 1)
        result.append({
            "key": key, "name": t["name"], "days": t["days"], "price": t["price"],
            "stars": t.get("stars") if STARS_ENABLED else None,
            "per_month": round(t["price"] / months),
            "discount": round((1 - t["price"] / (per_day * t["days"])) * 100),
            "cheese": key in CHEESE_TARIFFS,
        })
    return result


def user_state(user_id: int, bot_username: str) -> dict:
    user = get_user(user_id)
    active = is_subscription_active(user_id)
    subscription = {"active": active, "expires": None, "days_left": 0, "period_days": 0, "ever": bool(user["expires_at"])}
    if user["expires_at"]:
        expires = datetime.fromisoformat(user["expires_at"])
        seconds_left = max((expires - datetime.now()).total_seconds(), 0)
        subscription.update({
            "expires": format_date(user["expires_at"]),
            "days_left": math.ceil(seconds_left / 86400) if active else 0,
            "period_days": current_period_days(user_id),
        })
    return {
        "brand": BOT_NAME,
        "demo": DEMO_MODE,
        "subscription": subscription,
        "trial": {"available": trial_available(user), "days": trial_days_for(user), "invited": bool(user["referrer_id"])},
        "referral": referral_info(bot_username, user_id),
        "max_devices": MAX_DEVICES,
        "has_key": bool(user["wg_public_key"]),
        "cheese": {"eligible": is_cheese_eligible(user_id), "status": user["cheese_order_status"]},
        "tariffs": tariffs_payload(),
        "methods": {"stars": STARS_ENABLED, "card": card_payments_enabled(), "card_demo": DEMO_MODE},
        "devices": DEVICES,
        "support_url": SUPPORT_URL,
        "bot_url": f"https://t.me/{bot_username}",
    }


# ───────────────────────── Обработчики ─────────────────────────

async def reward_referrer(request, referrer_id):
    """Уведомить пригласившего о начисленных бонусных днях"""
    if not referrer_id:
        return
    try:
        await request.app["bot"].send_message(referrer_id,
            f"<b>🤝 +{REFERRAL_BONUS_DAYS} дней к подписке</b>\n\n"
            "Ваш друг оформил подписку — спасибо за рекомендацию!"
        )
    except Exception as e:
        logger.warning("Не удалось уведомить пригласившего %s: %s", referrer_id, e)


async def index(request):
    return web.FileResponse(os.path.join(STATIC_DIR, "index.html"), headers={"Cache-Control": "no-cache"})


async def api_state(request):
    return web.json_response(user_state(request["tg_user"]["id"], request.app["bot"].username))


async def api_trial(request):
    user_id = request["tg_user"]["id"]
    if is_subscription_active(user_id):
        return web.json_response({"ok": True, "state": user_state(user_id, request.app['bot'].username)})
    if not trial_available(get_user(user_id)):
        return web.json_response({"error": "Пробный период уже использован"}, status=400)
    start_trial(user_id)
    return web.json_response({"ok": True, "state": user_state(user_id, request.app['bot'].username)})


async def api_pay(request):
    user_id = request["tg_user"]["id"]
    body = await request.json()
    tariff_key, method = body.get("tariff"), body.get("method")
    if tariff_key not in TARIFFS or not TARIFFS[tariff_key]["price"]:
        return web.json_response({"error": "Неизвестный тариф"}, status=400)
    tariff = TARIFFS[tariff_key]
    bot = request.app["bot"]

    if method == "stars" and STARS_ENABLED and tariff.get("stars"):
        link = await bot.create_invoice_link(
            title=f"{BOT_NAME} — {tariff['name']}",
            description=f"Подписка на {tariff['days']} дн.: до {MAX_DEVICES} устройств, безлимитный трафик.",
            payload=f"stars:{tariff_key}:{user_id}",
            currency="XTR",
            prices=[LabeledPrice(tariff["name"], tariff["stars"])],
        )
        return web.json_response({"type": "invoice", "url": link})

    if method == "card" and card_payments_enabled():
        payment = await create_payment_link(tariff_key, user_id)
        if not payment:
            return web.json_response({"error": "Не удалось создать счёт"}, status=502)
        if payment["payment_id"].startswith("demo-"):
            await reward_referrer(request, record_payment(user_id, tariff_key, payment["payment_id"]))
            return web.json_response({"type": "paid", "state": user_state(user_id, request.app['bot'].username)})
        return web.json_response({"type": "url", "url": payment["confirmation_url"], "payment_id": payment["payment_id"]})

    return web.json_response({"error": "Способ оплаты недоступен"}, status=400)


async def api_pay_check(request):
    """Проверка оплаты картой (ЮKassa) после возврата в приложение"""
    user_id = request["tg_user"]["id"]
    body = await request.json()
    payment_id, tariff_key = body.get("payment_id", ""), body.get("tariff")
    if tariff_key not in TARIFFS:
        return web.json_response({"error": "Неизвестный тариф"}, status=400)
    status = await check_payment_status(payment_id)
    metadata = status.get("metadata", {})
    if not status["paid"]:
        return web.json_response({"paid": False})
    if metadata.get("user_id") != str(user_id) or metadata.get("tariff", tariff_key) != tariff_key:
        return web.json_response({"error": "Платёж не найден"}, status=400)
    await reward_referrer(request, record_payment(user_id, tariff_key, payment_id))
    return web.json_response({"paid": True, "state": user_state(user_id, request.app['bot'].username)})


async def api_key(request):
    user_id = request["tg_user"]["id"]
    if not is_subscription_active(user_id):
        return web.json_response({"error": "Подписка не активна"}, status=403)
    try:
        config = build_client_config(user_id)
    except WireGuardError as e:
        logger.error("Мини-приложение: ошибка ключа для %s: %s", user_id, e)
        return web.json_response({"error": "Не удалось создать ключ. Попробуйте позже."}, status=500)
    return web.json_response({"config": config, "qr": qr_data_url(config), "filename": "TvorogVPN.conf"})


async def api_key_reset(request):
    """Перевыпустить ключ (старый перестанет работать)"""
    user_id = request["tg_user"]["id"]
    if not is_subscription_active(user_id):
        return web.json_response({"error": "Подписка не активна"}, status=403)
    try:
        config = reset_client_key(user_id)
    except WireGuardError as e:
        logger.error("Мини-приложение: ошибка перевыпуска ключа для %s: %s", user_id, e)
        return web.json_response({"error": "Не удалось перевыпустить ключ. Попробуйте позже."}, status=500)
    return web.json_response({"config": config, "qr": qr_data_url(config), "filename": "TvorogVPN.conf"})


async def api_key_send(request):
    """Прислать ключ файлом в чат с ботом"""
    user_id = request["tg_user"]["id"]
    if not is_subscription_active(user_id):
        return web.json_response({"error": "Подписка не активна"}, status=403)
    try:
        config = build_client_config(user_id)
    except WireGuardError:
        return web.json_response({"error": "Не удалось создать ключ"}, status=500)
    await request.app["bot"].send_document(
        user_id,
        document=InputFile(config.encode(), filename="TvorogVPN.conf"),
        caption="<b>🔑 Ваш ключ Творог VPN</b>\n\nОткройте файл и импортируйте его в приложение.",
    )
    return web.json_response({"ok": True})


async def api_cities(request):
    cities = [{"id": cid, "name": name} for cid, name in list(POPULAR_CITIES.items())[:12]]
    return web.json_response({"cities": cities})


async def api_pvz(request):
    city = request.query.get("city", "")
    return web.json_response({"city": get_city_name(city), "points": get_pvz_list(city)})


async def api_gift_order(request):
    user_id = request["tg_user"]["id"]
    if not is_cheese_eligible(user_id):
        return web.json_response({"error": "Подарок недоступен"}, status=403)
    body = await request.json()
    city_id, pvz_id = body.get("city", ""), str(body.get("pvz", ""))
    pvz = get_pvz_by_id(city_id, pvz_id)
    if not pvz:
        return web.json_response({"error": "Пункт выдачи не найден"}, status=400)
    city_name = get_city_name(city_id)
    update_user(user_id, delivery_address=f"{city_name}, {pvz['address']}", cheese_order_status="pending")
    if ADMIN_ID:
        user = request["tg_user"]
        try:
            await request.app["bot"].send_message(
                ADMIN_ID, format_order_message(user.get("username") or "Без username", user_id, city_id, pvz_id)
            )
        except Exception as e:
            logger.error("Не удалось уведомить админа о заказе творога: %s", e)
    return web.json_response({"ok": True, "state": user_state(user_id, request.app['bot'].username)})


def create_app(bot) -> web.Application:
    app = web.Application(middlewares=[auth_middleware])
    app["bot"] = bot
    app.router.add_get("/", index)
    app.router.add_post("/api/state", api_state)
    app.router.add_post("/api/trial", api_trial)
    app.router.add_post("/api/pay", api_pay)
    app.router.add_post("/api/pay/check", api_pay_check)
    app.router.add_post("/api/key", api_key)
    app.router.add_post("/api/key/send", api_key_send)
    app.router.add_post("/api/key/reset", api_key_reset)
    app.router.add_post("/api/gift/cities", api_cities)
    app.router.add_post("/api/gift/pvz", api_pvz)
    app.router.add_post("/api/gift/order", api_gift_order)
    return app


async def start_webapp(application, port: int):
    runner = web.AppRunner(create_app(application.bot), access_log=None)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    return runner
