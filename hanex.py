import telebot
import time
import psycopg2
import os
import re
import requests
import locale
import datetime
import logging

from twocaptcha import TwoCaptcha
from telebot import types
from dotenv import load_dotenv
from seleniumwire import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.support import expected_conditions as EC


TWOCAPTCHA_API_KEY = "89a8f41a0641f085c8ca6e861e0fa571"


# CHROMEDRIVER_PATH = "/app/.chrome-for-testing/chromedriver-linux64/chromedriver"
CHROMEDRIVER_PATH = "/opt/homebrew/bin/chromedriver"

PROXY_HOST = "45.118.250.2"
PROXY_PORT = "8000"
PROXY_USER = "B01vby"
PROXY_PASS = "GBno0x"

http_proxy = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"

proxy = {
    "http": "http://B01vby:GBno0x@45.118.250.2:8000",
    "https": "http://B01vby:GBno0x@45.118.250.2:8000",
}

session = requests.Session()

# Настройка БД
DATABASE_URL = "postgres://uea5qru3fhjlj:p44343a46d4f1882a5ba2413935c9b9f0c284e6e759a34cf9569444d16832d4fe@c97r84s7psuajm.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d9pr93olpfl9bj"


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


# Инициализируем БД
def initialize_db():
    # Создаем подключение к базе данных PostgreSQL
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()

    # Создание таблицы для хранения статистики пользователей, если её нет
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id SERIAL PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            join_date DATE
        )
        """
    )

    # Создание таблицы для хранения данных об автомобилях, если её нет
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS car_info (
            car_id SERIAL PRIMARY KEY,
            date TEXT NOT NULL,
            engine_volume TEXT NOT NULL,
            price TEXT NOT NULL,
            UNIQUE (date, engine_volume, price) 
        )
        """
    )

    # Сохраняем изменения
    conn.commit()
    cursor.close()
    conn.close()


# Функция для сохранения информации о пользователе
def save_user_info(user):
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()

    # Добавление информации о пользователе в таблицу
    cursor.execute(
        """
        INSERT INTO user_stats (user_id, username, first_name, last_name, join_date)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
    """,
        (
            int(str(user.id)[0:5]),
            user.username,
            user.first_name,
            user.last_name,
            str(datetime.datetime.now().date()),
        ),
    )

    conn.commit()
    cursor.close()
    conn.close()


# Функция для получения всех пользователей
def get_all_users():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_stats")
    users = cursor.fetchall()
    conn.close()
    return users


