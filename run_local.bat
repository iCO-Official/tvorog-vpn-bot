@echo off
echo ========================================
echo    Творог VPN - Локальный запуск
echo ========================================
echo.

echo Проверка Python...
python --version
if %errorlevel% neq 0 (
    echo ОШИБКА: Python не установлен!
    echo Скачай с https://python.org
    pause
    exit /b 1
)

echo.
echo Установка зависимостей...
pip install python-telegram-bot aiohttp

echo.
echo Очистка кэша...
if exist __pycache__ rmdir /s /q __pycache__

echo.
echo Запуск бота...
echo Нажми Ctrl+C для остановки
echo.
python bot.py

pause