"""
API сервер для админ-панели Творог VPN
"""
import os
import sqlite3
import json
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from config import DATABASE_PATH

ADMIN_PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin.html")


def get_db():
    """Подключение к базе данных"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_stats():
    """Получить статистику"""
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now()

    # Всего пользователей
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    # Активные
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1 AND expires_at > ?", (now.isoformat(),))
    active_users = cursor.fetchone()[0]

    # Пробные
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM payments WHERE tariff = 'trial'")
    trial_users = cursor.fetchone()[0]

    # Оплатившие
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM payments WHERE tariff != 'trial' AND amount > 0")
    paid_users = cursor.fetchone()[0]

    # Доход
    cursor.execute("SELECT SUM(amount) FROM payments WHERE amount > 0")
    total_revenue = cursor.fetchone()[0] or 0

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    cursor.execute("SELECT SUM(amount) FROM payments WHERE amount > 0 AND created_at >= ?", (today_start.isoformat(),))
    today_revenue = cursor.fetchone()[0] or 0

    week_start = now - timedelta(days=7)
    cursor.execute("SELECT SUM(amount) FROM payments WHERE amount > 0 AND created_at >= ?", (week_start.isoformat(),))
    week_revenue = cursor.fetchone()[0] or 0

    month_start = now - timedelta(days=30)
    cursor.execute("SELECT SUM(amount) FROM payments WHERE amount > 0 AND created_at >= ?", (month_start.isoformat(),))
    month_revenue = cursor.fetchone()[0] or 0

    # Тарифы
    cursor.execute("SELECT tariff, COUNT(*), SUM(amount) FROM payments WHERE amount > 0 GROUP BY tariff")
    tariffs = [{"name": r[0], "count": r[1], "revenue": r[2] or 0} for r in cursor.fetchall()]

    # Творог
    cursor.execute("SELECT COUNT(*) FROM users WHERE cheese_order_status != 'none'")
    cheese_total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE cheese_order_status = 'pending'")
    cheese_pending = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE cheese_order_status = 'delivered'")
    cheese_delivered = cursor.fetchone()[0]

    # Новые
    cursor.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", (today_start.isoformat(),))
    new_today = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", (week_start.isoformat(),))
    new_week = cursor.fetchone()[0]

    # Доход по дням (неделя)
    daily_revenue = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE amount > 0 AND created_at >= ? AND created_at < ?", (day_start.isoformat(), day_end.isoformat()))
        revenue = cursor.fetchone()[0]
        daily_revenue.append({"date": day.strftime("%d.%m"), "revenue": revenue})

    conn.close()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "trial_users": trial_users,
        "paid_users": paid_users,
        "total_revenue": total_revenue,
        "today_revenue": today_revenue,
        "week_revenue": week_revenue,
        "month_revenue": month_revenue,
        "new_today": new_today,
        "new_week": new_week,
        "tariffs": tariffs,
        "cheese_total": cheese_total,
        "cheese_pending": cheese_pending,
        "cheese_delivered": cheese_delivered,
        "daily_revenue": daily_revenue
    }


def get_users():
    """Получить список пользователей"""
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now()

    cursor.execute("SELECT user_id, username, expires_at, cheese_order_status FROM users ORDER BY created_at DESC LIMIT 100")
    users = []
    for row in cursor.fetchall():
        status = "expired"
        if row["expires_at"]:
            expires = datetime.fromisoformat(row["expires_at"])
            if expires > now:
                status = "active"

        users.append({
            "id": row["user_id"],
            "username": row["username"] or "—",
            "status": status,
            "expires": row["expires_at"][:10] if row["expires_at"] else "—",
            "cheese": row["cheese_order_status"]
        })

    conn.close()
    return users


def get_payments():
    """Получить платежи"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, user_id, tariff, amount, created_at FROM payments ORDER BY created_at DESC LIMIT 100")
    payments = []
    for row in cursor.fetchall():
        payments.append({
            "id": row["id"],
            "user_id": row["user_id"],
            "tariff": row["tariff"],
            "amount": row["amount"],
            "date": row["created_at"][:10] if row["created_at"] else "—"
        })

    conn.close()
    return payments


class AdminHandler(BaseHTTPRequestHandler):
    """Обработчик запросов. Отдаёт только API и admin.html — никаких других файлов
    (раньше отдавалась вся папка бота, включая .env, базу и ключи клиентов)."""

    def _send(self, code, body: bytes, content_type: str):
        self.send_response(code)
        self.send_header('Content-type', content_type)
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        token = os.environ.get("API_TOKEN", "")
        if not token:
            return True
        query = parse_qs(urlparse(self.path).query)
        header = self.headers.get("Authorization", "")
        return header == f"Bearer {token}" or query.get("token", [""])[0] == token

    def do_GET(self):
        if not self._authorized():
            return self._send(401, b"Unauthorized", "text/plain")

        path = urlparse(self.path).path
        routes = {'/api/stats': get_stats, '/api/users': get_users, '/api/payments': get_payments}
        if path in routes:
            data = json.dumps(routes[path](), ensure_ascii=False).encode()
            return self._send(200, data, 'application/json; charset=utf-8')

        if path in ('/', '/index.html', '/admin.html'):
            with open(ADMIN_PAGE, 'rb') as f:
                return self._send(200, f.read(), 'text/html; charset=utf-8')

        return self._send(404, b"Not found", "text/plain")

    def log_message(self, format, *args):
        pass  # Отключаем логи


def run_server(port=8080):
    """Запуск сервера. По умолчанию слушает только localhost (API_HOST=0.0.0.0 — открыть наружу)"""
    host = os.environ.get("API_HOST", "127.0.0.1")
    server = HTTPServer((host, port), AdminHandler)
    print(f"Админ-панель запущена: http://{host}:{port}")
    server.serve_forever()


if __name__ == '__main__':
    run_server()
