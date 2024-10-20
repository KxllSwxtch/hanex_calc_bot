import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import locale
import datetime
import os
from dotenv import load_dotenv


# Подгрузка ключей из файла .env
load_dotenv()
bot_token = os.getenv("BOT_TOKEN")


# Настройка локали для форматирования чисел
locale.setlocale(locale.LC_ALL, "en_US.UTF-8")

API_TOKEN = "7888621171:AAEpwt5kDXtAVOW3ecSzv7zWOGnSzfUicQM"
bot = telebot.TeleBot(bot_token)

# Хранение идентификатора последнего сообщения об ошибке
last_error_message_id = {}


# Функция для создания главного меню
def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    calculate_button = types.KeyboardButton("🔍 Рассчитать автомобиль до Владивостока")
    feedback_button = types.KeyboardButton("✉️ Написать менеджеру")
    about_button = types.KeyboardButton("ℹ️ О компании HanExport")
    channel_button = types.KeyboardButton("📢 Наш Telegram-канал")
    whatsapp_button = types.KeyboardButton("📞 Связаться через WhatsApp")
    instagram_button = types.KeyboardButton("📸 Посетить наш Instagram")
    keyboard.add(
        calculate_button,
        feedback_button,
        about_button,
        channel_button,
        whatsapp_button,
        instagram_button,
    )
    return keyboard


# Функция для старта
@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_first_name = message.from_user.first_name
    welcome_message = (
        f"👋 Здравствуйте, {user_first_name}!\n"
        "Я бот компании HanExport для расчета стоимости авто до Владивостока! 🚗💰\n\n"
        "Пожалуйста, выберите действие из меню ниже:"
    )
    bot.send_message(message.chat.id, welcome_message, reply_markup=main_menu())


# Функция для расчета возраста автомобиля
def calculate_age(year):
    current_year = datetime.datetime.now().year
    age = current_year - year
    if age < 3:
        return "до 3-х лет"
    elif 3 <= age < 5:
        return "от 3-х до 5-ти лет"
    elif 5 <= age < 7:
        return "от 5-ти до 7-ми лет"
    else:
        return "от 7-ми лет и старше"


# Форматирование чисел
def format_number(number):
    return locale.format_string("%d", number, grouping=True)


# Обработка входящих сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_message = message.text

    # Обработка кнопки "Рассчитать автомобиль до Владивостока"
    if user_message == "🔍 Рассчитать автомобиль до Владивостока":
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите ссылку на автомобиль с сайта www.encar.com:",
        )

    # Обработка кнопки "Написать менеджеру"
    elif user_message == "✉️ Написать менеджеру":
        bot.send_message(
            message.chat.id, "Вы можете связаться с менеджером по ссылке: @hanexport11"
        )

    # Обработка кнопки "Связаться через WhatsApp"
    elif user_message == "📞 Связаться через WhatsApp":
        whatsapp_link = "https://wa.me/821084266744"
        bot.send_message(
            message.chat.id,
            f"Вы можете связаться с нами через WhatsApp по ссылке: {whatsapp_link}",
        )

    # Обработка кнопки "О компании HanExport"
    elif user_message == "ℹ️ О компании HanExport":
        about_message = (
            "HanExport — это компания, специализирующаяся на экспорте автомобилей "
            "из Южной Кореи в Россию. 🚘 Мы предлагаем широкий ассортимент автомобилей "
            "по конкурентоспособным ценам и гарантируем высокий уровень обслуживания. 🌟"
        )
        bot.send_message(message.chat.id, about_message)

    # Обработка кнопки "Наш Telegram-канал"
    elif user_message == "📢 Наш Telegram-канал":
        bot.send_message(
            message.chat.id, "Перейдите по ссылке на наш канал: https://t.me/hanexport1"
        )

    # Обработка кнопки "Посетить наш Instagram"
    elif user_message == "📸 Посетить наш Instagram":
        bot.send_message(
            message.chat.id,
            "Посетите наш Instagram по ссылке: https://www.instagram.com/han.export/",
        )

    # Проверка, является ли сообщение ссылкой на автомобиль
    elif "encar.com" in user_message:
        calculate_cost(user_message, message)
    else:
        send_error_message(
            message,
            "⚠️ Пожалуйста, выберите действие из меню или введите действительную ссылку на авто с сайта www.encar.com.",
        )


def send_error_message(message, error_text):
    global last_error_message_id

    # Удаляем предыдущее сообщение об ошибке, если оно существует
    if last_error_message_id.get(message.chat.id):
        try:
            bot.delete_message(message.chat.id, last_error_message_id[message.chat.id])
        except Exception:
            pass  # Игнорируем ошибки, если сообщение уже удалено или не существует

    # Отправляем новое сообщение об ошибке и сохраняем его идентификатор
    error_message = bot.reply_to(message, error_text)
    last_error_message_id[message.chat.id] = error_message.id


# Настройка локали для форматирования чисел
locale.setlocale(locale.LC_ALL, "en_US.UTF-8")


# Функция для форматирования чисел
def format_number(number):
    return locale.format_string("%d", number, grouping=True)


# Функция для расчета возраста автомобиля по году выпуска
def calculate_age(year):
    current_year = 2024  # Замените на актуальный год, если потребуется
    return current_year - int(year)


