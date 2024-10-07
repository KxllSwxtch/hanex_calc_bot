import telebot
from telebot import types

# Замените 'YOUR_TOKEN' на токен вашего бота
API_TOKEN = 'YOUR_TOKEN'
bot = telebot.TeleBot(API_TOKEN)

# Функция для создания клавиатуры с кнопкой "Start"
def start_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    start_button = types.KeyboardButton("Start")
    keyboard.add(start_button)
    return keyboard

# Функция для старта
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_first_name = message.from_user.first_name
    welcome_message = (
        f"Здравствуйте, {user_first_name}!\n"
        "Я бот для расчета стоимости авто до Владивостока!\n\n"
        "Нажмите кнопку 'Start', чтобы продолжить."
    )
    bot.send_message(message.chat.id, welcome_message, reply_markup=start_keyboard())
    
    # Описание бота, отображаемое при отсутствии истории переписки
    bot.send_message(message.chat.id, 
                     "What can this bot do?\n"
                     "Этот бот поможет вам рассчитать стоимость автомобилей, "
                     "импортируемых из Южной Кореи в Владивосток, включая все расходы.")

# Обработка кнопки "Start"
@bot.message_handler(func=lambda message: message.text == "Start")
def start_action(message):
    welcome_message = (
        "Просто отправьте мне ссылку на авто, с сайта www.encar.com "
        "и я рассчитаю вам конечную стоимость автомобиля с учетом всех расходов до Владивостока. ✅"
    )
    bot.send_message(message.chat.id, welcome_message)

# Обработка входящих сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_message = message.text
    
    # Проверка, является ли сообщение ссылкой на автомобиль
    if "encar.com" in user_message:
        calculate_cost(user_message, message)
    else:
        bot.reply_to(message, "Пожалуйста, введите действительную ссылку на авто с сайта www.encar.com.")

def calculate_cost(link, message):
    # Здесь будет реализация расчета стоимости автомобиля
    # Для примера просто отправим ссылку обратно
    bot.reply_to(message, f"Вы ввели ссылку: {link}. Теперь происходит расчет...")

# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)
