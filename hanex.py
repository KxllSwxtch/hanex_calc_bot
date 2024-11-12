import time
import pickle
import telebot
import os
import re
import requests
import locale
import datetime
import logging
from telebot import types
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoAlertPresentException


# CapSolver API key
CAPSOLVER_API_KEY = os.getenv("CAPSOLVER_API_KEY")  # Замените на ваш API-ключ CapSolver
SITE_KEY = os.getenv("SITE_KEY")
CHROMEDRIVER_PATH = "/app/.chrome-for-testing/chromedriver-linux64/chromedriver"
# CHROMEDRIVER_PATH = "/opt/homebrew/bin/chromedriver"
COOKIES_FILE = "cookies.pkl"

session = requests.Session()

# Configure logging
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Load keys from .env file
load_dotenv()
bot_token = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(bot_token)

# Set locale for number formatting
locale.setlocale(locale.LC_ALL, "en_US.UTF-8")

# Storage for the last error message ID
last_error_message_id = {}

# global variables
car_data = {}
car_id_external = ""
total_car_price = 0
usd_rate = 0

# users for collecting data about the users
users = set()
admins = [7311593407, 728438182]


# Функция для проверки админских прав
def is_admin(user_id):
    return user_id in admins


# Обработка команды для админов
@bot.message_handler(commands=["admin_menu"])
def admin_menu(message):
    if is_admin(message.from_user.id):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton("Отправить список пользователей бота"))
        keyboard.add(types.KeyboardButton("Выйти в главное меню"))
        bot.send_message(message.chat.id, "Админ меню", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к админ меню.")


@bot.message_handler(func=lambda message: message.text == "Выйти в главное меню")
def return_to_menu(message):
    bot.send_message(
        message.chat.id, "Вы вышли в главное меню", reply_markup=main_menu()
    )


@bot.message_handler(
    func=lambda message: message.text == "Отправить список пользователей бота"
)
def send_user_list(message):
    if is_admin(message.from_user.id):
        manager_id = 728438182
        user_list = "\n".join([str(user_id) for user_id in users])
        bot.send_message(manager_id, f"Список пользователей бота:\n{user_list}")
        bot.send_message(message.chat.id, "Список отправлен менеджеру.")
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к этой функции.")


# Добавление ID пользователей при каждом использовании бота
@bot.message_handler(func=lambda message: True)
def track_users(message):
    users.add(message.from_user.id)


# Функция для установки команд меню
def set_bot_commands():
    commands = [
        types.BotCommand("start", "Запустить бота"),
        types.BotCommand("cbr", "Курсы валют"),
        types.BotCommand("admin_menu", "Меню администратора"),
    ]
    bot.set_my_commands(commands)


# Функция для получения курсов валют с API
def get_currency_rates():
    global usd_rate

    print_message("КУРС ЦБ")

    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    response = requests.get(url)
    data = response.json()

    # Получаем курсы валют
    eur = data["Valute"]["EUR"]["Value"]
    usd = data["Valute"]["USD"]["Value"]
    krw = data["Valute"]["KRW"]["Value"] / data["Valute"]["KRW"]["Nominal"]
    cny = data["Valute"]["CNY"]["Value"]

    # Сохраняем глобально usd
    usd_rate = usd

    # Форматируем текст
    rates_text = (
        f"Курс валют ЦБ:\n\n"
        f"EUR {eur:.4f} ₽\n"
        f"USD {usd:.4f} ₽\n"
        f"KRW {krw:.4f} ₽\n"
        f"CNY {cny:.4f} ₽"
    )

    return rates_text


# Обработчик команды /cbr
@bot.message_handler(commands=["cbr"])
def cbr_command(message):
    try:
        rates_text = get_currency_rates()

        # Создаем клавиатуру с кнопкой для расчета автомобиля
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "🔍 Рассчитать стоимость автомобиля", callback_data="calculate_another"
            )
        )

        # Отправляем сообщение с курсами и клавиатурой
        bot.send_message(message.chat.id, rates_text, reply_markup=keyboard)
    except Exception as e:
        bot.send_message(
            message.chat.id, "Не удалось получить курсы валют. Попробуйте позже."
        )
        print(f"Ошибка при получении курсов валют: {e}")