# Функция для парсинга данных с сайта encar.com
def get_car_info(url):
    # Отправляем запрос на страницу автомобиля
    response = requests.get(url)

    print(response)

    # Проверяем успешность запроса
    if response.status_code == 200:
        # Создаем объект BeautifulSoup для парсинга HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Парсинг данных: цена, год, объем двигателя
        try:
            # Извлекаем год автомобиля (второй li со span с классом blind)
            year_li = soup.select_one("ul.list_carinfo li:nth-child(2) span.blind")
            year = int(year_li.text.strip()) if year_li else None
            print(f"Год автомобиля: {year}")  # Отладочное сообщение

            # Извлекаем объем двигателя (пятый li)
            engine_li = soup.select_one("ul.list_carinfo li:nth-child(5)")
            engine_volume = engine_li.text.strip() if engine_li else None
            print(f"Объем двигателя: {engine_volume}")  # Отладочное сообщение

            # Извлекаем стоимость автомобиля (span с классом txt_num)
            price_span = soup.select_one("span.txt_num")
            price = price_span.text.strip().replace(",", "") if price_span else None
            print(f"Стоимость автомобиля: {price}")  # Отладочное сообщение

            # Возвращаем результат
            return {
                "year": year,
                "engine_volume": engine_volume,
                "price": int(price) if price else None,
            }
        except Exception as e:
            print(f"Ошибка при парсинге данных: {e}")
            return None
    else:
        print(f"Ошибка запроса: {response.status_code}")  # Отладочное сообщение
        return None


# Основная функция для расчета стоимости
def calculate_cost(link, message):
    # Уведомление о начале обработки
    bot.send_message(message.chat.id, "Данные переданы в обработку ⏳")

    # Получаем данные с сайта encar.com
    car_info = get_car_info(link)

    if car_info:
        year = car_info["year"]
        engine_volume = car_info["engine_volume"]
        price = car_info["price"]

        if year and engine_volume and price:
            # Форматирование объема двигателя
            engine_volume_formatted = f"{engine_volume} cc"

            # Форматирование возраста
            age_formatted = calculate_age(year)

            # Примерные расчеты
            delivery_fee = 1000  # Фиксированная стоимость доставки
            taxes = price * 0.1  # Примерные налоги (10%)
            total_cost = price + delivery_fee + taxes

            # Форматируем стоимость
            total_cost_formatted = format_number(total_cost)
            price_formatted = format_number(price)

            # Формирование сообщения с результатом
            result_message = (
                f"Возраст: {age_formatted} лет\n"
                f"Стоимость: {price_formatted} KRW\n"
                f"Объём двигателя: {engine_volume_formatted}\n\n"
                f"Стоимость автомобиля под ключ во Владивосток: {total_cost_formatted} RUB\n\n"
                f"🔗 [Ссылка на автомобиль]({link})\n\n"
                "Данное авто попадает под санкции, пожалуйста уточните возможность отправки в вашу страну у менеджера @hanexport11\n\n"
                'Стоимость "под ключ" включает в себя все расходы до г. Владивосток, а именно: '
                "оформление экспорта в Корее, фрахт, услуги брокера, склады временного хранения, "
                "прохождение лаборатории для получения СБКТС и таможенную пошлину.\n\n"
                "Актуальные курсы валют вы можете посмотреть в Меню.\n\n"
                "По вопросам заказа авто вы можете обратиться к нашему менеджеру @hanexport11\n\n"
                "🔗[Официальный телеграм канал](https://t.me/hanexport1)\n"
            )

            # Отправка сообщения с результатами
            bot.send_message(message.chat.id, result_message, parse_mode="Markdown")

            # Кнопки
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

            # Отправка кнопок под сообщением
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


# Обработка нажатия кнопки "📊 Детализация расчёта"
@bot.callback_query_handler(func=lambda call: call.data == "detail")
def handle_detail_query(call):
    # Примерные значения для детализации
    price_in_rub = format_number(111500000)  # Примерная цена автомобиля в рублях
    export_document_fee = format_number(
        0
    )  # Стоимость оформления экспортных документов и доставки
    broker_fees = format_number(100000)  # Брокерские расходы, СВХ, СБКТС
    customs_duty = format_number(8130000)  # Таможенные пошлины

    detail_message = (
        "📊 **Детализация расчёта**\n\n"
        f"**Стоимость автомобиля:** {price_in_rub} RUB\n"
        f"**Оформление экспортных документов и доставка:** {export_document_fee} RUB\n"
        f"**Брокерские расходы (СВХ, СБКТС):** {broker_fees} RUB\n"
        f"**Таможенные пошлины:** {customs_duty} RUB\n\n"
        "Итого: "
        + format_number(111500000 + 1000 + 11150000)
        + " RUB"  # Итоговая стоимость
    )

    bot.send_message(call.message.chat.id, detail_message, parse_mode="Markdown")

    # Кнопки после детализации
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            "🔍 Рассчитать стоимость другого автомобиля",
            callback_data="calculate_another",
        ),
    )
    keyboard.add(
        types.InlineKeyboardButton(
            "✉️ Связаться с менеджером", url="https://t.me/hanexport11"
        ),
    )

    bot.send_message(call.message.chat.id, "Что делаем дальше?", reply_markup=keyboard)
    bot.answer_callback_query(call.id)  # Подтверждаем обработку нажатия кнопки


# Обработка нажатия кнопки "🔍 Рассчитать стоимость другого автомобиля"
@bot.callback_query_handler(func=lambda call: call.data == "calculate_another")
def handle_calculate_another(call):
    bot.send_message(
        call.message.chat.id,
        "Пожалуйста, введите ссылку на автомобиль с сайта www.encar.com:",
    )
    bot.answer_callback_query(call.id)  # Подтверждаем обработку нажатия кнопки


# Запуск бота
if __name__ == "__main__":
    bot.polling(none_stop=True)
