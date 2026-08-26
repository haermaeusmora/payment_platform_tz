# Payment Platform

Платформа для приёма платежей за онлайн-услуги.

## Установка

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

API
Method	Endpoint	Description
POST	/api/v1/invoices/	Создать счёт
GET	/api/v1/invoices/{id}/	Детали счёта
POST	/api/v1/invoices/{id}/cancel/	Отменить счёт
POST	/internal/payments/	Зафиксировать платёж
GET	/api/v1/merchants/{id}/balance/	Баланс
GET	/api/v1/merchants/{id}/report/	Отчёт

Уведомления
Уведомления отправляются через management-команду:
python manage.py send_notifications
Повторные попытки: 5 раз с экспоненциальной задержкой (5, 10, 20, 40, 80 минут).

Тесты
python manage.py test apps.core.tests

Допущения
Комиссия: 1% от суммы, но не менее 0.50 в валюте счёта

Переплата > 1% от суммы счёта → статус overpaid

Курсы валют: используются на момент платежа

Уведомления: асинхронные через management-команду

Не сделано:
Celery для асинхронных уведомлений

Нагрузочное тестирование

Мониторинг
