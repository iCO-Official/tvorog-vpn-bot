"""
Модуль для автоматизации заказа творога на Ozon
"""

# ID товара "Творог Коровка из Кореновки 180г" на Ozon
OZON_PRODUCT_ID = "154359454"
OZON_PRODUCT_NAME = "Творог Коровка из Кореновки 180г"
OZON_PRODUCT_PRICE = 76  # рублей

def generate_ozon_link(address: str = None) -> str:
    """
    Генерирует ссылку на товар на Ozon

    Args:
        address: Адрес доставки (необязательно)

    Returns:
        Ссылка на товар на Ozon
    """
    base_url = f"https://www.ozon.ru/product/{OZON_PRODUCT_ID}"

    if address:
        # Кодируем адрес для URL
        import urllib.parse
        encoded_address = urllib.parse.quote(address)
        return f"{base_url}?address={encoded_address}"

    return base_url

def format_cheese_order_message(username: str, user_id: int, address: str) -> str:
    """
    Форматирует сообщение для админа о заказе творога

    Args:
        username: Имя пользователя
        user_id: ID пользователя
        address: Адрес доставки

    Returns:
        Отформатированное сообщение
    """
    ozon_link = generate_ozon_link(address)

    return (
        f"🧀 <b>Новый заказ на творог!</b>\n\n"
        f"👤 Пользователь: @{username} (ID: {user_id})\n"
        f"📍 Адрес: {address}\n\n"
        f"🛒 <b>Закажи на Ozon:</b>\n"
        f"📦 {OZON_PRODUCT_NAME}\n"
        f"💰 Цена: {OZON_PRODUCT_PRICE}₽\n\n"
        f"🔗 <a href=\"{ozon_link}\">Открыть на Ozon</a>\n\n"
        f"После заказа выполни:\n"
        f"/set_cheese {user_id} ordered"
    )

def format_cheese_delivery_message(user_id: int) -> str:
    """
    Форматирует сообщение пользователю о доставке

    Args:
        user_id: ID пользователя

    Returns:
        Отформатированное сообщение
    """
    return (
        "✅ <b>Адрес принят!</b>\n\n"
        "Мы заказали творог на Ozon.\n"
        f"📦 {OZON_PRODUCT_NAME}\n"
        "🕐 Ожидай доставку в ближайшие 1-3 дня!\n\n"
        "А пока — наслаждайся VPN 🔒\n\n"
        "💡 <i>Творог можно добавить в кашу, запеканку или есть просто так 😋</i>"
    )