def get_users_for_week():
    today = datetime.date.today()
    # Находим последний день пятницы (текущая или предыдущая)
    days_since_friday = today.weekday() - 4  # 4 — это пятница
    last_friday = today - datetime.timedelta(days=days_since_friday)
    # Находим следующую пятницу
    next_friday = last_friday + datetime.timedelta(days=7)

    # Запрос на получение пользователей с последней пятницы по следующую
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM user_stats 
        WHERE join_date >= %s AND join_date < %s
        """,
        (last_friday, next_friday),
    )
    users = cursor.fetchall()
    conn.commit()
    cursor.close()
    conn.close()
    return users


@bot.message_handler(commands=["stats"])
def handle_stats(message):
    if is_admin(message.from_user.id):
        users = get_all_users()
        stats_message = "Список пользователей:\n\n"

        for user in users:
            stats_message += f"Никнейм: @{user[1]}\nИмя: {user[2]} {user[3]}\nДата начала пользования: {user[4]}\n\n"
        bot.reply_to(message, stats_message)
    else:
        bot.reply_to(message, "Эта функция доступна только администратору")


def print_message(message):
    print("\n\n##############")
    print(f"{message}")
    print("##############\n\n")
    return None


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
        types.BotCommand("stats", "Статистика"),
    ]
    bot.set_my_commands(commands)


# Функция для получения курсов валют с API
def get_currency_rates():
    global usd_rate

    print_message("ПОЛУЧАЕМ КУРС ЦБ")

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
        f"EUR {eur:.4f} ₽\n"
        f"USD {usd:.4f} ₽\n"
        f"KRW {krw:.4f} ₽\n"
        f"CNY {cny:.4f} ₽"
    )

    print_message(rates_text)

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
    user = message.from_user
    user_first_name = user.first_name

    # Сохраняем данные о пользователях бота
    save_user_info(user)

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


# Получаем текущий IP адрес
def get_ip():
    response = requests.get(
        "https://api.ipify.org?format=json", verify=True, proxies=proxy
    )
    ip = response.json()["ip"]
    return ip


# print_message(f"Current IP Address: {get_ip()}")


def extract_sitekey(driver, url):
    driver.get(url)

    iframe = driver.find_element(By.TAG_NAME, "iframe")
    iframe_src = iframe.get_attribute("src")
    match = re.search(r"k=([A-Za-z0-9_-]+)", iframe_src)

    if match:
        sitekey = match.group(1)
        return sitekey
    else:
        return None


def send_recaptcha_token(token):
    data = {"token": token, "action": "/dc/dc_cardetailview.do"}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "http://www.encar.com/index.do",
    }

    # Отправляем токен капчи на сервер
    url = "https://www.encar.com/validation_recaptcha.do?method=v3"
    response = requests.post(
        url, data=data, headers=headers, proxies=proxy, verify=True
    )

    # Выводим ответ для отладки
    print("\n\nОтвет от сервера:")
    print(f"Статус код: {response.status_code}")
    print(f"Тело ответа: {response.text}\n\n")

    try:
        result = response.json()

        if result[0]["success"]:
            print("reCAPTCHA успешно пройдена!")
            return True
        else:
            print("Ошибка проверки reCAPTCHA.")
            return False
    except requests.exceptions.JSONDecodeError:
        print("Ошибка: Ответ от сервера не является валидным JSON.")
        return False
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return False


def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.92 Safari/537.36"
    )

    prefs = {
        "profile.default_content_setting_values.notifications": 2,  # Отключить уведомления
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    seleniumwire_options = {"proxy": proxy}

    driver = webdriver.Chrome(
        options=chrome_options, seleniumwire_options=seleniumwire_options
    )

    return driver


def get_car_info(url):
    global car_id_external

    driver = create_driver()

    # Извлекаем carid с URL encar
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    car_id = query_params.get("carid", [None])[0]
    car_id_external = car_id

    try:
        # solver = TwoCaptcha("89a8f41a0641f085c8ca6e861e0fa571")

        is_recaptcha_solved = True

        driver.get(f"https://www.encar.com/dc/dc_cardetailview.do?carid={car_id}")

        # if "reCAPTCHA" in driver.page_source:
        #     is_recaptcha_solved = False
        #     print_message("Обнаружена reCAPTCHA, решаем...")

        #     sitekey = extract_sitekey(driver, url)
        #     print(f"Sitekey: {sitekey}")

        #     result = solver.recaptcha(sitekey, url)
        #     print(f'reCAPTCHA result: {result["code"][0:50]}...')

        #     is_recaptcha_solved = send_recaptcha_token(result["code"])

        if is_recaptcha_solved:
            # Достаём данные об авто после решения капчи
            car_date, car_price, car_engine_displacement, car_title = "", "", "", ""
            meta_elements = driver.find_elements(By.CSS_SELECTOR, "meta[name^='WT.']")

            meta_data = {}
            for meta in meta_elements:
                name = meta.get_attribute("name")
                content = meta.get_attribute("content")
                meta_data[name] = content

            car_date = f'01{meta_data["WT.z_month"]}{meta_data["WT.z_year"][-2:]}'
            car_price = meta_data["WT.z_price"]
            car_title = f'{meta_data["WT.z_model_name"]} {meta_data["WT.z_model"]}'

            try:
                dsp_element = driver.find_element(By.ID, "dsp")
                car_engine_displacement = dsp_element.get_attribute("value")
            except Exception as e:
                print(f"Ошибка при получении объема двигателя: {e}")

            print("АВТОМОБИЛЬ БЫЛ СОХРАНËН В БД")
            print(car_title)
            print(f"Registration Date: {car_date}")
            print(f"Car Engine Displacement: {car_engine_displacement}")
            print(f"Price: {car_price}")

            # Сохранение данных в базу
            conn = psycopg2.connect(DATABASE_URL, sslmode="require")
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO car_info (car_id, date, engine_volume, price)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (car_id) DO NOTHING
                """,
                (car_id, car_date, car_engine_displacement, car_price),
            )
            conn.commit()
            cursor.close()
            conn.close()

            new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={car_price}&date={car_date}&volume={car_engine_displacement}"

            driver.quit()
            return [new_url, car_title]

    except WebDriverException as e:
        print(f"Ошибка Selenium: {e}")
        driver.quit()
        return ["", "Произошла ошибка получения данных. Попробуйте ещё раз"]

    return ["", ""]


