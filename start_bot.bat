@echo off
echo ========================================
echo    Творог VPN Bot - Запуск
echo ========================================
echo.

echo Проверка Python...
python --version
if %errorlevel% neq 0 (
    echo ОШИБКА: Python не установлен!
    echo Скачайте Python с https://python.org
    pause
    exit /b 1
)

echo.
echo Проверка зависимостей...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ОШИБКА: Не удалось установить зависимости!
    pause
    exit /b 1
)

echo.
echo Запуск бота...
echo Нажмите Ctrl+C для остановки
echo.
python bot.py

pause