"""
API сервер для админ-панели Творог VPN
"""
import sqlite3
import json
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from config import DATABASE_PATH


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


class AdminHandler(SimpleHTTPRequestHandler):
    """Обработчик запросов"""

    def do_GET(self):
        if self.path == '/api/stats':
            data = get_stats()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

        elif self.path == '/api/users':
            data = get_users()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

        elif self.path == '/api/payments':
            data = get_payments()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

        elif self.path == '/' or self.path == '/index.html':
            self.path = '/admin.html'
            return super().do_GET()
        else:
            return super().do_GET()

    def log_message(self, format, *args):
        pass  # Отключаем логи


def run_server(port=8080):
    """Запуск сервера"""
    server = HTTPServer(('0.0.0.0', port), AdminHandler)
    print(f"Админ-панель запущена: http://localhost:{port}")
    server.serve_forever()


if __name__ == '__main__':
    run_server()
