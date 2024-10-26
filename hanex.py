import telebot
import os
import re
import requests
import json
import locale
import datetime
from telebot import types
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, parse_qs

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


# Main menu creation function
def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(
        types.KeyboardButton("🔍 Рассчитать автомобиль до Владивостока"),
        types.KeyboardButton("✉️ Написать менеджеру"),
        types.KeyboardButton("ℹ️ О компании HanExport"),
        types.KeyboardButton("📢 Наш Telegram-канал"),
        types.KeyboardButton("📞 Связаться через WhatsApp"),
        types.KeyboardButton("📸 Посетить наш Instagram"),
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


# Error message handling
def send_error_message(message, error_text):
    global last_error_message_id

    # Remove previous error message if it exists
    if last_error_message_id.get(message.chat.id):
        try:
            bot.delete_message(message.chat.id, last_error_message_id[message.chat.id])
        except Exception:
            pass

    # Send new error message and store its ID
    error_message = bot.reply_to(message, error_text)
    last_error_message_id[message.chat.id] = error_message.id


# Function to get car info using Selenium
def get_car_info(url):
    global car_id_external

    # Configure WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    )

    service = Service(
        "/opt/homebrew/bin/chromedriver"
    )  # Specify your chromedriver path

    try:
        # Start the WebDriver
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)

        # Check for reCAPTCHA
        if "reCAPTCHA" in driver.page_source:
            print("reCAPTCHA detected, please solve it manually.")
            input("Press Enter after solving reCAPTCHA...")

        # Parse the URL to get carid
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        car_id = query_params.get("carid", [None])[0]
        car_id_external = car_id

        # Find the gallery container
        gallery_element = driver.find_element(By.CSS_SELECTOR, "div.gallery_photo")
        items = gallery_element.find_elements(By.XPATH, ".//*")

        car_date = ""
        car_engine_capacity = ""
        car_price = ""

        for index, item in enumerate(items):
            if index == 10:
                car_date = item.text
            if index == 18:
                car_engine_capacity = item.text

        # Find the key info element
        keyinfo_element = driver.find_element(By.CSS_SELECTOR, "div.wrap_keyinfo")
        keyinfo_items = keyinfo_element.find_elements(By.XPATH, ".//*")
        keyinfo_texts = [item.text for item in keyinfo_items if item.text.strip() != ""]

        for index, info in enumerate(keyinfo_texts):
            if index == 12:
                car_price = info

        # Format values for the URL
        formatted_price = car_price.replace(",", "")
        formatted_engine_capacity = car_engine_capacity.replace(",", "")[0:-2]
        cleaned_date = "".join(filter(str.isdigit, car_date))
        formatted_date = f"01{cleaned_date[2:4]}{cleaned_date[:2]}"

        # Construct the new URL
        new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"

        return new_url

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return None

    finally:
        driver.quit()


