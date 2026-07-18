"""
Модуль оплаты через ЮKassa
"""
import uuid
import httpx
from datetime import datetime
from config import TARIFFS, YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, PAYMENT_METHODS


def create_payment_link(tariff_key: str, user_id: int) -> dict:
    """
    Создать платёжную ссылку через ЮKassa

    Returns:
        dict: {"payment_id": str, "confirmation_url": str}
    """
    tariff = TARIFFS[tariff_key]

    if tariff["price"] == 0:
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
            "return_url": f"https://t.me/tvorog_vpn_bot"
        },
        "capture": True,
        "description": f"Творог VPN - {tariff['name']}",
        "metadata": {
            "user_id": str(user_id),
            "tariff": tariff_key
        },
        "payment_method_data": {
            "type": "bank_card"
        }
    }

    # Добавляем доступные способы оплаты
    if "sbp" in PAYMENT_METHODS:
        payload["payment_method_data"]["type"] = "sbp"

    try:
        # Отправляем запрос
        response = httpx.post(
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
            print(f"Ошибка ЮKassa: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"Ошибка создания платежа: {e}")
        return None


def check_payment_status(payment_id: str) -> dict:
    """
    Проверить статус платежа

    Returns:
        dict: {"status": str, "paid": bool}
    """
    url = f"https://api.yookassa.ru/v3/payments/{payment_id}"

    try:
        response = httpx.get(
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
            return {"status": "error", "paid": False}

    except Exception as e:
        print(f"Ошибка проверки платежа: {e}")
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
