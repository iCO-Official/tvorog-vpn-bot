"""
Модуль оплаты: ЮKassa (карты, СБП) и CryptoBot (криптовалюта).
Оплата звёздами Telegram — в bot.py (встроена в Telegram).
"""
import logging
import uuid
import httpx
from datetime import datetime
from config import (
    TARIFFS, YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, DEMO_MODE,
    CRYPTO_PAY_TOKEN, CRYPTO_PAY_TESTNET, CRYPTO_ASSETS, BOT_NAME
)

logger = logging.getLogger(__name__)

YOOKASSA_TIMEOUT = 20
CRYPTO_PAY_API = "https://testnet-pay.crypt.bot/api" if CRYPTO_PAY_TESTNET else "https://pay.crypt.bot/api"


def card_payments_enabled() -> bool:
    """Оплата картой/СБП доступна: настроена ЮKassa или демо-режим"""
    return DEMO_MODE or bool(YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY)


def crypto_payments_enabled() -> bool:
    return bool(CRYPTO_PAY_TOKEN)


async def create_payment_link(tariff_key: str, user_id: int) -> dict:
    """
    Создать платёжную ссылку через ЮKassa

    Returns:
        dict: {"payment_id": str, "confirmation_url": str}
    """
    tariff = TARIFFS[tariff_key]

    if tariff["price"] == 0:
        return None

    if DEMO_MODE:
        return {
            "payment_id": f"demo-{uuid.uuid4()}",
            "confirmation_url": "https://t.me/tvorog_vpn_bot",
            "amount": tariff["price"],
            "tariff": tariff_key
        }

    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        logger.error("ЮKassa не настроена: заполните YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY в .env")
        return None

    # Уникальный ID платежа
    payment_id = str(uuid.uuid4())

    # Формируем запрос к ЮKassa API
    url = "https://api.yookassa.ru/v3/payments"

    payload = {
        "amount": {
            "value": f"{tariff['price']}.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/tvorog_vpn_bot"
        },
        "capture": True,
        "description": f"Творог VPN - {tariff['name']}",
        "metadata": {
            "user_id": str(user_id),
            "tariff": tariff_key
        }
    }

    try:
        # Отправляем запрос
        async with httpx.AsyncClient(timeout=YOOKASSA_TIMEOUT) as client:
            response = await client.post(
                url,
                json=payload,
                auth=(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY),
                headers={"Idempotence-Key": payment_id}
            )

        if response.status_code == 200:
            data = response.json()
            return {
                "payment_id": data["id"],
                "confirmation_url": data["confirmation"]["confirmation_url"],
                "amount": tariff["price"],
                "tariff": tariff_key
            }
        else:
            logger.error("Ошибка ЮKassa: %s - %s", response.status_code, response.text)
            return None

    except Exception as e:
        logger.exception("Ошибка создания платежа: %s", e)
        return None


async def check_payment_status(payment_id: str) -> dict:
    """
    Проверить статус платежа

    Returns:
        dict: {"status": str, "paid": bool}
    """
    if DEMO_MODE and payment_id.startswith("demo-"):
        return {"status": "succeeded", "paid": True, "amount": "0", "metadata": {}}

    url = f"https://api.yookassa.ru/v3/payments/{payment_id}"

    try:
        async with httpx.AsyncClient(timeout=YOOKASSA_TIMEOUT) as client:
            response = await client.get(
                url,
                auth=(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
            )

        if response.status_code == 200:
            data = response.json()
            return {
                "status": data["status"],
                "paid": data["status"] == "succeeded",
                "amount": data["amount"]["value"],
                "metadata": data.get("metadata", {})
            }
        else:
            logger.error("Ошибка проверки платежа ЮKassa: %s - %s", response.status_code, response.text)
            return {"status": "error", "paid": False}

    except Exception as e:
        logger.exception("Ошибка проверки платежа: %s", e)
        return {"status": "error", "paid": False}


def format_payment_message(tariff_key: str, payment_url: str) -> str:
    """Форматировать сообщение с ссылкой на оплату"""
    tariff = TARIFFS[tariff_key]

    return (
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


def get_tariff_info(tariff_key: str) -> str:
    """Получить информацию о тарифе"""
    if tariff_key not in TARIFFS:
        return "Неизвестный тариф"

    tariff = TARIFFS[tariff_key]
    return (
        f"📦 <b>{tariff['name']}</b>\n"
        f"💰 Цена: {tariff['price']} ₽\n"
        f"⏰ Срок: {tariff['days']} дней\n"
        f"🌐 Трафик: Без ограничений\n"
        f"📱 Устройства: До 3 штук"
    )


def format_subscription_status(user) -> str:
    """Форматировать статус подписки"""
    if not user or not user["expires_at"]:
        return "❌ Нет активной подписки"

    expires = datetime.fromisoformat(user["expires_at"])
    now = datetime.now()

    if expires > now:
        remaining = expires - now
        days = remaining.days
        return f"✅ Активна ещё {days} дней (до {expires.strftime('%d.%m.%Y')})"
    else:
        return "❌ Подписка истекла"


# ───────────────────────── CryptoBot (Crypto Pay API) ─────────────────────────

async def _crypto_request(method: str, params: dict) -> dict:
    async with httpx.AsyncClient(timeout=YOOKASSA_TIMEOUT) as client:
        response = await client.post(
            f"{CRYPTO_PAY_API}/{method}",
            json=params,
            headers={"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
        )
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Crypto Pay {method}: {data.get('error')}")
    return data["result"]


async def create_crypto_invoice(tariff_key: str, user_id: int) -> dict:
    """Счёт в CryptoBot. Сумма — цена тарифа в рублях, клиент платит USDT/TON по курсу."""
    tariff = TARIFFS[tariff_key]
    try:
        result = await _crypto_request("createInvoice", {
            "currency_type": "fiat",
            "fiat": "RUB",
            "amount": str(tariff["price"]),
            "accepted_assets": CRYPTO_ASSETS,
            "description": f"{BOT_NAME} — {tariff['name']}",
            "payload": f"{user_id}:{tariff_key}",
            "expires_in": 3600,
        })
        return {
            "payment_id": str(result["invoice_id"]),
            "confirmation_url": result.get("bot_invoice_url") or result.get("pay_url"),
        }
    except Exception as e:
        logger.exception("Ошибка создания счёта CryptoBot: %s", e)
        return None


async def check_crypto_invoice(invoice_id: str) -> dict:
    """Статус счёта CryptoBot в том же формате, что и check_payment_status"""
    try:
        result = await _crypto_request("getInvoices", {"invoice_ids": str(invoice_id)})
        items = result.get("items", [])
        if not items:
            return {"status": "error", "paid": False}
        invoice = items[0]
        user_id = (invoice.get("payload") or "").split(":")[0]
        return {
            "status": invoice["status"],
            "paid": invoice["status"] == "paid",
            "metadata": {"user_id": user_id} if user_id else {},
        }
    except Exception as e:
        logger.exception("Ошибка проверки счёта CryptoBot: %s", e)
        return {"status": "error", "paid": False}
