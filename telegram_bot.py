from app_settings import TOKEN_BOT_TELEGRAM, TELEGRAM_BOT_ACCESS_LIST, TOKEN_YADISK, EPIC_URL, TELEGRAM_BOT_ID, \
    TELEGRAM_CHAT_ID
from content_work import epic_free_games, steam_games
from datetime import datetime, timedelta
import asyncio
import aiogram
import yadisk
import os
import inspect
import sqlite3
import time


async def start_handler(event: aiogram.types.Message):
    user_id = str(event.from_user.id)
    if user_id in TELEGRAM_BOT_ACCESS_LIST:
        kb = [
            [aiogram.types.KeyboardButton('/epic_publish'), aiogram.types.KeyboardButton('/steam_publish')],
            [aiogram.types.KeyboardButton('/all_epic_steam_publish')],
            [aiogram.types.KeyboardButton('/watch_url_epic'), aiogram.types.KeyboardButton('/watch_url_steam')],
            [aiogram.types.KeyboardButton('/check_db_epic'), aiogram.types.KeyboardButton('/check_db_steam')],
            [aiogram.types.KeyboardButton('/download_db'), aiogram.types.KeyboardButton('/upload_db')],
        ]
        print(f'{user_id} - есть доступ')
    else:
        kb = [
            [aiogram.types.KeyboardButton('Уходи!')],
        ]
        await event.answer(f"⛔В доступе отказано⛔\n Ваш ID: {user_id}")
        print(f'{user_id} - отказано в доступе')

    keyboard = aiogram.types.ReplyKeyboardMarkup(keyboard=kb)
    await event.answer(
        f"Сладенький, {event.from_user.get_mention(as_html=True)} 👋!",
        parse_mode=aiogram.types.ParseMode.HTML,
        reply_markup=keyboard
    )