# Обработчик команды /currencyrates
@bot.message_handler(commands=["currencyrates"])
def currencyrates_command(message):
    bot.send_message(
        message.chat.id, "Актуальные курсы валют: ..."
    )  # Логика для курсов валют


# Main menu creation function
def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(
        types.KeyboardButton("Рассчитать автомобиль до Владивостока"),
        types.KeyboardButton("Написать менеджеру"),
        types.KeyboardButton("О компании HanExport"),
        types.KeyboardButton("Наш Telegram-канал"),
        types.KeyboardButton("Связаться через WhatsApp"),
        types.KeyboardButton("Посетить наш Instagram"),
    )
    return keyboard


# Start command handler
@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_first_name = message.from_user.first_name
    welcome_message = (
        f"👋 Здравствуйте, {user_first_name}!\n"
        "Я бот компании HanExport для расчета стоимости авто до Владивостока! 🚗💰\n\n"
        "Пожалуйста, выберите действие из меню ниже:"
    )
    bot.send_message(message.chat.id, welcome_message, reply_markup=main_menu())


# Error handling function
def send_error_message(message, error_text):
    global last_error_message_id

    # Remove previous error message if it exists
    if last_error_message_id.get(message.chat.id):
        try:
            bot.delete_message(message.chat.id, last_error_message_id[message.chat.id])
        except Exception as e:
            logging.error(f"Error deleting message: {e}")

    # Send new error message and store its ID
    error_message = bot.reply_to(message, error_text, reply_markup=main_menu())
    last_error_message_id[message.chat.id] = error_message.id
    logging.error(f"Error sent to user {message.chat.id}: {error_text}")


def save_cookies(driver):
    with open(COOKIES_FILE, "wb") as file:
        pickle.dump(driver.get_cookies(), file)


# Load cookies from file
def load_cookies(driver):
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)


def check_and_handle_alert(driver, timeout=5):
    try:
        # Ожидание появления alert в течение заданного времени
        WebDriverWait(driver, timeout).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        logging.info(f"Обнаружено всплывающее окно: {alert.text}")
        alert.accept()  # Закрытие alert
        logging.info("Всплывающее окно было закрыто.")
    except TimeoutException:
        logging.info("Нет активного всплывающего окна.")
    except NoAlertPresentException:
        logging.info("Alert исчез до попытки взаимодействия с ним.")


