import time
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
from selenium.common.exceptions import TimeoutException, NoAlertPresentException


CAPSOLVER_API_KEY = os.getenv("CAPSOLVER_API_KEY")  # Замените на ваш API-ключ CapSolver
CHROMEDRIVER_PATH = "/app/.chrome-for-testing/chromedriver-linux64/chromedriver"
# CHROMEDRIVER_PATH = "/opt/homebrew/bin/chromedriver"
# CHROMEDRIVER_PATH = "chromedriver"

PROXY_HOST = "45.118.250.2"
PROXY_PORT = "8000"
PROXY_USER = "B01vby"
PROXY_PASS = "GBno0x"

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
users = set()
admins = [7311593407, 728438182]


# Функция для добавления пользователя в список
def add_user_to_list(message):
    username = message.from_user.username

    if username:
        users.add(username)


# Функция для проверки, является ли пользователь администратором
def is_admin(user_id):
    return user_id in admins  # Здесь укажите ваш ID администратора


# Обработка команды "admin_menu"
@bot.message_handler(commands=["admin"])
def admin_menu(message):
    if is_admin(message.from_user.id):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton("Отправить список пользователей бота"))
        bot.send_message(message.chat.id, "Админ меню", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к админ меню.")


@bot.message_handler(
    func=lambda message: message.text == "Отправить список пользователей бота"
)
def send_user_list(message):
    if is_admin(message.from_user.id):
        manager_id = admins[0]
        user_list = "\n".join(
            [f"@{username}" for username in users if username]
        )  # Список username пользователей
        bot.send_message(manager_id, f"Список пользователей бота:\n{user_list}")
        bot.send_message(message.chat.id, "Список отправлен менеджеру.")
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к этой функции.")


# Функция для установки команд меню
def set_bot_commands():
    commands = [
        types.BotCommand("start", "Запустить бота"),
        types.BotCommand("cbr", "Курсы валют"),
        types.BotCommand("admin", "Меню администратора"),
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
    add_user_to_list(message)  # Добавляем пользователя в множество

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
        types.KeyboardButton("Расчёт"),
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

    add_user_to_list(message)

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


def check_and_handle_alert(driver):
    try:
        WebDriverWait(driver, 3).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        print(f"Обнаружено всплывающее окно: {alert.text}")
        alert.accept()  # Закрывает alert
        print("Всплывающее окно было закрыто.")
    except TimeoutException:
        print("Нет активного всплывающего окна.")
    except Exception as alert_exception:
        print(f"Ошибка при обработке alert: {alert_exception}")


def wait_for_page_to_load(driver, timeout=10):
    """Функция для ожидания полной загрузки страницы."""
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def get_car_info(url):
    global car_id_external

    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")  # Необходим для работы в Heroku
    chrome_options.add_argument("--headless")  # Необходим для работы в Heroku
    chrome_options.add_argument("--disable-dev-shm-usage")  # Решает проблемы с памятью
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--log-level=3")  # Отключение логов
    chrome_options.add_argument("--disable-application-cache")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-autofill")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    )

    # Инициализация драйвера
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(
        service=service,
        options=chrome_options,
    )

    try:
        # Загружаем страницу
        driver.get(url)
        check_and_handle_alert(driver)

        # Проверка на reCAPTCHA
        if "reCAPTCHA" in driver.page_source:
            print("Обнаружена reCAPTCHA. Пытаемся решить...")
            driver.refresh()
            print("Страница обновлена после reCAPTCHA.")
            check_and_handle_alert(driver)

        wait_for_page_to_load(driver)

        # Парсим URL для получения carid
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        car_id = query_params.get("carid", [None])[0]
        car_id_external = car_id

        # Проверка элемента areaLeaseRent
        try:
            print("Проверка на areaLeaseRent")

            lease_area = driver.find_element(By.ID, "areaLeaseRent")
            title_element = lease_area.find_element(By.CLASS_NAME, "title")

            if "리스정보" in title_element.text or "렌트정보" in title_element.text:
                print("Данная машина находится в лизинге.")
                return [
                    "",
                    "Данная машина находится в лизинге. Свяжитесь с менеджером.",
                ]
        except NoSuchElementException:
            print("Элемент areaLeaseRent не найден.")

        # Проверка элемента gallery_photo
        try:
            print("Проверка на gallery_photo")

            gallery_element = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "gallery_photo"))
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
                print("Элемент wrap_keyinfo не найден.")

        except NoSuchElementException:
            print("Элемент gallery_photo также не найден.")

        # Проверка элемента product_left
        try:
            print("Проверка на product_left")

            product_left = WebDriverWait(driver, 7).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "product_left"))
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
            print(f"Данные о машине получены: {new_url}, {car_title}")

            return [new_url, car_title]
        except Exception as e:
            print(f"Ошибка при обработке product_left: {e}")

        # Форматирование значений для URL
        formatted_price = car_price.replace(",", "") if car_price else "0"
        formatted_engine_capacity = (
            car_engine_capacity.replace(",", "")[:-2] if car_engine_capacity else "0"
        )
        cleaned_date = "".join(filter(str.isdigit, car_date))
        formatted_date = (
            f"01{cleaned_date[2:4]}{cleaned_date[:2]}" if cleaned_date else "010101"
        )

        # Конечный URL
        new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"

        driver.quit()

        print(f"Данные о машине получены: {new_url}, {car_title}")
        return [new_url, car_title]

    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")
        return None, None

    finally:
        driver.quit()


