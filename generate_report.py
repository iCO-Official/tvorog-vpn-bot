#!/usr/bin/env python3
"""
Генератор отчётов для Творог VPN
"""

import os
import sys
from datetime import datetime, timedelta

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, get_user_stats

def generate_report():
    """Генерация отчёта"""
    init_db()
    stats = get_user_stats()

    report = f"""
========================================
   Творог VPN - Отчёт
========================================
Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 Статистика:
   Всего пользователей: {stats['total_users']}
   Активных подписок: {stats['active_users']}
   Общий доход: {stats['total_revenue']} Stars

========================================
"""

    return report

def main():
    report = generate_report()
    print(report)

    # Сохранение отчёта в файл
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, 'w') as f:
        f.write(report)

    print(f"✅ Отчёт сохранён: {filename}")

if __name__ == "__main__":
    main()