# Function to get car info using Selenium
def get_car_info(url):
    global car_id_external

    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")  # Необходим для работы в Heroku
    chrome_options.add_argument("--disable-dev-shm-usage")  # Решает проблемы с памятью
    chrome_options.add_argument("--window-size=1920,1080")  # Устанавливает размер окна
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--enable-logging")
    chrome_options.add_argument("--v=1")  # Уровень логирования
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    )

    # Инициализация драйвера
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Загружаем страницу
        driver.get(url)
        check_and_handle_alert(driver)  # Обработка alert, если присутствует
        load_cookies(driver)  # Загрузка cookies

        # Проверка на reCAPTCHA
        if "reCAPTCHA" in driver.page_source:
            logging.info("Обнаружена reCAPTCHA. Пытаемся решить...")
            driver.refresh()
            logging.info("Страница обновлена после reCAPTCHA.")
            check_and_handle_alert(driver)  # Перепроверка после обновления страницы

        save_cookies(driver)  # Сохранение cookies
        logging.info("Куки сохранены.")

        # Парсим URL для получения carid
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        car_id = query_params.get("carid", [None])[0]

        # Проверка элемента areaLeaseRent
        try:
            lease_area = driver.find_element(By.ID, "areaLeaseRent")
            title_element = lease_area.find_element(By.CLASS_NAME, "title")

            if "리스정보" in title_element.text or "렌트정보" in title_element.text:
                logging.info("Данная машина находится в лизинге.")
                return [
                    "",
                    "Данная машина находится в лизинге. Свяжитесь с менеджером.",
                ]
        except NoSuchElementException:
            logging.warning("Элемент areaLeaseRent не найден.")

        # Инициализация переменных
        car_title, car_date, car_engine_capacity, car_price = "", "", "", ""

        # Проверка элемента product_left
        try:
            product_left = WebDriverWait(driver, 6).until(
                EC.presence_of_element_located((By.CLASS_NAME, "product_left"))
            )
            product_left_splitted = product_left.text.split("\n")

            car_title = product_left.find_element(
                By.CLASS_NAME, "prod_name"
            ).text.strip()

            car_date = (
                product_left_splitted[3] if len(product_left_splitted) > 3 else ""
            )
            car_engine_capacity = (
                product_left_splitted[6] if len(product_left_splitted) > 6 else ""
            )
            car_price = re.sub(r"\D", "", product_left_splitted[1])

            # Форматирование
            formatted_price = car_price.replace(",", "")
            formatted_engine_capacity = (
                car_engine_capacity.replace(",", "")[:-2]
                if car_engine_capacity
                else "0"
            )
            cleaned_date = "".join(filter(str.isdigit, car_date))
            formatted_date = (
                f"01{cleaned_date[2:4]}{cleaned_date[:2]}" if cleaned_date else "010101"
            )

            # Создание URL
            new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"
            logging.info(f"Данные о машине получены: {new_url}, {car_title}")
            return [new_url, car_title]
        except NoSuchElementException as e:
            logging.error(f"Ошибка при обработке product_left: {e}")
        except Exception as e:
            logging.error(f"Неизвестная ошибка при обработке product_left: {e}")

        # Проверка элемента gallery_photo
        try:
            gallery_element = WebDriverWait(driver, 6).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.gallery_photo"))
            )
            car_title = gallery_element.find_element(By.CLASS_NAME, "prod_name").text

            items = gallery_element.find_elements(By.XPATH, ".//*")
            if len(items) > 10:
                car_date = items[10].text
            if len(items) > 18:
                car_engine_capacity = items[18].text

            # Извлечение информации о ключах
            try:
                keyinfo_element = driver.find_element(
                    By.CSS_SELECTOR, "div.wrap_keyinfo"
                )
                keyinfo_items = keyinfo_element.find_elements(By.XPATH, ".//*")
                keyinfo_texts = [
                    item.text for item in keyinfo_items if item.text.strip()
                ]

                # Извлекаем цену, если элемент существует
                car_price = (
                    re.sub(r"\D", "", keyinfo_texts[12])
                    if len(keyinfo_texts) > 12
                    else None
                )
            except NoSuchElementException:
                logging.warning("Элемент wrap_keyinfo не найден.")
        except NoSuchElementException:
            logging.warning("Элемент gallery_photo также не найден.")

        # Форматирование значений для URL
        if car_price:
            formatted_price = car_price.replace(",", "")
        else:
            formatted_price = "0"  # Задаем значение по умолчанию

        formatted_engine_capacity = (
            car_engine_capacity.replace(",", "")[:-2] if car_engine_capacity else "0"
        )
        cleaned_date = "".join(filter(str.isdigit, car_date))
        formatted_date = (
            f"01{cleaned_date[2:4]}{cleaned_date[:2]}" if cleaned_date else "010101"
        )

        # Конечный URL
        new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"

        logging.info(f"Данные о машине получены: {new_url}, {car_title}")
        return [new_url, car_title]

    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")
        return None, None

    finally:
        # Обработка всплывающих окон (alerts)
        try:
            alert = driver.switch_to.alert
            alert.dismiss()
            logging.info("Всплывающее окно отклонено.")
        except NoAlertPresentException:
            logging.info("Нет активного всплывающего окна.")
        except Exception as alert_exception:
            logging.error(f"Ошибка при обработке alert: {alert_exception}")

        driver.quit()


