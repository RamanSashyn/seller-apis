import datetime
import logging.config
from environs import Env
from seller import download_stock

import requests

from seller import divide, price_conversion

logger = logging.getLogger(__file__)


def get_product_list(page, campaign_id, access_token):
    """Загружает список товаров с Яндекс.Маркет по указанной странице и кампании.

    Где искать:
        Возвращает данные с API Яндекс.Маркет.

    Что содержится в ответе:
        Ответ от API включает в себя информацию о товарах (offerMappingEntries).

    Аргументы:
        page (str): Токен страницы для получения товаров.
        campaign_id (str): ID кампании на Яндекс.Маркет.
        access_token (str): Токен доступа для авторизации.

    Возвращает:
        dict: Список товаров в виде JSON-объекта.

    Примеры:
        >>> get_product_list("nextPageToken", "12345", "access_token")
        {'result': [...]}

        >>> get_product_list("", "", "")  # В случае неправильных данных или токенов
        {'result': []}
    """
    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {
        "page_token": page,
        "limit": 200,
    }
    url = endpoint_url + f"campaigns/{campaign_id}/offer-mapping-entries"
    response = requests.get(url, headers=headers, params=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object.get("result")


def update_stocks(stocks, campaign_id, access_token):
    """Обновляет остатки товаров на Яндекс.Маркет.

    Где искать:
        Возвращает ответ от API Яндекс.Маркет.

    Что содержится в ответе:
        Ответ от API содержит результат обновления остатков товаров.

    Аргументы:
        stocks (list): Список товаров с новыми остатками.
        campaign_id (str): ID кампании на Яндекс.Маркет.
        access_token (str): Токен доступа для API Яндекс.Маркет.

    Возвращает:
        dict: Ответ от API.
    """
    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {"skus": stocks}
    url = endpoint_url + f"campaigns/{campaign_id}/offers/stocks"
    response = requests.put(url, headers=headers, json=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object


def update_price(prices, campaign_id, access_token):
    """Обновляет цены товаров на Яндекс.Маркет.

    Где искать:
        Возвращает ответ от API Яндекс.Маркет.

    Что содержится в ответе:
        Ответ от API будет содержать информацию о результате обновления цен.

    Аргументы:
        prices (list): Список товаров с новыми ценами.
        campaign_id (str): ID кампании на Яндекс.Маркет.
        access_token (str): Токен доступа для авторизации.

    Возвращает:
        dict: Ответ от API.

    Примеры:
        >>> update_price([{"id": "12345", "price": {"value": 1000}}], "12345", "access_token")
        {'result': 'success'}
        """
    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {"offers": prices}
    url = endpoint_url + f"campaigns/{campaign_id}/offer-prices/updates"
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object


def get_offer_ids(campaign_id, market_token):
    """Получает список артикулов товаров из Яндекс.Маркет по заданной кампании.

    Где искать:
        Ответ содержит список артикулов товаров, полученных из API Яндекс.Маркет.

    Что содержится в ответе:
        Список артикулов товаров (shopSku).

    Аргументы:
        campaign_id (str): ID кампании на Яндекс.Маркет.
        market_token (str): Токен доступа к Яндекс.Маркет API.

    Возвращает:
        list[str]: Список артикулов товаров (shopSku).

    Примеры:
        >>> get_offer_ids("12345", "access_token")
        ['12345', '67890']
    """
    page = ""
    product_list = []
    while True:
        some_prod = get_product_list(page, campaign_id, market_token)
        product_list.extend(some_prod.get("offerMappingEntries"))
        page = some_prod.get("paging").get("nextPageToken")
        if not page:
            break
    offer_ids = []
    for product in product_list:
        offer_ids.append(product.get("offer").get("shopSku"))
    return offer_ids


def create_stocks(watch_remnants, offer_ids, warehouse_id):
    """Создает структуру для обновления остатков на Яндекс.Маркет.

    Где искать:
        Ответ от API Яндекс.Маркет.

    Что содержится в ответе:
        Содержит список товаров с их остатками для обновления в Яндекс.Маркет.

    Аргументы:
        watch_remnants (list): Список остатков с кодами и количеством.
        offer_ids (list): Список артикулов товаров.
        warehouse_id (str): ID склада для обновления остатков.

    Возвращает:
        list[dict]: Список с информацией о товарах и их остатках для загрузки в Яндекс.Маркет.

    Пример:
        >>> create_stocks([{'Код': '12345', 'Количество': '10'}], ['12345'], '100')
        [{'sku': '12345', 'warehouseId': '100', 'items': [{'count': 10, 'type': 'FIT', 'updatedAt': '2025-01-01T12:00:00Z'}]}]
    """
    # Уберем то, что не загружено в market
    stocks = list()
    date = str(datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z")
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            count = str(watch.get("Количество"))
            if count == ">10":
                stock = 100
            elif count == "1":
                stock = 0
            else:
                stock = int(watch.get("Количество"))
            stocks.append(
                {
                    "sku": str(watch.get("Код")),
                    "warehouseId": warehouse_id,
                    "items": [
                        {
                            "count": stock,
                            "type": "FIT",
                            "updatedAt": date,
                        }
                    ],
                }
            )
            offer_ids.remove(str(watch.get("Код")))
    # Добавим недостающее из загруженного:
    for offer_id in offer_ids:
        stocks.append(
            {
                "sku": offer_id,
                "warehouseId": warehouse_id,
                "items": [
                    {
                        "count": 0,
                        "type": "FIT",
                        "updatedAt": date,
                    }
                ],
            }
        )
    return stocks


def create_prices(watch_remnants, offer_ids):
    """Создает структуру для обновления цен товаров на Яндекс.Маркет.

    Где искать:
        Ответ от API Яндекс.Маркет.

    Что содержится в ответе:
        Ответ от API будет содержать обновленные цены товаров.

    Аргументы:
        watch_remnants (list): Список с ценами товаров.
        offer_ids (list): Список артикулов товаров.

    Возвращает:
        list[dict]: Список с информацией о товарах и их ценах для загрузки в Яндекс.Маркет.

    Примеры:
        >>> create_prices([{'Код': '12345', 'Цена': '1000'}], ['12345'])
        [{'id': '12345', 'price': {'value': 1000, 'currencyId': 'RUR'}}]
    """
    prices = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            price = {
                "id": str(watch.get("Код")),
                # "feed": {"id": 0},
                "price": {
                    "value": int(price_conversion(watch.get("Цена"))),
                    # "discountBase": 0,
                    "currencyId": "RUR",
                    # "vat": 0,
                },
                # "marketSku": 0,
                # "shopSku": "string",
            }
            prices.append(price)
    return prices


async def upload_prices(watch_remnants, campaign_id, market_token):
    """Загружает обновленные цены на Яндекс.Маркет.

     Где искать:
        Ответ от API Яндекс.Маркет.

    Что содержится в ответе:
        Список обновленных цен товаров.

    Аргументы:
        watch_remnants (list): Список остатков с ценами.
        campaign_id (str): ID кампании на Яндекс.Маркет.
        market_token (str): Токен доступа для API Яндекс.Маркет.

    Возвращает:
        list[dict]: Список обновленных цен.
    """
    offer_ids = get_offer_ids(campaign_id, market_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_prices in list(divide(prices, 500)):
        update_price(some_prices, campaign_id, market_token)
    return prices


async def upload_stocks(watch_remnants, campaign_id, market_token, warehouse_id):
    """Загружает обновленные остатки товаров на Яндекс.Маркет.

    Где искать:
        Ответ от API Яндекс.Маркет.

    Что содержится в ответе:
        Список товаров с ненулевыми остатками и полный список остатков.

    Аргументы:
        watch_remnants (list): Список остатков с количеством.
        campaign_id (str): ID кампании на Яндекс.Маркет.
        market_token (str): Токен доступа для API Яндекс.Маркет.
        warehouse_id (str): ID склада для обновления остатков.

    Возвращает:
        tuple[list[dict], list[dict]]: Список товаров с ненулевыми остатками и полный список остатков.
    """
    offer_ids = get_offer_ids(campaign_id, market_token)
    stocks = create_stocks(watch_remnants, offer_ids, warehouse_id)
    for some_stock in list(divide(stocks, 2000)):
        update_stocks(some_stock, campaign_id, market_token)
    not_empty = list(
        filter(lambda stock: (stock.get("items")[0].get("count") != 0), stocks)
    )
    return not_empty, stocks


def main():
    """Основная функция для обновления остатков и цен на Яндекс.Маркет.

    Где искать:
        Ответы возвращаются от API Яндекс.Маркет, как в случае с обновлением остатков и цен.

    Что содержится в ответе:
        Ответы содержат результаты обновлений остатков и цен на товары.

    Возвращает:
        None
    """
    env = Env()
    market_token = env.str("MARKET_TOKEN")
    campaign_fbs_id = env.str("FBS_ID")
    campaign_dbs_id = env.str("DBS_ID")
    warehouse_fbs_id = env.str("WAREHOUSE_FBS_ID")
    warehouse_dbs_id = env.str("WAREHOUSE_DBS_ID")

    watch_remnants = download_stock()
    try:
        # FBS
        offer_ids = get_offer_ids(campaign_fbs_id, market_token)
        # Обновить остатки FBS
        stocks = create_stocks(watch_remnants, offer_ids, warehouse_fbs_id)
        for some_stock in list(divide(stocks, 2000)):
            update_stocks(some_stock, campaign_fbs_id, market_token)
        # Поменять цены FBS
        upload_prices(watch_remnants, campaign_fbs_id, market_token)

        # DBS
        offer_ids = get_offer_ids(campaign_dbs_id, market_token)
        # Обновить остатки DBS
        stocks = create_stocks(watch_remnants, offer_ids, warehouse_dbs_id)
        for some_stock in list(divide(stocks, 2000)):
            update_stocks(some_stock, campaign_dbs_id, market_token)
        # Поменять цены DBS
        upload_prices(watch_remnants, campaign_dbs_id, market_token)
    except requests.exceptions.ReadTimeout:
        print("Превышено время ожидания...")
    except requests.exceptions.ConnectionError as error:
        print(error, "Ошибка соединения")
    except Exception as error:
        print(error, "ERROR_2")


if __name__ == "__main__":
    main()
