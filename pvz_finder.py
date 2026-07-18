"""
Модуль для поиска пунктов выдачи Ozon
"""

import httpx
from typing import List, Dict, Optional

# Популярные города с пунктами выдачи Ozon
POPULAR_CITIES = {
    "moscow": "Москва",
    "spb": "Санкт-Петербург",
    "volgograd": "Волгоград",
    "krasnodar": "Краснодар",
    "novosibirsk": "Новосибирск",
    "ekaterinburg": "Екатеринбург",
    "kazan": "Казань",
    "nizhny_novgorod": "Нижний Новгород",
    "chelyabinsk": "Челябинск",
    "samara": "Самара",
    "ufa": "Уфа",
    "rostov": "Ростов-на-Дону",
    "krasnoyarsk": "Красноярск",
    "voronezh": "Воронеж",
    "perm": "Пермь",
    "voronezh": "Воронеж",
    "tyumen": "Тюмень",
    "omsk": "Омск",
    "bing": "Барнаул",
    "irkutsk": "Иркутск",
    "habarovsk": "Хабаровск",
    "vladivostok": "Владивосток",
}

# Примеры пунктов выдачи (в реальном проекте — из API Ozon)
SAMPLE_PVZ = {
    "moscow": [
        {"id": "1", "name": "Ozon Зеленоград", "address": "г. Зеленоград, корп. 1101"},
        {"id": "2", "name": "Ozon Митино", "address": "ул. Митинская, д. 36"},
        {"id": "3", "name": "Ozon Тушино", "address": "ул. Тушинская, д. 14"},
        {"id": "4", "name": "Ozon Строгино", "address": "ул. Маршала Катукова, д. 18"},
        {"id": "5", "name": "Ozon Коммунарка", "address": "п. Коммунарка, ул. Фитарёвская, д. 1"},
    ],
    "spb": [
        {"id": "1", "name": "Ozon Невский", "address": "Невский пр., д. 90"},
        {"id": "2", "name": "Ozon Московский", "address": "Московский пр., д. 107"},
        {"id": "3", "name": "Ozon Выборгская", "address": "Выборгская ул., д. 15"},
    ],
    "volgograd": [
        {"id": "1", "name": "Ozon Центр", "address": "ул. Ленина, д. 48"},
        {"id": "2", "name": "Ozon Краснооктябрьская", "address": "Краснооктябрьская ул., д. 31"},
        {"id": "3", "name": "Ozon Динамо", "address": "пр. Динамовский, д. 7"},
    ],
    "krasnodar": [
        {"id": "1", "name": "Ozon Красная", "address": "ул. Красная, д. 176"},
        {"id": "2", "name": "Ozon Северная", "address": "ул. Северная, д. 332"},
    ],
    "default": [
        {"id": "1", "name": "Ozon Центральный", "address": "Центральная ул., д. 1"},
        {"id": "2", "name": "Ozon Вокзал", "address": "ул. Вокзальная, д. 10"},
        {"id": "3", "name": "Ozon Торговый центр", "address": "Торговая ул., д. 25"},
    ]
}


def get_city_keyboard():
    """Клавиатура выбора города"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = []
    # Первые 6 городов
    popular = ["moscow", "spb", "volgograd", "krasnodar", "novosibirsk", "ekaterinburg"]
    for city_id in popular:
        keyboard.append([InlineKeyboardButton(
            POPULAR_CITIES[city_id],
            callback_data=f"city_{city_id}"
        )])

    # Остальные города
    other_cities = [k for k in POPULAR_CITIES.keys() if k not in popular]
    for city_id in other_cities[:6]:
        keyboard.append([InlineKeyboardButton(
            POPULAR_CITIES[city_id],
            callback_data=f"city_{city_id}"
        )])

    # Другой город
    keyboard.append([InlineKeyboardButton("📍 Другой город", callback_data="city_other")])

    return InlineKeyboardMarkup(keyboard)


def get_pvz_list(city_id: str) -> List[Dict]:
    """Получить список пунктов выдачи по городу"""
    # В реальном проекте здесь будет запрос к Ozon API
    # Пока используем демо-данные
    return SAMPLE_PVZ.get(city_id, SAMPLE_PVZ["default"])


def get_pvz_keyboard(city_id: str):
    """Клавиатура выбора пункта выдачи"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    pvz_list = get_pvz_list(city_id)
    keyboard = []

    for pvz in pvz_list:
        keyboard.append([InlineKeyboardButton(
            f"📍 {pvz['name']}\n{pvz['address']}",
            callback_data=f"pvz_{city_id}_{pvz['id']}"
        )])

    # Кнопка "Назад"
    keyboard.append([InlineKeyboardButton("🔙 Назад к городам", callback_data="back_to_cities")])

    return InlineKeyboardMarkup(keyboard)


def get_city_name(city_id: str) -> str:
    """Получить название города по ID"""
    return POPULAR_CITIES.get(city_id, "Неизвестный город")


def get_pvz_by_id(city_id: str, pvz_id: str) -> Optional[Dict]:
    """Получить пункт выдачи по ID"""
    pvz_list = get_pvz_list(city_id)
    for pvz in pvz_list:
        if pvz["id"] == pvz_id:
            return pvz
    return None


def format_order_message(username: str, user_id: int, city_id: str, pvz_id: str) -> str:
    """Форматирование сообщения о заказе для админа"""
    city_name = get_city_name(city_id)
    pvz = get_pvz_by_id(city_id, pvz_id)

    if not pvz:
        return "❌ Ошибка: пункт выдачи не найден"

    return (
        f"🧀 <b>Новый заказ на творог!</b>\n\n"
        f"👤 Пользователь: @{username} (ID: {user_id})\n"
        f"🏙️ Город: {city_name}\n"
        f"📍 Пункт выдачи: {pvz['name']}\n"
        f"📍 Адрес: {pvz['address']}\n\n"
        f"📦 <b>Товар:</b> Творог Коровка из Кореновки 180г\n"
        f"💰 <b>Цена:</b> ~76₽\n\n"
        f"🔗 <a href=\"https://www.ozon.ru/product/154359454\">Открыть на Ozon</a>\n\n"
        f"После заказа выполни:\n"
        f"/set_cheese {user_id} ordered"
    )