# Function to calculate the total cost
def calculate_cost(link, message):
    global car_data

    print_message("ЗАПРОС НА РАСЧЁТ АВТОМОБИЛЯ")

    # Отправляем сообщение и сохраняем его ID
    processing_message = bot.send_message(
        message.chat.id, "Данные переданы в обработку. Пожалуйста подождите ⏳"
    )

    # Проверка ссылки на мобильную версию
    if "fem.encar.com" in link:
        car_id_match = re.findall(r"\d+", link)
        if car_id_match:
            car_id = car_id_match[0]  # Use the first match of digits
            link = f"https://www.encar.com/dc/dc_cardetailview.do?carid={car_id}"
        else:
            send_error_message(message, "🚫 Не удалось извлечь carid из ссылки.")
            return

    result = get_car_info(link)

    if result is None:
        print(f"Ошибка при вызове get_car_info для ссылки: {link}")
        send_error_message(
            message,
            "🚫 Произошла ошибка при получении данных. Проверьте ссылку и попробуйте снова или выберите действие ниже.",
        )
        bot.delete_message(message.chat.id, processing_message.message_id)
        return

    new_url, car_title = result

    # Если данные не были получены
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
        bot.delete_message(message.chat.id, processing_message.message_id)
        return

    # Если есть новая ссылка
    if new_url:
        try:
            response = requests.get(new_url)
            response.raise_for_status()
            json_response = response.json()
        except requests.RequestException as e:
            logging.error(f"Ошибка при запросе данных: {e}")
            send_error_message(
                message,
                "🚫 Произошла ошибка при получении данных. Проверьте ссылку и попробуйте снова.",
            )
            bot.delete_message(message.chat.id, processing_message.message_id)
            return
        except ValueError:
            logging.error("Получен некорректный JSON.")
            send_error_message(
                message,
                "🚫 Неверный формат данных. Проверьте ссылку или повторите попытку.",
            )
            bot.delete_message(message.chat.id, processing_message.message_id)
            return

        car_data = json_response

        result = json_response.get("result", {})
        car = result.get("car", {})
        price = result.get("price", {}).get("car", {}).get("krw", 0)

        year = car.get("date", "").split()[-1] if "date" in car else None

        engine_volume_raw = car.get("engineVolume", None)
        engine_volume = re.sub(r"\D+", "", engine_volume_raw)

        if not (year and engine_volume and price):
            logging.warning("Не удалось извлечь все необходимые данные из JSON.")
            bot.send_message(
                message.chat.id,
                "🚫 Не удалось извлечь все необходимые данные. Проверьте ссылку.",
            )
            bot.delete_message(message.chat.id, processing_message.message_id)
            return

        # Форматирование данных
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

        total_cost = (
            int(grand_total) - int(recycling_fee) - int(duty_cleaning)
        ) + 110000
        total_cost_formatted = format_number(total_cost)
        price_formatted = format_number(price)

        # Формирование сообщения результата
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

        # Клавиатура с дальнейшими действиями
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("📊 Детализация расчёта", callback_data="detail")
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

        bot.send_message(message.chat.id, "Что делаем дальше?", reply_markup=keyboard)

        # Удаляем сообщение о передаче данных в обработку
        bot.delete_message(message.chat.id, processing_message.message_id)

    else:
        send_error_message(
            message,
            "🚫 Произошла ошибка при получении данных. Проверьте ссылку и попробуйте снова.",
        )
        bot.delete_message(message.chat.id, processing_message.message_id)


# Function to get insurance total
def get_insurance_total():
    global car_id_external
    print_message("[ЗАПРОС] ТЕХНИЧЕСКИЙ ОТЧËТ ОБ АВТОМОБИЛЕ")

    # Настройка WebDriver с нужными опциями
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
    chrome_options.add_argument("--enable-javascript")
    chrome_options.add_argument("--v=1")  # Уровень логирования
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    )

    service = Service(CHROMEDRIVER_PATH)

    # Формируем URL
    url = f"http://www.encar.com/dc/dc_cardetailview.do?method=kidiFirstPop&carid={car_id_external}&wtClick_carview=044"

    try:
        # Запускаем WebDriver
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)

        print("car_id_external: ", car_id_external)

        try:
            smlist_element = WebDriverWait(driver, 7).until(
                EC.presence_of_element_located((By.CLASS_NAME, "smlist"))
            )
        except NoSuchElementException:
            print("Элемент 'smlist' не найден.")
            return ["Нет данных", "Нет данных"]

        # Находим таблицу
        table = smlist_element.find_element(By.TAG_NAME, "table")
        rows = table.find_elements(By.TAG_NAME, "tr")

        # Извлекаем данные
        damage_to_my_car = (
            rows[4].find_elements(By.TAG_NAME, "td")[1].text if len(rows) > 4 else "0"
        )
        damage_to_other_car = (
            rows[5].find_elements(By.TAG_NAME, "td")[1].text if len(rows) > 5 else "0"
        )

        # Упрощенная функция для извлечения числа
        def extract_large_number(damage_text):
            if "없음" in damage_text:
                return "0"
            numbers = re.findall(r"[\d,]+(?=\s*원)", damage_text)
            return numbers[0] if numbers else "0"

        # Форматируем данные
        damage_to_my_car_formatted = extract_large_number(damage_to_my_car)
        damage_to_other_car_formatted = extract_large_number(damage_to_other_car)

        return [damage_to_my_car_formatted, damage_to_other_car_formatted]

    except Exception as e:
        print(f"Произошла ошибка при получении данных: {e}")
        return ["Ошибка при получении данных", ""]

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
            f"Услуги Брокера: <b>{format_number(110000)}₽</b>\n\n"
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
                f'<a href="https://fem.encar.com/cars/report/accident/{car_id_external}">🔗 Посмотреть страховую историю вручную 🔗</a>'
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
    if user_message == "Расчёт":
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