async def download_db(event: aiogram.types.Message):
    await event.answer(
        text=f'{inspect.currentframe().f_code.co_name} - start!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )
    # -----------------------------------------------------------------
    if os.path.isfile("DB_BreadPlace"):
        os.remove("DB_BreadPlace")
    ya = yadisk.YaDisk(token=TOKEN_YADISK)
    ya.download("!BreadPlace!/DB_BreadPlace", "DB_BreadPlace")
    text = f'Локальная копия БД загружена на сервер'
    await event.bot.send_message(
        chat_id=TELEGRAM_BOT_ID,
        text=text,
        parse_mode=aiogram.types.ParseMode.HTML
    )
    # -----------------------------------------------------------------
    # ответ о завершении
    await event.answer(
        text=f'{inspect.currentframe().f_code.co_name} - finish!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )


# обработка поиска доступного контента
async def epic_publish(event: aiogram.types.Message):
    # ответ перед началом
    await event.answer(
        text=f'{inspect.currentframe().f_code.co_name} - start!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )
    # -----------------------------------------------------------------
    for_message_handler = '<strong>📌 Epic Games Store (RU🇷🇺)</strong>\n\n'
    # получаем информацию из EpicStoreGames
    epic = await epic_free_games(base_url=EPIC_URL)
    # Раздачи в магазине есть
    if epic:
        # удаляем локальную копию БД если есть
        if os.path.isfile("DB_BreadPlace"):
            os.remove("DB_BreadPlace")
        # скачиваем новую версию БД
        ya = yadisk.YaDisk(token=TOKEN_YADISK)
        ya.download("!BreadPlace!/DB_BreadPlace", "DB_BreadPlace")
        # -------------------------------------------------------------------
        # подключаемся к бд
        conn = sqlite3.connect('DB_BreadPlace')
        cur = conn.cursor()
        # стягиваем данные из бд
        DB_EpicGames = cur.execute("SELECT create_date , name  FROM PostsFreeEpicGames").fetchall()
        # список для публикации
        for_public = []
        for item in epic:
            exists_status = 1
            # в базе есть записи
            for db_post in DB_EpicGames:
                # ранее не раздавалась
                if item["name"] != db_post[1]:
                    exists_status = 0
                # ранее уже раздавалась
                elif item["name"] == db_post[1]:
                    date_db_post = datetime.strptime(db_post[0][:-6], "%Y-%m-%d %H:%M:%S.")
                    start_free_date = datetime.strptime(item["create_date"][:-6], "%Y-%m-%d %H:%M:%S.")
                    # раздача была давно
                    if (start_free_date - date_db_post).days > 29:
                        exists_status = 0
                        break
                    # раздача недавно
                    elif (datetime.now() - date_db_post).days <= 29:
                        exists_status = 1
                        break
            # формируем список для постов новых
            if exists_status == 0:
                for_public.append(
                    {
                        "name": item["name"],
                        "price_old": item["price_old"],
                        "price_new": item["price_new"],
                        "discount_percentage": item["discount_percentage"],
                        "src_cart": item["src_cart"],
                        "src_img": item["src_img"],
                        "create_date": item["create_date"],
                        "modify_date": item["modify_date"],
                        'free_start': item["free_start"],
                        'free_end': item["free_end"]
                    }
                )
            # в базе ничего нет
            if len(DB_EpicGames) == 0:
                for_public.append(
                    {
                        "name": item["name"],
                        "price_old": item["price_old"],
                        "price_new": item["price_new"],
                        "discount_percentage": item["discount_percentage"],
                        "src_cart": item["src_cart"],
                        "src_img": item["src_img"],
                        "create_date": item["create_date"],
                        "modify_date": item["modify_date"],
                        'free_start': item["free_start"],
                        'free_end': item["free_end"]
                    }
                )
        # --------------------------------------------------------------------
        # публикуем посты в телегу
        for public in for_public:
            # формируем дату конца раздачи
            free_end = datetime.strptime(public['free_end'][:-6], "%Y-%m-%d %H:%M:%S") + + timedelta(hours=3)
            hour = str(free_end.hour)
            if len(hour) < 2:
                hour = f'0{hour}'
            minute = str(free_end.minute)
            if len(minute) < 2:
                minute = f'0{minute}'
            day = str(free_end.day)
            if len(day) < 2:
                day = f'0{day}'
            month = str(free_end.month)
            if len(month) < 2:
                month = f'0{month}'
            free_end = f'{day}/{month}/{str(free_end.year)[2:]} {hour}:{minute}'
            if public["price_old"] != '0.0':
                msg = f'<b>🎮 {public["name"]}</b>\n\n {for_message_handler}' \
                      f'✏ <em>Цена: <strike>{public["price_old"]}</strike> ₽ -- бесплатно\n' \
                      f'🗓 До: {free_end} МСК (+3)</em>\n\n' \
                      f'🎁 <a href="{public["src_cart"]}">Забрать бесплатно</a> 🎁\n'
            else:
                msg = f'<b>🎮 {public["name"]}</b>\n' \
                      f'\n✏ <code>Временно бесплатная</code>\n' \
                      f'✏ <code>До:{free_end} МСК(+3)</code>\n\n' \
                      f'🎁 <a href="{public["src_cart"]}">Забрать бесплатно</a> 🎁\n'
            photo = public["src_img"]
            caption = f'{msg}'
            await event.bot.send_photo(
                chat_id=TELEGRAM_CHAT_ID,
                caption=caption,
                parse_mode=aiogram.types.ParseMode.HTML,
                photo=photo
            )
            # записываем в базу
            sql = "INSERT INTO PostsFreeEpicGames VALUES (:name, :price_old, :price_new, :discount_percentage," \
                  " :src_cart, :src_img, :create_date, :modify_date, :free_start, :free_end)"
            cur.execute(sql,
                        {"name": public["name"],
                         "price_old": public["price_old"],
                         "price_new": public["price_new"],
                         "discount_percentage": public["discount_percentage"],
                         "src_cart": public["src_cart"],
                         "src_img": public["src_img"],
                         "create_date": public["create_date"],
                         "modify_date": public["modify_date"],
                         'free_start': public["free_start"],
                         'free_end': public["free_end"]
                         })
            conn.commit()
            time.sleep(3)
        # закрыть соединение
        conn.close()
        # если только повторы
        if len(for_public) == 0:
            await event.answer(
                text=f'{for_message_handler}❌ Ничего нового не раздается!',
                parse_mode=aiogram.types.ParseMode.HTML,
            )
        # -------------------------------------------------------------------
        # загружаем книгу на яндекс диск
        ya.remove("!BreadPlace!/DB_BreadPlace")
        ya.upload("DB_BreadPlace", "!BreadPlace!/DB_BreadPlace")
        # удаляем в локальном хранилище
        if os.path.isfile("DB_BreadPlace"):
            os.remove("DB_BreadPlace")
    # Раздач в магазине нет
    else:
        await event.answer(
            text=f'{for_message_handler}❌ Активных раздач нет!',
            parse_mode=aiogram.types.ParseMode.HTML,
        )
    # -----------------------------------------------------------------
    # ответ о завершении
    await event.answer(
        text=f'{inspect.currentframe().f_code.co_name} - finish!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )


async def watch_url_epic(event: aiogram.types.Message):
    await event.answer(
        text=f'{inspect.currentframe().f_code.co_name} - start!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )
    # -----------------------------------------------------------------
    for_message_handler = '<strong>📌 Epic Games Store (RU🇷🇺)</strong>\n\n'
    epic = await epic_free_games(EPIC_URL)
    if epic:
        names = []
        for item in epic:
            names.append(f"{item['name']}|{item['price_old']}\n")
        await event.answer(
            text=f'{for_message_handler}{"".join(names)}',
            parse_mode=aiogram.types.ParseMode.HTML,
        )
    else:
        await event.answer(
            text=f'{for_message_handler}❌ Активных раздач нет!',
            parse_mode=aiogram.types.ParseMode.HTML,
        )
    # -----------------------------------------------------------------
    await event.answer(
        text=f'{inspect.currentframe().f_code.co_name} - finish!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )


async def watch_url_steam(event: aiogram.types.Message):
    await event.answer(
        text=f'{inspect.currentframe().f_code.co_name} - start!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )

    # -----------------------------------------------------------------
    async def runner(region):
        steam = await steam_games(cc=f'{region}')  # discount=80
        region_dict = {
            "KZ": "KZ🇰🇿",
            "RU": "RU🇷🇺"
        }
        for_message_handler = f'<strong>📌 Steam Apps Store ({region_dict[region]})</strong>\n'
        if steam:
            names = []
            for item in steam:
                names.append(f"{item['name']}|{item['price_old']}|{item['region']}\n")
            await event.answer(
                text=f'{for_message_handler}{"".join(names)}',
                parse_mode=aiogram.types.ParseMode.HTML,
            )
        else:
            await event.answer(
                text=f'{for_message_handler}❌ Активных раздач нет!',
                parse_mode=aiogram.types.ParseMode.HTML,
            )

    await runner('RU')
    time.sleep(0.2)
    await runner('KZ')
    # -----------------------------------------------------------------
    await event.answer(
        text=f'{inspect.currentframe().f_code.co_name} - finish!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )


async def upload_db(event: aiogram.types.Message):
    await event.answer(
        text=f'{inspect.currentframe().f_code.co_name} - start!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )
    # -----------------------------------------------------------------
    if os.path.isfile("DB_BreadPlace"):
        ya = yadisk.YaDisk(token=TOKEN_YADISK)
        ya.remove("!BreadPlace!/DB_BreadPlace")
        ya.upload("DB_BreadPlace", "!BreadPlace!/DB_BreadPlace")
        text = f'Локальная копия БД загружена на яндекс диск'
    else:
        text = f'Локальная копия БД отсутствует физически'
    await event.bot.send_message(
        chat_id=TELEGRAM_BOT_ID,
        text=text,
        parse_mode=aiogram.types.ParseMode.HTML
    )
    # -----------------------------------------------------------------
    await event.answer(
        text=f'{inspect.currentframe().f_code.co_name} - finish!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )


async def steam_publish(event: aiogram.types.Message):
    # ответ перед началом
    await event.answer(
        text=f'{inspect.currentframe().f_code.co_name} - start!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )
    # ----------------------------------------------------------------------------------------------------------------
    region_dict = {
        "KZ": "KZ🇰🇿",
        "RU": "RU🇷🇺"
    }
    for_message_handler = '<strong>📌 Steam Apps Store (RU🇷🇺, KZ🇰🇿)</strong>\n'
    # получаем информацию из EpicStoreGames
    steam_kz = await steam_games(cc='KZ')  # discount=80
    steam_ru = await steam_games(cc='RU')  # discount=80
    all_steam = None
    # Раздачи в магазине есть
    if steam_kz:
        all_steam = steam_kz
    if steam_ru:
        if all_steam:
            all_steam += steam_ru
        else:
            all_steam = steam_ru
    # проверяем есть ли раздачи
    if all_steam:
        # удаляем локальную копию БД если есть
        if os.path.isfile("DB_BreadPlace"):
            os.remove("DB_BreadPlace")
        # скачиваем новую версию БД
        ya = yadisk.YaDisk(token=TOKEN_YADISK)
        ya.download("!BreadPlace!/DB_BreadPlace", "DB_BreadPlace")
        # -------------------------------------------------------------------
        # подключаемся к бд
        conn = sqlite3.connect('DB_BreadPlace')
        cur = conn.cursor()
        # стягиваем данные из бд
        DB_STEAM = cur.execute("SELECT create_date , name  FROM PostsFreeSteamApps").fetchall()
        # список для публикации
        for_public = []
        for item in all_steam:
            exists_status = 1
            # в базе есть записи
            for db_post in DB_STEAM:
                # ранее не раздавалась
                if item["name"] != db_post[1]:
                    exists_status = 1
                # ранее уже раздавалась
                elif item["name"] == db_post[1]:
                    date_db_post = datetime.strptime(db_post[0][:-6], "%Y-%m-%d %H:%M:%S.")
                    start_free_date = datetime.strptime(item["create_date"][:-6], "%Y-%m-%d %H:%M:%S.")
                    # раздача была давно
                    if (start_free_date - date_db_post).days > 29:
                        exists_status = 0
                        break
                    # раздача недавно
                    elif (datetime.now() - date_db_post).days <= 29:
                        exists_status = 1
            # формируем список для постов новых
            if exists_status == 0:
                for_public.append(
                    {
                        "name": item["name"],
                        "price_old": item["price_old"],
                        "price_new": item["price_new"],
                        "discount_percentage": item["discount_percentage"],
                        "src_cart": item["src_cart"],
                        "src_img": item["src_img"],
                        "create_date": item["create_date"],
                        "modify_date": item["modify_date"],
                        'free_start': item["free_start"],
                        'free_end': item["free_end"],
                        'region': item["region"],
                    }
                )
            # в базе ничего нет
            if len(DB_STEAM) == 0:
                for_public.append(
                    {
                        "name": item["name"],
                        "price_old": item["price_old"],
                        "price_new": item["price_new"],
                        "discount_percentage": item["discount_percentage"],
                        "src_cart": item["src_cart"],
                        "src_img": item["src_img"],
                        "create_date": item["create_date"],
                        "modify_date": item["modify_date"],
                        'free_start': item["free_start"],
                        'free_end': item["free_end"],
                        'region': item["region"],
                    }
                )
        # -------------------
        currencies = {
            "KZ": "₸",
            "RU": "₽",
        }
        # публикуем посты в телегу
        for public in for_public:
            if public['region'] == 'KZ':
                for_message_handler = '<strong>📌 Steam Apps Store (KZ🇰🇿)</strong>\n'
                msg = f'🎮 <b>{public["name"]}</b>\n\n{for_message_handler}' \
                      f'\n✏ <em>Цена: <strike>{public["price_old"]}</strike> {currencies["KZ"]} -- бесплатно\n' \
                      f'🗓 До: {public["free_end"]}</em>\n\n' \
                      f'🎁 <a href="{public["src_cart"]}">Забрать бесплатно</a> 🎁\n'
                caption = f'{msg}'
                await event.bot.send_photo(
                    chat_id=TELEGRAM_CHAT_ID,
                    caption=caption,
                    parse_mode=aiogram.types.ParseMode.HTML,
                    photo=public['src_img']
                )
            if public['region'] == 'RU':
                for_message_handler = '<strong>📌 Steam Apps Store (RU🇷🇺)</strong>\n'
                msg = f'🎮 <b>{public["name"]}</b>\n\n{for_message_handler}' \
                      f'\n✏ <em>Цена: <strike>{public["price_old"]}</strike> {currencies["RU"]} -- бесплатно\n' \
                      f'🗓 До: {public["free_end"]}</em>\n\n' \
                      f'🎁 <a href="{public["src_cart"]}">Забрать бесплатно</a> 🎁\n'
                caption = f'{msg}'
                await event.bot.send_photo(
                    chat_id=TELEGRAM_CHAT_ID,
                    caption=caption,
                    parse_mode=aiogram.types.ParseMode.HTML,
                    photo=public['src_img']
                )
            # ---------------------------------
            # записываем в базу
            sql = "INSERT INTO PostsFreeSteamApps VALUES (:name, :price_old, :price_new, :discount_percentage," \
                  " :src_cart, :src_img, :create_date, :modify_date, :region, :free_start, :free_end)"
            cur.execute(sql,
                        {"name": public["name"],
                         "price_old": public["price_old"],
                         "price_new": public["price_new"],
                         "discount_percentage": public["discount_percentage"],
                         "src_cart": public["src_cart"],
                         "src_img": public["src_img"],
                         "create_date": public["create_date"],
                         "modify_date": public["modify_date"],
                         'region': public["region"],
                         'free_start': public["free_start"],
                         'free_end': public["free_end"],
                         })
            conn.commit()
            time.sleep(3)
        # закрыть соединение
        conn.close()
        if os.path.isfile("DB_BreadPlace"):
            # загружаем книгу на яндекс диск
            ya.remove("!BreadPlace!/DB_BreadPlace")
            ya.upload("DB_BreadPlace", "!BreadPlace!/DB_BreadPlace")
            # удаляем в локальном хранилище
            os.remove("DB_BreadPlace")
        # если только повторы
        if len(for_public) == 0:
            await event.answer(
                text=f'{for_message_handler}❌ Ничего нового не раздается!',
                parse_mode=aiogram.types.ParseMode.HTML,
            )
    # если раздач нет
    else:
        await event.answer(
            text=f'{for_message_handler}❌ Активных раздач нет!',
            parse_mode=aiogram.types.ParseMode.HTML,
        )
    # ----------------------------------------------------------------------------------------------------------------
    await event.answer(
        text=f'{inspect.currentframe().f_code.co_name} - finish!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )


async def check_db_epic(event: aiogram.types.Message):
    await event.answer(
        text=f'{inspect.currentframe().f_code.co_name} - start!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )
    # -----------------------------------------------------------------
    if os.path.isfile("DB_BreadPlace"):
        os.remove("DB_BreadPlace")
    ya = yadisk.YaDisk(token=TOKEN_YADISK)
    ya.download("!BreadPlace!/DB_BreadPlace", "DB_BreadPlace")
    # подключаемся к бд
    conn = sqlite3.connect('DB_BreadPlace')
    cur = conn.cursor()
    # стягиваем данные из бд
    DB_EPIC = cur.execute(
        "SELECT  name, create_date  FROM PostsFreeEpicGames pfeg ORDER BY create_date DESC LIMIT 30").fetchall()
    for_public = []
    for_message_handler = '<strong>📌DB EpicGamesStore (RU🇷🇺) - макс. 30</strong>\n\n'
    if DB_EPIC:
        for item in DB_EPIC:
            for_public.append(f"{item[0]}|{item[1][:-6]}\n")
        await event.answer(
            text=f'{for_message_handler}{"".join(for_public)}',
            parse_mode=aiogram.types.ParseMode.HTML,
        )
    else:
        await event.answer(
            text=f'{for_message_handler}База данных пустая!',
            parse_mode=aiogram.types.ParseMode.HTML,
        )
    # закрыть соединение
    conn.close()
    # -----------------------------------------------------------------
    await event.answer(
        text=f'{inspect.currentframe().f_code.co_name} - finish!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )


async def check_db_steam(event: aiogram.types.Message):
    await event.answer(
        text=f'{inspect.currentframe().f_code.co_name} - start!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )
    # -----------------------------------------------------------------
    if os.path.isfile("DB_BreadPlace"):
        os.remove("DB_BreadPlace")
    ya = yadisk.YaDisk(token=TOKEN_YADISK)
    ya.download("!BreadPlace!/DB_BreadPlace", "DB_BreadPlace")
    # подключаемся к бд
    conn = sqlite3.connect('DB_BreadPlace')
    cur = conn.cursor()
    # стягиваем данные из бд
    DB_STEAM = cur.execute(
        "SELECT  name, region, create_date  FROM PostsFreeSteamApps pfsa ORDER BY create_date DESC LIMIT 60").fetchall()
    for_public = []
    for_message_handler = '<strong>📌DB SteamAppsStore (RU🇷🇺, KZ🇰🇿) - макс. 60</strong>\n\n'
    if DB_STEAM:
        for item in DB_STEAM:
            for_public.append(f"{item[0]}|{item[1][:-6]}\n")
        await event.answer(
            text=f'{for_message_handler}{"".join(for_public)}',
            parse_mode=aiogram.types.ParseMode.HTML,
        )
    else:
        await event.answer(
            text=f'{for_message_handler}База данных пустая!',
            parse_mode=aiogram.types.ParseMode.HTML,
        )
    # закрыть соединение
    conn.close()
    # -----------------------------------------------------------------
    await event.answer(
        text=f'{inspect.currentframe().f_code.co_name} - finish!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )


async def all_epic_steam_publish(event: aiogram.types.Message):
    await event.answer(
        text=f'⚠️{inspect.currentframe().f_code.co_name} - start!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )
    # -----------------------------------------------------------------
    await epic_publish(event)
    time.sleep(5)
    await steam_publish(event)
    # -----------------------------------------------------------------
    await event.answer(
        text=f'⚠️{inspect.currentframe().f_code.co_name} - finish!',
        parse_mode=aiogram.types.ParseMode.HTML,
    )


# --------------------------------------------------------------------------------------------------------------------
async def main():
    bot = aiogram.Bot(token=TOKEN_BOT_TELEGRAM)
    try:
        disp = aiogram.Dispatcher(bot=bot)
        disp.register_message_handler(start_handler, commands={"start"})

        disp.register_message_handler(download_db, commands={"download_db"}, chat_id=TELEGRAM_BOT_ACCESS_LIST)
        disp.register_message_handler(upload_db, commands={"upload_db"}, chat_id=TELEGRAM_BOT_ACCESS_LIST)

        disp.register_message_handler(epic_publish, commands={"epic_publish"}, chat_id=TELEGRAM_BOT_ACCESS_LIST)
        disp.register_message_handler(steam_publish, commands={"steam_publish"}, chat_id=TELEGRAM_BOT_ACCESS_LIST)

        disp.register_message_handler(watch_url_epic, commands={"watch_url_epic"}, chat_id=TELEGRAM_BOT_ACCESS_LIST)
        disp.register_message_handler(watch_url_steam, commands={"watch_url_steam"}, chat_id=TELEGRAM_BOT_ACCESS_LIST)

        disp.register_message_handler(check_db_epic, commands={"check_db_epic"}, chat_id=TELEGRAM_BOT_ACCESS_LIST)
        disp.register_message_handler(check_db_steam, commands={"check_db_steam"}, chat_id=TELEGRAM_BOT_ACCESS_LIST)

        disp.register_message_handler(all_epic_steam_publish, commands={"all_epic_steam_publish"},
                                      chat_id=TELEGRAM_BOT_ACCESS_LIST)
        await disp.start_polling()
    finally:
        session = await bot.get_session()
        await session.close()


asyncio.run(main())