# Function to calculate the total cost
def calculate_cost(link, message):
    global car_data

    print("НОВЫЙ ЗАПРОС")

    bot.send_message(message.chat.id, "Данные переданы в обработку ⏳")

    # Check if the link is from the mobile version
    if "fem.encar.com" in link:
        # Extract all digits from the mobile link
        car_id_match = re.findall(r"\d+", link)
        if car_id_match:
            car_id = car_id_match[0]  # Use the first match of digits
            # Create the new URL
            link = f"https://www.encar.com/dc/dc_cardetailview.do?carid={car_id}"
        else:
            send_error_message(message, "🚫 Не удалось извлечь carid из ссылки.")
            return

    # Get car info and new URL
    new_url = get_car_info(link)

    if new_url:
        response = requests.get(new_url)

        if response.status_code == 200:
            json_response = response.json()
            car_data = json_response

            # Extract year from the car date string
            year = json_response.get("result")["car"]["date"].split()[-1]
            engine_volume = json_response.get("result")["car"]["engineVolume"]
            price = json_response.get("result")["price"]["car"]["krw"]

            if year and engine_volume and price:
                engine_volume_formatted = f"{engine_volume} cc"
                age_formatted = calculate_age(year)

                total_cost = json_response.get("result")["price"]["grandTotal"]
                total_cost_formatted = format_number(total_cost)
                price_formatted = format_number(price)

                result_message = (
                    f"Возраст: {age_formatted}\n"
                    f"Стоимость: {price_formatted} KRW\n"
                    f"Объём двигателя: {engine_volume_formatted}\n\n"
                    f"Стоимость автомобиля под ключ во Владивосток: {total_cost_formatted}₽\n\n"
                    f"🔗 [Ссылка на автомобиль]({link})\n\n"
                    "Данное авто попадает под санкции, пожалуйста уточните возможность отправки в вашу страну у менеджера @hanexport11\n\n"
                    'Стоимость "под ключ" включает в себя все расходы до г. Владивосток, а именно: '
                    "оформление экспорта в Корее, фрахт, услуги брокера, склады временного хранения, "
                    "прохождение лаборатории для получения СБКТС и таможенную пошлину.\n\n"
                    "Актуальные курсы валют вы можете посмотреть в Меню.\n\n"
                    "По вопросам заказа авто вы можете обратиться к нашему менеджеру @hanexport11\n\n"
                    "🔗[Официальный телеграм канал](https://t.me/hanexport1)\n"
                )

                bot.send_message(message.chat.id, result_message, parse_mode="Markdown")

                # Inline buttons for further actions
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton(
                        "📊 Детализация расчёта", callback_data="detail"
                    ),
                )
                keyboard.add(
                    types.InlineKeyboardButton(
                        "📝 Технический отчёт об автомобиле",
                        callback_data="technical_report",
                    ),
                )
                keyboard.add(
                    types.InlineKeyboardButton(
                        "✉️ Связаться с менеджером", url="https://t.me/hanexport11"
                    ),
                )
                keyboard.add(
                    types.InlineKeyboardButton(
                        "🔍 Рассчитать стоимость другого автомобиля",
                        callback_data="calculate_another",
                    ),
                )

                bot.send_message(
                    message.chat.id, "Что делаем дальше?", reply_markup=keyboard
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "🚫 Не удалось извлечь все необходимые данные. Проверьте ссылку.",
                )
        else:
            send_error_message(
                message,
                "🚫 Произошла ошибка при получении данных. Проверьте ссылку и попробуйте снова.",
            )
    else:
        send_error_message(
            message,
            "🚫 Произошла ошибка при получении данных. Проверьте ссылку и попробуйте снова.",
        )


def get_insurance_total(car_id):
    # Configure WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    )

    service = Service("/opt/homebrew/bin/chromedriver")

    # Define the URL
    url = f"http://www.encar.com/dc/dc_cardetailview.do?method=kidiFirstPop&carid={car_id}&wtClick_carview=044"

    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)

        # Check for reCAPTCHA presence
        if "reCAPTCHA" in driver.page_source:
            print("reCAPTCHA detected, please solve it manually.")
            input("Press Enter after solving reCAPTCHA...")

        try:
            smlist_element = driver.find_element(By.CLASS_NAME, "smlist")
            # Выводим содержимое элемента
            smlist_list = smlist_element.text.split("\n")
            damage_to_my_car = (
                "0" if smlist_list[-2] == "없음" else smlist_list[-2].split(", ")[1]
            )
            damage_to_other_car = (
                "0" if smlist_list[-1] == "없음" else smlist_list[-1].split(", ")[1]
            )

            damage_to_my_car_formatted = ",".join(re.findall(r"\d+", damage_to_my_car))
            damage_to_other_car_formatted = ",".join(
                re.findall(r"\d+", damage_to_other_car)
            )
        except Exception as e:
            print(f"Не удалось найти элемент с классом 'smlist': {e}")

        # Optional: Process the text to extract relevant data
        return [damage_to_my_car_formatted, damage_to_other_car_formatted]

    except Exception as e:
        print(f"Error occurred: {e}")
        return "Error retrieving insurance details."

    finally:
        driver.quit()