# Function to calculate the total cost
def calculate_cost(link, message):
    print_message("ЗАПРОС НА РАСЧЁТ АВТОМОБИЛЯ")

    global car_data

    # Отправляем сообщение и сохраняем его ID
    processing_message = bot.send_message(
        message.chat.id, "Данные переданы в обработку ⏳"
    )

    # Проверка ссылки на мобильную версию
    if "fem.encar.com" in link:
        car_id_match = re.findall(r"\d+", link)
        if car_id_match:
            car_id = car_id_match[0]
            link = f"https://www.encar.com/dc/dc_cardetailview.do?carid={car_id}"
        else:
            send_error_message(message, "🚫 Не удалось извлечь carid из ссылки.")
            bot.delete_message(
                message.chat.id, processing_message.message_id
            )  # Удаляем сообщение
            return

    # Получение информации о автомобиле
    result = get_car_info(link)

    if result is None:
        send_error_message(
            message,
            "🚫 Произошла ошибка при получении данных. Проверьте ссылку и попробуйте снова или выберите действие ниже.",
        )
        bot.delete_message(
            message.chat.id,
            processing_message.message_id,
        )  # Удаляем сообщение
        return

    new_url, car_title = result

    if not new_url and car_title:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "Написать менеджеру", url="https://t.me/hanexport11"
            )
        )
        keyboard.add(
            types.InlineKeyboardButton(
                "🔍 Рассчитать стоимость другого автомобиля",
                callback_data="calculate_another",
            )
        )
        bot.send_message(
            message.chat.id, car_title, parse_mode="Markdown", reply_markup=keyboard
        )
        bot.delete_message(
            message.chat.id, processing_message.message_id
        )  # Удаляем сообщение
        return

    if new_url:
        response = requests.get(new_url)

        if response.status_code == 200:
            json_response = response.json()
            car_data = json_response

            result = json_response.get("result", {})
            car = result.get("car", {})
            price = result.get("price", {}).get("car", {}).get("krw", 0)

            year = car.get("date", "").split()[-1]
            engine_volume = car.get("engineVolume", 0)

            print(year, engine_volume, price)

            if year and engine_volume and price:
                engine_volume_formatted = f"{format_number(int(engine_volume))} cc"
                age_formatted = calculate_age(year)

                grand_total = result.get("price", {}).get("grandTotal", 0)
                recycling_fee = (
                    result.get("price", {})
                    .get("russian", {})
                    .get("recyclingFee", {})
                    .get("rub", 0)
                )
                duty_cleaning = (
                    result.get("price", {})
                    .get("korea", {})
                    .get("dutyCleaning", {})
                    .get("rub", 0)
                )

                total_cost = int(grand_total) - int(recycling_fee)
                total_cost_formatted = format_number(total_cost)
                price_formatted = format_number(price)

                result_message = (
                    f"Возраст: {age_formatted}\n"
                    f"Стоимость: {price_formatted} KRW\n"
                    f"Объём двигателя: {engine_volume_formatted}\n\n"
                    f"Стоимость автомобиля под ключ до Владивостока: \n**{total_cost_formatted}₽**\n\n"
                    f"🔗 [Ссылка на автомобиль]({link})\n\n"
                    "Если данное авто попадает под санкции, пожалуйста уточните возможность отправки в вашу страну у менеджера @hanexport11\n\n"
                    "🔗[Официальный телеграм канал](https://t.me/hanexport1)\n"
                )

                bot.send_message(message.chat.id, result_message, parse_mode="Markdown")

                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton(
                        "📊 Детализация расчёта", callback_data="detail"
                    )
                )
                keyboard.add(
                    types.InlineKeyboardButton(
                        "📝 Технический отчёт об автомобиле",
                        callback_data="technical_report",
                    )
                )
                keyboard.add(
                    types.InlineKeyboardButton(
                        "✉️ Связаться с менеджером", url="https://t.me/hanexport11"
                    )
                )
                keyboard.add(
                    types.InlineKeyboardButton(
                        "🔍 Рассчитать стоимость другого автомобиля",
                        callback_data="calculate_another",
                    )
                )

                bot.send_message(
                    message.chat.id, "Что делаем дальше?", reply_markup=keyboard
                )

                # Удаляем сообщение о передаче данных в обработку
                bot.delete_message(message.chat.id, processing_message.message_id)

            else:
                bot.send_message(
                    message.chat.id,
                    "🚫 Не удалось извлечь все необходимые данные. Проверьте ссылку.",
                )
                bot.delete_message(
                    message.chat.id, processing_message.message_id
                )  # Удаляем сообщение
        else:
            send_error_message(
                message,
                "🚫 Произошла ошибка при получении данных. Проверьте ссылку и попробуйте снова.",
            )
            bot.delete_message(
                message.chat.id, processing_message.message_id
            )  # Удаляем сообщение
    else:
        send_error_message(
            message,
            "🚫 Произошла ошибка при получении данных. Проверьте ссылку и попробуйте снова.",
        )
        bot.delete_message(
            message.chat.id, processing_message.message_id
        )  # Удаляем сообщение


