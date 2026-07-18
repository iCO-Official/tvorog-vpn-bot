.PHONY: install start stop restart status logs backup restore update clean test

# Установка зависимостей
install:
	pip3 install -r requirements.txt

# Запуск бота
start:
	./start_bot.sh

# Остановка бота
stop:
	./stop_bot.sh

# Перезапуск бота
restart:
	./restart_bot.sh

# Проверка статуса
status:
	./status.sh

# Просмотр логов
logs:
	./logs.sh

# Резервное копирование
backup:
	./backup.sh

# Восстановление
restore:
	./restore.sh

# Обновление
update:
	./update_bot.sh

# Очистка
clean:
	./cleanup.sh

# Тестирование
test:
	python3 test_bot.py

# Генерация отчёта
report:
	python3 generate_report.py

# Добавление пользователя
add-user:
	python3 add_user.py $(USER_ID) $(DAYS)

# Удаление пользователя
remove-user:
	python3 remove_user.py $(USER_ID)

# Помощь
help:
	@echo "Доступные команды:"
	@echo "  make install      - Установка зависимостей"
	@echo "  make start        - Запуск бота"
	@echo "  make stop         - Остановка бота"
	@echo "  make restart      - Перезапуск бота"
	@echo "  make status       - Проверка статуса"
	@echo "  make logs         - Просмотр логов"
	@echo "  make backup       - Резервное копирование"
	@echo "  make restore      - Восстановление"
	@echo "  make update       - Обновление"
	@echo "  make clean        - Очистка"
	@echo "  make test         - Тестирование"
	@echo "  make report       - Генерация отчёта"
	@echo "  make add-user USER_ID=123 DAYS=30"
	@echo "  make remove-user USER_ID=123"