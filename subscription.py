"""
Общая логика подписки и VPN-ключей — для бота и мини-приложения.
"""
import base64
import io
import sqlite3

from urllib.parse import quote

from config import (
    TARIFFS, TRIAL_DAYS, DATABASE_PATH, BOT_NAME,
    REFERRAL_BONUS_DAYS, REFERRAL_FRIEND_BONUS_DAYS,
)
from database import (
    get_user, update_user, activate_subscription, add_payment, get_used_wg_ips,
    set_referrer, get_referral_stats,
)
from vpn_manager import (
    generate_wg_keys, get_next_ip, add_peer, remove_peer, create_client_config, WireGuardError
)


def trial_available(user) -> bool:
    """Пробный период доступен только тем, у кого ещё никогда не было подписки"""
    return not user or not user["expires_at"]


def trial_days_for(user) -> int:
    """Пробный период: приглашённым друзьям — дольше"""
    if user and user["referrer_id"]:
        return TRIAL_DAYS + REFERRAL_FRIEND_BONUS_DAYS
    return TRIAL_DAYS


def record_payment(user_id: int, tariff_key: str, payment_id: str):
    """Активировать подписку после оплаты и записать платёж.
    Если это первая оплата приглашённого друга — начислить бонус пригласившему.
    Возвращает ID пригласившего, которому начислен бонус, иначе None."""
    tariff = TARIFFS[tariff_key]
    activate_subscription(user_id, tariff["days"])
    add_payment(user_id, tariff["price"], tariff_key, payment_id)

    user = get_user(user_id)
    if tariff["price"] and user["referrer_id"] and not user["referral_rewarded"]:
        update_user(user_id, referral_rewarded=1)
        if get_user(user["referrer_id"]):
            activate_subscription(user["referrer_id"], REFERRAL_BONUS_DAYS)
            return user["referrer_id"]
    return None


def start_trial(user_id: int) -> int:
    """Включить пробный период, вернуть его длительность в днях"""
    days = trial_days_for(get_user(user_id))
    activate_subscription(user_id, days)
    add_payment(user_id, 0, "trial", "trial")
    return days


# ───────────────────────── Рефералы ─────────────────────────

REF_PREFIX = "ref_"


def parse_referrer(start_param: str):
    """ID пригласившего из параметра ссылки ref_123"""
    if start_param and start_param.startswith(REF_PREFIX) and start_param[len(REF_PREFIX):].isdigit():
        return int(start_param[len(REF_PREFIX):])
    return None


def attach_referrer(user_id: int, start_param: str):
    """Привязать нового пользователя к пригласившему. Возвращает ID пригласившего или None."""
    referrer_id = parse_referrer(start_param)
    if referrer_id and set_referrer(user_id, referrer_id):
        return referrer_id
    return None


def referral_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start={REF_PREFIX}{user_id}"


def referral_share_url(bot_username: str, user_id: int) -> str:
    text = (
        f"Пользуюсь {BOT_NAME} — быстрый VPN прямо в Telegram. "
        f"По моей ссылке — {TRIAL_DAYS + REFERRAL_FRIEND_BONUS_DAYS} дней бесплатно:"
    )
    return f"https://t.me/share/url?url={quote(referral_link(bot_username, user_id))}&text={quote(text)}"


def referral_info(bot_username: str, user_id: int) -> dict:
    stats = get_referral_stats(user_id)
    return {
        **stats,
        "link": referral_link(bot_username, user_id),
        "share_url": referral_share_url(bot_username, user_id),
        "bonus_days": REFERRAL_BONUS_DAYS,
        "friend_trial_days": TRIAL_DAYS + REFERRAL_FRIEND_BONUS_DAYS,
        "base_trial_days": TRIAL_DAYS,
        "earned_days": stats["paid"] * REFERRAL_BONUS_DAYS,
    }


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


def reset_client_key(user_id: int) -> str:
    """Перевыпустить ключ: старый отключается от сервера, IP остаётся прежним. Возвращает новый конфиг."""
    user = get_user(user_id)
    if user["wg_public_key"]:
        try:
            remove_peer(user["wg_public_key"])
        except WireGuardError:
            pass  # пира могло уже не быть на сервере
    private_key, public_key = generate_wg_keys()
    update_user(user_id, wg_private_key=private_key, wg_public_key=public_key)
    return build_client_config(user_id)


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