# Function to get insurance total
def get_insurance_total():
    print_message("[ЗАПРОС] ТЕХНИЧЕСКИЙ ОТЧЁТ ОБ АВТОМОБИЛЕ")

    global car_id_external

    # Настройка WebDriver с нужными опциями
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Формируем URL
    url = f"http://www.encar.com/dc/dc_cardetailview.do?method=kidiFirstPop&carid={car_id_external}&wtClick_carview=044"

    driver.get(url)
    load_cookies(driver)
    check_and_handle_alert(driver)

    try:
        driver.get(url)
        check_and_handle_alert(driver)

        save_cookies()

        # Ожидаем появления элемента 'smlist' с явным ожиданием
        smlist_element = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CLASS_NAME, "smlist"))
        )

        # Находим таблицу и извлекаем данные
        table = smlist_element.find_element(By.TAG_NAME, "table")
        rows = table.find_elements(By.TAG_NAME, "tr")

        # Функция для получения данных о повреждениях
        def get_damage_data(row_index):
            if len(rows) > row_index:
                return rows[row_index].find_elements(By.TAG_NAME, "td")[1].text
            return None  # Вернем None, если данных нет

        # Извлекаем данные о повреждениях
        damage_to_my_car = get_damage_data(4)
        damage_to_other_car = get_damage_data(5)

        # Упрощенная функция для извлечения числа
        def extract_large_number(damage_text):
            if "없음" in damage_text:
                return "0"
            numbers = re.findall(r"[\d,]+(?=\s*원)", damage_text)
            return numbers[0] if numbers else "0"

        # Форматируем данные
        damage_to_my_car_formatted = (
            extract_large_number(damage_to_my_car) if damage_to_my_car else "Нет данных"
        )
        damage_to_other_car_formatted = (
            extract_large_number(damage_to_other_car)
            if damage_to_other_car
            else "Нет данных"
        )

        # Проверяем, если нет данных
        if damage_to_my_car_formatted == "0" and damage_to_other_car_formatted == "0":
            return None  # Вернем None, если нет данных о страховых выплатах

        return [
            (
                damage_to_my_car_formatted
                if damage_to_my_car_formatted != "0"
                else "Нет данных"
            ),
            (
                damage_to_other_car_formatted
                if damage_to_other_car_formatted != "0"
                else "Нет данных"
            ),
        ]

    except NoSuchElementException:
        print("Элемент 'smlist' не найден.")
        return None  # Вернем None, если элемент не найден
    except Exception as e:
        print(f"Произошла ошибка при получении данных: {e}")
        return None  # Вернем None в случае ошибки

    finally:
        driver.quit()


