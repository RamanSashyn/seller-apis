import io
import logging.config
import os
import re
import zipfile
from environs import Env

import pandas as pd
import requests

logger = logging.getLogger(__file__)


def get_product_list(last_id, client_id, seller_token):
    """Получает список товаров магазина Ozon.

    Аргументы:
        last_id (str): ID последнего товара из предыдущего запроса.
        client_id (str): ID клиента Ozon.
        seller_token (str): Токен авторизации для продавца.

    Возвращает:
        dict: Ответ от API в формате JSON. Содержит ключи:
            - 'items' (list): Список товаров.
            - 'total' (int): Общее количество товаров.
            - 'last_id' (str): ID последнего товара в ответе.

    Примеры:
        >>> get_product_list("12345", "client_id", "seller_token")
        {'items': [...], 'total': 1000, 'last_id': '67890'}

        >>> get_product_list("", "wrong_client_id", "wrong_token")
        {'result': 'error'}
    """
    url = "https://api-seller.ozon.ru/v2/product/list"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {
        "filter": {
            "visibility": "ALL",
        },
        "last_id": last_id,
        "limit": 1000,
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    response_object = response.json()
    return response_object.get("result")


def get_offer_ids(client_id, seller_token):
    """Получает артикулы всех товаров магазина Ozon.

    Аргументы:
        client_id (str): ID клиента Ozon.
        seller_token (str): Токен авторизации для продавца.

    Возвращает:
        list: Список offer_id всех товаров.

    Пример:
        >>> get_offer_ids("client_id", "seller_token")
        ['1001', '1002', ...]
    """
    last_id = ""
    product_list = []
    while True:
        some_prod = get_product_list(last_id, client_id, seller_token)
        product_list.extend(some_prod.get("items"))
        total = some_prod.get("total")
        last_id = some_prod.get("last_id")
        if total == len(product_list):
            break
    offer_ids = []
    for product in product_list:
        offer_ids.append(product.get("offer_id"))
    return offer_ids


def update_price(prices: list, client_id, seller_token):
    """ Обновляет цены товаров на Ozon.

    Аргументы:
        prices (list): Список словарей с полями "offer_id" и "price".
        client_id (str): ID клиента Ozon.
        seller_token (str): Токен авторизации для продавца.

    Возвращает:
        dict: Ответ от API в формате JSON. Содержит ключи:
            - 'result' (str): Статус операции ('success' или 'error').

    Примеры:
        >>> update_price([{'offer_id': '1001', 'price': '500'}], "client_id", "seller_token")
        {'result': 'success'}
    """
    url = "https://api-seller.ozon.ru/v1/product/import/prices"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"prices": prices}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def update_stocks(stocks: list, client_id, seller_token):
    """Обновляет остатки товаров на Ozon.

    Аргументы:
        stocks (list): Список словарей с полями "offer_id" и "stock".
        client_id (str): ID клиента Ozon.
        seller_token (str): Токен авторизации для продавца.

    Возвращает:
        dict: Ответ в формате JSON. Содержит ключи:
            - 'result' (str): Статус операции ('success' или 'error').

    Пример:
        >>> update_stocks([{'offer_id': '1001', 'stock': 10}], "client_id", "seller_token")
        {'result': 'success'}
    """
    url = "https://api-seller.ozon.ru/v1/product/import/stocks"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"stocks": stocks}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def download_stock():
    """Скачивает и обрабатывает файл остатков с сайта Casio.

    Возвращает:
        list: Список словарей с остатками товаров, считанными из Excel-файла.
    """
    # Скачать остатки с сайта
    casio_url = "https://timeworld.ru/upload/files/ostatki.zip"
    session = requests.Session()
    response = session.get(casio_url)
    response.raise_for_status()
    with response, zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(".")
    # Создаем список остатков часов:
    excel_file = "ostatki.xls"
    watch_remnants = pd.read_excel(
        io=excel_file,
        na_values=None,
        keep_default_na=False,
        header=17,
    ).to_dict(orient="records")
    os.remove("./ostatki.xls")  # Удалить файл
    return watch_remnants


