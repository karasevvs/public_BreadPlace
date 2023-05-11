from datetime import datetime
from app_settings import STEAM_KZ_KEY, EPIC_URL
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import dateutil.parser
import inspect
import requests
import time
import asyncio


async def write_logs(func_name, file_name, error=None):
    """
    Функция логирования результатов работы различных функций.
    По умолчанию файлы логов: (successful_logs, error_logs, logs)
    Если ошибки нет, то None
    :param func_name: имя функции подлежащей логированию
    :param file_name: имя файла без расширения куда будем писать лог
    :param error: ошибка подлежащая логированию
    :return: ничего
    """
    log = f'date={str(datetime.utcnow())}; func_name={func_name}; ' \
          f'error={error}; '
    with open(f'{file_name}.txt', 'a', encoding='utf-8') as file:
        file.writelines(log + '\n')


async def steam_games(cc, discount=100):
    try:
        if cc == 'RU':
            max_counter = 20
        else:
            max_counter = 10
        counter = 1
        # для хранения результатов
        result_carts = []

        agent = UserAgent(browsers=['chrome']).random
        headers = {
            "User-Agent": agent
        }
        params = {
            "key": STEAM_KZ_KEY,
            "sort_by": "Price_ASC",
            "category1": "998%2C994%2C21%2C996",
            "specials": "1",
            "ndl": "1",
            "cc": cc,
            "realm": "1",
            "l": "russian",
        }
        currencies = {
            "KZ": "₸",
            "RU": "pуб.",
        }
        response = requests.get("https://store.steampowered.com/search/", headers=headers, params=params)
        soup = BeautifulSoup(response.content, "html.parser")
        carts = soup.find('div', {"id": "search_result_container"}).find_all("a")
        time.sleep(0.5)
        for cart in carts:
            # ищем название товара
            name = cart.find('div', class_='col search_name ellipsis')
            if name is not None:
                name = name.find("span").text
            else:
                name = ""

            # ищем ссылку на товар
            src_cart = cart.get("href")

            # ищем цену товара
            prices = cart.find('div', class_='col search_price discounted responsive_secondrow')
            if prices is None:
                price_old, price_new = '', ''
            else:
                price_old = ''
                price_new = ''
                prices = prices.text.split(f'{currencies[f"{cc}"]}')
                # ишем старую цену
                for elem in prices[0]:
                    if elem.isdigit():
                        price_old += elem
                    elif elem == ',':
                        price_old += '.'
                # ишем новую цену
                for elem in prices[1]:
                    if elem.isdigit():
                        price_new += elem
                    elif elem == ',':
                        price_new += '.'
                if prices[1] == 'Бесплатно':
                    price_new = '0'

            # ищем ссылку на обложку товара
            src = cart.find('div', class_='col search_capsule')
            if src is not None:
                src = src.find('img').get('src')
                src_img = src.replace('capsule_sm_120', 'header')
            else:
                src_img = ''

            # ищем размер скидки
            percentage = cart.find('div', class_='col search_discount responsive_secondrow')
            if percentage is not None:
                percentage = percentage.find("span")
                if percentage is not None:
                    sale = ''
                    for elem in percentage.text:
                        if elem.isdigit():
                            sale += elem
                    discount_percentage = sale
                else:
                    discount_percentage = ''
            else:
                discount_percentage = ''

            # проверяем, чтобы была цена, т.к. с ру регионом проблема + отбор по скидке
            if price_new != '' and int(discount_percentage) >= discount:
                get_param = {
                    "cc": cc,
                    "l": "russian",
                }
                r = requests.get(f'{src_cart}',
                                 headers=headers,
                                 params=get_param)
                sp = BeautifulSoup(r.text, "html.parser")
                data = sp.find('p', class_="game_purchase_discount_countdown")
                free_end = 'ограниченное предложение'
                if data.find("span"):
                    if data.find("span").text:
                        free_end = data.find("span").text
                else:
                    st = data.text.find("канчивается") + 12
                    free_end = data.text[st:]
                # добавляем карточки
                result_carts.append({
                    'name': name,
                    'price_old': price_old,
                    'price_new': price_new,
                    'discount_percentage': discount_percentage,
                    'src_cart': src_cart,
                    'src_img': src_img,
                    'create_date': str(datetime.utcnow()),
                    'modify_date': str(datetime.utcnow()),
                    'free_start': '',
                    'free_end': free_end,
                    'region': cc
                })
            if counter > max_counter:
                break
            counter += 1
        await write_logs(func_name=inspect.currentframe().f_code.co_name, file_name='successful_logs',
                         error='successfully')
        return result_carts
    except Exception as error:
        await write_logs(func_name=inspect.currentframe().f_code.co_name, file_name='error_logs', error=error)
        return None
    finally:
        await write_logs(func_name=inspect.currentframe().f_code.co_name, file_name='logs', error='used')


