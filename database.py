import sqlite3
from datetime import datetime, timedelta
from config import DATABASE_PATH

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            expires_at TEXT,
            wg_private_key TEXT,
            wg_public_key TEXT,
            server_id TEXT DEFAULT 'main',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_active TEXT,
            delivery_address TEXT,
            cheese_order_status TEXT DEFAULT 'none',
            cheese_order_date TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            tariff TEXT,
            payment_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    conn.commit()
    conn.close()

def get_user(user_id: int) -> dict:
    """Получить пользователя по ID"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "user_id": row[0],
            "username": row[1],
            "expires_at": row[2],
            "wg_private_key": row[3],
            "wg_public_key": row[4],
            "server_id": row[5],
            "is_active": row[6],
            "created_at": row[7],
            "last_active": row[8],
            "delivery_address": row[9],
            "cheese_order_status": row[10],
            "cheese_order_date": row[11]
        }
    return None

def create_user(user_id: int, username: str) -> dict:
    """Создать нового пользователя"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Проверяем, существует ли уже пользователь
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        conn.close()
        return get_user(user_id)

    cursor.execute(
        "INSERT INTO users (user_id, username, created_at) VALUES (?, ?, ?)",
        (user_id, username, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    return get_user(user_id)

def update_user(user_id: int, **kwargs):
    """Обновить данные пользователя"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    updates = []
    values = []
    for key, value in kwargs.items():
        updates.append(f"{key} = ?")
        values.append(value)

    values.append(user_id)
    cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?", values)
    conn.commit()
    conn.close()

def activate_subscription(user_id: int, days: int):
    """Активировать подписку"""
    user = get_user(user_id)
    now = datetime.now()

    if user and user["expires_at"]:
        expires = datetime.fromisoformat(user["expires_at"])
        if expires > now:
            # Продлеваем существующую подписку
            new_expires = expires + timedelta(days=days)
        else:
            # Если подписка истекла, начинаем с сейчас
            new_expires = now + timedelta(days=days)
    else:
        new_expires = now + timedelta(days=days)

    update_user(user_id, expires_at=new_expires.isoformat(), is_active=1)

def is_subscription_active(user_id: int) -> bool:
    """Проверить, активна ли подписка"""
    user = get_user(user_id)
    if not user or not user["expires_at"]:
        return False

    expires = datetime.fromisoformat(user["expires_at"])
    return expires > datetime.now()

def add_payment(user_id: int, amount: int, tariff: str, payment_id: str):
    """Добавить запись о платеже"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO payments (user_id, amount, tariff, payment_id, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, tariff, payment_id, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_user_stats() -> dict:
    """Получить статистику пользователей"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1 AND expires_at > ?", (datetime.now().isoformat(),))
    active_users = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(amount) FROM payments")
    total_revenue = cursor.fetchone()[0] or 0

    conn.close()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_revenue": total_revenue
    }

def get_all_active_users() -> list:
    """Получить всех активных пользователей"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT user_id FROM users WHERE is_active = 1 AND expires_at > ?",
        (datetime.now().isoformat(),)
    )
    users = [row[0] for row in cursor.fetchall()]
    conn.close()

    return users

def is_cheese_eligible(user_id: int) -> bool:
    """Проверить, имеет ли пользователь право на бесплатный творог"""
    user = get_user(user_id)
    if not user:
        return False

    # Проверяем, не получал ли уже творог
    if user["cheese_order_status"] != "none":
        return False

    # Проверяем последний платеж
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT tariff FROM payments WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()

    if result:
        tariff = result[0]
        # Творог при покупке от 1 месяца
        return tariff in ["month", "quarter", "year"]

    return False

def get_pending_cheese_orders() -> list:
    """Получить.pending заказы на творог"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT user_id, username, delivery_address FROM users WHERE cheese_order_status = 'pending'"
    )
    orders = [
        {"user_id": row[0], "username": row[1], "address": row[2]}
        for row in cursor.fetchall()
    ]
    conn.close()

    return orders

def update_cheese_order(user_id: int, status: str):
    """Обновить статус заказа на творог"""
    update_user(
        user_id,
        cheese_order_status=status,
        cheese_order_date=datetime.now().isoformat() if status == "ordered" else None
    )