def create_stocks(watch_remnants, offer_ids):
    """Создаёт список остатков для загрузки в Ozon.

    Аргументы:
        watch_remnants (list): Список остатков из файла.
        offer_ids (list): Список артикулов (offer_id) из магазина.

    Возвращает:
        list: Сформированный список остатков с полями 'offer_id' и 'stock'.
    """
    # Уберем то, что не загружено в seller
    stocks = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            count = str(watch.get("Количество"))
            if count == ">10":
                stock = 100
            elif count == "1":
                stock = 0
            else:
                stock = int(watch.get("Количество"))
            stocks.append({"offer_id": str(watch.get("Код")), "stock": stock})
            offer_ids.remove(str(watch.get("Код")))
    # Добавим недостающее из загруженного:
    for offer_id in offer_ids:
        stocks.append({"offer_id": offer_id, "stock": 0})
    return stocks


def create_prices(watch_remnants, offer_ids):
    """Создаёт список цен для загрузки в Ozon.

    Аргументы:
        watch_remnants (list): Список остатков из файла.
        offer_ids (list): Список артикулов (offer_id) из магазина.

    Возвращает:
        list: Сформированный список цен с полями 'offer_id', 'price', и др.
    """
    prices = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            price = {
                "auto_action_enabled": "UNKNOWN",
                "currency_code": "RUB",
                "offer_id": str(watch.get("Код")),
                "old_price": "0",
                "price": price_conversion(watch.get("Цена")),
            }
            prices.append(price)
    return prices


def price_conversion(price: str) -> str:
    """Преобразует строку с ценой в числовую строку без форматирования.

    Функция убирает всё, что не относится к числам и возвращает
    только числовую часть в виде строки.

    Аргументы:
         price (str): Строка с ценой, например, "5'990.00 руб."

    Возвращает:
         str: Число в виде строки, например, "5990".

    Примеры:
        >>> price_conversion("5'990.00 руб.")
        '5990'

        >>> price_conversion("Ошибка")
        ''
    """
    return re.sub("[^0-9]", "", price.split(".")[0])


def divide(lst: list, n: int):
    """Делит список lst на части по n элементов

    Аргументы:
        lst (list): Список для разделения.
        n (int): Количество элементов в каждой части.

    Возвращает:
        Generator: Части списка.

    Пример:
        >>> list(divide([1, 2, 3, 4, 5], 2))
        [[1, 2], [3, 4], [5]]
    """
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


async def upload_prices(watch_remnants, client_id, seller_token):
    """Загружает цены на Ozon.

    Аргументы:
        watch_remnants (list): Список остатков из файла.
        client_id (str): ID клиента Ozon.
        seller_token (str): Токен авторизации для продавца.

    Возвращает:
        list: Загруженные цены для всех offer_id.
    """
    offer_ids = get_offer_ids(client_id, seller_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_price in list(divide(prices, 1000)):
        update_price(some_price, client_id, seller_token)
    return prices


async def upload_stocks(watch_remnants, client_id, seller_token):
    """Загружает остатки на Ozon.

    Аргументы:
        watch_remnants (list): Список остатков из файла.
        client_id (str): ID клиента Ozon.
        seller_token (str): Токен авторизации для продавца.

    Возвращает:
        tuple:
            - not_empty (list): Остатки без нулевых значений.
            - stocks (list): Полный список остатков.
    """
    offer_ids = get_offer_ids(client_id, seller_token)
    stocks = create_stocks(watch_remnants, offer_ids)
    for some_stock in list(divide(stocks, 100)):
        update_stocks(some_stock, client_id, seller_token)
    not_empty = list(filter(lambda stock: (stock.get("stock") != 0), stocks))
    return not_empty, stocks


def main():
    env = Env()
    seller_token = env.str("SELLER_TOKEN")
    client_id = env.str("CLIENT_ID")
    try:
        offer_ids = get_offer_ids(client_id, seller_token)
        watch_remnants = download_stock()
        # Обновить остатки
        stocks = create_stocks(watch_remnants, offer_ids)
        for some_stock in list(divide(stocks, 100)):
            update_stocks(some_stock, client_id, seller_token)
        # Поменять цены
        prices = create_prices(watch_remnants, offer_ids)
        for some_price in list(divide(prices, 900)):
            update_price(some_price, client_id, seller_token)
    except requests.exceptions.ReadTimeout:
        print("Превышено время ожидания...")
    except requests.exceptions.ConnectionError as error:
        print(error, "Ошибка соединения")
    except Exception as error:
        print(error, "ERROR_2")


if __name__ == "__main__":
    main()