# Callback query handler
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    global car_data, car_id_external, usd_rate

    if call.data.startswith("detail"):
        print("\n\n####################")
        print("[ЗАПРОС] ДЕТАЛИЗАЦИЯ РАСЧËТА")
        print("####################\n\n")

        details = {
            "car_price_korea": car_data.get("result")["price"]["car"]["rub"],
            "dealer_fee": car_data.get("result")["price"]["korea"]["ab"]["rub"],
            "korea_logistics": car_data.get("result")["price"]["korea"]["logistic"][
                "rub"
            ],
            "customs_fee": car_data.get("result")["price"]["korea"]["dutyCleaning"][
                "rub"
            ],
            "delivery_fee": car_data.get("result")["price"]["korea"]["delivery"]["rub"],
            "dealer_commission": car_data.get("result")["price"]["korea"][
                "dealerCommission"
            ]["rub"],
            "russiaDuty": car_data.get("result")["price"]["russian"]["duty"]["rub"],
            "recycle_fee": car_data.get("result")["price"]["russian"]["recyclingFee"][
                "rub"
            ],
            "registration": car_data.get("result")["price"]["russian"]["registration"][
                "rub"
            ],
            "sbkts": car_data.get("result")["price"]["russian"]["sbkts"]["rub"],
            "svhAndExpertise": car_data.get("result")["price"]["russian"][
                "svhAndExpertise"
            ]["rub"],
            "delivery": car_data.get("result")["price"]["russian"]["delivery"]["rub"],
        }

        car_price_formatted = format_number(details["car_price_korea"])
        dealer_fee_formatted = format_number(details["dealer_fee"])
        korea_logistics_formatted = format_number(details["korea_logistics"])
        delivery_fee_formatted = format_number(details["delivery_fee"])
        dealer_commission_formatted = format_number(details["dealer_commission"])
        russia_duty_formatted = format_number(details["russiaDuty"])
        registration_formatted = format_number(details["registration"])
        sbkts_formatted = format_number(details["sbkts"])
        svh_expertise_formatted = format_number(details["svhAndExpertise"])

        # Construct cost breakdown message
        detail_message = (
            "📝 Детализация расчёта:\n\n"
            f"Стоимость авто: <b>{car_price_formatted}₽</b>\n\n"
            f"Услуги HanExport: <b>{dealer_fee_formatted}₽</b>\n\n"
            f"Логистика по Южной Корее: <b>{korea_logistics_formatted}₽</b>\n\n"
            f"Доставка до Владивостока: <b>{delivery_fee_formatted}₽</b>\n\n"
            f"Комиссия дилера: <b>{dealer_commission_formatted}₽</b>\n\n"
            f"Единая таможенная ставка (ЕТС): <b>{russia_duty_formatted}₽</b>\n\n"
            f"Оформление: <b>{registration_formatted}₽</b>\n\n"
            f"СБКТС: <b>{sbkts_formatted}₽</b>\n\n"
            f"СВХ + Экспертиза: <b>{svh_expertise_formatted}₽</b>\n\n"
        )

        bot.send_message(call.message.chat.id, detail_message, parse_mode="HTML")

        # Inline buttons for further actions
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "Рассчитать стоимость другого автомобиля",
                callback_data="calculate_another",
            )
        )
        keyboard.add(
            types.InlineKeyboardButton(
                "Связаться с менеджером", url="https://t.me/hanexport11"
            )
        )

        bot.send_message(
            call.message.chat.id, "Что делаем дальше?", reply_markup=keyboard
        )

    elif call.data == "technical_report":
        # Retrieve insurance information
        insurance_info = get_insurance_total()

        # Проверка на наличие ошибки
        if (
            insurance_info is None
            or "Ошибка" in insurance_info[0]
            or "Ошибка" in insurance_info[1]
        ):
            error_message = (
                "Не удалось получить данные о страховых выплатах. \n\n"
                f'<a href="http://www.encar.com/dc/dc_cardetailview.do?method=kidiFirstPop&carid={car_id_external}&wtClick_carview=044">🔗 Посмотреть страховую историю вручную 🔗</a>'
            )

            # Inline buttons for further actions
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(
                    "Рассчитать стоимость другого автомобиля",
                    callback_data="calculate_another",
                )
            )
            keyboard.add(
                types.InlineKeyboardButton(
                    "Связаться с менеджером", url="https://t.me/hanexport11"
                )
            )

            # Отправка сообщения об ошибке
            bot.send_message(
                call.message.chat.id,
                error_message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            current_car_insurance_payments = (
                "0" if len(insurance_info[0]) == 0 else insurance_info[0]
            )
            other_car_insurance_payments = (
                "0" if len(insurance_info[1]) == 0 else insurance_info[1]
            )

            # Construct the message for the technical report
            tech_report_message = (
                f"Страховые выплаты по представленному автомобилю: \n<b>{current_car_insurance_payments} ₩</b>\n\n"
                f"Страховые выплаты другим участникам ДТП: \n<b>{other_car_insurance_payments} ₩</b>\n\n"
                f'<a href="https://fem.encar.com/cars/report/inspect/{car_id_external}">🔗 Ссылка на схему повреждений кузовных элементов 🔗</a>'
            )

            # Inline buttons for further actions
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(
                    "Рассчитать стоимость другого автомобиля",
                    callback_data="calculate_another",
                )
            )
            keyboard.add(
                types.InlineKeyboardButton(
                    "Связаться с менеджером", url="https://t.me/hanexport11"
                )
            )

            bot.send_message(
                call.message.chat.id,
                tech_report_message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

    elif call.data == "calculate_another":
        bot.send_message(
            call.message.chat.id,
            "Пожалуйста, введите ссылку на автомобиль с сайта www.encar.com:",
        )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_message = message.text.strip()

    # Проверяем нажатие кнопки "Рассчитать автомобиль"
    if user_message == "Рассчитать автомобиль до Владивостока":
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите ссылку на автомобиль с сайта www.encar.com:",
        )

    # Проверка на корректность ссылки
    elif re.match(r"^https?://(www|fem)\.encar\.com/.*", user_message):
        calculate_cost(user_message, message)

    # Проверка на другие команды
    elif user_message == "Написать менеджеру":
        bot.send_message(
            message.chat.id, "Вы можете связаться с менеджером по ссылке: @hanexport11"
        )
    elif user_message == "Связаться через WhatsApp":
        whatsapp_link = "https://wa.me/821084266744"
        bot.send_message(
            message.chat.id,
            f"Вы можете связаться с нами через WhatsApp по ссылке: {whatsapp_link}",
        )
    elif user_message == "О компании HanExport":
        about_message = (
            "HanExport — это компания, специализирующаяся на экспорте автомобилей "
            "из Южной Кореи. Мы предлагаем широкий выбор автомобилей и прозрачные условия "
            "для наших клиентов."
        )
        bot.send_message(message.chat.id, about_message)
    elif user_message == "Наш Telegram-канал":
        channel_link = "https://t.me/hanexport1"
        bot.send_message(
            message.chat.id, f"Подписывайтесь на наш Telegram-канал: {channel_link}"
        )
    elif user_message == "Посетить наш Instagram":
        instagram_link = "https://www.instagram.com/hanexport1"
        bot.send_message(message.chat.id, f"Посетите наш Instagram: {instagram_link}")

    # Если сообщение не соответствует ни одному из условий
    else:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите корректную ссылку на автомобиль с сайта www.encar.com или fem.encar.com.",
        )