async def epic_free_games(base_url):
    try:
        # для хранения результатов
        result_carts = []
        agent = UserAgent(browsers=['chrome']).random
        headers = {
            "User-Agent": agent
        }
        contents = requests.get(base_url, headers=headers)
        # получаем список бесплатных товаров
        free_games = contents.json()
        free_games_list = free_games["data"]["Catalog"]["searchStore"]["elements"]

        # обходим список
        for game in free_games_list:
            start = ''
            end = ''
            # если уже доступно
            if game["promotions"] is not None and game["promotions"]["promotionalOffers"] is not None:
                if len(game["promotions"]["promotionalOffers"]) > 0:
                    start = game["promotions"]["promotionalOffers"][0]["promotionalOffers"][0][
                        "startDate"]
                    start = dateutil.parser.isoparse(start)
                    end = game["promotions"]["promotionalOffers"][0]["promotionalOffers"][0][
                        "endDate"]
                    end = dateutil.parser.isoparse(end)
            # ищем имя товара
            name = game["title"]
            # ищем ссылку на обложку товара
            src_img = game["keyImages"][0]["url"]
            #  ищем старую цену товара
            price_old = game["price"]["totalPrice"]["originalPrice"]
            price_old_rub = str(price_old // 100) + "." + str(price_old % 100)
            # ищем новую цену товара
            price_new = game["price"]["totalPrice"]["discountPrice"]
            price_new_rub = str(price_new // 100) + "." + str(price_new % 100)
            # ищем ссылку на id товара
            src_cart = game["catalogNs"]["mappings"]
            # проверяем вдруг игра стала бесплатной
            if len(game["offerMappings"]) > 0:
                src_cart = game["offerMappings"]
            # формируем ссылку на товар
            if len(src_cart) != 0:
                src_cart = "https://store.epicgames.com/ru/p/" + src_cart[0]["pageSlug"] + "/"
            else:
                src_cart = ''
            # отсекаем бесплатные игры
            if price_new == 0:
                discount_percentage = '100'
            else:
                # расчитаем % скидки
                discount_percentage = str(int(100 - (price_new / (price_old / 100))))
            # проферяем валидность товара и формируем список
            if price_new == 0 and src_cart != '' and start != '' and end != '':
                result_carts.append({
                    'name': name,
                    'price_old': price_old_rub,
                    'price_new': price_new_rub,
                    'discount_percentage': discount_percentage,
                    'src_cart': src_cart,
                    'src_img': src_img,
                    'create_date': str(datetime.utcnow()),
                    'modify_date': str(datetime.utcnow()),
                    'free_start': str(start),
                    'free_end': str(end)
                })
        await write_logs(func_name=inspect.currentframe().f_code.co_name, file_name='successful_logs',
                         error='successfully')
        return result_carts
    except Exception as error:
        await write_logs(func_name=inspect.currentframe().f_code.co_name, file_name='error_logs', error=error)
        return None
    finally:
        await write_logs(func_name=inspect.currentframe().f_code.co_name, file_name='logs', error='used')

# --------------------------------------------------------------------------------------------------------------------
