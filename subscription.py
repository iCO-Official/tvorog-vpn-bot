"""
Общая логика подписки и VPN-ключей — для бота и мини-приложения.
"""
import base64
import io
import sqlite3

from config import TARIFFS, TRIAL_DAYS, DATABASE_PATH
from database import (
    get_user, update_user, activate_subscription, add_payment, get_used_wg_ips
)
from vpn_manager import generate_wg_keys, get_next_ip, add_peer, create_client_config


def trial_available(user) -> bool:
    """Пробный период доступен только тем, у кого ещё никогда не было подписки"""
    return not user or not user["expires_at"]


def record_payment(user_id: int, tariff_key: str, payment_id: str):
    """Активировать подписку после оплаты и записать платёж"""
    tariff = TARIFFS[tariff_key]
    activate_subscription(user_id, tariff["days"])
    add_payment(user_id, tariff["price"], tariff_key, payment_id)


def start_trial(user_id: int):
    activate_subscription(user_id, TRIAL_DAYS)
    add_payment(user_id, 0, "trial", "trial")


def current_period_days(user_id: int) -> int:
    """Длительность последнего оплаченного периода (для индикатора срока)"""
    conn = sqlite3.connect(DATABASE_PATH)
    row = conn.execute(
        "SELECT tariff FROM payments WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
    ).fetchone()
    conn.close()
    if row and row[0] in TARIFFS and TARIFFS[row[0]]["days"]:
        return TARIFFS[row[0]]["days"]
    return TRIAL_DAYS


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


def build_client_config(user_id: int) -> str:
    user = ensure_vpn_peer(user_id)
    return create_client_config(user["wg_private_key"], user["wg_ip"])


def qr_png(data: str) -> bytes:
    import qrcode
    buf = io.BytesIO()
    qrcode.make(data, border=2).save(buf, format="PNG")
    return buf.getvalue()


def qr_data_url(data: str) -> str:
    return "data:image/png;base64," + base64.b64encode(qr_png(data)).decode()