# Function to calculate the total cost
def calculate_cost(link, message):
    global car_data

    print_message("ЗАПРОС НА РАСЧЁТ АВТОМОБИЛЯ")

    # Отправляем сообщение и сохраняем его ID
    processing_message = bot.send_message(
        message.chat.id, "Данные переданы в обработку. Пожалуйста подождите ⏳"
    )

    car_id = None

    # Проверка ссылки на мобильную версию
    if "fem.encar.com" in link:
        car_id_match = re.findall(r"\d+", link)
        if car_id_match:
            car_id = car_id_match[0]  # Use the first match of digits
            link = f"http://www.encar.com/dc/dc_cardetailview.do?carid={car_id}"
        else:
            send_error_message(message, "🚫 Не удалось извлечь carid из ссылки.")
            return
    else:
        # Извлекаем carid с URL encar
        parsed_url = urlparse(link)
        query_params = parse_qs(parsed_url.query)
        car_id = query_params.get("carid", [None])[0]

    # Проверяем наличие автомобиля в базе данных
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT date, engine_volume, price FROM car_info WHERE car_id = %s", (car_id,)
    )
    car_from_db = cursor.fetchone()
    new_url = ""
    car_title = ""

    if car_from_db:
        # Автомобиль найден в БД, используем данные
        date, engine_volume, price = car_from_db
        print(
            f"Автомобиль найден в базе данных: {car_id}, {date}, {engine_volume}, {price}"
        )
        new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={price}&date={date}&volume={engine_volume}"
    else:
        print("Автомобиль не был найден в базе данных.")
        # Автомобиля нет в базе, вызываем get_car_info
        result = get_car_info(link)
        new_url, car_title = result

        if result is None:
            print(f"Ошибка при вызове get_car_info для ссылки: {link}")
            send_error_message(
                message,
                "🚫 Произошла ошибка при получении данных. Проверьте ссылку и попробуйте снова.",
            )
            bot.delete_message(message.chat.id, processing_message.message_id)
            return

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

    driver = create_driver()
    url = f"http://www.encar.com/dc/dc_cardetailview.do?method=kidiFirstPop&carid={car_id_external}&wtClick_carview=044"

    try:
        # Запускаем WebDriver
        driver.get(url)

        try:
            smlist_element = driver.find_element(By.CLASS_NAME, "smlist")
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
        delivery_fee_formatted = format_number(details["delivery_fee"])
        dealer_commission_formatted = format_number(details["dealer_commission"])
        russia_duty_formatted = format_number(details["russiaDuty"])

        detail_message = (
            "📝 Детализация расчёта:\n\n"
            f"Стоимость авто: <b>{car_price_formatted}₽</b>\n\n"
            f"Услуги HanExport: <b>{dealer_fee_formatted}₽</b>\n\n"
            f"Услуги Брокера: <b>{format_number(115000)}₽</b>\n    - Оформление: <b>45,000₽</>\n    - Регистрация: <b>15,000₽</b>\n    - Услуга брокера: <b>15,000₽</b>\n    - Транспортные расходы: <b>10,000₽</b>\n    - Ставка ПРР от <b>35,000₽</b> до <b>37,000₽</b> в зависимости от склада\n\n"
            f"Логистика по Южной Корее: <b>{format_number(30000)}₽</b>\n\n"
            f"Доставка до Владивостока: <b>{delivery_fee_formatted}₽</b>\n\n"
            f"Комиссия дилера: <b>{dealer_commission_formatted}₽</b>\n\n"
            f"Единая таможенная ставка (ЕТС): <b>{russia_duty_formatted}₽</b>\n\n"
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
            or "Нет данных" in insurance_info[0]
            or "Нет данных" in insurance_info[1]
        ):
            error_message = (
                "Не удалось получить данные о страховых выплатах. \n\n"
                f'<a href="https://fem.encar.com/cars/report/accident/{car_id_external}">🔗 Посмотреть страховую историю вручную 🔗</a>\n\n\n'
                f"<b>Найдите две строки:</b>\n\n"
                f"보험사고 이력 (내차 피해) - Выплаты по представленному автомобилю\n"
                f"보험사고 이력 (타차 가해) - Выплаты другим участникам ДТП"
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
    user = message.from_user
    user_message = message.text.strip()

    # Проверяем нажатие кнопки "Рассчитать автомобиль"
    if user_message == "Расчёт":
        # Сохраняем пользователя в БД
        save_user_info(user)

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


# Run the bot
if __name__ == "__main__":
    initialize_db()
    get_currency_rates()
    set_bot_commands()
    bot.polling(none_stop=True)