# Callback query handler
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    global car_data, car_id_external

    if call.data.startswith("detail"):
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

        # Construct cost breakdown message
        detail_message = (
            "📝 Детализация расчёта:\n\n"
            f"Стоимость авто: {format_number(details['car_price_korea'])}₽\n"
            f"Услуги HanExport: {format_number(details['dealer_fee'])}₽\n"
            f"Логистика по Южной Корее: {format_number(details['korea_logistics'])}₽\n"
            f"Таможенная очистка: {format_number(details['customs_fee'])}₽\n"
            f"Доставка до Владивостока: {format_number(details['delivery_fee'])}₽\n"
            f"Комиссия дилера: {format_number(details['dealer_commission'])}₽\n"
            f"Единая таможенная ставка (ЕТС): {format_number(details['russiaDuty'])}₽\n"
            f"Утилизационный сбор: {format_number(details['recycle_fee'])}₽\n"
            f"Оформление: {format_number(details['registration'])}₽\n"
            f"СБКТС: {format_number(details['sbkts'])}₽\n"
            f"СВХ + Экспертиза: {format_number(details['svhAndExpertise'])}₽\n"
            f"Перегон: {format_number(details['delivery'])}₽\n"
        )

        bot.send_message(call.message.chat.id, detail_message)

        # Inline buttons for further actions
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "📉 Рассчитать стоимость другого автомобиля",
                callback_data="calculate_another",
            )
        )
        keyboard.add(
            types.InlineKeyboardButton(
                "✉️ Связаться с менеджером", url="https://t.me/hanexport11"
            )
        )

        bot.send_message(
            call.message.chat.id, "Что делаем дальше?", reply_markup=keyboard
        )

    elif call.data == "technical_report":
        # Retrieve insurance information
        insurance_info = get_insurance_total(car_id_external)

        # Construct the message for the technical report
        tech_report_message = (
            f"Страховые выплаты по представленному автомобилю: {insurance_info[0]}₩\n\n"
            f"Страховые выплаты другим участникам ДТП: {insurance_info[1]}₩\n\n"
            f"[🔗 Ссылка на схему повреждений кузовных элементов 🔗](https://fem.encar.com/cars/report/inspect/{car_id_external})"
        )

        # Inline buttons for further actions
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "📉 Рассчитать стоимость другого автомобиля",
                callback_data="calculate_another",
            )
        )
        keyboard.add(
            types.InlineKeyboardButton(
                "✉️ Связаться с менеджером", url="https://t.me/hanexport11"
            )
        )

        bot.send_message(
            call.message.chat.id,
            tech_report_message,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    elif call.data == "calculate_another":
        bot.send_message(
            call.message.chat.id,
            "Пожалуйста, введите ссылку на автомобиль с сайта www.encar.com:",
        )


# Message handler for processing the car calculation request
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_message = message.text

    if user_message == "🔍 Рассчитать автомобиль до Владивостока":
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите ссылку на автомобиль с сайта www.encar.com:",
        )
    elif user_message == "✉️ Написать менеджеру":
        bot.send_message(
            message.chat.id, "Вы можете связаться с менеджером по ссылке: @hanexport11"
        )
    elif user_message == "📞 Связаться через WhatsApp":
        whatsapp_link = "https://wa.me/821084266744"
        bot.send_message(
            message.chat.id,
            f"Вы можете связаться с нами через WhatsApp по ссылке: {whatsapp_link}",
        )
    elif user_message == "ℹ️ О компании HanExport":
        about_message = (
            "HanExport — это компания, специализирующаяся на экспорте автомобилей "
            "из Южной Кореи. Мы предлагаем широкий выбор автомобилей и прозрачные условия "
            "для наших клиентов."
        )
        bot.send_message(message.chat.id, about_message)
    elif user_message == "📢 Наш Telegram-канал":
        channel_link = "https://t.me/hanexport1"
        bot.send_message(
            message.chat.id, f"Подписывайтесь на наш Telegram-канал: {channel_link}"
        )
    elif user_message == "📸 Посетить наш Instagram":
        instagram_link = "https://www.instagram.com/hanexport1"
        bot.send_message(message.chat.id, f"Посетите наш Instagram: {instagram_link}")

    # Process the car URL
    elif user_message.startswith("http"):
        calculate_cost(user_message, message)


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
    bot.polling(none_stop=True)
