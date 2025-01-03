# Скрипт для синхронизации остатков и цен с Ozon

Этот скрипт помогает автоматизировать процесс обновления цен и остатков товаров на Ozon, используя данные с сайта Casio.

## Что делает скрипт?

1. Загружает данные о товарах с Ozon: список товаров и их артикулы.
2. Скачивает файл с остатками с сайта Casio и обрабатывает его.
3. Сравнивает данные Ozon с Casio, чтобы обновить остатки и цены.
4. Загружает новые данные (цены и остатки) на Ozon.

## Зачем это нужно?

- **Экономия времени**: больше не нужно вручную обновлять остатки и цены.
- **Точность**: данные берутся из надёжных источников и автоматически синхронизируются.
- **Простота использования**: скрипт сам делает всю работу.

## Как работает?

1. Скрипт подключается к API Ozon, чтобы получить данные о товарах.
2. Скачивает файл с остатками с сайта Casio.
3. Обрабатывает данные и проверяет, какие товары нужно обновить.
4. Загружает изменения (цены и остатки) на Ozon.

## Что нужно для работы?

- Токен и ID клиента Ozon (их можно получить в личном кабинете Ozon Seller).
- Установить переменные окружения:
  - `SELLER_TOKEN` — ваш токен продавца.
  - `CLIENT_ID` — ID клиента.

## Проблемы, которые решает скрипт

- Постоянная ручная работа с обновлением данных.
- Ошибки из-за человеческого фактора при вводе цен и остатков.
- Задержка обновлений из-за занятости или забывчивости.

## Заключение

Этот скрипт отлично подойдёт для автоматизации работы с товарами на Ozon. Просто запускаете его — и данные обновляются сами!