# Utility function to calculate the age category
def calculate_age(year):
    current_year = datetime.datetime.now().year
    age = current_year - int(year)

    if age < 3:
        return f"До 3 лет"
    elif 3 <= age < 5:
        return f"от 3 до 5 лет"
    else:
        return f"от 5 лет"


def format_number(number):
    return locale.format_string("%d", number, grouping=True)


def print_message(message):
    print("\n\n##############")
    print(f"{message}")
    print("##############\n\n")
    return None


# Run the bot
if __name__ == "__main__":
    get_currency_rates()
    set_bot_commands()
    bot.polling(none_stop=True)


# def solve_recaptcha_v3():
#     payload = {
#         "clientKey": CAPSOLVER_API_KEY,
#         "task": {
#             "type": "ReCaptchaV3TaskProxyLess",
#             "websiteKey": SITE_KEY,
#             "websiteURL": "http://www.encar.com:80",
#             "pageAction": "/dc/dc_cardetailview_do",
#         },
#     }
#     res = requests.post("https://api.capsolver.com/createTask", json=payload)
#     resp = res.json()
#     task_id = resp.get("taskId")
#     if not task_id:
#         print("Не удалось создать задачу:", res.text)
#         return None
#     print(f"Получен taskId: {task_id} / Ожидание результата...")

#     while True:
#         time.sleep(1)
#         payload = {"clientKey": CAPSOLVER_API_KEY, "taskId": task_id}
#         res = requests.post("https://api.capsolver.com/getTaskResult", json=payload)
#         resp = res.json()
#         if resp.get("status") == "ready":
#             print("reCAPTCHA успешно решена")
#             return resp.get("solution", {}).get("gRecaptchaResponse")
#         if resp.get("status") == "failed" or resp.get("errorId"):
#             print("Решение не удалось! Ответ:", res.text)
#             return None
